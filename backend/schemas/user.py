"""
User and Organization Pydantic schemas
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict
from datetime import datetime
from uuid import UUID

from models.user import AccountType, UserRole, UserStatus, SubscriptionPlan, SubscriptionStatus


# ============================================================================
# Organization Schemas
# ============================================================================

class OrganizationBase(BaseModel):
    """Base organization schema"""
    name: str = Field(..., min_length=1, max_length=255)
    type: AccountType
    tax_id: Optional[str] = Field(None, max_length=50)
    nmls_number: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=2)
    zip: Optional[str] = Field(None, max_length=10)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    website: Optional[str] = Field(None, max_length=255)


class OrganizationCreate(OrganizationBase):
    """Schema for creating organization"""
    subscription_plan: SubscriptionPlan = SubscriptionPlan.FREE_TRIAL


class OrganizationUpdate(BaseModel):
    """Schema for updating organization"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    tax_id: Optional[str] = None
    nmls_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    subscription_plan: Optional[SubscriptionPlan] = None
    subscription_status: Optional[SubscriptionStatus] = None


class OrganizationResponse(OrganizationBase):
    """Schema for organization response"""
    id: UUID
    subscription_plan: SubscriptionPlan
    subscription_status: SubscriptionStatus
    features: Dict = {}
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# User Schemas
# ============================================================================

class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    account_type: AccountType
    role: UserRole = UserRole.LOAN_OFFICER


class UserCreate(UserBase):
    """Schema for creating user"""
    password: str = Field(..., min_length=8)
    organization_id: Optional[UUID] = None
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseModel):
    """Schema for updating user"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    preferences: Optional[Dict] = None


class UserResponse(UserBase):
    """Schema for user response"""
    id: UUID
    status: UserStatus
    organization_id: Optional[UUID] = None
    preferences: Dict = {}
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserWithOrganization(UserResponse):
    """Schema for user with organization details"""
    organization: Optional[OrganizationResponse] = None
    
    class Config:
        from_attributes = True
