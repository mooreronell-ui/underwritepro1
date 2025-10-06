"""
Lender API Routes
Underwriting policies, pipeline management, credit decisions, and portfolio monitoring
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime

from database_config import get_db
from services.lender_service import (
    UnderwritingPolicyService,
    LoanPipelineService,
    CreditDecisionService
)


router = APIRouter(prefix="/api/lender", tags=["lender"])


# ========================================================================
# Request/Response Models
# ========================================================================

class CreatePolicyRequest(BaseModel):
    """Request to create underwriting policy"""
    policy_name: str
    loan_types: List[str]
    min_dscr: Optional[Decimal] = None
    max_ltv: Optional[Decimal] = None
    min_credit_score: Optional[int] = None
    min_years_in_business: Optional[Decimal] = None
    max_loan_amount: Optional[Decimal] = None
    min_loan_amount: Optional[Decimal] = None
    required_documents: Optional[List[str]] = None
    special_conditions: Optional[str] = None


class AddToPipelineRequest(BaseModel):
    """Request to add loan to pipeline"""
    loan_application_id: UUID
    pipeline_stage: str
    assigned_underwriter: Optional[UUID] = None
    priority: str = 'medium'
    target_close_date: Optional[datetime] = None


class RecordDecisionRequest(BaseModel):
    """Request to record credit decision"""
    loan_application_id: UUID
    decision: str
    decision_rationale: Optional[str] = None
    approved_amount: Optional[Decimal] = None
    approved_rate: Optional[Decimal] = None
    approved_term: Optional[int] = None
    conditions: Optional[List[str]] = None
    decline_reason: Optional[str] = None


# ========================================================================
# Underwriting Policy Endpoints
# ========================================================================

@router.post("/policies", status_code=status.HTTP_201_CREATED)
def create_policy(
    request: CreatePolicyRequest,
    organization_id: UUID,
    db: Session = Depends(get_db)
):
    """Create a custom underwriting policy"""
    try:
        policy = UnderwritingPolicyService.create_policy(
            db=db,
            organization_id=organization_id,
            **request.model_dump()
        )
        
        return {
            "success": True,
            "policy": {
                "id": str(policy.id),
                "policy_name": policy.policy_name,
                "loan_types": policy.loan_types,
                "min_dscr": float(policy.min_dscr) if policy.min_dscr else None,
                "max_ltv": float(policy.max_ltv) if policy.max_ltv else None,
                "min_credit_score": policy.min_credit_score,
                "is_active": policy.is_active
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create policy: {str(e)}"
        )


@router.get("/policies", status_code=status.HTTP_200_OK)
def get_policies(
    organization_id: UUID,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get all underwriting policies"""
    policies = UnderwritingPolicyService.get_policies(
        db=db,
        organization_id=organization_id,
        is_active=is_active
    )
    
    return {
        "success": True,
        "count": len(policies),
        "policies": [
            {
                "id": str(policy.id),
                "policy_name": policy.policy_name,
                "loan_types": policy.loan_types,
                "min_dscr": float(policy.min_dscr) if policy.min_dscr else None,
                "max_ltv": float(policy.max_ltv) if policy.max_ltv else None,
                "min_credit_score": policy.min_credit_score,
                "min_years_in_business": float(policy.min_years_in_business) if policy.min_years_in_business else None,
                "max_loan_amount": float(policy.max_loan_amount) if policy.max_loan_amount else None,
                "min_loan_amount": float(policy.min_loan_amount) if policy.min_loan_amount else None,
                "required_documents": policy.required_documents,
                "is_active": policy.is_active
            }
            for policy in policies
        ]
    }


