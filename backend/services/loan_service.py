"""
Loan Application CRUD Service
Business logic for loan application management
"""

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import secrets

from models.loan import LoanApplication, LoanStatus, LoanStage
from schemas.loan import (
    LoanApplicationCreate,
    LoanApplicationUpdate,
    LoanApplicationStats
)


class LoanApplicationService:
    """Service for loan application operations"""
    
    @staticmethod
    def generate_application_number() -> str:
        """
        Generate unique application number
        Format: LA-YYYYMMDD-XXXX (e.g., LA-20251006-A1B2)
        """
        date_part = datetime.now().strftime("%Y%m%d")
        random_part = secrets.token_hex(2).upper()
        return f"LA-{date_part}-{random_part}"
    
    @staticmethod
    def create(
        db: Session,
        loan_data: LoanApplicationCreate,
        created_by: UUID
    ) -> LoanApplication:
        """
        Create new loan application
        """
        # Generate application number
        application_number = LoanApplicationService.generate_application_number()
        
        # Ensure uniqueness
        while db.query(LoanApplication).filter(
            LoanApplication.application_number == application_number
        ).first():
            application_number = LoanApplicationService.generate_application_number()
        
        # Create loan application
        loan = LoanApplication(
            application_number=application_number,
            **loan_data.model_dump(),
            created_by=created_by,
            status=LoanStatus.DRAFT,
            stage=LoanStage.INTAKE
        )
        
        db.add(loan)
        db.commit()
        db.refresh(loan)
        
        return loan
    
    @staticmethod
    def get_by_id(
        db: Session,
        loan_id: UUID,
        organization_id: Optional[UUID] = None
    ) -> Optional[LoanApplication]:
        """
        Get loan application by ID
        """
        query = db.query(LoanApplication).filter(LoanApplication.id == loan_id)
        
        # Filter by organization if provided (for access control)
        if organization_id:
            query = query.filter(LoanApplication.organization_id == organization_id)
        
        return query.first()
    
    @staticmethod
    def get_by_application_number(
        db: Session,
        application_number: str,
        organization_id: Optional[UUID] = None
    ) -> Optional[LoanApplication]:
        """
        Get loan application by application number
        """
        query = db.query(LoanApplication).filter(
            LoanApplication.application_number == application_number
        )
        
        if organization_id:
            query = query.filter(LoanApplication.organization_id == organization_id)
        
        return query.first()
    
    @staticmethod
    def get_all(
        db: Session,
        organization_id: Optional[UUID] = None,
        status: Optional[LoanStatus] = None,
        stage: Optional[LoanStage] = None,
        assigned_to: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[LoanApplication]:
        """
        Get all loan applications with filters
        """
        query = db.query(LoanApplication)
        
        # Apply filters
        if organization_id:
            query = query.filter(LoanApplication.organization_id == organization_id)
        
        if status:
            query = query.filter(LoanApplication.status == status)
        
        if stage:
            query = query.filter(LoanApplication.stage == stage)
        
        if assigned_to:
            query = query.filter(LoanApplication.assigned_to == assigned_to)
        
        # Order by most recent first
        query = query.order_by(LoanApplication.created_at.desc())
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def update(
        db: Session,
        loan_id: UUID,
        loan_data: LoanApplicationUpdate,
        organization_id: Optional[UUID] = None
    ) -> Optional[LoanApplication]:
        """
        Update loan application
        """
        loan = LoanApplicationService.get_by_id(db, loan_id, organization_id)
        
        if not loan:
            return None
        
        # Update fields
        update_data = loan_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(loan, field, value)
        
        db.commit()
        db.refresh(loan)
        
        return loan
    
    @staticmethod
    def delete(
        db: Session,
        loan_id: UUID,
        organization_id: Optional[UUID] = None
    ) -> bool:
        """
        Delete loan application
        """
        loan = LoanApplicationService.get_by_id(db, loan_id, organization_id)
        
        if not loan:
            return False
        
        db.delete(loan)
        db.commit()
        
        return True
    
    @staticmethod
    def submit_loan(
        db: Session,
        loan_id: UUID,
        organization_id: Optional[UUID] = None
    ) -> Optional[LoanApplication]:
        """
        Submit loan application (change status from DRAFT to SUBMITTED)
        """
        loan = LoanApplicationService.get_by_id(db, loan_id, organization_id)
        
        if not loan or loan.status != LoanStatus.DRAFT:
            return None
        
        loan.status = LoanStatus.SUBMITTED
        loan.stage = LoanStage.DOCUMENT_COLLECTION
        loan.submitted_at = datetime.utcnow()
        
        db.commit()
        db.refresh(loan)
        
        return loan
    
    @staticmethod
    def get_statistics(
        db: Session,
        organization_id: Optional[UUID] = None
    ) -> LoanApplicationStats:
        """
        Get loan application statistics
        """
        query = db.query(LoanApplication)
        
        if organization_id:
            query = query.filter(LoanApplication.organization_id == organization_id)
        
        # Total counts
        total_loans = query.count()
        pending_loans = query.filter(LoanApplication.status == LoanStatus.SUBMITTED).count()
        in_review_loans = query.filter(LoanApplication.status == LoanStatus.IN_REVIEW).count()
        approved_loans = query.filter(LoanApplication.status.in_([
            LoanStatus.APPROVED,
            LoanStatus.APPROVED_WITH_CONDITIONS
        ])).count()
        declined_loans = query.filter(LoanApplication.status == LoanStatus.DECLINED).count()
        
        # Total loan amount
        total_amount_result = query.with_entities(
            func.sum(LoanApplication.loan_amount)
        ).scalar()
        total_loan_amount = total_amount_result or 0
        
        # Average loan amount
        avg_amount_result = query.with_entities(
            func.avg(LoanApplication.loan_amount)
        ).scalar()
        average_loan_amount = avg_amount_result or 0
        
        # By loan type
        by_loan_type = {}
        loan_type_counts = query.with_entities(
            LoanApplication.loan_type,
            func.count(LoanApplication.id)
        ).group_by(LoanApplication.loan_type).all()
        
        for loan_type, count in loan_type_counts:
            by_loan_type[loan_type.value] = count
        
        # By status
        by_status = {}
        status_counts = query.with_entities(
            LoanApplication.status,
            func.count(LoanApplication.id)
        ).group_by(LoanApplication.status).all()
        
        for status, count in status_counts:
            by_status[status.value] = count
        
        # By stage
        by_stage = {}
        stage_counts = query.with_entities(
            LoanApplication.stage,
            func.count(LoanApplication.id)
        ).group_by(LoanApplication.stage).all()
        
        for stage, count in stage_counts:
            by_stage[stage.value] = count
        
        return LoanApplicationStats(
            total_loans=total_loans,
            pending_loans=pending_loans,
            in_review_loans=in_review_loans,
            approved_loans=approved_loans,
            declined_loans=declined_loans,
            total_loan_amount=total_loan_amount,
            average_loan_amount=average_loan_amount,
            by_loan_type=by_loan_type,
            by_status=by_status,
            by_stage=by_stage
        )
    
    @staticmethod
    def get_with_details(
        db: Session,
        loan_id: UUID,
        organization_id: Optional[UUID] = None
    ) -> Optional[LoanApplication]:
        """
        Get loan application with all related data (eager loading)
        """
        query = db.query(LoanApplication).filter(LoanApplication.id == loan_id)
        
        if organization_id:
            query = query.filter(LoanApplication.organization_id == organization_id)
        
        # Eager load relationships
        query = query.options(
            joinedload(LoanApplication.borrower),
            joinedload(LoanApplication.guarantors),
            joinedload(LoanApplication.property_info),
            joinedload(LoanApplication.financial_ratios),
            joinedload(LoanApplication.risk_assessment),
            joinedload(LoanApplication.documents)
        )
        
        return query.first()
