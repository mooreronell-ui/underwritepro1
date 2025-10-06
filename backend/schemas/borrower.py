"""
Borrower and Guarantor Pydantic schemas
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal


# ============================================================================
# Borrower Schemas
# ============================================================================

class BorrowerBase(BaseModel):
    """Base borrower schema"""
    business_legal_name: str = Field(..., min_length=1, max_length=255)
    business_dba: Optional[str] = Field(None, max_length=255)
    business_structure: Optional[str] = Field(None, max_length=50)
    tax_id: Optional[str] = Field(None, max_length=50)
    date_established: Optional[date] = None
    years_in_business: Optional[Decimal] = Field(None, ge=0, decimal_places=1)
    
    # Industry
    industry: Optional[str] = Field(None, max_length=100)
    naics_code: Optional[str] = Field(None, max_length=10)
    num_employees: Optional[int] = Field(None, ge=0)
    annual_revenue: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    business_description: Optional[str] = None
    
    # Contact
    business_address: Optional[str] = None
    business_city: Optional[str] = Field(None, max_length=100)
    business_state: Optional[str] = Field(None, max_length=2)
    business_zip: Optional[str] = Field(None, max_length=10)
    business_phone: Optional[str] = Field(None, max_length=50)
    business_email: Optional[EmailStr] = None
    website: Optional[str] = Field(None, max_length=255)
    
    # Credit
    business_credit_score: Optional[int] = Field(None, ge=0, le=100)
    business_credit_report_date: Optional[date] = None
    
    @validator('business_state')
    def validate_state(cls, v):
        """Validate state code"""
        if v and len(v) != 2:
            raise ValueError('State must be 2-letter code')
        return v.upper() if v else v


class BorrowerCreate(BorrowerBase):
    """Schema for creating borrower"""
    loan_application_id: UUID
    
    class Config:
        json_schema_extra = {
            "example": {
                "business_legal_name": "Tech Innovations LLC",
                "business_dba": "TechInno",
                "business_structure": "llc",
                "tax_id": "12-3456789",
                "date_established": "2015-01-15",
                "years_in_business": 10.0,
                "industry": "Software Development",
                "naics_code": "541511",
                "num_employees": 25,
                "annual_revenue": 5000000.00,
                "business_description": "Custom software development for enterprise clients",
                "business_address": "123 Tech Street",
                "business_city": "San Francisco",
                "business_state": "CA",
                "business_zip": "94105",
                "business_phone": "(415) 555-0100",
                "business_email": "info@techinno.com",
                "website": "https://www.techinno.com",
                "business_credit_score": 75,
                "loan_application_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }


class BorrowerUpdate(BaseModel):
    """Schema for updating borrower"""
    business_legal_name: Optional[str] = None
    business_dba: Optional[str] = None
    business_structure: Optional[str] = None
    tax_id: Optional[str] = None
    date_established: Optional[date] = None
    years_in_business: Optional[Decimal] = None
    industry: Optional[str] = None
    naics_code: Optional[str] = None
    num_employees: Optional[int] = None
    annual_revenue: Optional[Decimal] = None
    business_description: Optional[str] = None
    business_address: Optional[str] = None
    business_city: Optional[str] = None
    business_state: Optional[str] = None
    business_zip: Optional[str] = None
    business_phone: Optional[str] = None
    business_email: Optional[EmailStr] = None
    website: Optional[str] = None
    business_credit_score: Optional[int] = None
    business_credit_report_date: Optional[date] = None


class BorrowerResponse(BorrowerBase):
    """Schema for borrower response"""
    id: UUID
    loan_application_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Guarantor Schemas
# ============================================================================

class GuarantorBase(BaseModel):
    """Base guarantor schema"""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    
    # Business relationship
    ownership_percentage: Optional[Decimal] = Field(None, ge=0, le=100, decimal_places=2)
    title: Optional[str] = Field(None, max_length=100)
    years_with_company: Optional[Decimal] = Field(None, ge=0, decimal_places=1)
    
    # Contact
    home_address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=2)
    zip: Optional[str] = Field(None, max_length=10)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    
    # Credit
    credit_score: Optional[int] = Field(None, ge=300, le=850)
    credit_report_date: Optional[date] = None
    
    # Financials
    annual_income: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    monthly_debt_payments: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    net_worth: Optional[Decimal] = Field(None, decimal_places=2)
    liquid_assets: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    
    @validator('state')
    def validate_state(cls, v):
        """Validate state code"""
        if v and len(v) != 2:
            raise ValueError('State must be 2-letter code')
        return v.upper() if v else v


class GuarantorCreate(GuarantorBase):
    """Schema for creating guarantor"""
    loan_application_id: UUID
    ssn_encrypted: Optional[str] = None  # Should be encrypted before storage
    
    class Config:
        json_schema_extra = {
            "example": {
                "first_name": "John",
                "last_name": "Smith",
                "date_of_birth": "1975-06-15",
                "ownership_percentage": 60.00,
                "title": "CEO",
                "years_with_company": 10.0,
                "home_address": "456 Residential Ave",
                "city": "San Francisco",
                "state": "CA",
                "zip": "94105",
                "phone": "(415) 555-0200",
                "email": "john.smith@example.com",
                "credit_score": 750,
                "annual_income": 250000.00,
                "monthly_debt_payments": 5000.00,
                "net_worth": 2000000.00,
                "liquid_assets": 500000.00,
                "loan_application_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }


class GuarantorUpdate(BaseModel):
    """Schema for updating guarantor"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    ownership_percentage: Optional[Decimal] = None
    title: Optional[str] = None
    years_with_company: Optional[Decimal] = None
    home_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    credit_score: Optional[int] = None
    credit_report_date: Optional[date] = None
    annual_income: Optional[Decimal] = None
    monthly_debt_payments: Optional[Decimal] = None
    net_worth: Optional[Decimal] = None
    liquid_assets: Optional[Decimal] = None


class GuarantorResponse(GuarantorBase):
    """Schema for guarantor response"""
    id: UUID
    loan_application_id: UUID
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    full_name: Optional[str] = None
    
    class Config:
        from_attributes = True
