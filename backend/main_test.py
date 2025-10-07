from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
import json
import os

# Use SQLite database for testing
from database import (
    init_db, get_db, User, Organization, Borrower, Deal, Document,
    UnderwritingResult, Report, AuditLog
)
from auth_test import (
    get_password_hash, verify_password, create_access_token,
    get_current_active_user, require_role
)
from loan_schemas import LoanApplicationCreate, LoanApplicationResponse, LoanStatsResponse

# Initialize FastAPI app
app = FastAPI(
    title="UnderwritePro SaaS API (Test)",
    version="2.0.0",
    description="F500-level Commercial Loan Underwriting Platform - Test Version"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# Pydantic models
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

# Health check
@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0-test"}

# Auth endpoints
@app.post("/api/auth/register", status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user and organization"""
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create organization
    org = Organization(name=user.organization_name)
    db.add(org)
    db.flush()
    
    # Create user
    new_user = User(
        email=user.email,
        password_hash=get_password_hash(user.password),
        full_name=user.full_name,
        role="broker",
        organization_id=org.id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "role": new_user.role,
        "organization_id": new_user.organization_id
    }

@app.post("/api/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and get access token"""
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
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

# Loan endpoints
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
    """Get loan statistics"""
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
        # Create borrower (without organization_id as it's not in the SQLite schema)
        borrower = Borrower(
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
            interest_rate=0.065,
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
        
        # Log the creation (using correct field names for SQLite schema)
        audit_log = AuditLog(
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            event_type="loan_created",
            action="create",
            resource_type="deal",
            resource_id=deal.id,
            payload=f"Created loan application for {borrower.name}"
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
    """AI Advisor endpoint"""
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
    
    # Log the interaction (using correct field names for SQLite schema)
    audit_log = AuditLog(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        event_type="ai_query",
        action="query",
        resource_type="ai_advisor",
        resource_id="advisor_1",
        payload=f"Question: {request.question[:100]}"
    )
    db.add(audit_log)
    db.commit()
    
    return {"answer": answer, "confidence": 0.95}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
