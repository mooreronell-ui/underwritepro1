"""
Lender Services
Custom underwriting policies, loan pipeline, portfolio management, and covenant monitoring
"""

from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from uuid import UUID
from decimal import Decimal
from datetime import datetime, timedelta

from models.lender import (
    UnderwritingPolicy,
    LoanPipeline,
    CreditDecision,
    LoanServicing,
    CovenantMonitoring,
    PortfolioAnalytics
)
from models.loan import LoanApplication


class UnderwritingPolicyService:
    """
    Service for managing custom underwriting policies
    """
    
    @staticmethod
    def create_policy(
        db: Session,
        organization_id: UUID,
        policy_name: str,
        loan_types: List[str],
        min_dscr: Optional[Decimal] = None,
        max_ltv: Optional[Decimal] = None,
        min_credit_score: Optional[int] = None,
        min_years_in_business: Optional[Decimal] = None,
        max_loan_amount: Optional[Decimal] = None,
        min_loan_amount: Optional[Decimal] = None,
        required_documents: Optional[List[str]] = None,
        special_conditions: Optional[str] = None,
        is_active: bool = True
    ) -> UnderwritingPolicy:
        """Create a custom underwriting policy"""
        policy = UnderwritingPolicy(
            organization_id=organization_id,
            policy_name=policy_name,
            loan_types=loan_types,
            min_dscr=min_dscr,
            max_ltv=max_ltv,
            min_credit_score=min_credit_score,
            min_years_in_business=min_years_in_business,
            max_loan_amount=max_loan_amount,
            min_loan_amount=min_loan_amount,
            required_documents=required_documents or [],
            special_conditions=special_conditions,
            is_active=is_active
        )
        
        db.add(policy)
        db.commit()
        db.refresh(policy)
        
        return policy
    
    @staticmethod
    def get_policies(
        db: Session,
        organization_id: UUID,
        is_active: Optional[bool] = None
    ) -> List[UnderwritingPolicy]:
        """Get all policies for an organization"""
        query = db.query(UnderwritingPolicy).filter(
            UnderwritingPolicy.organization_id == organization_id
        )
        
        if is_active is not None:
            query = query.filter(UnderwritingPolicy.is_active == is_active)
        
        return query.order_by(UnderwritingPolicy.policy_name).all()
    
    @staticmethod
    def get_policy_by_id(db: Session, policy_id: UUID) -> Optional[UnderwritingPolicy]:
        """Get policy by ID"""
        return db.query(UnderwritingPolicy).filter(
            UnderwritingPolicy.id == policy_id
        ).first()
    
    @staticmethod
    def check_policy_compliance(
        db: Session,
        policy_id: UUID,
        loan: LoanApplication
    ) -> Dict[str, any]:
        """Check if a loan complies with policy requirements"""
        policy = UnderwritingPolicyService.get_policy_by_id(db, policy_id)
        
        if not policy:
            raise ValueError("Policy not found")
        
        violations = []
        warnings = []
        
        # Check loan type
        if loan.loan_type.value not in policy.loan_types:
            violations.append(f"Loan type '{loan.loan_type.value}' not allowed by policy")
        
        # Check loan amount
        if policy.min_loan_amount and loan.loan_amount < policy.min_loan_amount:
            violations.append(f"Loan amount ${loan.loan_amount:,.2f} below minimum ${policy.min_loan_amount:,.2f}")
        
        if policy.max_loan_amount and loan.loan_amount > policy.max_loan_amount:
            violations.append(f"Loan amount ${loan.loan_amount:,.2f} exceeds maximum ${policy.max_loan_amount:,.2f}")
        
        # Check ratios
        if loan.financial_ratios:
            ratios = loan.financial_ratios
            
            # DSCR
            if policy.min_dscr:
                dscr = ratios.global_dscr or ratios.property_dscr or ratios.business_dscr
                if dscr and dscr < policy.min_dscr:
                    violations.append(f"DSCR {dscr:.2f}x below minimum {policy.min_dscr:.2f}x")
            
            # LTV
            if policy.max_ltv and ratios.ltv:
                if ratios.ltv > policy.max_ltv:
                    violations.append(f"LTV {ratios.ltv:.1f}% exceeds maximum {policy.max_ltv:.1f}%")
        
        # Check credit score
        if policy.min_credit_score:
            borrower = loan.borrower
            guarantor = loan.guarantors[0] if loan.guarantors else None
            
            business_credit = borrower.business_credit_score if borrower else None
            personal_credit = guarantor.credit_score if guarantor else None
            
            if business_credit and business_credit < policy.min_credit_score:
                warnings.append(f"Business credit score {business_credit} below minimum {policy.min_credit_score}")
            
            if personal_credit and personal_credit < policy.min_credit_score:
                violations.append(f"Personal credit score {personal_credit} below minimum {policy.min_credit_score}")
        
        # Check years in business
        if policy.min_years_in_business and loan.borrower:
            if loan.borrower.years_in_business and loan.borrower.years_in_business < policy.min_years_in_business:
                warnings.append(f"Years in business {loan.borrower.years_in_business:.1f} below minimum {policy.min_years_in_business:.1f}")
        
        is_compliant = len(violations) == 0
        
        return {
            'is_compliant': is_compliant,
            'violations': violations,
            'warnings': warnings,
            'policy_name': policy.policy_name
        }


