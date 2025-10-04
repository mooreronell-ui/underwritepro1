"""
UnderwritePro SaaS - Production Application
Enterprise-grade FastAPI application with security, monitoring, and scalability
"""
import os
import sys
import logging
import json
import shutil
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, Request, HTTPException, Depends, File, UploadFile, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

# Import local modules
from database_unified import (
    get_db, init_db, check_db_connection, get_pool_status,
    User, Organization, Borrower, Deal, Document, UnderwritingResult, Report, AuditLog, FinancialData
)
from auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_active_user, require_role
)
from underwriting import UnderwritingEngine, UnderwritingRequest, FinancialData as UWFinancialData, LoanTerms
from document_parser import DocumentParser
from report_generator import ReportGenerator
from security import validate_file_upload, SECURITY_HEADERS, PasswordPolicy

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    logger.info("Starting UnderwritePro SaaS...")
    
    # Startup
    try:
        # Debug: Log environment variables related to database
        logger.info("=== Environment Check ===")
        logger.info(f"DATABASE_URL exists: {bool(os.getenv('DATABASE_URL'))}")
        logger.info(f"DATABASE_PUBLIC_URL exists: {bool(os.getenv('DATABASE_PUBLIC_URL'))}")
        logger.info(f"PORT: {os.getenv('PORT', 'not set')}")
        logger.info(f"RAILWAY_ENVIRONMENT: {os.getenv('RAILWAY_ENVIRONMENT', 'not set')}")
        logger.info("========================")
        
        # Create necessary directories first
        os.makedirs("uploads", exist_ok=True)
        os.makedirs("reports", exist_ok=True)
        logger.info("Directories created successfully")
        
        # Try to connect to database (but don't crash if it fails immediately)
        # Railway sometimes takes a moment to link services
        db_connected = check_db_connection()
        if db_connected:
            # Initialize database tables
            init_db()
            logger.info("Database initialized successfully")
        else:
            logger.warning("Database connection not available at startup - will retry on first request")
            logger.warning("This is normal if Railway is still linking services")
        
        logger.info("UnderwritePro SaaS started successfully")
    except Exception as e:
        logger.error(f"Startup error (non-fatal): {e}")
        logger.info("Application will continue and retry database connection on first request")
    
    yield
    
    # Shutdown
    logger.info("Shutting down UnderwritePro SaaS...")

# Initialize FastAPI app
app = FastAPI(
    title="UnderwritePro SaaS API - Complete Edition",
    version="4.0.0",
    description="Complete Commercial Lending Ecosystem with AI Bots, LMS, Practice Mode, Gamification, Communication Automation, and Workflow Management",
    lifespan=lifespan
)

# Import enhanced routes
try:
    from enhanced_routes import communication_router, ai_router, workflow_router
    from subscription_routes import router as subscription_router
    from new_features_routes import router as new_features_router
    app.include_router(communication_router)
    app.include_router(ai_router)
    app.include_router(workflow_router)
    app.include_router(subscription_router)
    app.include_router(new_features_router, prefix="/api", tags=["New Features"])
    logger.info("Enhanced platform features loaded successfully")
except Exception as e:
    logger.warning(f"Enhanced features not available: {e}")

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    return response

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = datetime.utcnow()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        
        # Log response
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Response: {response.status_code} - Duration: {duration:.3f}s")
        
        return response
    except Exception as e:
        logger.error(f"Request failed: {e}")
        raise

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=100)
    organization_name: str = Field(..., min_length=1, max_length=100)

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    organization_id: str

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class BorrowerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    entity_type: str = Field(..., pattern=r'^(individual|llc|corp|partnership)$')
    tax_id: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None

class DealCreate(BaseModel):
    borrower_id: str
    deal_type: str = Field(..., pattern=r'^(purchase|refi)$')
    loan_amount: Optional[float] = Field(None, gt=0, lt=1000000000)
    appraised_value: Optional[float] = Field(None, gt=0, lt=1000000000)
    interest_rate: float = Field(0.065, gt=0, lt=1)
    amortization_months: int = Field(240, gt=0, lt=600)
    balloon_months: Optional[int] = Field(60, gt=0, lt=600)

class DealResponse(BaseModel):
    id: str
    borrower_id: str
    deal_type: str
    status: str
    loan_amount: Optional[float]
    appraised_value: Optional[float]
    interest_rate: float
    created_at: datetime

class UnderwriteRequest(BaseModel):
    financial_data: dict
    stress_test: bool = False

# ==================== Health & Monitoring ====================

