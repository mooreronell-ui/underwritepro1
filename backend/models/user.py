"""
User and Organization models for dual-tier system
"""

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from .base import Base, TimestampMixin, UUIDMixin


class AccountType(str, enum.Enum):
    """Account type enum"""
    BROKER = "broker"
    LENDER = "lender"


class UserRole(str, enum.Enum):
    """User role enum"""
    ADMIN = "admin"
    LOAN_OFFICER = "loan_officer"
    UNDERWRITER = "underwriter"
    PROCESSOR = "processor"
    VIEWER = "viewer"


class UserStatus(str, enum.Enum):
    """User status enum"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class SubscriptionPlan(str, enum.Enum):
    """Subscription plan enum"""
    FREE_TRIAL = "free_trial"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    """Subscription status enum"""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"


class Organization(Base, UUIDMixin, TimestampMixin):
    """
    Organization model - represents a broker firm or lender
    """
    __tablename__ = "organizations"
    
    # Basic Info
    name = Column(String(255), nullable=False)
    type = Column(SQLEnum(AccountType), nullable=False)
    
    # Identification
    tax_id = Column(String(50))
    nmls_number = Column(String(50))  # For brokers
    
    # Address
    address = Column(String(500))
    city = Column(String(100))
    state = Column(String(2))
    zip = Column(String(10))
    
    # Contact
    phone = Column(String(50))
    email = Column(String(255))
    website = Column(String(255))
    
    # Subscription
    subscription_plan = Column(SQLEnum(SubscriptionPlan), default=SubscriptionPlan.FREE_TRIAL)
    subscription_status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.TRIALING)
    stripe_customer_id = Column(String(255))
    stripe_subscription_id = Column(String(255))
    
    # Features (JSON for flexible tier-based features)
    features = Column(JSON, default=dict)
    
    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    loan_applications = relationship("LoanApplication", back_populates="organization")
    
    def __repr__(self):
        return f"<Organization(name='{self.name}', type='{self.type}')>"


class User(Base, UUIDMixin, TimestampMixin):
    """
    User model - represents individual users (brokers, loan officers, underwriters, etc.)
    """
    __tablename__ = "users"
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50))
    
    # Account
    account_type = Column(SQLEnum(AccountType), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.LOAN_OFFICER)
    status = Column(SQLEnum(UserStatus), default=UserStatus.ACTIVE)
    
    # Organization
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))
    
    # Preferences
    preferences = Column(JSON, default=dict)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    created_loans = relationship(
        "LoanApplication",
        foreign_keys="LoanApplication.created_by",
        back_populates="creator"
    )
    assigned_loans = relationship(
        "LoanApplication",
        foreign_keys="LoanApplication.assigned_to",
        back_populates="assignee"
    )
    
    def __repr__(self):
        return f"<User(email='{self.email}', role='{self.role}')>"
    
    @property
    def is_broker(self):
        """Check if user is a broker"""
        return self.account_type == AccountType.BROKER
    
    @property
    def is_lender(self):
        """Check if user is a lender"""
        return self.account_type == AccountType.LENDER
    
    @property
    def is_admin(self):
        """Check if user is an admin"""
        return self.role == UserRole.ADMIN
    
    @property
    def is_underwriter(self):
        """Check if user is an underwriter"""
        return self.role == UserRole.UNDERWRITER
