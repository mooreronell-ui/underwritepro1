from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, timedelta
import json
import os
import shutil

from database import (
    init_db, get_db, User, Organization, Borrower, Deal, Document,
    UnderwritingResult, Report, AuditLog
)
from auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_active_user, require_role
)
from underwriting import UnderwritingEngine, UnderwritingRequest, FinancialData, LoanTerms
from document_parser import DocumentParser
from report_generator import ReportGenerator

# Import enhanced routes (AI, Communication, Workflows)
try:
    from enhanced_routes import ai_router, communication_router, workflow_router
    ENHANCED_ROUTES_AVAILABLE = True
except ImportError:
    ENHANCED_ROUTES_AVAILABLE = False
    print("Warning: Enhanced routes not available")

# Initialize FastAPI app
app = FastAPI(
    title="UnderwritePro SaaS API",
    version="2.0.0",
    description="F500-level Commercial Loan Underwriting Platform"
)

# CORS middleware - Allow all origins for now
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads and reports directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("reports", exist_ok=True)

# Initialize database
init_db()

# Register enhanced routes if available
if ENHANCED_ROUTES_AVAILABLE:
    app.include_router(ai_router)
    app.include_router(communication_router)
    app.include_router(workflow_router)
    print("✅ Enhanced routes registered (AI, Communication, Workflows)")

# Pydantic models for requests/responses
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    organization_name: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    organization_id: str

class Token(BaseModel):
    access_token: str
    token_type: str

class BorrowerCreate(BaseModel):
    name: str
    entity_type: str = "individual"
    tax_id: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

class DealCreate(BaseModel):
    borrower_id: str
    deal_type: str
    loan_amount: Optional[float] = None
    appraised_value: Optional[float] = None
    interest_rate: float = 0.065
    amortization_months: int = 240
    balloon_months: Optional[int] = 60

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

# Health check
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Authentication endpoints
@app.post("/api/auth/register", response_model=UserResponse, status_code=201)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user and organization"""
    
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
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        organization_id=user.organization_id
    )

@app.post("/api/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and get access token"""
    
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
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
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        organization_id=current_user.organization_id
    )

# Borrower endpoints
@app.post("/api/borrowers", status_code=201)
def create_borrower(
    borrower_data: BorrowerCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new borrower"""
    
    borrower = Borrower(**borrower_data.dict())
    db.add(borrower)
    db.commit()
    db.refresh(borrower)
    
    return {"id": borrower.id, "name": borrower.name}

@app.get("/api/borrowers")
def list_borrowers(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all borrowers"""
    borrowers = db.query(Borrower).all()
    return {"items": [{"id": b.id, "name": b.name, "entity_type": b.entity_type} for b in borrowers]}

# Deal endpoints
@app.post("/api/deals", response_model=DealResponse, status_code=201)
def create_deal(
    deal_data: DealCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new deal"""
    
    deal = Deal(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        **deal_data.dict()
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    
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

@app.get("/api/deals")
def list_deals(
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
def get_deal(
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
    uw_results = db.query(UnderwritingResult).filter(UnderwritingResult.deal_id == deal_id).order_by(UnderwritingResult.calculated_at.desc()).first()
    
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
        "documents": [{"id": d.id, "filename": d.filename, "type": d.document_type, "parsed": d.parsed} for d in documents],
        "underwriting_result": {
            "dscr": uw_results.dscr_base,
            "ltv": uw_results.ltv,
            "recommendation": json.loads(uw_results.calculation_trace).get("recommendation") if uw_results.calculation_trace else None
        } if uw_results else None,
        "created_at": deal.created_at.isoformat()
    }

# Document endpoints
@app.post("/api/deals/{deal_id}/documents")
async def upload_document(
    deal_id: str,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload a document to a deal"""
    
    deal = db.query(Deal).filter(
        Deal.id == deal_id,
        Deal.organization_id == current_user.organization_id
    ).first()
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    # Save file
    file_path = f"uploads/{deal_id}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Create document record
    document = Document(
        deal_id=deal_id,
        document_type=document_type,
        filename=file.filename,
        file_path=file_path,
        file_size=os.path.getsize(file_path),
        uploaded_by=current_user.id
    )
    db.add(document)
    
    # Update deal status
    if deal.status == "intake":
        deal.status = "parsing"
    
    db.commit()
    db.refresh(document)
    
    return {"id": document.id, "filename": document.filename, "message": "Document uploaded successfully"}

@app.post("/api/deals/{deal_id}/documents/{document_id}/parse")
def parse_document(
    deal_id: str,
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Parse an uploaded document"""
    
    document = db.query(Document).filter(Document.id == document_id, Document.deal_id == deal_id).first()
    
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
    
    return {
        "document_id": document_id,
        "fields": [f.dict() for f in parsed.fields],
        "confidence_score": parsed.confidence_score
    }

# Underwriting endpoints
@app.post("/api/deals/{deal_id}/underwrite")
def underwrite_deal(
    deal_id: str,
    request_data: UnderwriteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Run underwriting analysis on a deal"""
    
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
    
    financial_data = FinancialData(**request_data.financial_data)
    
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
        calculated_by=current_user.id
    )
    db.add(uw_result)
    
    # Update deal status
    deal.status = "complete"
    db.commit()
    
    return result.dict()

# Report endpoints
@app.post("/api/deals/{deal_id}/reports/{report_type}")
def generate_report(
    deal_id: str,
    report_type: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate a report for a deal"""
    
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
        raise HTTPException(status_code=400, detail="No underwriting results found. Please run underwriting first.")
    
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
        "recommendation": "APPROVE"
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
    
    return {"report_id": report.id, "file_path": output_path, "message": "Report generated successfully"}

# Mount static files and serve frontend
frontend_dist = "../frontend/dist"
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