@app.get("/")
async def root():
    """Root endpoint for Railway health checks"""
    return {
        "app": "UnderwritePro SaaS",
        "version": "4.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def simple_health():
    """Simple health check for Railway"""
    return {"status": "ok"}

@app.get("/api/health")
@limiter.limit("1000/minute")
async def health_check(request: Request):
    """Detailed health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected" if check_db_connection() else "disconnected"
    }

@app.get("/api/metrics")
@limiter.limit("10/minute")
async def get_metrics(
    request: Request,
    current_user: User = Depends(require_role(["admin"]))
):
    """Get application metrics (admin only)"""
    pool_status = get_pool_status()
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "database_pool": pool_status,
        "environment": os.getenv("ENVIRONMENT", "production")
    }

# ==================== Authentication ====================

@app.post("/api/auth/register", response_model=UserResponse, status_code=201)
@limiter.limit("20/minute")
async def register(request: Request, user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user and organization"""
    try:
        # Validate password
        is_valid, error = PasswordPolicy.validate(user_data.password)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error)
        
        # Check if user exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create organization
        org = Organization(
            name=user_data.organization_name,
            plan="starter"
        )
        db.add(org)
        db.flush()
        
        # Create user
        user = User(
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            role="broker",
            organization_id=org.id
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"New user registered: {user.email}")
        
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            organization_id=user.organization_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/api/auth/login", response_model=Token)
@limiter.limit("30/minute")
async def login_json(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Login with JSON (email/password) and get access token"""
    try:
        user = db.query(User).filter(User.email == login_data.email).first()
        if not user or not verify_password(login_data.password, user.password_hash):
            logger.warning(f"Failed login attempt for: {login_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Create access token
        access_token = create_access_token(data={"sub": user.id})
        
        logger.info(f"User logged in: {user.email}")
        
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.post("/api/auth/login/form", response_model=Token)
@limiter.limit("30/minute")
async def login_form(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login and get access token"""
    try:
        user = db.query(User).filter(User.email == form_data.username).first()
        if not user or not verify_password(form_data.password, user.password_hash):
            logger.warning(f"Failed login attempt for: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Create access token
        access_token = create_access_token(data={"sub": user.id})
        
        logger.info(f"User logged in: {user.email}")
        
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.get("/api/auth/me", response_model=UserResponse)
@limiter.limit("60/minute")
async def get_current_user_info(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        organization_id=current_user.organization_id
    )

# ==================== Borrowers ====================

@app.post("/api/borrowers", status_code=201)
@limiter.limit("30/minute")
async def create_borrower(
    request: Request,
    borrower_data: BorrowerCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new borrower"""
    try:
        borrower = Borrower(**borrower_data.dict())
        db.add(borrower)
        db.commit()
        db.refresh(borrower)
        
        logger.info(f"Borrower created: {borrower.name} by user {current_user.email}")
        
        return {"id": borrower.id, "name": borrower.name}
    except Exception as e:
        logger.error(f"Failed to create borrower: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create borrower")

@app.get("/api/borrowers")
@limiter.limit("60/minute")
async def list_borrowers(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all borrowers"""
    borrowers = db.query(Borrower).all()
    return {
        "items": [
            {"id": b.id, "name": b.name, "entity_type": b.entity_type}
            for b in borrowers
        ]
    }

# ==================== Deals ====================

@app.post("/api/deals", response_model=DealResponse, status_code=201)
@limiter.limit("30/minute")
async def create_deal(
    request: Request,
    deal_data: DealCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new deal"""
    try:
        deal = Deal(
            organization_id=current_user.organization_id,
            created_by=current_user.id,
            **deal_data.dict()
        )
        db.add(deal)
        db.commit()
        db.refresh(deal)
        
        logger.info(f"Deal created: {deal.id} by user {current_user.email}")
        
        return DealResponse(
            id=deal.id,
            borrower_id=deal.borrower_id,
            deal_type=deal.deal_type,
            status=deal.status,
            loan_amount=deal.loan_amount,
            appraised_value=deal.appraised_value,
            interest_rate=deal.interest_rate,
            created_at=deal.created_at
        )
    except Exception as e:
        logger.error(f"Failed to create deal: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create deal")

@app.get("/api/deals")
@limiter.limit("60/minute")
async def list_deals(
    request: Request,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all deals for the user's organization"""
    query = db.query(Deal).filter(Deal.organization_id == current_user.organization_id)
    
    if status:
        query = query.filter(Deal.status == status)
    
    deals = query.order_by(Deal.created_at.desc()).all()
    
    result = []
    for deal in deals:
        borrower = db.query(Borrower).filter(Borrower.id == deal.borrower_id).first()
        result.append({
            "id": deal.id,
            "borrower_name": borrower.name if borrower else "Unknown",
            "deal_type": deal.deal_type,
            "status": deal.status,
            "loan_amount": deal.loan_amount,
            "created_at": deal.created_at.isoformat()
        })
    
    return {"items": result}

@app.get("/api/deals/{deal_id}")
@limiter.limit("60/minute")
async def get_deal(
    request: Request,
    deal_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get deal details"""
    deal = db.query(Deal).filter(
        Deal.id == deal_id,
        Deal.organization_id == current_user.organization_id
    ).first()
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    borrower = db.query(Borrower).filter(Borrower.id == deal.borrower_id).first()
    documents = db.query(Document).filter(Document.deal_id == deal_id).all()
    uw_results = db.query(UnderwritingResult).filter(
        UnderwritingResult.deal_id == deal_id
    ).order_by(UnderwritingResult.calculated_at.desc()).first()
    
    return {
        "id": deal.id,
        "borrower": {"id": borrower.id, "name": borrower.name} if borrower else None,
        "deal_type": deal.deal_type,
        "status": deal.status,
        "loan_amount": deal.loan_amount,
        "appraised_value": deal.appraised_value,
        "interest_rate": deal.interest_rate,
        "amortization_months": deal.amortization_months,
        "balloon_months": deal.balloon_months,
        "documents": [
            {"id": d.id, "filename": d.filename, "type": d.document_type, "parsed": d.parsed}
            for d in documents
        ],
        "underwriting_result": {
            "dscr": uw_results.dscr_base,
            "ltv": uw_results.ltv,
            "risk_rating": uw_results.risk_rating,
            "recommendation": uw_results.recommendation
        } if uw_results else None,
        "created_at": deal.created_at.isoformat()
    }

# ==================== Documents ====================

@app.post("/api/deals/{deal_id}/documents")
@limiter.limit("20/minute")
async def upload_document(
    request: Request,
    deal_id: str,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload a document to a deal"""
    try:
        # Verify deal exists and user has access
        deal = db.query(Deal).filter(
            Deal.id == deal_id,
            Deal.organization_id == current_user.organization_id
        ).first()
        
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        # Read file content for validation
        file_content = await file.read()
        file_size = len(file_content)
        
        # Validate file
        validate_file_upload(file.filename, file.content_type, file_size, max_size_mb=10)
        
        # Save file
        file_path = f"uploads/{deal_id}_{uuid.uuid4()}_{file.filename}"
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # Create document record
        document = Document(
            deal_id=deal_id,
            document_type=document_type,
            filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            uploaded_by=current_user.id
        )
        db.add(document)
        
        # Update deal status
        if deal.status == "intake":
            deal.status = "parsing"
        
        db.commit()
        db.refresh(document)
        
        logger.info(f"Document uploaded: {file.filename} to deal {deal_id}")
        
        return {
            "id": document.id,
            "filename": document.filename,
            "message": "Document uploaded successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Document upload failed")

@app.post("/api/deals/{deal_id}/documents/{document_id}/parse")
@limiter.limit("10/minute")
async def parse_document(
    request: Request,
    deal_id: str,
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Parse an uploaded document"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.deal_id == deal_id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Parse document
        parsed = DocumentParser.parse_document(document.file_path, document.document_type)
        
        # Update document with parsed data
        document.parsed = True
        document.parsed_data = json.dumps({
            "fields": [f.dict() for f in parsed.fields],
            "confidence_score": parsed.confidence_score
        })
        document.confidence_score = parsed.confidence_score
        
        db.commit()
        
        logger.info(f"Document parsed: {document.filename}")
        
        return {
            "document_id": document_id,
            "fields": [f.dict() for f in parsed.fields],
            "confidence_score": parsed.confidence_score
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document parsing failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Document parsing failed")

# ==================== Underwriting ====================

@app.post("/api/deals/{deal_id}/underwrite")
@limiter.limit("20/minute")
async def underwrite_deal(
    request: Request,
    deal_id: str,
    request_data: UnderwriteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Run underwriting analysis on a deal"""
    try:
        deal = db.query(Deal).filter(
            Deal.id == deal_id,
            Deal.organization_id == current_user.organization_id
        ).first()
        
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        # Build underwriting request
        loan_terms = LoanTerms(
            loan_amount=deal.loan_amount or 0,
            interest_rate=deal.interest_rate,
            amortization_months=deal.amortization_months,
            balloon_months=deal.balloon_months
        )
        
        financial_data = UWFinancialData(**request_data.financial_data)
        
        uw_request = UnderwritingRequest(
            loan_terms=loan_terms,
            financial_data=financial_data,
            appraised_value=deal.appraised_value or 0,
            stress_test=request_data.stress_test
        )
        
        # Run underwriting
        result = UnderwritingEngine.underwrite(uw_request)
        
        # Save result
        uw_result = UnderwritingResult(
            deal_id=deal_id,
            dscr_base=result.dscr_base,
            dscr_stressed=result.dscr_stressed,
            ltv=result.ltv,
            global_cash_flow=result.global_cash_flow,
            annual_debt_service=result.annual_debt_service,
            monthly_payment=result.monthly_payment,
            liquidity_months=result.liquidity_months,
            business_cash_flow=result.business_cash_flow,
            personal_income=result.personal_income,
            addbacks=json.dumps(result.addbacks),
            flags=json.dumps(result.flags),
            calculation_trace=json.dumps(result.calculation_trace),
            risk_rating=result.flags[0] if result.flags else "PASS",
            recommendation="APPROVE" if result.dscr_base >= 1.25 else "DECLINE",
            calculated_by=current_user.id
        )
        db.add(uw_result)
        
        # Update deal status
        deal.status = "complete"
        db.commit()
        
        logger.info(f"Underwriting completed for deal {deal_id}")
        
        return result.dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Underwriting failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Underwriting failed")

# ==================== Reports ====================

@app.post("/api/deals/{deal_id}/reports/{report_type}")
@limiter.limit("10/minute")
async def generate_report(
    request: Request,
    deal_id: str,
    report_type: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate a report for a deal"""
    try:
        deal = db.query(Deal).filter(
            Deal.id == deal_id,
            Deal.organization_id == current_user.organization_id
        ).first()
        
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        # Get borrower
        borrower = db.query(Borrower).filter(Borrower.id == deal.borrower_id).first()
        
        # Get underwriting result
        uw_result = db.query(UnderwritingResult).filter(
            UnderwritingResult.deal_id == deal_id
        ).order_by(UnderwritingResult.calculated_at.desc()).first()
        
        if not uw_result:
            raise HTTPException(
                status_code=400,
                detail="No underwriting results found. Please run underwriting first."
            )
        
        # Prepare data
        deal_data = {
            "borrower_name": borrower.name if borrower else "Unknown",
            "deal_type": deal.deal_type,
            "loan_amount": deal.loan_amount,
            "appraised_value": deal.appraised_value,
            "interest_rate": deal.interest_rate,
            "amortization_months": deal.amortization_months,
            "balloon_months": deal.balloon_months
        }
        
        uw_data = {
            "dscr_base": uw_result.dscr_base,
            "dscr_stressed": uw_result.dscr_stressed,
            "ltv": uw_result.ltv,
            "global_cash_flow": uw_result.global_cash_flow,
            "annual_debt_service": uw_result.annual_debt_service,
            "monthly_payment": uw_result.monthly_payment,
            "business_cash_flow": uw_result.business_cash_flow,
            "personal_income": uw_result.personal_income,
            "addbacks": json.loads(uw_result.addbacks) if uw_result.addbacks else {},
            "flags": json.loads(uw_result.flags) if uw_result.flags else [],
            "strengths": [],
            "risks": [],
            "mitigants": [],
            "recommendation": uw_result.recommendation or "APPROVE"
        }
        
        financial_data = {
            "business_net_income": uw_result.business_cash_flow,
            "depreciation": 0,
            "amortization": 0
        }
        
        # Generate report
        output_path = f"reports/{deal_id}_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        if report_type == "executive_summary":
            ReportGenerator.generate_executive_summary(deal_data, uw_data, output_path)
        elif report_type == "credit_memo":
            ReportGenerator.generate_credit_memo(deal_data, uw_data, financial_data, output_path)
        elif report_type == "stip_sheet":
            ReportGenerator.generate_stip_sheet(deal_data, output_path)
        else:
            raise HTTPException(status_code=400, detail="Invalid report type")
        
        # Save report record
        report = Report(
            deal_id=deal_id,
            report_type=report_type,
            file_path=output_path,
            file_size=os.path.getsize(output_path),
            generated_by=current_user.id
        )
        db.add(report)
        db.commit()
        
        logger.info(f"Report generated: {report_type} for deal {deal_id}")
        
        return {
            "report_id": report.id,
            "file_path": output_path,
            "message": "Report generated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Report generation failed")

# ==================== Static Files & Frontend ====================

# Mount static files and serve frontend
frontend_dist = "static"
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=f"{frontend_dist}/assets"), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the React frontend for all non-API routes"""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # Serve index.html for all other routes (React Router)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )
