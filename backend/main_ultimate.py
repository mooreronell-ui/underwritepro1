"""
UnderwritePro SaaS - Production Ultimate Edition
Enterprise-grade commercial loan underwriting platform
"""
from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import os
import json
import uuid
from decimal import Decimal

# Import database models
from database_unified import (
    init_db, get_db, User, Organization, Borrower, Deal, Document,
    UnderwritingResult, Report, AuditLog
)

# Import authentication
from auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_active_user, require_role
)

# Import loan schemas
from loan_schemas import LoanApplicationCreate, LoanApplicationResponse, LoanStatsResponse

# Import enterprise modules
from underwriting_engine_pro import (
    UnderwritingEnginePro, LoanRequest, BorrowerProfile, PropertyDetails,
    FinancialStatement
)
from document_processor_pro import DocumentProcessorPro, DocumentType
from report_generator_pro import ReportGeneratorPro
from ai_advisor_pro import AIAdvisorPro

# Initialize FastAPI app
app = FastAPI(
    title="UnderwritePro SaaS - Ultimate Edition",
    description="Enterprise Commercial Loan Underwriting Platform",
    version="3.0.0-ultimate"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize enterprise engines
underwriting_engine = UnderwritingEnginePro()
document_processor = DocumentProcessorPro()
report_generator = ReportGeneratorPro()
ai_advisor = AIAdvisorPro()

# Initialize database
init_db()

# Pydantic models for requests
class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str
    organization_name: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class AIAskRequest(BaseModel):
    question: str
    loan_id: Optional[str] = None
    context: Optional[Dict] = None

class UnderwritingRequest(BaseModel):
    loan_id: str

class ReportGenerationRequest(BaseModel):
    loan_id: str
    report_type: str  # "credit_memo" or "executive_summary"

# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "3.0.0-ultimate",
        "timestamp": datetime.now().isoformat(),
        "modules": {
            "underwriting_engine": "active",
            "document_processor": "active",
            "report_generator": "active",
            "ai_advisor": "active"
        }
    }

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/api/auth/register")
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create organization if provided
    org_id = None
    if user_data.organization_name:
        org = Organization(
            name=user_data.organization_name,
            subscription_tier="starter",
            subscription_status="trial"
        )
        db.add(org)
        db.flush()
        org_id = org.id
    
    # Create user
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        organization_id=org_id,
        role="admin" if org_id else "user"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {"message": "User registered successfully", "user_id": user.id}

@app.post("/api/auth/login")
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user"""
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        }
    }

# ============================================================================
# LOAN MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/loans")
def list_loans(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all loans for the user's organization"""
    query = db.query(Deal).filter(Deal.organization_id == current_user.organization_id)
    
    if status:
        query = query.filter(Deal.status == status)
    
    deals = query.order_by(Deal.created_at.desc()).all()
    
    result = []
    for deal in deals:
        borrower = db.query(Borrower).filter(Borrower.id == deal.borrower_id).first()
        # Parse metadata to get additional info
        try:
            metadata = json.loads(deal.metadata) if deal.metadata and isinstance(deal.metadata, str) else {}
        except:
            metadata = {}
        
        result.append({
            "id": deal.id,
            "borrower_name": borrower.name if borrower else "Unknown",
            "company_name": metadata.get("borrower_company", borrower.name if borrower else "Unknown"),
            "loan_amount": deal.loan_amount,
            "loan_type": deal.deal_type,
            "loan_purpose": metadata.get("loan_purpose", deal.deal_type),
            "status": deal.status,
            "property_address": metadata.get("property_address"),
            "property_city": metadata.get("property_city"),
            "property_state": metadata.get("property_state"),
            "created_at": deal.created_at.isoformat()
        })
    
    return result

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
    """Create a new loan application"""
    try:
        # Create borrower
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
        
        # Create deal
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

