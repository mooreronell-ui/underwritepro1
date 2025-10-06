"""
Property models for commercial real estate loans
"""

from sqlalchemy import Column, String, ForeignKey, Numeric, Integer, Date, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base, TimestampMixin, UUIDMixin


class Property(Base, UUIDMixin, TimestampMixin):
    """
    Property model - represents the collateral property
    """
    __tablename__ = "properties"
    
    # Foreign Key
    loan_application_id = Column(UUID(as_uuid=True), ForeignKey("loan_applications.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Property Location
    property_address = Column(Text, nullable=False)
    city = Column(String(100))
    state = Column(String(2))
    zip = Column(String(10))
    county = Column(String(100))
    apn = Column(String(50))  # Assessor's Parcel Number
    
    # Property Type (already in loan_application, but kept for convenience)
    property_type = Column(String(50))
    property_subtype = Column(String(50))
    
    # Physical Characteristics
    square_footage = Column(Integer)
    rentable_square_footage = Column(Integer)
    lot_size = Column(Numeric(10, 2))  # acres
    year_built = Column(Integer)
    year_renovated = Column(Integer)
    num_units = Column(Integer)  # For multi-family
    num_stories = Column(Integer)
    parking_spaces = Column(Integer)
    zoning = Column(String(50))
    
    # Valuation
    purchase_price = Column(Numeric(15, 2))
    appraised_value = Column(Numeric(15, 2))
    appraisal_date = Column(Date)
    appraisal_type = Column(String(50))  # 'desktop', 'restricted', 'summary', 'self_contained'
    
    # Owner Occupancy
    is_owner_occupied = Column(Boolean, default=False)
    owner_occupied_percentage = Column(Numeric(5, 2))
    
    # Current Financing
    existing_loan_balance = Column(Numeric(15, 2))
    existing_lender = Column(String(255))
    existing_rate = Column(Numeric(5, 3))
    existing_payment = Column(Numeric(15, 2))
    
    # Relationships
    loan_application = relationship("LoanApplication", back_populates="property_info")
    financials = relationship("PropertyFinancials", back_populates="property_ref", cascade="all, delete-orphan")
    rent_roll = relationship("RentRoll", back_populates="property_ref", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Property(address='{self.property_address}')>"
    
    @property
    def ltv(self):
        """Calculate Loan-to-Value ratio"""
        if self.appraised_value and self.loan_application:
            return (self.loan_application.loan_amount / self.appraised_value) * 100
        return None


class PropertyFinancials(Base, UUIDMixin, TimestampMixin):
    """
    Property Financials model - represents annual income and expenses for investment properties
    """
    __tablename__ = "property_financials"
    
    # Foreign Key
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    
    # Year
    year = Column(Integer, nullable=False)
    
    # Income
    gross_potential_rent = Column(Numeric(15, 2))
    vacancy_loss = Column(Numeric(15, 2))
    other_income = Column(Numeric(15, 2))
    effective_gross_income = Column(Numeric(15, 2))
    
    # Expenses
    property_taxes = Column(Numeric(15, 2))
    insurance = Column(Numeric(15, 2))
    property_management = Column(Numeric(15, 2))
    utilities = Column(Numeric(15, 2))
    repairs_maintenance = Column(Numeric(15, 2))
    landscaping = Column(Numeric(15, 2))
    trash_removal = Column(Numeric(15, 2))
    pest_control = Column(Numeric(15, 2))
    marketing = Column(Numeric(15, 2))
    legal_professional = Column(Numeric(15, 2))
    replacement_reserves = Column(Numeric(15, 2))
    other_expenses = Column(Numeric(15, 2))
    total_operating_expenses = Column(Numeric(15, 2))
    
    # Net Operating Income
    net_operating_income = Column(Numeric(15, 2))
    
    # Relationships
    property_ref = relationship("Property", back_populates="financials")
    
    def __repr__(self):
        return f"<PropertyFinancials(year={self.year}, NOI=${self.net_operating_income})>"
    
    def calculate_noi(self):
        """Calculate Net Operating Income"""
        if self.effective_gross_income and self.total_operating_expenses:
            self.net_operating_income = self.effective_gross_income - self.total_operating_expenses
        return self.net_operating_income


class RentRoll(Base, UUIDMixin, TimestampMixin):
    """
    Rent Roll model - represents individual units/tenants for investment properties
    """
    __tablename__ = "rent_roll"
    
    # Foreign Key
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    
    # Unit/Tenant Information
    unit_number = Column(String(50))
    tenant_name = Column(String(255))
    square_footage = Column(Integer)
    
    # Lease Terms
    lease_start_date = Column(Date)
    lease_end_date = Column(Date)
    lease_type = Column(String(50))  # 'gross', 'modified_gross', 'nnn'
    
    # Rent
    current_monthly_rent = Column(Numeric(15, 2))
    market_monthly_rent = Column(Numeric(15, 2))
    security_deposit = Column(Numeric(15, 2))
    
    # Additional Terms
    tenant_improvements = Column(Numeric(15, 2))
    free_rent_months = Column(Integer)
    rent_escalation_percentage = Column(Numeric(5, 2))
    options_to_renew = Column(Integer)
    
    # Status
    occupancy_status = Column(String(20))  # 'occupied', 'vacant', 'notice'
    
    # Relationships
    property_ref = relationship("Property", back_populates="rent_roll")
    
    def __repr__(self):
        return f"<RentRoll(unit='{self.unit_number}', tenant='{self.tenant_name}')>"
    
    @property
    def annual_rent(self):
        """Calculate annual rent"""
        if self.current_monthly_rent:
            return self.current_monthly_rent * 12
        return None
    
    @property
    def is_vacant(self):
        """Check if unit is vacant"""
        return self.occupancy_status == 'vacant'
