"""
Broker API Routes
Lender network, loan submissions, rate quotes, and commissions
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime

from database_config import get_db
from services.broker_service import (
    LenderNetworkService,
    LoanSubmissionService,
    RateQuoteService,
    BrokerCommissionService
)


router = APIRouter(prefix="/api/broker", tags=["broker"])


# ========================================================================
# Request/Response Models
# ========================================================================

class AddLenderRequest(BaseModel):
    """Request to add lender to network"""
    lender_name: str
    lender_type: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    loan_types_offered: Optional[List[str]] = None
    min_loan_amount: Optional[Decimal] = None
    max_loan_amount: Optional[Decimal] = None
    typical_rate_range: Optional[str] = None
    notes: Optional[str] = None


class SubmitLoanRequest(BaseModel):
    """Request to submit loan to lender"""
    loan_application_id: UUID
    lender_id: UUID
    submission_notes: Optional[str] = None


class AddRateQuoteRequest(BaseModel):
    """Request to add rate quote"""
    submission_id: UUID
    interest_rate: Decimal
    term_months: int
    amortization_months: Optional[int] = None
    fees: Optional[Decimal] = None
    points: Optional[Decimal] = None
    quote_valid_until: Optional[datetime] = None
    conditions: Optional[str] = None
    notes: Optional[str] = None


class RecordCommissionRequest(BaseModel):
    """Request to record commission"""
    loan_application_id: UUID
    lender_id: UUID
    commission_amount: Decimal
    commission_percentage: Optional[Decimal] = None
    expected_payment_date: Optional[datetime] = None
    notes: Optional[str] = None


# ========================================================================
# Lender Network Endpoints
# ========================================================================

@router.post("/lenders", status_code=status.HTTP_201_CREATED)
def add_lender(
    request: AddLenderRequest,
    organization_id: UUID,
    db: Session = Depends(get_db)
):
    """Add a lender to broker's network"""
    try:
        lender = LenderNetworkService.add_lender(
            db=db,
            organization_id=organization_id,
            **request.model_dump()
        )
        
        return {
            "success": True,
            "lender": {
                "id": str(lender.id),
                "lender_name": lender.lender_name,
                "lender_type": lender.lender_type,
                "contact_name": lender.contact_name,
                "contact_email": lender.contact_email,
                "loan_types_offered": lender.loan_types_offered,
                "is_active": lender.is_active
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add lender: {str(e)}"
        )


@router.get("/lenders", status_code=status.HTTP_200_OK)
def get_lenders(
    organization_id: UUID,
    is_active: Optional[bool] = None,
    lender_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all lenders in broker's network"""
    lenders = LenderNetworkService.get_lenders(
        db=db,
        organization_id=organization_id,
        is_active=is_active,
        lender_type=lender_type
    )
    
    return {
        "success": True,
        "count": len(lenders),
        "lenders": [
            {
                "id": str(lender.id),
                "lender_name": lender.lender_name,
                "lender_type": lender.lender_type,
                "contact_name": lender.contact_name,
                "contact_email": lender.contact_email,
                "contact_phone": lender.contact_phone,
                "loan_types_offered": lender.loan_types_offered,
                "min_loan_amount": float(lender.min_loan_amount) if lender.min_loan_amount else None,
                "max_loan_amount": float(lender.max_loan_amount) if lender.max_loan_amount else None,
                "typical_rate_range": lender.typical_rate_range,
                "is_active": lender.is_active
            }
            for lender in lenders
        ]
    }


@router.get("/lenders/match", status_code=status.HTTP_200_OK)
def find_matching_lenders(
    organization_id: UUID,
    loan_type: str,
    loan_amount: Decimal,
    db: Session = Depends(get_db)
):
    """Find lenders that match loan criteria"""
    lenders = LenderNetworkService.find_matching_lenders(
        db=db,
        organization_id=organization_id,
        loan_type=loan_type,
        loan_amount=loan_amount
    )
    
    return {
        "success": True,
        "count": len(lenders),
        "matching_lenders": [
            {
                "id": str(lender.id),
                "lender_name": lender.lender_name,
                "lender_type": lender.lender_type,
                "contact_name": lender.contact_name,
                "contact_email": lender.contact_email,
                "typical_rate_range": lender.typical_rate_range
            }
            for lender in lenders
        ]
    }


# ========================================================================
# Loan Submission Endpoints
# ========================================================================

@router.post("/submissions", status_code=status.HTTP_201_CREATED)
def submit_loan_to_lender(
    request: SubmitLoanRequest,
    submitted_by: UUID,
    db: Session = Depends(get_db)
):
    """Submit a loan application to a lender"""
    try:
        submission = LoanSubmissionService.submit_to_lender(
            db=db,
            loan_application_id=request.loan_application_id,
            lender_id=request.lender_id,
            submitted_by=submitted_by,
            submission_notes=request.submission_notes
        )
        
        return {
            "success": True,
            "submission": {
                "id": str(submission.id),
                "loan_application_id": str(submission.loan_application_id),
                "lender_id": str(submission.lender_id),
                "submission_status": submission.submission_status,
                "submitted_at": submission.created_at.isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit loan: {str(e)}"
        )


@router.get("/submissions/loan/{loan_id}", status_code=status.HTTP_200_OK)
def get_submissions_for_loan(
    loan_id: UUID,
    db: Session = Depends(get_db)
):
    """Get all submissions for a loan"""
    submissions = LoanSubmissionService.get_submissions_for_loan(db, loan_id)
    
    return {
        "success": True,
        "count": len(submissions),
        "submissions": [
            {
                "id": str(sub.id),
                "lender_name": sub.lender.lender_name,
                "submission_status": sub.submission_status,
                "submitted_at": sub.created_at.isoformat(),
                "lender_response": sub.lender_response,
                "approved_at": sub.approved_at.isoformat() if sub.approved_at else None,
                "declined_at": sub.declined_at.isoformat() if sub.declined_at else None
            }
            for sub in submissions
        ]
    }


@router.put("/submissions/{submission_id}/status", status_code=status.HTTP_200_OK)
def update_submission_status(
    submission_id: UUID,
    status: str,
    lender_response: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Update submission status"""
    submission = LoanSubmissionService.update_submission_status(
        db=db,
        submission_id=submission_id,
        status=status,
        lender_response=lender_response
    )
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    return {
        "success": True,
        "submission": {
            "id": str(submission.id),
            "submission_status": submission.submission_status,
            "lender_response": submission.lender_response
        }
    }


# ========================================================================
# Rate Quote Endpoints
# ========================================================================

@router.post("/quotes", status_code=status.HTTP_201_CREATED)
def add_rate_quote(
    request: AddRateQuoteRequest,
    db: Session = Depends(get_db)
):
    """Add a rate quote from a lender"""
    try:
        quote = RateQuoteService.add_quote(
            db=db,
            **request.model_dump()
        )
        
        return {
            "success": True,
            "quote": {
                "id": str(quote.id),
                "submission_id": str(quote.submission_id),
                "interest_rate": float(quote.interest_rate),
                "term_months": quote.term_months,
                "fees": float(quote.fees) if quote.fees else None,
                "points": float(quote.points) if quote.points else None,
                "quote_valid_until": quote.quote_valid_until.isoformat() if quote.quote_valid_until else None
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add quote: {str(e)}"
        )


@router.get("/quotes/loan/{loan_id}", status_code=status.HTTP_200_OK)
def get_quotes_for_loan(
    loan_id: UUID,
    db: Session = Depends(get_db)
):
    """Get all rate quotes for a loan"""
    quotes = RateQuoteService.get_quotes_for_loan(db, loan_id)
    
    return {
        "success": True,
        "count": len(quotes),
        "quotes": [
            {
                "id": str(quote.id),
                "lender_name": quote.submission.lender.lender_name,
                "interest_rate": float(quote.interest_rate),
                "term_months": quote.term_months,
                "amortization_months": quote.amortization_months,
                "fees": float(quote.fees) if quote.fees else 0,
                "points": float(quote.points) if quote.points else 0,
                "conditions": quote.conditions,
                "quote_valid_until": quote.quote_valid_until.isoformat() if quote.quote_valid_until else None,
                "is_selected": quote.is_selected
            }
            for quote in quotes
        ]
    }


@router.get("/quotes/compare/{loan_id}", status_code=status.HTTP_200_OK)
def compare_quotes(
    loan_id: UUID,
    db: Session = Depends(get_db)
):
    """Compare all quotes for a loan"""
    comparison = RateQuoteService.compare_quotes(db, loan_id)
    
    return {
        "success": True,
        "count": len(comparison),
        "comparison": comparison
    }


@router.post("/quotes/{quote_id}/select", status_code=status.HTTP_200_OK)
def select_quote(
    quote_id: UUID,
    selected_by: UUID,
    db: Session = Depends(get_db)
):
    """Mark a quote as selected"""
    quote = RateQuoteService.select_quote(db, quote_id, selected_by)
    
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found"
        )
    
    return {
        "success": True,
        "message": "Quote selected successfully"
    }


# ========================================================================
# Commission Endpoints
# ========================================================================

@router.post("/commissions", status_code=status.HTTP_201_CREATED)
def record_commission(
    request: RecordCommissionRequest,
    db: Session = Depends(get_db)
):
    """Record a commission for a closed loan"""
    try:
        commission = BrokerCommissionService.record_commission(
            db=db,
            **request.model_dump()
        )
        
        return {
            "success": True,
            "commission": {
                "id": str(commission.id),
                "loan_application_id": str(commission.loan_application_id),
                "commission_amount": float(commission.commission_amount),
                "payment_status": commission.payment_status,
                "expected_payment_date": commission.expected_payment_date.isoformat() if commission.expected_payment_date else None
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record commission: {str(e)}"
        )


@router.get("/commissions", status_code=status.HTTP_200_OK)
def get_commissions(
    organization_id: UUID,
    payment_status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get commissions by status"""
    if payment_status:
        commissions = BrokerCommissionService.get_commissions_by_status(
            db, organization_id, payment_status
        )
    else:
        # Get all commissions
        from models.broker import BrokerCommission
        from models.loan import LoanApplication
        commissions = db.query(BrokerCommission).join(LoanApplication).filter(
            LoanApplication.organization_id == organization_id
        ).all()
    
    return {
        "success": True,
        "count": len(commissions),
        "commissions": [
            {
                "id": str(comm.id),
                "loan_application_id": str(comm.loan_application_id),
                "lender_name": comm.lender.lender_name,
                "commission_amount": float(comm.commission_amount),
                "commission_percentage": float(comm.commission_percentage) if comm.commission_percentage else None,
                "payment_status": comm.payment_status,
                "expected_payment_date": comm.expected_payment_date.isoformat() if comm.expected_payment_date else None,
                "payment_date": comm.payment_date.isoformat() if comm.payment_date else None
            }
            for comm in commissions
        ]
    }


@router.get("/commissions/summary", status_code=status.HTTP_200_OK)
def get_commission_summary(
    organization_id: UUID,
    db: Session = Depends(get_db)
):
    """Get commission summary statistics"""
    summary = BrokerCommissionService.get_commission_summary(db, organization_id)
    
    return {
        "success": True,
        "summary": summary
    }


@router.put("/commissions/{commission_id}/mark-paid", status_code=status.HTTP_200_OK)
def mark_commission_paid(
    commission_id: UUID,
    payment_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Mark a commission as paid"""
    commission = BrokerCommissionService.mark_commission_paid(
        db, commission_id, payment_date
    )
    
    if not commission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commission not found"
        )
    
    return {
        "success": True,
        "message": "Commission marked as paid",
        "payment_date": commission.payment_date.isoformat()
    }
