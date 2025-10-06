"""
Broker Services
Lender network management, loan submissions, and commission tracking
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from models.broker import (
    LenderNetwork,
    LoanSubmission,
    RateQuote,
    BrokerCommission
)
from models.loan import LoanApplication


class LenderNetworkService:
    """
    Service for managing broker's lender network
    """
    
    @staticmethod
    def add_lender(
        db: Session,
        organization_id: UUID,
        lender_name: str,
        lender_type: str,
        contact_name: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        loan_types_offered: Optional[List[str]] = None,
        min_loan_amount: Optional[Decimal] = None,
        max_loan_amount: Optional[Decimal] = None,
        typical_rate_range: Optional[str] = None,
        notes: Optional[str] = None
    ) -> LenderNetwork:
        """Add a lender to broker's network"""
        lender = LenderNetwork(
            organization_id=organization_id,
            lender_name=lender_name,
            lender_type=lender_type,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            loan_types_offered=loan_types_offered or [],
            min_loan_amount=min_loan_amount,
            max_loan_amount=max_loan_amount,
            typical_rate_range=typical_rate_range,
            notes=notes,
            is_active=True
        )
        
        db.add(lender)
        db.commit()
        db.refresh(lender)
        
        return lender
    
    @staticmethod
    def get_lenders(
        db: Session,
        organization_id: UUID,
        is_active: Optional[bool] = None,
        lender_type: Optional[str] = None
    ) -> List[LenderNetwork]:
        """Get all lenders in broker's network"""
        query = db.query(LenderNetwork).filter(
            LenderNetwork.organization_id == organization_id
        )
        
        if is_active is not None:
            query = query.filter(LenderNetwork.is_active == is_active)
        
        if lender_type:
            query = query.filter(LenderNetwork.lender_type == lender_type)
        
        return query.order_by(LenderNetwork.lender_name).all()
    
    @staticmethod
    def get_lender_by_id(db: Session, lender_id: UUID) -> Optional[LenderNetwork]:
        """Get lender by ID"""
        return db.query(LenderNetwork).filter(LenderNetwork.id == lender_id).first()
    
    @staticmethod
    def update_lender(
        db: Session,
        lender_id: UUID,
        **updates
    ) -> Optional[LenderNetwork]:
        """Update lender information"""
        lender = LenderNetworkService.get_lender_by_id(db, lender_id)
        if not lender:
            return None
        
        for field, value in updates.items():
            if hasattr(lender, field):
                setattr(lender, field, value)
        
        db.commit()
        db.refresh(lender)
        
        return lender
    
    @staticmethod
    def deactivate_lender(db: Session, lender_id: UUID) -> bool:
        """Deactivate a lender"""
        lender = LenderNetworkService.get_lender_by_id(db, lender_id)
        if not lender:
            return False
        
        lender.is_active = False
        db.commit()
        
        return True
    
    @staticmethod
    def find_matching_lenders(
        db: Session,
        organization_id: UUID,
        loan_type: str,
        loan_amount: Decimal
    ) -> List[LenderNetwork]:
        """Find lenders that match loan criteria"""
        lenders = LenderNetworkService.get_lenders(db, organization_id, is_active=True)
        
        matching = []
        for lender in lenders:
            # Check loan type
            if loan_type not in lender.loan_types_offered:
                continue
            
            # Check loan amount
            if lender.min_loan_amount and loan_amount < lender.min_loan_amount:
                continue
            if lender.max_loan_amount and loan_amount > lender.max_loan_amount:
                continue
            
            matching.append(lender)
        
        return matching