@app.get("/api/loans/{loan_id}")
def get_loan(
    loan_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get loan details"""
    deal = db.query(Deal).filter(
        Deal.id == loan_id,
        Deal.organization_id == current_user.organization_id
    ).first()
    
    if not deal:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    borrower = db.query(Borrower).filter(Borrower.id == deal.borrower_id).first()
    
    try:
        metadata = json.loads(deal.metadata) if deal.metadata else {}
    except:
        metadata = {}
    
    return {
        "id": deal.id,
        "borrower_name": borrower.name if borrower else "Unknown",
        "borrower_email": borrower.email if borrower else None,
        "borrower_phone": borrower.phone if borrower else None,
        "company_name": metadata.get("borrower_company"),
        "loan_amount": deal.loan_amount,
        "loan_type": deal.deal_type,
        "loan_purpose": metadata.get("loan_purpose"),
        "status": deal.status,
        "property_type": metadata.get("property_type"),
        "property_address": metadata.get("property_address"),
        "property_city": metadata.get("property_city"),
        "property_state": metadata.get("property_state"),
        "property_value": deal.appraised_value,
        "annual_revenue": metadata.get("annual_revenue"),
        "net_income": metadata.get("net_income"),
        "credit_score": metadata.get("borrower_credit_score"),
        "years_in_business": metadata.get("years_in_business"),
        "created_at": deal.created_at.isoformat()
    }

# ============================================================================
# UNDERWRITING ENDPOINTS
# ============================================================================

@app.post("/api/underwriting/analyze")
def analyze_loan(
    request: UnderwritingRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Perform comprehensive underwriting analysis"""
    # Get loan details
    deal = db.query(Deal).filter(
        Deal.id == request.loan_id,
        Deal.organization_id == current_user.organization_id
    ).first()
    
    if not deal:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    borrower = db.query(Borrower).filter(Borrower.id == deal.borrower_id).first()
    
    try:
        metadata = json.loads(deal.metadata) if deal.metadata else {}
    except:
        metadata = {}
    
    # Prepare data for underwriting engine
    loan_request = LoanRequest(
        loan_amount=Decimal(str(deal.loan_amount)),
        interest_rate=Decimal(str(deal.interest_rate or 0.065)),
        term_months=deal.amortization_months or 60,
        amortization_months=deal.amortization_months or 60,
        loan_purpose=metadata.get("loan_purpose", "commercial real estate"),
        loan_type=deal.deal_type,
        down_payment=Decimal(str(metadata.get("down_payment", 0)))
    )
    
    borrower_profile = BorrowerProfile(
        name=borrower.name if borrower else "Unknown",
        entity_type=borrower.entity_type if borrower else "llc",
        credit_score=metadata.get("borrower_credit_score"),
        years_in_business=metadata.get("years_in_business"),
        industry=metadata.get("industry", "commercial real estate"),
        annual_revenue=Decimal(str(metadata.get("annual_revenue", 0))),
        net_worth=Decimal(str(metadata.get("net_worth", 0))),
        liquidity=Decimal(str(metadata.get("liquidity", 0)))
    )
    
    property_details = PropertyDetails(
        property_type=metadata.get("property_type", "office"),
        address=metadata.get("property_address", ""),
        appraised_value=Decimal(str(deal.appraised_value or 0)),
        purchase_price=Decimal(str(metadata.get("purchase_price", 0))),
        net_operating_income=Decimal(str(metadata.get("net_income", 0)))
    ) if deal.appraised_value else None
    
    # Run underwriting
    result = underwriting_engine.underwrite(
        loan_request=loan_request,
        borrower=borrower_profile,
        property_details=property_details,
        existing_debt_service=Decimal(str(metadata.get("monthly_debt_service", 0)))
    )
    
    # Save underwriting result
    uw_result = UnderwritingResult(
        deal_id=deal.id,
        dscr=float(result.dscr),
        ltv=float(result.ltv),
        debt_yield=float(result.debt_yield),
        recommendation=result.recommendation,
        risk_rating=result.risk_rating,
        analysis_data=json.dumps({
            "dscr_stressed": float(result.dscr_stressed),
            "risk_score": result.risk_score,
            "probability_of_default": float(result.probability_of_default),
            "red_flags": result.red_flags,
            "yellow_flags": result.yellow_flags,
            "strengths": result.strengths,
            "required_conditions": result.required_conditions,
            "calculations": result.calculations
        }, default=str)
    )
    db.add(uw_result)
    
    # Update deal status based on recommendation
    if result.recommendation == "APPROVE":
        deal.status = "approved"
    elif result.recommendation == "DECLINE":
        deal.status = "declined"
    else:
        deal.status = "conditional"
    
    db.commit()
    
    # Return results
    return {
        "loan_id": deal.id,
        "recommendation": result.recommendation,
        "dscr": float(result.dscr),
        "dscr_stressed": float(result.dscr_stressed),
        "ltv": float(result.ltv),
        "debt_yield": float(result.debt_yield),
        "risk_score": result.risk_score,
        "risk_rating": result.risk_rating,
        "probability_of_default": float(result.probability_of_default),
        "monthly_payment": float(result.monthly_payment),
        "total_debt_service": float(result.total_debt_service),
        "global_cash_flow": float(result.global_cash_flow),
        "max_loan_amount": float(result.max_loan_amount),
        "suggested_rate": float(result.suggested_rate),
        "red_flags": result.red_flags,
        "yellow_flags": result.yellow_flags,
        "strengths": result.strengths,
        "required_conditions": result.required_conditions,
        "financial_ratios": {
            "current_ratio": float(result.current_ratio) if result.current_ratio else None,
            "debt_to_equity": float(result.debt_to_equity) if result.debt_to_equity else None,
            "profit_margin": float(result.profit_margin) if result.profit_margin else None,
            "roe": float(result.roe) if result.roe else None
        }
    }

# ============================================================================
# AI ADVISOR ENDPOINTS
# ============================================================================

@app.post("/api/ai/ask")
def ai_ask(
    request: AIAskRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """AI Advisor endpoint - answers commercial lending questions"""
    
    # Get context if loan_id provided
    context = request.context or {}
    if request.loan_id:
        deal = db.query(Deal).filter(
            Deal.id == request.loan_id,
            Deal.organization_id == current_user.organization_id
        ).first()
        
        if deal:
            try:
                metadata = json.loads(deal.metadata) if deal.metadata else {}
            except:
                metadata = {}
            
            context.update({
                "loan_amount": deal.loan_amount,
                "loan_type": deal.deal_type,
                "status": deal.status,
                **metadata
            })
    
    # Get AI response
    response = ai_advisor.ask_underwriting_question(
        question=request.question,
        context=context if context else None
    )
    
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
    
    return response

# ============================================================================
# DOCUMENT PROCESSING ENDPOINTS
# ============================================================================

@app.post("/api/documents/upload")
async def upload_document(
    loan_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload and process a document"""
    # Verify loan exists
    deal = db.query(Deal).filter(
        Deal.id == loan_id,
        Deal.organization_id == current_user.organization_id
    ).first()
    
    if not deal:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    # Save file temporarily
    file_path = f"/tmp/{uuid.uuid4()}_{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    try:
        # Process document
        result = document_processor.process_document(file_path)
        
        # Save document record
        doc = Document(
            deal_id=loan_id,
            document_type=result.document_type.value,
            filename=file.filename,
            file_path=file_path,
            file_size=result.metadata.file_size_bytes,
            analysis_data=json.dumps({
                "extracted_fields": [f.dict() for f in result.extracted_fields],
                "financial_data": result.financial_data.dict() if result.financial_data else None,
                "property_data": result.property_data.dict() if result.property_data else None,
                "borrower_data": result.borrower_data.dict() if result.borrower_data else None,
                "key_findings": result.key_findings,
                "data_quality_score": result.data_quality_score,
                "missing_fields": result.missing_fields,
                "validation_errors": result.validation_errors
            }, default=str)
        )
        db.add(doc)
        db.commit()
        
        return {
            "document_id": doc.id,
            "document_type": result.document_type.value,
            "data_quality_score": result.data_quality_score,
            "key_findings": result.key_findings,
            "missing_fields": result.missing_fields,
            "validation_errors": result.validation_errors,
            "extracted_data": {
                "financial_data": result.financial_data.dict() if result.financial_data else None,
                "property_data": result.property_data.dict() if result.property_data else None,
                "borrower_data": result.borrower_data.dict() if result.borrower_data else None
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")
    finally:
        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)

# ============================================================================
# REPORT GENERATION ENDPOINTS
# ============================================================================

@app.post("/api/reports/generate")
def generate_report(
    request: ReportGenerationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate PDF report"""
    # Get loan and underwriting data
    deal = db.query(Deal).filter(
        Deal.id == request.loan_id,
        Deal.organization_id == current_user.organization_id
    ).first()
    
    if not deal:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    borrower = db.query(Borrower).filter(Borrower.id == deal.borrower_id).first()
    uw_result = db.query(UnderwritingResult).filter(UnderwritingResult.deal_id == deal.id).first()
    
    if not uw_result:
        raise HTTPException(status_code=400, detail="Loan must be underwritten first")
    
    try:
        metadata = json.loads(deal.metadata) if deal.metadata else {}
        analysis_data = json.loads(uw_result.analysis_data) if uw_result.analysis_data else {}
    except:
        metadata = {}
        analysis_data = {}
    
    # Prepare data for report
    loan_data = {
        "loan_amount": deal.loan_amount,
        "loan_type": deal.deal_type,
        "loan_purpose": metadata.get("loan_purpose", ""),
        "interest_rate": deal.interest_rate or 0.065,
        "term_months": deal.amortization_months or 60,
        "amortization_months": deal.amortization_months or 60
    }
    
    borrower_data = {
        "name": borrower.name if borrower else "Unknown",
        "entity_type": borrower.entity_type if borrower else "llc",
        "industry": metadata.get("industry", "Commercial Real Estate"),
        "years_in_business": metadata.get("years_in_business", 0),
        "credit_score": metadata.get("borrower_credit_score"),
        "annual_revenue": metadata.get("annual_revenue", 0)
    }
    
    property_data = {
        "property_type": metadata.get("property_type", ""),
        "address": metadata.get("property_address", ""),
        "appraised_value": deal.appraised_value or 0,
        "square_footage": metadata.get("square_footage", 0),
        "year_built": metadata.get("year_built"),
        "occupancy_rate": metadata.get("occupancy_rate", 1.0)
    } if deal.appraised_value else None
    
    underwriting_results = {
        "recommendation": uw_result.recommendation,
        "dscr": uw_result.dscr,
        "dscr_stressed": analysis_data.get("dscr_stressed", 0),
        "ltv": uw_result.ltv,
        "debt_yield": uw_result.debt_yield,
        "risk_score": analysis_data.get("risk_score", 0),
        "risk_rating": uw_result.risk_rating,
        "probability_of_default": analysis_data.get("probability_of_default", 0),
        "red_flags": analysis_data.get("red_flags", []),
        "yellow_flags": analysis_data.get("yellow_flags", []),
        "strengths": analysis_data.get("strengths", []),
        "required_conditions": analysis_data.get("required_conditions", []),
        "max_loan_amount": analysis_data.get("max_loan_amount", 0),
        "suggested_rate": analysis_data.get("suggested_rate", 0.065),
        "monthly_payment": analysis_data.get("monthly_payment", 0),
        "total_debt_service": analysis_data.get("total_debt_service", 0),
        "global_cash_flow": analysis_data.get("global_cash_flow", 0)
    }
    
    financial_analysis = {
        "current_ratio": analysis_data.get("current_ratio", 0),
        "debt_to_equity": analysis_data.get("debt_to_equity", 0),
        "profit_margin": analysis_data.get("profit_margin", 0),
        "roe": analysis_data.get("roe", 0)
    }
    
    # Generate report
    output_path = f"/tmp/report_{request.loan_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    if request.report_type == "credit_memo":
        report_generator.generate_credit_memo(
            loan_data=loan_data,
            borrower_data=borrower_data,
            property_data=property_data,
            underwriting_results=underwriting_results,
            financial_analysis=financial_analysis,
            output_path=output_path
        )
    else:  # executive_summary
        report_generator.generate_executive_summary(
            loan_data=loan_data,
            borrower_data=borrower_data,
            underwriting_results=underwriting_results,
            output_path=output_path
        )
    
    # Save report record
    report = Report(
        deal_id=deal.id,
        report_type=request.report_type,
        file_path=output_path,
        generated_by=current_user.id
    )
    db.add(report)
    db.commit()
    
    # Return file
    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename=f"{request.report_type}_{deal.id}.pdf"
    )

# ============================================================================
# FRONTEND SERVING
# ============================================================================

# Mount static files (CSS, JS, images)
# Use backend/static directory where frontend is deployed on Render
frontend_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(frontend_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_path, "assets")), name="assets")

# Serve index.html for all non-API routes (SPA routing)
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve React frontend"""
    # Don't serve frontend for API routes
    if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi"):
        raise HTTPException(status_code=404, detail="Not found")
    
    # Serve index.html for all other routes
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return JSONResponse(
            status_code=503,
            content={
                "error": "Frontend not built",
                "message": "Please build the frontend first: cd frontend && npm run build"
            }
        )

# ============================================================================
# STARTUP
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    
    print("=" * 60)
    print("🚀 UnderwritePro SaaS - Ultimate Edition")
    print("=" * 60)
    print(f"Starting server on port {port}...")
    print(f"API Docs: http://localhost:{port}/docs")
    print(f"Frontend: http://localhost:{port}/")
    print("=" * 60)
    
    uvicorn.run(
        "main_ultimate:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
