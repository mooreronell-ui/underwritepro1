"""
Property Pydantic schemas
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal


# ============================================================================
# Property Schemas
# ============================================================================

class PropertyBase(BaseModel):
    """Base property schema"""
    property_address: str = Field(..., min_length=1)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=2)
    zip: Optional[str] = Field(None, max_length=10)
    county: Optional[str] = Field(None, max_length=100)
    apn: Optional[str] = Field(None, max_length=50)
    
    # Property type
    property_type: Optional[str] = Field(None, max_length=50)
    property_subtype: Optional[str] = Field(None, max_length=50)
    
    # Physical characteristics
    square_footage: Optional[int] = Field(None, gt=0)
    rentable_square_footage: Optional[int] = Field(None, gt=0)
    lot_size: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    year_built: Optional[int] = Field(None, ge=1800, le=2100)
    year_renovated: Optional[int] = Field(None, ge=1800, le=2100)
    num_units: Optional[int] = Field(None, gt=0)
    num_stories: Optional[int] = Field(None, gt=0)
    parking_spaces: Optional[int] = Field(None, ge=0)
    zoning: Optional[str] = Field(None, max_length=50)
    
    # Valuation
    purchase_price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    appraised_value: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    appraisal_date: Optional[date] = None
    appraisal_type: Optional[str] = Field(None, max_length=50)
    
    # Owner occupancy
    is_owner_occupied: bool = False
    owner_occupied_percentage: Optional[Decimal] = Field(None, ge=0, le=100, decimal_places=2)
    
    # Existing financing
    existing_loan_balance: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    existing_lender: Optional[str] = Field(None, max_length=255)
    existing_rate: Optional[Decimal] = Field(None, ge=0, le=100, decimal_places=3)
    existing_payment: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    
    @validator('state')
    def validate_state(cls, v):
        """Validate state code"""
        if v and len(v) != 2:
            raise ValueError('State must be 2-letter code')
        return v.upper() if v else v


class PropertyCreate(PropertyBase):
    """Schema for creating property"""
    loan_application_id: UUID


class PropertyUpdate(BaseModel):
    """Schema for updating property"""
    property_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    county: Optional[str] = None
    apn: Optional[str] = None
    property_type: Optional[str] = None
    property_subtype: Optional[str] = None
    square_footage: Optional[int] = None
    rentable_square_footage: Optional[int] = None
    lot_size: Optional[Decimal] = None
    year_built: Optional[int] = None
    year_renovated: Optional[int] = None
    num_units: Optional[int] = None
    num_stories: Optional[int] = None
    parking_spaces: Optional[int] = None
    zoning: Optional[str] = None
    purchase_price: Optional[Decimal] = None
    appraised_value: Optional[Decimal] = None
    appraisal_date: Optional[date] = None
    appraisal_type: Optional[str] = None
    is_owner_occupied: Optional[bool] = None
    owner_occupied_percentage: Optional[Decimal] = None
    existing_loan_balance: Optional[Decimal] = None
    existing_lender: Optional[str] = None
    existing_rate: Optional[Decimal] = None
    existing_payment: Optional[Decimal] = None


class PropertyResponse(PropertyBase):
    """Schema for property response"""
    id: UUID
    loan_application_id: UUID
    created_at: datetime
    updated_at: datetime
    
    # Computed field
    ltv: Optional[Decimal] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# Property Financials Schemas
# ============================================================================

class PropertyFinancialsBase(BaseModel):
    """Base property financials schema"""
    year: int = Field(..., ge=1900, le=2100)
    
    # Income
    gross_potential_rent: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    vacancy_loss: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    other_income: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    effective_gross_income: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    
    # Expenses
    property_taxes: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    insurance: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    property_management: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    utilities: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    repairs_maintenance: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    landscaping: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    trash_removal: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    pest_control: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    marketing: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    legal_professional: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    replacement_reserves: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    other_expenses: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    total_operating_expenses: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    
    # NOI
    net_operating_income: Optional[Decimal] = Field(None, decimal_places=2)


class PropertyFinancialsCreate(PropertyFinancialsBase):
    """Schema for creating property financials"""
    property_id: UUID


class PropertyFinancialsResponse(PropertyFinancialsBase):
    """Schema for property financials response"""
    id: UUID
    property_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Rent Roll Schemas
# ============================================================================

class RentRollBase(BaseModel):
    """Base rent roll schema"""
    unit_number: Optional[str] = Field(None, max_length=50)
    tenant_name: Optional[str] = Field(None, max_length=255)
    square_footage: Optional[int] = Field(None, gt=0)
    
    # Lease terms
    lease_start_date: Optional[date] = None
    lease_end_date: Optional[date] = None
    lease_type: Optional[str] = Field(None, max_length=50)
    
    # Rent
    current_monthly_rent: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    market_monthly_rent: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    security_deposit: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    
    # Additional terms
    tenant_improvements: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    free_rent_months: Optional[int] = Field(None, ge=0)
    rent_escalation_percentage: Optional[Decimal] = Field(None, ge=0, le=100, decimal_places=2)
    options_to_renew: Optional[int] = Field(None, ge=0)
    
    # Status
    occupancy_status: Optional[str] = Field(None, max_length=20)


class RentRollCreate(RentRollBase):
    """Schema for creating rent roll entry"""
    property_id: UUID


class RentRollResponse(RentRollBase):
    """Schema for rent roll response"""
    id: UUID
    property_id: UUID
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    annual_rent: Optional[Decimal] = None
    is_vacant: bool = False
    
    class Config:
        from_attributes = True
