"""
Loan Application Pydantic schemas
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal

from models.loan import LoanType, PropertyType, LoanStatus, LoanStage


# ============================================================================
# Loan Application Schemas
# ============================================================================

class LoanApplicationBase(BaseModel):
    """Base loan application schema"""
    loan_type: LoanType
    property_type: Optional[PropertyType] = None
    loan_amount: Decimal = Field(..., gt=0, decimal_places=2)
    loan_purpose: Optional[str] = None
    requested_term: Optional[int] = Field(None, gt=0, le=360)  # months
    requested_amortization: Optional[int] = Field(None, gt=0, le=360)  # months
    requested_rate: Optional[Decimal] = Field(None, ge=0, le=100, decimal_places=3)
    estimated_closing_date: Optional[date] = None
    
    @validator('requested_amortization')
    def validate_amortization(cls, v, values):
        """Validate amortization is >= term"""
        if v and 'requested_term' in values and values['requested_term']:
            if v < values['requested_term']:
                raise ValueError('Amortization must be >= loan term')
        return v


class LoanApplicationCreate(LoanApplicationBase):
    """Schema for creating loan application"""
    organization_id: UUID
    
    class Config:
        json_schema_extra = {
            "example": {
                "loan_type": "owner_occupied_cre",
                "property_type": "office",
                "loan_amount": 500000.00,
                "loan_purpose": "Purchase and renovate office building for business operations",
                "requested_term": 120,
                "requested_amortization": 300,
                "requested_rate": 7.500,
                "estimated_closing_date": "2025-12-31",
                "organization_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }


class LoanApplicationUpdate(BaseModel):
    """Schema for updating loan application"""
    loan_type: Optional[LoanType] = None
    property_type: Optional[PropertyType] = None
    loan_amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    loan_purpose: Optional[str] = None
    requested_term: Optional[int] = Field(None, gt=0, le=360)
    requested_amortization: Optional[int] = Field(None, gt=0, le=360)
    requested_rate: Optional[Decimal] = Field(None, ge=0, le=100, decimal_places=3)
    estimated_closing_date: Optional[date] = None
    status: Optional[LoanStatus] = None
    stage: Optional[LoanStage] = None
    assigned_to: Optional[UUID] = None


class LoanApplicationResponse(LoanApplicationBase):
    """Schema for loan application response"""
    id: UUID
    application_number: str
    status: LoanStatus
    stage: LoanStage
    created_by: Optional[UUID] = None
    organization_id: UUID
    assigned_to: Optional[UUID] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    funded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class LoanApplicationList(BaseModel):
    """Schema for loan application list item (summary)"""
    id: UUID
    application_number: str
    loan_type: LoanType
    loan_amount: Decimal
    status: LoanStatus
    stage: LoanStage
    borrower_name: Optional[str] = None  # Computed field
    property_address: Optional[str] = None  # Computed field
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class LoanApplicationDetail(LoanApplicationResponse):
    """Schema for detailed loan application with related data"""
    # Will be populated by includes
    borrower: Optional[dict] = None
    guarantors: Optional[list] = None
    property_info: Optional[dict] = None
    financial_ratios: Optional[dict] = None
    risk_assessment: Optional[dict] = None
    documents_count: int = 0
    
    class Config:
        from_attributes = True


# ============================================================================
# Loan Application Statistics
# ============================================================================

class LoanApplicationStats(BaseModel):
    """Schema for loan application statistics"""
    total_loans: int = 0
    pending_loans: int = 0
    in_review_loans: int = 0
    approved_loans: int = 0
    declined_loans: int = 0
    total_loan_amount: Decimal = Decimal('0.00')
    average_loan_amount: Decimal = Decimal('0.00')
    
    # By loan type
    by_loan_type: dict = {}
    
    # By status
    by_status: dict = {}
    
    # By stage
    by_stage: dict = {}


# ============================================================================
# Loan Submission (for multi-step intake)
# ============================================================================

class LoanIntakeStep1(BaseModel):
    """Step 1: Basic loan information"""
    loan_type: LoanType
    property_type: Optional[PropertyType] = None
    loan_amount: Decimal = Field(..., gt=0)
    loan_purpose: Optional[str] = None


class LoanIntakeStep2(BaseModel):
    """Step 2: Loan terms"""
    requested_term: int = Field(..., gt=0, le=360)
    requested_amortization: int = Field(..., gt=0, le=360)
    requested_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    estimated_closing_date: Optional[date] = None


class LoanIntakeComplete(LoanApplicationCreate):
    """Complete loan intake (all steps)"""
    pass