class LoanPipelineService:
    """
    Service for managing loan pipeline
    """
    
    @staticmethod
    def add_to_pipeline(
        db: Session,
        loan_application_id: UUID,
        pipeline_stage: str,
        assigned_underwriter: Optional[UUID] = None,
        priority: str = 'medium',
        target_close_date: Optional[datetime] = None
    ) -> LoanPipeline:
        """Add loan to pipeline"""
        pipeline_item = LoanPipeline(
            loan_application_id=loan_application_id,
            pipeline_stage=pipeline_stage,
            assigned_underwriter=assigned_underwriter,
            priority=priority,
            target_close_date=target_close_date
        )
        
        db.add(pipeline_item)
        db.commit()
        db.refresh(pipeline_item)
        
        return pipeline_item
    
    @staticmethod
    def get_pipeline(
        db: Session,
        organization_id: UUID,
        stage: Optional[str] = None,
        assigned_to: Optional[UUID] = None
    ) -> List[LoanPipeline]:
        """Get pipeline items"""
        query = db.query(LoanPipeline).join(LoanApplication).filter(
            LoanApplication.organization_id == organization_id
        )
        
        if stage:
            query = query.filter(LoanPipeline.pipeline_stage == stage)
        
        if assigned_to:
            query = query.filter(LoanPipeline.assigned_underwriter == assigned_to)
        
        return query.order_by(LoanPipeline.priority.desc(), LoanPipeline.created_at).all()
    
    @staticmethod
    def update_stage(
        db: Session,
        pipeline_id: UUID,
        new_stage: str
    ) -> Optional[LoanPipeline]:
        """Update pipeline stage"""
        item = db.query(LoanPipeline).filter(LoanPipeline.id == pipeline_id).first()
        
        if not item:
            return None
        
        item.pipeline_stage = new_stage
        item.last_stage_change = datetime.utcnow()
        
        # Calculate days in previous stage
        if item.last_stage_change:
            days_in_stage = (datetime.utcnow() - item.last_stage_change).days
            item.days_in_current_stage = days_in_stage
        
        db.commit()
        db.refresh(item)
        
        return item
    
    @staticmethod
    def get_pipeline_metrics(
        db: Session,
        organization_id: UUID
    ) -> Dict[str, any]:
        """Get pipeline metrics"""
        from sqlalchemy import func
        
        # Count by stage
        stage_counts = db.query(
            LoanPipeline.pipeline_stage,
            func.count(LoanPipeline.id)
        ).join(LoanApplication).filter(
            LoanApplication.organization_id == organization_id
        ).group_by(LoanPipeline.pipeline_stage).all()
        
        # Count by priority
        priority_counts = db.query(
            LoanPipeline.priority,
            func.count(LoanPipeline.id)
        ).join(LoanApplication).filter(
            LoanApplication.organization_id == organization_id
        ).group_by(LoanPipeline.priority).all()
        
        # Average days in pipeline
        avg_days = db.query(
            func.avg(LoanPipeline.days_in_current_stage)
        ).join(LoanApplication).filter(
            LoanApplication.organization_id == organization_id
        ).scalar() or 0
        
        return {
            'by_stage': {stage: count for stage, count in stage_counts},
            'by_priority': {priority: count for priority, count in priority_counts},
            'average_days_in_stage': float(avg_days)
        }


