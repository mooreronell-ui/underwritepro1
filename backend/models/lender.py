"""
Lender-specific models for underwriting and portfolio management
"""

from sqlalchemy import Column, String, ForeignKey, Numeric, Boolean, JSON, DateTime, Date, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from .base import Base, TimestampMixin, UUIDMixin


class PolicyStatus(str, enum.Enum):
    """Policy status enum"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"


class CreditDecisionType(str, enum.Enum):
    """Credit decision type enum"""
    APPROVED = "approved"
    APPROVED_WITH_CONDITIONS = "approved_with_conditions"
    DECLINED = "declined"
    SUSPENDED = "suspended"


class PaymentStatus(str, enum.Enum):
    """Payment status enum"""
    CURRENT = "current"
    LATE = "late"
    DEFAULT = "default"
    PAID_OFF = "paid_off"


class CovenantStatus(str, enum.Enum):
    """Covenant status enum"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING = "pending"
    WAIVED = "waived"


class UnderwritingPolicy(Base, UUIDMixin, TimestampMixin):
    """
    Underwriting Policy model - lender-defined underwriting rules
    """
    __tablename__ = "underwriting_policies"
    
    # Foreign Key
    lender_organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Policy Details
    policy_name = Column(String(255), nullable=False)
    loan_type = Column(String(50))  # Which loan type this applies to
    property_type = Column(String(50))
    
    # Minimum Requirements
    min_dscr = Column(Numeric(5, 2))
    min_credit_score = Column(Integer)
    max_ltv = Column(Numeric(5, 2))
    min_years_in_business = Column(Numeric(4, 1))
    min_liquidity = Column(Numeric(15, 2))
    
    # Loan Limits
    min_loan_amount = Column(Numeric(15, 2))
    max_loan_amount = Column(Numeric(15, 2))
    
    # Terms
    max_loan_term = Column(Integer)
    max_amortization = Column(Integer)
    
    # Other Requirements
    personal_guarantee_required = Column(Boolean, default=True)
    environmental_required = Column(Boolean, default=False)
    appraisal_required = Column(Boolean, default=True)
    
    # Pricing Matrix
    pricing_matrix = Column(JSON)  # Risk-based pricing rules
    
    # Status
    status = Column(String(20), default=PolicyStatus.ACTIVE.value)
    effective_date = Column(Date)
    expiration_date = Column(Date)
    
    # Relationships
    lender_organization = relationship("Organization", foreign_keys=[lender_organization_id])
    
    def __repr__(self):
        return f"<UnderwritingPolicy(name='{self.policy_name}', status='{self.status}')>"
    
    @property
    def is_active(self):
        """Check if policy is active"""
        return self.status == PolicyStatus.ACTIVE.value


class LoanPipeline(Base, UUIDMixin, TimestampMixin):
    """
    Loan Pipeline model - lender's view of loan progress
    """
    __tablename__ = "loan_pipeline"
    
    # Foreign Keys
    loan_application_id = Column(UUID(as_uuid=True), ForeignKey("loan_applications.id"), nullable=False, unique=True)
    lender_organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Assignment
    loan_officer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    processor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    underwriter_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Stage Tracking
    current_stage = Column(String(50))
    stage_entered_at = Column(DateTime)
    expected_close_date = Column(Date)
    
    # Milestones
    application_complete_date = Column(Date)
    underwriting_complete_date = Column(Date)
    approval_date = Column(Date)
    docs_out_date = Column(Date)
    funding_date = Column(Date)
    
    # Metrics
    days_in_pipeline = Column(Integer)
    days_in_underwriting = Column(Integer)
    
    # Relationships
    loan_application = relationship("LoanApplication", back_populates="pipeline_entry")
    lender_organization = relationship("Organization", foreign_keys=[lender_organization_id])
    loan_officer = relationship("User", foreign_keys=[loan_officer_id])
    processor = relationship("User", foreign_keys=[processor_id])
    underwriter = relationship("User", foreign_keys=[underwriter_id])
    
    def __repr__(self):
        return f"<LoanPipeline(loan={self.loan_application_id}, stage='{self.current_stage}')>"


