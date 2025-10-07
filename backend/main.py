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

try:
    from database_unified import (
        init_db, get_db, User, Organization, Borrower, Deal, Document,
        UnderwritingResult, Report, AuditLog
    )
except:
    # Fallback to SQLite database for local testing
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
from loan_schemas import LoanApplicationCreate, LoanApplicationResponse, LoanStatsResponse

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

# Loans endpoint (alias for deals - for frontend compatibility)
@app.get("/api/loans")
def list_loans(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all loans (deals) for the user's organization"""
    # Reuse the deals logic
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
            "company_name": borrower.name if borrower else "Unknown",  # Add company_name for frontend
            "loan_amount": deal.loan_amount,
            "status": deal.status,
            "loan_purpose": deal.deal_type,  # Map deal_type to loan_purpose
            "created_at": deal.created_at.isoformat()
        })
    
    return result  # Return array directly (not wrapped in {"items"})

@app.get("/api/loans/stats")
def get_loan_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get loan statistics for the dashboard"""
    deals = db.query(Deal).filter(Deal.organization_id == current_user.organization_id).all()
    
    total_loans = len(deals)
    total_volume = sum(deal.loan_amount or 0 for deal in deals)
    pending_loans = len([d for d in deals if d.status == "pending"])
    approved_loans = len([d for d in deals if d.status == "approved"])
    rejected_loans = len([d for d in deals if d.status == "rejected"])
    average_loan_amount = total_volume / total_loans if total_loans > 0 else 0
    
    return {
        "total_loans": total_loans,
        "total_volume": total_volume,
        "pending_loans": pending_loans,
        "approved_loans": approved_loans,
        "rejected_loans": rejected_loans,
        "average_loan_amount": average_loan_amount
    }

@app.post("/api/loans")
def create_loan(
    loan_data: LoanApplicationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new loan application from frontend"""
    try:
        # Create borrower with full information
        borrower = Borrower(
            organization_id=current_user.organization_id,
            name=loan_data.borrower_name,
            entity_type="business" if loan_data.borrower_company else "individual",
            email=loan_data.borrower_email,
            phone=loan_data.borrower_phone,
            address=f"{loan_data.property_address}, {loan_data.property_city}, {loan_data.property_state}"
        )
        db.add(borrower)
        db.flush()
        
        # Create deal with comprehensive data
        deal = Deal(
            organization_id=current_user.organization_id,
            borrower_id=borrower.id,
            deal_type=loan_data.loan_type,
            loan_amount=loan_data.loan_amount,
            appraised_value=loan_data.property_value,
            interest_rate=0.065,  # Default rate
            amortization_months=loan_data.term_months,
            balloon_months=loan_data.term_months,
            status="pending",
            metadata=json.dumps({
                "loan_purpose": loan_data.loan_purpose,
                "property_type": loan_data.property_type,
                "property_address": loan_data.property_address,
                "property_city": loan_data.property_city,
                "property_state": loan_data.property_state,
                "property_zip": loan_data.property_zip,
                "purchase_price": loan_data.purchase_price,
                "annual_revenue": loan_data.annual_revenue,
                "net_income": loan_data.net_income,
                "monthly_debt_service": loan_data.monthly_debt_service,
                "down_payment": loan_data.down_payment,
                "borrower_credit_score": loan_data.borrower_credit_score,
                "years_in_business": loan_data.years_in_business,
                "borrower_company": loan_data.borrower_company
            })
        )
        db.add(deal)
        db.commit()
        db.refresh(deal)
        
        # Log the creation
        audit_log = AuditLog(
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            action="loan_created",
            entity_type="deal",
            entity_id=deal.id,
            details=f"Created loan application for {borrower.name}"
        )
        db.add(audit_log)
        db.commit()
        
        return {
            "id": deal.id,
            "borrower_name": borrower.name,
            "company_name": loan_data.borrower_company or borrower.name,
            "loan_amount": deal.loan_amount,
            "loan_type": deal.deal_type,
            "loan_purpose": loan_data.loan_purpose,
            "status": deal.status,
            "property_address": loan_data.property_address,
            "property_city": loan_data.property_city,
            "property_state": loan_data.property_state,
            "created_at": deal.created_at.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create loan: {str(e)}")

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

# AI Advisor endpoint
class AIAskRequest(BaseModel):
    question: str
    loan_id: Optional[str] = None

@app.post("/api/ai/ask")
def ai_ask(
    request: AIAskRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """AI Advisor endpoint - answers commercial lending questions"""
    
    # Knowledge base for commercial lending
    knowledge_base = {
        "documents": [
            "For commercial loans, you typically need: 1) Business tax returns (2-3 years), 2) Personal tax returns of guarantors, 3) Business financial statements (P&L, Balance Sheet), 4) Rent roll (for investment properties), 5) Purchase agreement, 6) Property appraisal, 7) Business plan, 8) Personal financial statement (PFS)",
            "Loan-to-Value (LTV) is calculated as: LTV = (Loan Amount / Appraised Property Value) × 100. For example, a $750,000 loan on a $1,000,000 property = 75% LTV. Most commercial lenders require LTV below 80% for owner-occupied and 75% for investment properties.",
            "Credit score requirements vary by loan type. For SBA 7(a) loans, minimum is typically 680. For conventional commercial loans, 680-700+ is preferred. For owner-occupied CRE, 700+ is ideal. Lower scores may require higher down payments or personal guarantees.",
            "Debt Service Coverage Ratio (DSCR) measures cash flow available to cover debt payments. Formula: DSCR = Net Operating Income / Annual Debt Service. A DSCR of 1.25 means the property generates 25% more income than needed for debt payments. Most lenders require minimum 1.20-1.25 DSCR.",
            "Owner-occupied CRE is when the business owner occupies 51%+ of the property for their business operations. Investment property is purchased solely for rental income. Owner-occupied typically gets better rates and terms (SBA 7(a) eligible) while investment properties have stricter requirements.",
            "Global DSCR considers all income sources (business income, rental income, personal income) and all debt obligations (existing debts + new loan). Formula: Global DSCR = (Total Income from All Sources) / (Total Debt Service from All Obligations). This provides a complete picture of repayment ability."
        ]
    }
    
    # Simple keyword matching for demo
    question_lower = request.question.lower()
    
    if "document" in question_lower or "need" in question_lower:
        answer = knowledge_base["documents"][0]
    elif "ltv" in question_lower or "loan-to-value" in question_lower or "loan to value" in question_lower:
        answer = knowledge_base["documents"][1]
    elif "credit score" in question_lower:
        answer = knowledge_base["documents"][2]
    elif "dscr" in question_lower or "debt service" in question_lower:
        answer = knowledge_base["documents"][3]
    elif "owner-occupied" in question_lower or "investment property" in question_lower:
        answer = knowledge_base["documents"][4]
    elif "global" in question_lower:
        answer = knowledge_base["documents"][5]
    else:
        answer = "I'm an AI advisor specialized in commercial loan underwriting. I can help you with questions about:\n\n• Required documents for commercial loans\n• Financial ratios (DSCR, LTV, Debt Yield)\n• Credit requirements and guidelines\n• Property types and loan structures\n• Risk assessment and underwriting criteria\n\nPlease ask me a specific question about commercial lending!"
    
    # Log the interaction
    audit_log = AuditLog(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="ai_query",
        entity_type="ai_advisor",
        entity_id="advisor_1",
        details=f"Question: {request.question[:100]}"
    )
    db.add(audit_log)
    db.commit()
    
    return {"answer": answer, "confidence": 0.95}

# Mount static files and serve frontend
frontend_dist = os.path.join(os.path.dirname(__file__), "static")
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
