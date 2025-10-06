"""
Borrower and Guarantor models
"""

from sqlalchemy import Column, String, ForeignKey, Numeric, Integer, Date, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base, TimestampMixin, UUIDMixin


class Borrower(Base, UUIDMixin, TimestampMixin):
    """
    Borrower model - represents the business entity borrowing
    """
    __tablename__ = "borrowers"
    
    # Foreign Key
    loan_application_id = Column(UUID(as_uuid=True), ForeignKey("loan_applications.id", ondelete="CASCADE"), nullable=False)
    
    # Business Information
    business_legal_name = Column(String(255), nullable=False)
    business_dba = Column(String(255))
    business_structure = Column(String(50))  # 'llc', 'corporation', 's_corp', 'partnership', 'sole_prop'
    tax_id = Column(String(50))
    date_established = Column(Date)
    years_in_business = Column(Numeric(4, 1))
    
    # Industry
    industry = Column(String(100))
    naics_code = Column(String(10))
    num_employees = Column(Integer)
    annual_revenue = Column(Numeric(15, 2))
    business_description = Column(Text)
    
    # Contact Information
    business_address = Column(Text)
    business_city = Column(String(100))
    business_state = Column(String(2))
    business_zip = Column(String(10))
    business_phone = Column(String(50))
    business_email = Column(String(255))
    website = Column(String(255))
    
    # Credit
    business_credit_score = Column(Integer)
    business_credit_report_date = Column(Date)
    
    # Relationships
    loan_application = relationship("LoanApplication", back_populates="borrower")
    
    def __repr__(self):
        return f"<Borrower(name='{self.business_legal_name}')>"


class Guarantor(Base, UUIDMixin, TimestampMixin):
    """
    Guarantor model - represents owners/principals providing personal guarantees
    """
    __tablename__ = "guarantors"
    
    # Foreign Key
    loan_application_id = Column(UUID(as_uuid=True), ForeignKey("loan_applications.id", ondelete="CASCADE"), nullable=False)
    
    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    ssn_encrypted = Column(String(255))  # Encrypted SSN
    date_of_birth = Column(Date)
    
    # Business Relationship
    ownership_percentage = Column(Numeric(5, 2))
    title = Column(String(100))
    years_with_company = Column(Numeric(4, 1))
    
    # Contact Information
    home_address = Column(Text)
    city = Column(String(100))
    state = Column(String(2))
    zip = Column(String(10))
    phone = Column(String(50))
    email = Column(String(255))
    
    # Credit
    credit_score = Column(Integer)
    credit_report_date = Column(Date)
    
    # Personal Financials
    annual_income = Column(Numeric(15, 2))
    monthly_debt_payments = Column(Numeric(15, 2))
    net_worth = Column(Numeric(15, 2))
    liquid_assets = Column(Numeric(15, 2))
    
    # Relationships
    loan_application = relationship("LoanApplication", back_populates="guarantors")
    
    def __repr__(self):
        return f"<Guarantor(name='{self.first_name} {self.last_name}')>"
    
    @property
    def full_name(self):
        """Get full name"""
        return f"{self.first_name} {self.last_name}"