class CreditDecision(Base, UUIDMixin, TimestampMixin):
    """
    Credit Decision model - underwriter's credit decision
    """
    __tablename__ = "credit_decisions"
    
    # Foreign Keys
    loan_application_id = Column(UUID(as_uuid=True), ForeignKey("loan_applications.id"), nullable=False, unique=True)
    underwriter_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Decision
    decision = Column(String(50), nullable=False)  # 'approved', 'approved_with_conditions', 'declined', 'suspended'
    decision_date = Column(Date, nullable=False)
    
    # Approved Terms
    approved_amount = Column(Numeric(15, 2))
    approved_rate = Column(Numeric(5, 3))
    approved_term = Column(Integer)
    approved_amortization = Column(Integer)
    
    # Conditions
    conditions_precedent = Column(Text)  # Conditions before closing
    conditions_subsequent = Column(Text)  # Conditions after closing
    
    # Covenants
    financial_covenants = Column(JSON)
    operational_covenants = Column(JSON)
    
    # Collateral
    required_collateral = Column(Text)
    lien_position = Column(String(20))  # 'first', 'second', 'subordinated'
    
    # Guarantees
    guarantees_required = Column(Text)
    
    # Rationale
    strengths = Column(Text)
    weaknesses = Column(Text)
    mitigating_factors = Column(Text)
    decline_reason = Column(Text)  # If declined
    
    # Approval
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))  # Senior underwriter or credit committee
    approval_date = Column(Date)
    
    # Relationships
    loan_application = relationship("LoanApplication", back_populates="credit_decision_record")
    underwriter = relationship("User", foreign_keys=[underwriter_id])
    approver = relationship("User", foreign_keys=[approved_by])
    
    def __repr__(self):
        return f"<CreditDecision(decision='{self.decision}', amount=${self.approved_amount})>"
    
    @property
    def is_approved(self):
        """Check if decision is approved"""
        return self.decision in [CreditDecisionType.APPROVED.value, CreditDecisionType.APPROVED_WITH_CONDITIONS.value]