class CreditDecisionService:
    """
    Service for credit decisioning
    """
    
    @staticmethod
    def record_decision(
        db: Session,
        loan_application_id: UUID,
        decision: str,
        decided_by: UUID,
        decision_rationale: Optional[str] = None,
        approved_amount: Optional[Decimal] = None,
        approved_rate: Optional[Decimal] = None,
        approved_term: Optional[int] = None,
        conditions: Optional[List[str]] = None,
        decline_reason: Optional[str] = None
    ) -> CreditDecision:
        """Record a credit decision"""
        credit_decision = CreditDecision(
            loan_application_id=loan_application_id,
            decision=decision,
            decided_by=decided_by,
            decision_rationale=decision_rationale,
            approved_amount=approved_amount,
            approved_rate=approved_rate,
            approved_term=approved_term,
            conditions=conditions or [],
            decline_reason=decline_reason
        )
        
        db.add(credit_decision)
        db.commit()
        db.refresh(credit_decision)
        
        # Update loan application status
        loan = db.query(LoanApplication).filter(
            LoanApplication.id == loan_application_id
        ).first()
        
        if loan:
            if decision == 'approved':
                loan.status = 'approved'
                loan.approved_at = datetime.utcnow()
            elif decision == 'approved_with_conditions':
                loan.status = 'approved_with_conditions'
                loan.approved_at = datetime.utcnow()
            elif decision == 'declined':
                loan.status = 'declined'
            
            db.commit()
        
        return credit_decision
    
    @staticmethod
    def get_decision(
        db: Session,
        loan_application_id: UUID
    ) -> Optional[CreditDecision]:
        """Get credit decision for a loan"""
        return db.query(CreditDecision).filter(
            CreditDecision.loan_application_id == loan_application_id
        ).order_by(CreditDecision.created_at.desc()).first()
    
    @staticmethod
    def get_decision_metrics(
        db: Session,
        organization_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, any]:
        """Get decision metrics"""
        from sqlalchemy import func
        
        query = db.query(CreditDecision).join(LoanApplication).filter(
            LoanApplication.organization_id == organization_id
        )
        
        if start_date:
            query = query.filter(CreditDecision.created_at >= start_date)
        if end_date:
            query = query.filter(CreditDecision.created_at <= end_date)
        
        # Count by decision
        decision_counts = query.with_entities(
            CreditDecision.decision,
            func.count(CreditDecision.id)
        ).group_by(CreditDecision.decision).all()
        
        # Total approved amount
        total_approved = query.filter(
            CreditDecision.decision.in_(['approved', 'approved_with_conditions'])
        ).with_entities(
            func.sum(CreditDecision.approved_amount)
        ).scalar() or Decimal('0')
        
        return {
            'by_decision': {decision: count for decision, count in decision_counts},
            'total_approved_amount': float(total_approved),
            'approval_rate': 0  # Calculate based on counts
        }


class LoanServicingService:
    """
    Service for loan servicing an
