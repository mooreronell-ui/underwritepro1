"""
Loan Application Schemas for Frontend-Backend Integration
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class LoanApplicationCreate(BaseModel):
    """Schema for creating a new loan application from the frontend"""
    # Loan Details
    loan_type: str
    loan_amount: float
    loan_purpose: str
    term_months: int
    
    # Borrower Info
    borrower_name: str
    borrower_company: Optional[str] = None
    borrower_email: EmailStr
    borrower_phone: str
    borrower_credit_score: Optional[int] = None
    years_in_business: Optional[int] = None
    
    # Property Details
    property_type: str
    property_address: str
    property_city: str
    property_state: str
    property_zip: Optional[str] = None
    property_value: float
    purchase_price: Optional[float] = None
    
    # Financial Info
    annual_revenue: float
    net_income: float
    monthly_debt_service: Optional[float] = None
    down_payment: Optional[float] = None


class LoanApplicationResponse(BaseModel):
    """Schema for loan application response"""
    id: str
    borrower_name: str
    company_name: Optional[str]
    loan_amount: float
    loan_type: str
    loan_purpose: str
    status: str
    property_address: Optional[str]
    property_city: Optional[str]
    property_state: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True


class LoanStatsResponse(BaseModel):
    """Schema for loan statistics"""
    total_loans: int
    total_volume: float
    pending_loans: int
    approved_loans: int
    rejected_loans: int
    average_loan_amount: float