@router.post("/policies/{policy_id}/check-compliance", status_code=status.HTTP_200_OK)
def check_policy_compliance(
    policy_id: UUID,
    loan_application_id: UUID,
    db: Session = Depends(get_db)
):
    """Check if a loan complies with policy requirements"""
    from models.loan import LoanApplication
    
    loan = db.query(LoanApplication).filter(
        LoanApplication.id == loan_application_id
    ).first()
    
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan application not found"
        )
    
    try:
        compliance = UnderwritingPolicyService.check_policy_compliance(
            db=db,
            policy_id=policy_id,
            loan=loan
        )
        
        return {
            "success": True,
            "compliance": compliance
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ========================================================================
# Pipeline Management Endpoints
# ========================================================================

@router.post("/pipeline", status_code=status.HTTP_201_CREATED)
def add_to_pipeline(
    request: AddToPipelineRequest,
    db: Session = Depends(get_db)
):
    """Add loan to pipeline"""
    try:
        pipeline_item = LoanPipelineService.add_to_pipeline(
            db=db,
            **request.model_dump()
        )
        
        return {
            "success": True,
            "pipeline_item": {
                "id": str(pipeline_item.id),
                "loan_application_id": str(pipeline_item.loan_application_id),
                "pipeline_stage": pipeline_item.pipeline_stage,
                "priority": pipeline_item.priority,
                "assigned_underwriter": str(pipeline_item.assigned_underwriter) if pipeline_item.assigned_underwriter else None
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add to pipeline: {str(e)}"
        )


@router.get("/pipeline", status_code=status.HTTP_200_OK)
def get_pipeline(
    organization_id: UUID,
    stage: Optional[str] = None,
    assigned_to: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """Get pipeline items"""
    pipeline = LoanPipelineService.get_pipeline(
        db=db,
        organization_id=organization_id,
        stage=stage,
        assigned_to=assigned_to
    )
    
    return {
        "success": True,
        "count": len(pipeline),
        "pipeline": [
            {
                "id": str(item.id),
                "loan_application_id": str(item.loan_application_id),
                "pipeline_stage": item.pipeline_stage,
                "priority": item.priority,
                "days_in_current_stage": item.days_in_current_stage,
                "target_close_date": item.target_close_date.isoformat() if item.target_close_date else None,
                "assigned_underwriter": str(item.assigned_underwriter) if item.assigned_underwriter else None
            }
            for item in pipeline
        ]
    }


@router.put("/pipeline/{pipeline_id}/stage", status_code=status.HTTP_200_OK)
def update_pipeline_stage(
    pipeline_id: UUID,
    new_stage: str,
    db: Session = Depends(get_db)
):
    """Update pipeline stage"""
    item = LoanPipelineService.update_stage(db, pipeline_id, new_stage)
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline item not found"
        )
    
    return {
        "success": True,
        "pipeline_item": {
            "id": str(item.id),
            "pipeline_stage": item.pipeline_stage,
            "days_in_current_stage": item.days_in_current_stage
        }
    }


@router.get("/pipeline/metrics", status_code=status.HTTP_200_OK)
def get_pipeline_metrics(
    organization_id: UUID,
    db: Session = Depends(get_db)
):
    """Get pipeline metrics"""
    metrics = LoanPipelineService.get_pipeline_metrics(db, organization_id)
    
    return {
        "success": True,
        "metrics": metrics
    }


# ========================================================================
# Credit Decision Endpoints
# ========================================================================

@router.post("/decisions", status_code=status.HTTP_201_CREATED)
def record_credit_decision(
    request: RecordDecisionRequest,
    decided_by: UUID,
    db: Session = Depends(get_db)
):
    """Record a credit decision"""
    try:
        decision = CreditDecisionService.record_decision(
            db=db,
            decided_by=decided_by,
            **request.model_dump()
        )
        
        return {
            "success": True,
            "decision": {
                "id": str(decision.id),
                "loan_application_id": str(decision.loan_application_id),
                "decision": decision.decision,
                "approved_amount": float(decision.approved_amount) if decision.approved_amount else None,
                "approved_rate": float(decision.approved_rate) if decision.approved_rate else None,
                "approved_term": decision.approved_term,
                "conditions": decision.conditions,
                "decline_reason": decision.decline_reason,
                "decided_at": decision.created_at.isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record decision: {str(e)}"
        )


@router.get("/decisions/{loan_id}", status_code=status.HTTP_200_OK)
def get_credit_decision(
    loan_id: UUID,
    db: Session = Depends(get_db)
):
    """Get credit decision for a loan"""
    decision = CreditDecisionService.get_decision(db, loan_id)
    
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No credit decision found for this loan"
        )
    
    return {
        "success": True,
        "decision": {
            "id": str(decision.id),
            "loan_application_id": str(decision.loan_application_id),
            "decision": decision.decision,
            "decision_rationale": decision.decision_rationale,
            "approved_amount": float(decision.approved_amount) if decision.approved_amount else None,
            "approved_rate": float(decision.approved_rate) if decision.approved_rate else None,
            "approved_term": decision.approved_term,
            "conditions": decision.conditions,
            "decline_reason": decision.decline_reason,
            "decided_at": decision.created_at.isoformat()
        }
    }


@router.get("/decisions/metrics", status_code=status.HTTP_200_OK)
def get_decision_metrics(
    organization_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Get decision metrics"""
    metrics = CreditDecisionService.get_decision_metrics(
        db=db,
        organization_id=organization_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return {
        "success": True,
        "metrics": metrics
    }
