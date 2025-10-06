"""
Document models for file management
"""

from sqlalchemy import Column, String, ForeignKey, Integer, Boolean, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from .base import Base, TimestampMixin, UUIDMixin


class DocumentType(str, enum.Enum):
    """Document type enum"""
    FINANCIAL_STATEMENT = "financial_statement"
    TAX_RETURN = "tax_return"
    BANK_STATEMENT = "bank_statement"
    RENT_ROLL = "rent_roll"
    OPERATING_STATEMENT = "operating_statement"
    APPRAISAL = "appraisal"
    ENVIRONMENTAL_REPORT = "environmental_report"
    TITLE_REPORT = "title_report"
    INSURANCE = "insurance"
    CREDIT_REPORT = "credit_report"
    PERSONAL_FINANCIAL_STATEMENT = "personal_financial_statement"
    BUSINESS_PLAN = "business_plan"
    LEASE_AGREEMENT = "lease_agreement"
    PURCHASE_AGREEMENT = "purchase_agreement"
    ARTICLES_OF_INCORPORATION = "articles_of_incorporation"
    OPERATING_AGREEMENT = "operating_agreement"
    OTHER = "other"


class DocumentStatus(str, enum.Enum):
    """Document status enum"""
    PENDING = "pending"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class DocumentCategory(str, enum.Enum):
    """Document category enum"""
    FINANCIAL = "financial"
    LEGAL = "legal"
    PROPERTY = "property"
    CREDIT = "credit"
    COMPLIANCE = "compliance"
    OTHER = "other"


class Document(Base, UUIDMixin, TimestampMixin):
    """
    Document model - represents uploaded files and documents
    """
    __tablename__ = "documents"
    
    # Foreign Key
    loan_application_id = Column(UUID(as_uuid=True), ForeignKey("loan_applications.id", ondelete="CASCADE"), nullable=False)
    
    # Document Info
    document_type = Column(String(100), nullable=False)
    document_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)  # bytes
    mime_type = Column(String(100))
    
    # Classification
    year = Column(Integer)
    category = Column(String(50))
    
    # Status
    status = Column(String(20), default=DocumentStatus.PENDING.value)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    reviewed_at = Column(DateTime)
    review_notes = Column(String(1000))
    
    # OCR & Extraction
    ocr_completed = Column(Boolean, default=False)
    extracted_data = Column(JSON)
    
    # Metadata
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationships
    loan_application = relationship("LoanApplication", back_populates="documents")
    uploader = relationship("User", foreign_keys=[uploaded_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    
    def __repr__(self):
        return f"<Document(name='{self.document_name}', type='{self.document_type}')>"
    
    @property
    def is_reviewed(self):
        """Check if document has been reviewed"""
        return self.status in [DocumentStatus.REVIEWED.value, DocumentStatus.APPROVED.value, DocumentStatus.REJECTED.value]
    
    @property
    def is_approved(self):
        """Check if document is approved"""
        return self.status == DocumentStatus.APPROVED.value
    
    @property
    def file_size_mb(self):
        """Get file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0