class LoanSubmissionService:
    """
    Service for submitting loans to lenders
    """
    
    @staticmethod
    def submit_to_lender(
        db: Session,
        loan_application_id: UUID,
        lender_id: UUID,
        submitted_by: UUID,
        submission_notes: Optional[str] = None
    ) -> LoanSubmission:
        """Submit a loan application to a lender"""
        submission = LoanSubmission(
            loan_application_id=loan_application_id,
            lender_id=lender_id,
            submitted_by=submitted_by,
            submission_status='submitted',
            submission_notes=submission_notes
        )
        
        db.add(submission)
        db.commit()
        db.refresh(submission)
        
        return submission
    
    @staticmethod
    def get_submissions_for_loan(
        db: Session,
        loan_application_id: UUID
    ) -> List[LoanSubmission]:
        """Get all submissions for a loan"""
        return db.query(LoanSubmission).filter(
            LoanSubmission.loan_application_id == loan_application_id
        ).order_by(LoanSubmission.created_at.desc()).all()
    
    @staticmethod
    def get_submissions_by_status(
        db: Session,
        organization_id: UUID,
        status: str
    ) -> List[LoanSubmission]:
        """Get all submissions with a specific status"""
        return db.query(LoanSubmission).join(
            LoanApplication
        ).filter(
            LoanApplication.organization_id == organization_id,
            LoanSubmission.submission_status == status
        ).order_by(LoanSubmission.created_at.desc()).all()
    
    @staticmethod
    def update_submission_status(
        db: Session,
        submission_id: UUID,
        status: str,
        lender_response: Optional[str] = None
    ) -> Optional[LoanSubmission]:
        """Update submission status"""
        submission = db.query(LoanSubmission).filter(
            LoanSubmission.id == submission_id
        ).first()
        
        if not submission:
            return None
        
        submission.submission_status = status
        
        if lender_response:
            submission.lender_response = lender_response
        
        if status == 'approved':
            submission.approved_at = datetime.utcnow()
        elif status == 'declined':
            submission.declined_at = datetime.utcnow()
        
        db.commit()
        db.refresh(submission)
        
        return submission


class RateQuoteService:
    """
    Service for managing rate quotes from lenders
    """
    
    @staticmethod
    def add_quote(
        db: Session,
        submission_id: UUID,
        interest_rate: Decimal,
        term_months: int,
        amortization_months: Optional[int] = None,
        fees: Optional[Decimal] = None,
        points: Optional[Decimal] = None,
        quote_valid_until: Optional[datetime] = None,
        conditions: Optional[str] = None,
        notes: Optional[str] = None
    ) -> RateQuote:
        """Add a rate quote from a lender"""
        quote = RateQuote(
            submission_id=submission_id,
            interest_rate=interest_rate,
            term_months=term_months,
            amortization_months=amortization_months,
            fees=fees,
            points=points,
            quote_valid_until=quote_valid_until,
            conditions=conditions,
            notes=notes,
            is_active=True
        )
        
        db.add(quote)
        db.commit()
        db.refresh(quote)
        
        return quote
    
    @staticmethod
    def get_quotes_for_submission(
        db: Session,
        submission_id: UUID
    ) -> List[RateQuote]:
        """Get all rate quotes for a submission"""
        return db.query(RateQuote).filter(
            RateQuote.submission_id == submission_id,
            RateQuote.is_active == True
        ).order_by(RateQuote.interest_rate).all()
    
    @staticmethod
    def get_quotes_for_loan(
        db: Session,
        loan_application_id: UUID
    ) -> List[RateQuote]:
        """Get all rate quotes for a loan across all submissions"""
        return db.query(RateQuote).join(
            LoanSubmission
        ).filter(
            LoanSubmission.loan_application_id == loan_application_id,
            RateQuote.is_active == True
        ).order_by(RateQuote.interest_rate).all()
    
    @staticmethod
    def compare_quotes(
        db: Session,
        loan_application_id: UUID
    ) -> List[dict]:
        """Compare all quotes for a loan"""
        quotes = RateQuoteService.get_quotes_for_loan(db, loan_application_id)
        
        comparison = []
        for quote in quotes:
            submission = quote.submission
            lender = submission.lender
            
            comparison.append({
                'lender_name': lender.lender_name,
                'interest_rate': float(quote.interest_rate),
                'term_months': quote.term_months,
                'fees': float(quote.fees) if quote.fees else 0,
                'points': float(quote.points) if quote.points else 0,
                'conditions': quote.conditions,
                'quote_valid_until': quote.quote_valid_until.isoformat() if quote.quote_valid_until else None,
                'submission_id': str(submission.id),
                'quote_id': str(quote.id)
            })
        
        return comparison
    
    @staticmethod
    def select_quote(
        db: Session,
        quote_id: UUID,
        selected_by: UUID
    ) -> Optional[RateQuote]:
        """Mark a quote as selected"""
        quote = db.query(RateQuote).filter(RateQuote.id == quote_id).first()
        
        if not quote:
            return None
        
        quote.is_selected = True
        quote.selected_by = selected_by
        quote.selected_at = datetime.utcnow()
        
        db.commit()
        db.refresh(quote)
        
        return quote


