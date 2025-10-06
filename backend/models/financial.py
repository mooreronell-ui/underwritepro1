"""
Financial Statement and Analysis models
"""

from sqlalchemy import Column, String, ForeignKey, Numeric, Integer, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

from .base import Base, TimestampMixin, UUIDMixin


class FinancialStatement(Base, UUIDMixin, TimestampMixin):
    """
    Financial Statement model - represents business financial statements
    """
    __tablename__ = "financial_statements"
    
    # Foreign Key
    loan_application_id = Column(UUID(as_uuid=True), ForeignKey("loan_applications.id", ondelete="CASCADE"), nullable=False)
    
    # Statement Info
    statement_type = Column(String(50), nullable=False)  # 'income_statement', 'balance_sheet', 'cash_flow'
    year = Column(Integer, nullable=False)
    is_ytd = Column(Boolean, default=False)
    
    # Income Statement Fields
    revenue = Column(Numeric(15, 2))
    cost_of_goods_sold = Column(Numeric(15, 2))
    gross_profit = Column(Numeric(15, 2))
    operating_expenses = Column(Numeric(15, 2))
    ebitda = Column(Numeric(15, 2))
    depreciation = Column(Numeric(15, 2))
    amortization = Column(Numeric(15, 2))
    interest_expense = Column(Numeric(15, 2))
    taxes = Column(Numeric(15, 2))
    net_income = Column(Numeric(15, 2))
    
    # Balance Sheet Fields
    cash = Column(Numeric(15, 2))
    accounts_receivable = Column(Numeric(15, 2))
    inventory = Column(Numeric(15, 2))
    other_current_assets = Column(Numeric(15, 2))
    total_current_assets = Column(Numeric(15, 2))
    fixed_assets = Column(Numeric(15, 2))
    accumulated_depreciation = Column(Numeric(15, 2))
    intangible_assets = Column(Numeric(15, 2))
    other_long_term_assets = Column(Numeric(15, 2))
    total_assets = Column(Numeric(15, 2))
    
    accounts_payable = Column(Numeric(15, 2))
    short_term_debt = Column(Numeric(15, 2))
    other_current_liabilities = Column(Numeric(15, 2))
    total_current_liabilities = Column(Numeric(15, 2))
    long_term_debt = Column(Numeric(15, 2))
    other_long_term_liabilities = Column(Numeric(15, 2))
    total_liabilities = Column(Numeric(15, 2))
    shareholders_equity = Column(Numeric(15, 2))
    
    # Cash Flow Fields
    operating_cash_flow = Column(Numeric(15, 2))
    investing_cash_flow = Column(Numeric(15, 2))
    financing_cash_flow = Column(Numeric(15, 2))
    net_cash_flow = Column(Numeric(15, 2))
    
    # Metadata
    source = Column(String(50))  # 'uploaded', 'manual', 'ocr_extracted'
    verified = Column(Boolean, default=False)
    
    # Relationships
    loan_application = relationship("LoanApplication", back_populates="financial_statements")
    
    def __repr__(self):
        return f"<FinancialStatement(type='{self.statement_type}', year={self.year})>"


class FinancialRatios(Base, UUIDMixin, TimestampMixin):
    """
    Financial Ratios model - calculated ratios for underwriting analysis
    """
    __tablename__ = "financial_ratios"
    
    # Foreign Key
    loan_application_id = Column(UUID(as_uuid=True), ForeignKey("loan_applications.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Debt Service Coverage Ratios
    global_dscr = Column(Numeric(5, 2))  # For owner-occupied
    business_dscr = Column(Numeric(5, 2))
    property_dscr = Column(Numeric(5, 2))  # For investment properties
    personal_dscr = Column(Numeric(5, 2))
    
    # Leverage Ratios
    ltv = Column(Numeric(5, 2))  # Loan-to-Value
    ltc = Column(Numeric(5, 2))  # Loan-to-Cost (for construction)
    dti = Column(Numeric(5, 2))  # Debt-to-Income
    debt_to_ebitda = Column(Numeric(5, 2))
    
    # Liquidity Ratios
    current_ratio = Column(Numeric(5, 2))
    quick_ratio = Column(Numeric(5, 2))
    cash_ratio = Column(Numeric(5, 2))
    working_capital = Column(Numeric(15, 2))
    
    # Profitability Ratios
    gross_margin = Column(Numeric(5, 2))
    operating_margin = Column(Numeric(5, 2))
    net_margin = Column(Numeric(5, 2))
    ebitda_margin = Column(Numeric(5, 2))
    roa = Column(Numeric(5, 2))  # Return on Assets
    roe = Column(Numeric(5, 2))  # Return on Equity
    
    # Investment Property Ratios
    cap_rate = Column(Numeric(5, 2))  # Capitalization Rate
    debt_yield = Column(Numeric(5, 2))
    cash_on_cash_return = Column(Numeric(5, 2))
    break_even_occupancy = Column(Numeric(5, 2))
    operating_expense_ratio = Column(Numeric(5, 2))
    
    # Metadata
    calculation_method = Column(String(50))
    
    # Relationships
    loan_application = relationship("LoanApplication", back_populates="financial_ratios")
    
    def __repr__(self):
        return f"<FinancialRatios(DSCR={self.global_dscr}, LTV={self.ltv})>"


class RiskAssessment(Base, UUIDMixin, TimestampMixin):
    """
    Risk Assessment model - automated risk scoring and recommendations
    """
    __tablename__ = "risk_assessments"
    
    # Foreign Key
    loan_application_id = Column(UUID(as_uuid=True), ForeignKey("loan_applications.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Overall Risk Score (0-100, higher is better)
    overall_risk_score = Column(Integer)
    risk_rating = Column(String(20))  # 'exceptional', 'strong', 'acceptable', 'marginal', 'substandard', 'unacceptable'
    
    # Component Scores
    dscr_score = Column(Integer)
    credit_score_component = Column(Integer)
    ltv_score = Column(Integer)
    tenure_score = Column(Integer)
    profitability_score = Column(Integer)
    liquidity_score = Column(Integer)
    industry_risk_score = Column(Integer)
    collateral_score = Column(Integer)
    
    # Risk Factors
    risk_factors = Column(JSON)  # Array of identified risks
    mitigating_factors = Column(JSON)  # Array of mitigants
    
    # Recommendation
    automated_decision = Column(String(50))  # 'approve', 'decline', 'refer'
    max_loan_amount = Column(Numeric(15, 2))
    recommended_terms = Column(Text)
    required_conditions = Column(Text)
    
    # Metadata
    assessed_by = Column(String(20))  # 'system', 'underwriter'
    model_version = Column(String(20))
    
    # Relationships
    loan_application = relationship("LoanApplication", back_populates="risk_assessment")
    
    def __repr__(self):
        return f"<RiskAssessment(score={self.overall_risk_score}, rating='{self.risk_rating}')>"
    
    @property
    def is_approvable(self):
        """Check if risk assessment recommends approval"""
        return self.automated_decision == 'approve'
    
    @property
    def risk_level(self):
        """Get risk level description"""
        if self.overall_risk_score >= 90:
            return "Minimal Risk"
        elif self.overall_risk_score >= 80:
            return "Low Risk"
        elif self.overall_risk_score >= 70:
            return "Moderate Risk"
        elif self.overall_risk_score >= 60:
            return "Elevated Risk"
        elif self.overall_risk_score >= 50:
            return "High Risk"
        else:
            return "Excessive Risk"
