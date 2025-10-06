"""
Financial Statement and Analysis Pydantic schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from uuid import UUID
from decimal import Decimal


# ============================================================================
# Financial Statement Schemas
# ============================================================================

class FinancialStatementBase(BaseModel):
    """Base financial statement schema"""
    statement_type: str = Field(..., max_length=50)
    year: int = Field(..., ge=1900, le=2100)
    is_ytd: bool = False
    
    # Income statement fields
    revenue: Optional[Decimal] = Field(None, decimal_places=2)
    cost_of_goods_sold: Optional[Decimal] = Field(None, decimal_places=2)
    gross_profit: Optional[Decimal] = Field(None, decimal_places=2)
    operating_expenses: Optional[Decimal] = Field(None, decimal_places=2)
    ebitda: Optional[Decimal] = Field(None, decimal_places=2)
    depreciation: Optional[Decimal] = Field(None, decimal_places=2)
    amortization: Optional[Decimal] = Field(None, decimal_places=2)
    interest_expense: Optional[Decimal] = Field(None, decimal_places=2)
    taxes: Optional[Decimal] = Field(None, decimal_places=2)
    net_income: Optional[Decimal] = Field(None, decimal_places=2)
    
    # Balance sheet fields
    cash: Optional[Decimal] = Field(None, decimal_places=2)
    accounts_receivable: Optional[Decimal] = Field(None, decimal_places=2)
    inventory: Optional[Decimal] = Field(None, decimal_places=2)
    other_current_assets: Optional[Decimal] = Field(None, decimal_places=2)
    total_current_assets: Optional[Decimal] = Field(None, decimal_places=2)
    fixed_assets: Optional[Decimal] = Field(None, decimal_places=2)
    accumulated_depreciation: Optional[Decimal] = Field(None, decimal_places=2)
    intangible_assets: Optional[Decimal] = Field(None, decimal_places=2)
    other_long_term_assets: Optional[Decimal] = Field(None, decimal_places=2)
    total_assets: Optional[Decimal] = Field(None, decimal_places=2)
    
    accounts_payable: Optional[Decimal] = Field(None, decimal_places=2)
    short_term_debt: Optional[Decimal] = Field(None, decimal_places=2)
    other_current_liabilities: Optional[Decimal] = Field(None, decimal_places=2)
    total_current_liabilities: Optional[Decimal] = Field(None, decimal_places=2)
    long_term_debt: Optional[Decimal] = Field(None, decimal_places=2)
    other_long_term_liabilities: Optional[Decimal] = Field(None, decimal_places=2)
    total_liabilities: Optional[Decimal] = Field(None, decimal_places=2)
    shareholders_equity: Optional[Decimal] = Field(None, decimal_places=2)
    
    # Cash flow fields
    operating_cash_flow: Optional[Decimal] = Field(None, decimal_places=2)
    investing_cash_flow: Optional[Decimal] = Field(None, decimal_places=2)
    financing_cash_flow: Optional[Decimal] = Field(None, decimal_places=2)
    net_cash_flow: Optional[Decimal] = Field(None, decimal_places=2)
    
    # Metadata
    source: Optional[str] = Field(None, max_length=50)
    verified: bool = False


class FinancialStatementCreate(FinancialStatementBase):
    """Schema for creating financial statement"""
    loan_application_id: UUID


class FinancialStatementResponse(FinancialStatementBase):
    """Schema for financial statement response"""
    id: UUID
    loan_application_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Financial Ratios Schemas
# ============================================================================

class FinancialRatiosResponse(BaseModel):
    """Schema for financial ratios response"""
    id: UUID
    loan_application_id: UUID
    
    # DSCR
    global_dscr: Optional[Decimal] = None
    business_dscr: Optional[Decimal] = None
    property_dscr: Optional[Decimal] = None
    personal_dscr: Optional[Decimal] = None
    
    # Leverage
    ltv: Optional[Decimal] = None
    ltc: Optional[Decimal] = None
    dti: Optional[Decimal] = None
    debt_to_ebitda: Optional[Decimal] = None
    
    # Liquidity
    current_ratio: Optional[Decimal] = None
    quick_ratio: Optional[Decimal] = None
    cash_ratio: Optional[Decimal] = None
    working_capital: Optional[Decimal] = None
    
    # Profitability
    gross_margin: Optional[Decimal] = None
    operating_margin: Optional[Decimal] = None
    net_margin: Optional[Decimal] = None
    ebitda_margin: Optional[Decimal] = None
    roa: Optional[Decimal] = None
    roe: Optional[Decimal] = None
    
    # Investment property
    cap_rate: Optional[Decimal] = None
    debt_yield: Optional[Decimal] = None
    cash_on_cash_return: Optional[Decimal] = None
    break_even_occupancy: Optional[Decimal] = None
    operating_expense_ratio: Optional[Decimal] = None
    
    calculation_method: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Risk Assessment Schemas
# ============================================================================

class RiskAssessmentResponse(BaseModel):
    """Schema for risk assessment response"""
    id: UUID
    loan_application_id: UUID
    
    # Overall risk
    overall_risk_score: Optional[int] = None
    risk_rating: Optional[str] = None
    
    # Component scores
    dscr_score: Optional[int] = None
    credit_score_component: Optional[int] = None
    ltv_score: Optional[int] = None
    tenure_score: Optional[int] = None
    profitability_score: Optional[int] = None
    liquidity_score: Optional[int] = None
    industry_risk_score: Optional[int] = None
    collateral_score: Optional[int] = None
    
    # Risk factors
    risk_factors: Optional[List[str]] = None
    mitigating_factors: Optional[List[str]] = None
    
    # Recommendation
    automated_decision: Optional[str] = None
    max_loan_amount: Optional[Decimal] = None
    recommended_terms: Optional[str] = None
    required_conditions: Optional[str] = None
    
    # Metadata
    assessed_by: Optional[str] = None
    model_version: Optional[str] = None
    
    # Computed fields
    is_approvable: bool = False
    risk_level: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