class BrokerCommissionService:
    """
    Service for tracking broker commissions
    """
    
    @staticmethod
    def record_commission(
        db: Session,
        loan_application_id: UUID,
        lender_id: UUID,
        commission_amount: Decimal,
        commission_percentage: Optional[Decimal] = None,
        payment_status: str = 'pending',
        expected_payment_date: Optional[datetime] = None,
        notes: Optional[str] = None
    ) -> BrokerCommission:
        """Record a commission for a closed loan"""
        commission = BrokerCommission(
            loan_application_id=loan_application_id,
            lender_id=lender_id,
            commission_amount=commission_amount,
            commission_percentage=commission_percentage,
            payment_status=payment_status,
            expected_payment_date=expected_payment_date,
            notes=notes
        )
        
        db.add(commission)
        db.commit()
        db.refresh(commission)
        
        return commission
    
    @staticmethod
    def get_commissions_by_status(
        db: Session,
        organization_id: UUID,
        status: str
    ) -> List[BrokerCommission]:
        """Get commissions by payment status"""
        return db.query(BrokerCommission).join(
            LoanApplication
        ).filter(
            LoanApplication.organization_id == organization_id,
            BrokerCommission.payment_status == status
        ).order_by(BrokerCommission.created_at.desc()).all()
    
    @staticmethod
    def mark_commission_paid(
        db: Session,
        commission_id: UUID,
        payment_date: Optional[datetime] = None
    ) -> Optional[BrokerCommission]:
        """Mark a commission as paid"""
        commission = db.query(BrokerCommission).filter(
            BrokerCommission.id == commission_id
        ).first()
        
        if not commission:
            return None
        
        commission.payment_status = 'paid'
        commission.payment_date = payment_date or datetime.utcnow()
        
        db.commit()
        db.refresh(commission)
        
        return commission
    
    @staticmethod
    def get_commission_summary(
        db: Session,
        organization_id: UUID
    ) -> dict:
        """Get commission summary statistics"""
        from sqlalchemy import func
        
        # Total commissions
        total = db.query(
            func.sum(BrokerCommission.commission_amount)
        ).join(LoanApplication).filter(
            LoanApplication.organization_id == organization_id
        ).scalar() or Decimal('0')
        
        # Paid commissions
        paid = db.query(
            func.sum(BrokerCommission.commission_amount)
        ).join(LoanApplication).filter(
            LoanApplication.organization_id == organization_id,
            BrokerCommission.payment_status == 'paid'
        ).scalar() or Decimal('0')
        
        # Pending commissions
        pending = db.query(
            func.sum(BrokerCommission.commission_amount)
        ).join(LoanApplication).filter(
            LoanApplication.organization_id == organization_id,
            BrokerCommission.payment_status == 'pending'
        ).scalar() or Decimal('0')
        
        # Count by status
        counts = db.query(
            BrokerCommission.payment_status,
            func.count(BrokerCommission.id)
        ).join(LoanApplication).filter(
            LoanApplication.organization_id == organization_id
        ).group_by(BrokerCommission.payment_status).all()
        
        count_dict = {status: count for status, count in counts}
        
        return {
            'total_commissions': float(total),
            'paid_commissions': float(paid),
            'pending_commissions': float(pending),
            'count_paid': count_dict.get('paid', 0),
            'count_pending': count_dict.get('pending', 0),
            'count_expected': count_dict.get('expected', 0)
        }