class LoanServicing(Base, UUIDMixin, TimestampMixin):
    """
    Loan Servicing model - post-closing loan management
    """
    __tablename__ = "loan_servicing"
    
    # Foreign Keys
    loan_application_id = Column(UUID(as_uuid=True), ForeignKey("loan_applications.id"), nullable=False, unique=True)
    lender_organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Loan Details
    funded_amount = Column(Numeric(15, 2), nullable=False)
    funded_date = Column(Date, nullable=False)
    maturity_date = Column(Date, nullable=False)
    interest_rate = Column(Numeric(5, 3), nullable=False)
    payment_amount = Column(Numeric(15, 2), nullable=False)
    payment_frequency = Column(String(20))  # 'monthly', 'quarterly'
    
    # Current Status
    current_balance = Column(Numeric(15, 2))
    principal_paid = Column(Numeric(15, 2), default=0)
    interest_paid = Column(Numeric(15, 2), default=0)
    next_payment_date = Column(Date)
    
    # Performance
    payment_status = Column(String(20), default=PaymentStatus.CURRENT.value)
    days_past_due = Column(Integer, default=0)
    num_late_payments = Column(Integer, default=0)
    
    # Risk Rating
    current_risk_rating = Column(String(20))
    last_risk_review_date = Column(Date)
    
    # Relationships
    loan_application = relationship("LoanApplication", back_populates="servicing_record")
    lender_organization = relationship("Organization", foreign_keys=[lender_organization_id])
    covenant_monitoring = relationship("CovenantMonitoring", back_populates="loan_servicing", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<LoanServicing(balance=${self.current_balance}, status='{self.payment_status}')>"
    
    @property
    def is_current(self):
        """Check if loan is current"""
        return self.payment_status == PaymentStatus.CURRENT.value
    
    @property
    def is_delinquent(self):
        """Check if loan is delinquent"""
        return self.payment_status in [PaymentStatus.LATE.value, PaymentStatus.DEFAULT.value]
    
    @property
    def remaining_term_months(self):
        """Calculate remaining term in months"""
        from datetime import date
        if self.maturity_date:
            delta = self.maturity_date - date.today()
            return max(0, delta.days // 30)
        return None


class CovenantMonitoring(Base, UUIDMixin, TimestampMixin):
    """
    Covenant Monitoring model - tracks loan covenant compliance
    """
    __tablename__ = "covenant_monitoring"
    
    # Foreign Key
    loan_servicing_id = Column(UUID(as_uuid=True), ForeignKey("loan_servicing.id"), nullable=False)
    
    # Covenant Details
    covenant_type = Column(String(50))  # 'financial', 'operational'
    covenant_description = Column(Text, nullable=False)
    measurement_frequency = Column(String(20))  # 'quarterly', 'annually'
    
    # Requirements
    required_value = Column(Numeric(15, 2))
    actual_value = Column(Numeric(15, 2))
    compliance_status = Column(String(20))  # 'compliant', 'non_compliant', 'pending'
    
    # Reporting
    reporting_date = Column(Date)
    next_reporting_date = Column(Date)
    
    # Actions
    violation_noted = Column(Boolean, default=False)
    waiver_granted = Column(Boolean, default=False)
    cure_period_days = Column(Integer)
    
    # Notes
    notes = Column(Text)
    
    # Relationships
    loan_servicing = relationship("LoanServicing", back_populates="covenant_monitoring")
    
    def __repr__(self):
        return f"<CovenantMonitoring(type='{self.covenant_type}', status='{self.compliance_status}')>"
    
    @property
    def is_compliant(self):
        """Check if covenant is compliant"""
        return self.compliance_status == CovenantStatus.COMPLIANT.value


class PortfolioAnalytics(Base, UUIDMixin, TimestampMixin):
    """
    Portfolio Analytics model - aggregated portfolio metrics
    """
    __tablename__ = "portfolio_analytics"
    
    # Foreign Key
    lender_organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    analysis_date = Column(Date, nullable=False)
    
    # Portfolio Composition
    total_loans = Column(Integer)
    total_outstanding_balance = Column(Numeric(15, 2))
    average_loan_size = Column(Numeric(15, 2))
    
    # By Loan Type
    owner_occupied_count = Column(Integer)
    owner_occupied_balance = Column(Numeric(15, 2))
    investment_property_count = Column(Integer)
    investment_property_balance = Column(Numeric(15, 2))
    
    # Performance
    current_loans = Column(Integer)
    late_loans = Column(Integer)
    default_loans = Column(Integer)
    delinquency_rate = Column(Numeric(5, 2))
    
    # Risk
    weighted_average_dscr = Column(Numeric(5, 2))
    weighted_average_ltv = Column(Numeric(5, 2))
    weighted_average_risk_score = Column(Integer)
    
    # Concentrations
    top_industry_concentration = Column(Numeric(5, 2))
    top_geographic_concentration = Column(Numeric(5, 2))
    
    # Additional Metrics
    metrics_data = Column(JSON)
    
    # Relationships
    lender_organization = relationship("Organization", foreign_keys=[lender_organization_id])
    
    def __repr__(self):
        return f"<PortfolioAnalytics(date={self.analysis_date}, total_loans={self.total_loans})>"
    
    @property
    def portfolio_health_score(self):
        """Calculate overall portfolio health score"""
        if self.delinquency_rate is not None and self.weighted_average_dscr:
            # Simple health score: 100 - (delinquency_rate * 10) + (dscr bonus)
            score = 100 - (float(self.delinquency_rate) * 10)
            if float(self.weighted_average_dscr) > 1.25:
                score += 10
            return max(0, min(100, score))
        return None
