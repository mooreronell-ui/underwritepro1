"""
Broker-specific models for deal origination and packaging
"""

from sqlalchemy import Column, String, ForeignKey, Numeric, Boolean, JSON, DateTime, Date, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from .base import Base, TimestampMixin, UUIDMixin


class RelationshipStatus(str, enum.Enum):
    """Relationship status enum"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class SubmissionStatus(str, enum.Enum):
    """Submission status enum"""
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"


class QuoteStatus(str, enum.Enum):
    """Quote status enum"""
    ACTIVE = "active"
    EXPIRED = "expired"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class CommissionStatus(str, enum.Enum):
    """Commission status enum"""
    PENDING = "pending"
    PAID = "paid"
    DISPUTED = "disputed"


class LenderNetwork(Base, UUIDMixin, TimestampMixin):
    """
    Lender Network model - broker's network of lenders
    """
    __tablename__ = "lender_network"
    
    # Foreign Keys
    broker_organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    lender_organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Relationship
    relationship_status = Column(String(20), default=RelationshipStatus.ACTIVE.value)
    approval_status = Column(String(20))  # 'approved', 'pending', 'rejected'
    
    # Terms
    commission_split = Column(Numeric(5, 2))  # Percentage broker receives
    preferred_lender = Column(Boolean, default=False)
    
    # Loan Products
    loan_products = Column(JSON)  # Array of loan products this lender offers
    
    # Contact
    primary_contact_name = Column(String(255))
    primary_contact_email = Column(String(255))
    primary_contact_phone = Column(String(50))
    
    # Notes
    notes = Column(Text)
    
    # Relationships
    broker_organization = relationship("Organization", foreign_keys=[broker_organization_id])
    lender_organization = relationship("Organization", foreign_keys=[lender_organization_id])
    
    def __repr__(self):
        return f"<LenderNetwork(broker={self.broker_organization_id}, lender={self.lender_organization_id})>"


class LoanSubmission(Base, UUIDMixin, TimestampMixin):
    """
    Loan Submission model - broker submitting loan to lender
    """
    __tablename__ = "loan_submissions"
    
    # Foreign Keys
    loan_application_id = Column(UUID(as_uuid=True), ForeignKey("loan_applications.id"), nullable=False)
    broker_organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    lender_organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Submission
    submitted_at = Column(DateTime, nullable=False)
    submitted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Status
    status = Column(String(50), default=SubmissionStatus.SUBMITTED.value)
    lender_response = Column(Text)
    responded_at = Column(DateTime)
    
    # Terms Offered
    approved_amount = Column(Numeric(15, 2))
    approved_rate = Column(Numeric(5, 3))
    approved_term = Column(Integer)
    conditions = Column(Text)
    
    # Commission
    commission_rate = Column(Numeric(5, 3))
    commission_amount = Column(Numeric(15, 2))
    commission_paid = Column(Boolean, default=False)
    commission_paid_date = Column(Date)
    
    # Relationships
    loan_application = relationship("LoanApplication", back_populates="submissions")
    broker_organization = relationship("Organization", foreign_keys=[broker_organization_id])
    lender_organization = relationship("Organization", foreign_keys=[lender_organization_id])
    submitter = relationship("User", foreign_keys=[submitted_by])
    
    def __repr__(self):
        return f"<LoanSubmission(loan={self.loan_application_id}, status='{self.status}')>"
    
    @property
    def is_approved(self):
        """Check if submission is approved"""
        return self.status == SubmissionStatus.APPROVED.value
    
    @property
    def is_pending(self):
        """Check if submission is pending"""
        return self.status in [SubmissionStatus.SUBMITTED.value, SubmissionStatus.IN_REVIEW.value]


class RateQuote(Base, UUIDMixin, TimestampMixin):
    """
    Rate Quote model - lender's quote to broker
    """
    __tablename__ = "rate_quotes"
    
    # Foreign Keys
    loan_application_id = Column(UUID(as_uuid=True), ForeignKey("loan_applications.id"), nullable=False)
    lender_organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Quote Details
    loan_amount = Column(Numeric(15, 2), nullable=False)
    interest_rate = Column(Numeric(5, 3), nullable=False)
    loan_term = Column(Integer, nullable=False)
    amortization = Column(Integer)
    rate_type = Column(String(20))  # 'fixed', 'variable'
    
    # Fees
    origination_fee = Column(Numeric(15, 2))
    processing_fee = Column(Numeric(15, 2))
    underwriting_fee = Column(Numeric(15, 2))
    other_fees = Column(Numeric(15, 2))
    total_fees = Column(Numeric(15, 2))
    
    # Terms
    prepayment_penalty = Column(Text)
    special_conditions = Column(Text)
    
    # Validity
    quote_date = Column(Date, nullable=False)
    expiration_date = Column(Date, nullable=False)
    status = Column(String(20), default=QuoteStatus.ACTIVE.value)
    
    # Relationships
    loan_application = relationship("LoanApplication", back_populates="rate_quotes")
    lender_organization = relationship("Organization", foreign_keys=[lender_organization_id])
    
    def __repr__(self):
        return f"<RateQuote(amount=${self.loan_amount}, rate={self.interest_rate}%)>"
    
    @property
    def is_valid(self):
        """Check if quote is still valid"""
        from datetime import date
        return self.status == QuoteStatus.ACTIVE.value and self.expiration_date >= date.today()
    
    @property
    def monthly_payment(self):
        """Calculate estimated monthly payment (P&I only)"""
        if self.loan_amount and self.interest_rate and self.amortization:
            monthly_rate = (self.interest_rate / 100) / 12
            num_payments = self.amortization
            if monthly_rate > 0:
                payment = self.loan_amount * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
                return round(payment, 2)
        return None


class BrokerCommission(Base, UUIDMixin, TimestampMixin):
    """
    Broker Commission model - tracks commissions earned
    """
    __tablename__ = "broker_commissions"
    
    # Foreign Keys
    loan_application_id = Column(UUID(as_uuid=True), ForeignKey("loan_applications.id"), nullable=False)
    broker_organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    broker_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))  # Individual loan officer
    
    # Commission Details
    commission_type = Column(String(50))  # 'origination', 'servicing', 'referral'
    commission_rate = Column(Numeric(5, 3), nullable=False)
    commission_amount = Column(Numeric(15, 2), nullable=False)
    
    # Payment
    payment_status = Column(String(20), default=CommissionStatus.PENDING.value)
    payment_date = Column(Date)
    payment_method = Column(String(50))
    payment_reference = Column(String(100))
    
    # Split (if applicable)
    split_with_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    split_percentage = Column(Numeric(5, 2))
    split_amount = Column(Numeric(15, 2))
    
    # Notes
    notes = Column(Text)
    
    # Relationships
    loan_application = relationship("LoanApplication", back_populates="broker_commissions")
    broker_organization = relationship("Organization", foreign_keys=[broker_organization_id])
    broker_user = relationship("User", foreign_keys=[broker_user_id])
    split_with_user = relationship("User", foreign_keys=[split_with_user_id])
    
    def __repr__(self):
        return f"<BrokerCommission(amount=${self.commission_amount}, status='{self.payment_status}')>"
    
    @property
    def is_paid(self):
        """Check if commission has been paid"""
        return self.payment_status == CommissionStatus.PAID.value
    
    @property
    def net_commission(self):
        """Calculate net commission after split"""
        if self.split_amount:
            return self.commission_amount - self.split_amount
        return self.commission_amount
