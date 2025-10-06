"""
Loan Application models
"""

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, Numeric, Integer, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from .base import Base, TimestampMixin, UUIDMixin


class LoanType(str, enum.Enum):
    """Loan type enum"""
    OWNER_OCCUPIED_CRE = "owner_occupied_cre"
    INVESTMENT_PROPERTY = "investment_property"
    MULTI_FAMILY = "multi_family"
    EQUIPMENT_FINANCING = "equipment_financing"
    BUSINESS_ACQUISITION = "business_acquisition"
    WORKING_CAPITAL = "working_capital"
    LINE_OF_CREDIT = "line_of_credit"
    CONSTRUCTION = "construction"
    DEVELOPMENT = "development"
    SBA_7A = "sba_7a"
    SBA_504 = "sba_504"
    BRIDGE_FINANCING = "bridge_financing"
    MEZZANINE_FINANCING = "mezzanine_financing"


class PropertyType(str, enum.Enum):
    """Property type enum"""
    OFFICE = "office"
    RETAIL = "retail"
    INDUSTRIAL = "industrial"
    WAREHOUSE = "warehouse"
    MULTI_FAMILY = "multi_family"
    MIXED_USE = "mixed_use"
    HOSPITALITY = "hospitality"
    SELF_STORAGE = "self_storage"
    LAND = "land"
    SPECIAL_PURPOSE = "special_purpose"


class LoanStatus(str, enum.Enum):
    """Loan status enum"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    UNDERWRITING = "underwriting"
    APPROVED = "approved"
    APPROVED_WITH_CONDITIONS = "approved_with_conditions"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"
    FUNDED = "funded"
    CLOSED = "closed"


class LoanStage(str, enum.Enum):
    """Loan stage enum"""
    INTAKE = "intake"
    DOCUMENT_COLLECTION = "document_collection"
    FINANCIAL_ANALYSIS = "financial_analysis"
    UNDERWRITING = "underwriting"
    CREDIT_DECISION = "credit_decision"
    APPROVAL = "approval"
    CLOSING = "closing"
    FUNDED = "funded"


class LoanApplication(Base, UUIDMixin, TimestampMixin):
    """
    Loan Application model - core entity for both broker and lender versions
    """
    __tablename__ = "loan_applications"
    
    # Identification
    application_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Loan Type
    loan_type = Column(SQLEnum(LoanType), nullable=False)
    property_type = Column(SQLEnum(PropertyType))
    
    # Ownership
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Loan Request
    loan_amount = Column(Numeric(15, 2), nullable=False)
    loan_purpose = Column(Text)
    requested_term = Column(Integer)  # months
    requested_amortization = Column(Integer)  # months
    requested_rate = Column(Numeric(5, 3))
    estimated_closing_date = Column(DateTime)
    
    # Status
    status = Column(SQLEnum(LoanStatus), default=LoanStatus.DRAFT)
    stage = Column(SQLEnum(LoanStage), default=LoanStage.INTAKE)
    
    # Timestamps
    submitted_at = Column(DateTime)
    approved_at = Column(DateTime)
    funded_at = Column(DateTime)
    
    # Broker-specific fields
    broker_commission_rate = Column(Numeric(5, 3))
    broker_commission_amount = Column(Numeric(15, 2))
    submitted_to_lender_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    
    # Lender-specific fields
    underwriter_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    credit_decision = Column(String(50))  # 'approved', 'declined', 'conditional'
    decision_date = Column(DateTime)
    decision_notes = Column(Text)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_loans")
    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="assigned_loans")
    organization = relationship("Organization", foreign_keys=[organization_id], back_populates="loan_applications")
    submitted_to_lender = relationship("Organization", foreign_keys=[submitted_to_lender_id])
    underwriter = relationship("User", foreign_keys=[underwriter_id])
    
    # Child relationships
    borrower = relationship("Borrower", back_populates="loan_application", uselist=False, cascade="all, delete-orphan")
    guarantors = relationship("Guarantor", back_populates="loan_application", cascade="all, delete-orphan")
    property_info = relationship("Property", back_populates="loan_application", uselist=False, cascade="all, delete-orphan")
    financial_statements = relationship("FinancialStatement", back_populates="loan_application", cascade="all, delete-orphan")
    financial_ratios = relationship("FinancialRatios", back_populates="loan_application", uselist=False, cascade="all, delete-orphan")
    risk_assessment = relationship("RiskAssessment", back_populates="loan_application", uselist=False, cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="loan_application", cascade="all, delete-orphan")
    
    # Broker relationships
    submissions = relationship("LoanSubmission", back_populates="loan_application", cascade="all, delete-orphan")
    rate_quotes = relationship("RateQuote", back_populates="loan_application", cascade="all, delete-orphan")
    broker_commissions = relationship("BrokerCommission", back_populates="loan_application", cascade="all, delete-orphan")
    
    # Lender relationships
    pipeline_entry = relationship("LoanPipeline", back_populates="loan_application", uselist=False, cascade="all, delete-orphan")
    credit_decision_record = relationship("CreditDecision", back_populates="loan_application", uselist=False, cascade="all, delete-orphan")
    servicing_record = relationship("LoanServicing", back_populates="loan_application", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<LoanApplication(number='{self.application_number}', amount=${self.loan_amount})>"
    
    @property
    def is_draft(self):
        """Check if loan is in draft status"""
        return self.status == LoanStatus.DRAFT
    
    @property
    def is_submitted(self):
        """Check if loan has been submitted"""
        return self.status in [
            LoanStatus.SUBMITTED,
            LoanStatus.IN_REVIEW,
            LoanStatus.UNDERWRITING,
            LoanStatus.APPROVED,
            LoanStatus.APPROVED_WITH_CONDITIONS,
            LoanStatus.FUNDED
        ]
    
    @property
    def is_approved(self):
        """Check if loan is approved"""
        return self.status in [LoanStatus.APPROVED, LoanStatus.APPROVED_WITH_CONDITIONS]
    
    @property
    def is_closed(self):
        """Check if loan is closed"""
        return self.status in [LoanStatus.DECLINED, LoanStatus.WITHDRAWN, LoanStatus.FUNDED, LoanStatus.CLOSED]
