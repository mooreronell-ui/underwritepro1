"""
UnderwritePro SaaS - Production Application
Enterprise-grade FastAPI application with full error handling,
logging, rate limiting, and monitoring
"""
import os
import sys
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Depends, File, UploadFile, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
from sqlalchemy.orm import Session
import shutil
import uuid

# Load environment variables
load_dotenv(".env.production")

# Import local modules
from database_prod import get_db, init_db, check_db_connection, get_pool_status, engine, Base
from database import User, Organization, Deal, Document, FinancialData, UnderwritingResult
from auth import get_password_hash, verify_password, create_access_token, get_current_active_user
from underwriting import UnderwritingEngine
from document_parser import DocumentParser
from report_generator import ReportGenerator

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
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
        # Check database connection
        if not check_db_connection():
            logger.error("Failed to connect to database")
            raise Exception("Database connection failed")
        
        # Initialize database tables
        init_db()
        logger.info("Database initialized successfully")
        
        # Create uploads directory
        os.makedirs("uploads", exist_ok=True)
        
        logger.info("UnderwritePro SaaS started successfully")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down UnderwritePro SaaS...")
    engine.dispose()
    logger.info("Shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="UnderwritePro API",
    description="Commercial Loan Underwriting SaaS Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."}
    )

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        
        # Log response
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Response: {response.status_code} - Duration: {duration:.3f}s"
        )
        
        return response
    except Exception as e:
        logger.error(f"Request failed: {e}", exc_info=True)
        raise

# ==================== Health & Monitoring ====================

@app.get("/api/health")
@limiter.limit("100/minute")
async def health_check(request: Request):
    """Health check endpoint for load balancers"""
    db_status = check_db_connection()
    pool_status = get_pool_status()
    
    return {
        "status": "healthy" if db_status else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected" if db_status else "disconnected",
        "pool": pool_status
    }

@app.get("/api/metrics")
@limiter.limit("10/minute")
async def metrics(request: Request):
    """Metrics endpoint for monitoring"""
    return {
        "pool_status": get_pool_status(),
        "timestamp": datetime.utcnow().isoformat()
    }

# ==================== Authentication ====================

@app.post("/api/auth/register", status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    organization_name: str = Form(...),
    db: Session = Depends(get_db)
):
    """Register a new user"""
    try:
        # Check if user exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create organization
        org = Organization(
            id=str(uuid.uuid4()),
            name=organization_name
        )
        db.add(org)
        db.flush()
        
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            organization_id=org.id,
            role="admin"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"New user registered: {email}")
        
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "message": "Registration successful"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/api/auth/login")
@limiter.limit("10/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login and get access token"""
    try:
        user = db.query(User).filter(User.email == form_data.username).first()
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password"
            )
        
        access_token = create_access_token(data={"sub": user.email})
        
        logger.info(f"User logged in: {user.email}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Login failed")

@app.get("/api/auth/me")
@limiter.limit("100/minute")
async def get_current_user_info(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "organization_id": current_user.organization_id
    }

# ==================== Deals ====================

@app.post("/api/deals", status_code=201)
@limiter.limit("30/minute")
async def create_deal(
    request: Request,
    borrower_name: str = Form(...),
    entity_type: str = Form(...),
    deal_type: str = Form(...),
    loan_amount: float = Form(...),
    appraised_value: float = Form(...),
    interest_rate: float = Form(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new deal"""
    try:
        deal_id = str(uuid.uuid4())
        
        deal = Deal(
            id=deal_id,
            organization_id=current_user.organization_id,
            borrower_name=borrower_name,
            entity_type=entity_type,
            deal_type=deal_type,
            loan_amount=loan_amount,
            appraised_value=appraised_value,
            interest_rate=interest_rate,
            status="intake",
            created_by=current_user.id
        )
        db.add(deal)
        db.commit()
        db.refresh(deal)
        
        logger.info(f"Deal created: {deal_id} by {current_user.email}")
        
        return {
            "id": deal.id,
            "borrower_name": deal.borrower_name,
            "status": deal.status
        }
    except Exception as e:
        logger.error(f"Deal creation failed: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Deal creation failed")

@app.get("/api/deals")
@limiter.limit("100/minute")
async def get_deals(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all deals for current user's organization"""
    try:
        deals = db.query(Deal).filter(
            Deal.organization_id == current_user.organization_id
        ).order_by(Deal.created_at.desc()).all()
        
        return [
            {
                "id": d.id,
                "borrower_name": d.borrower_name,
                "deal_type": d.deal_type,
                "loan_amount": d.loan_amount,
                "status": d.status,
                "created_at": d.created_at.isoformat() if d.created_at else None
            }
            for d in deals
        ]
    except Exception as e:
        logger.error(f"Failed to fetch deals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch deals")

@app.get("/api/deals/{deal_id}")
@limiter.limit("100/minute")
async def get_deal(
    request: Request,
    deal_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get deal details"""
    try:
        deal = db.query(Deal).filter(
            Deal.id == deal_id,
            Deal.organization_id == current_user.organization_id
        ).first()
        
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        # Get documents
        documents = db.query(Document).filter(Document.deal_id == deal_id).all()
        
        # Get underwriting result
        underwriting = db.query(UnderwritingResult).filter(
            UnderwritingResult.deal_id == deal_id
        ).first()
        
        return {
            "id": deal.id,
            "borrower_name": deal.borrower_name,
            "entity_type": deal.entity_type,
            "deal_type": deal.deal_type,
            "loan_amount": deal.loan_amount,
            "appraised_value": deal.appraised_value,
            "interest_rate": deal.interest_rate,
            "status": deal.status,
            "created_at": deal.created_at.isoformat() if deal.created_at else None,
            "documents": [
                {
                    "id": d.id,
                    "filename": d.filename,
                    "type": d.document_type,
                    "parsed": d.parsed
                }
                for d in documents
            ],
            "underwriting_result": {
                "dscr": underwriting.dscr,
                "ltv": underwriting.ltv,
                "recommendation": underwriting.recommendation
            } if underwriting else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch deal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch deal")

# ==================== Document Upload ====================

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
        # Validate deal
        deal = db.query(Deal).filter(
            Deal.id == deal_id,
            Deal.organization_id == current_user.organization_id
        ).first()
        
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        # Validate file size
        max_size = int(os.getenv("MAX_UPLOAD_SIZE_MB", 10)) * 1024 * 1024
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > max_size:
            raise HTTPException(status_code=413, detail="File too large")
        
        # Save file
        file_path = f"uploads/{deal_id}_{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Create document record
        document = Document(
            id=str(uuid.uuid4()),
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
        logger.error(f"Document upload failed: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Document upload failed")

# Serve frontend
app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_prod:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
