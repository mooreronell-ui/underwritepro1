"""
UnderwritePro Database Models
The Apple of Commercial Underwriting

This package contains all SQLAlchemy models for the dual-tier system:
- Broker Version: Deal origination and packaging
- Lender Version: Full underwriting and portfolio management
"""

from .base import Base, TimestampMixin
from .user import User, Organization
from .loan import LoanApplication, LoanStatus, LoanStage
from .borrower import Borrower, Guarantor
from .property import Property, PropertyFinancials, RentRoll
from .financial import FinancialStatement, FinancialRatios, RiskAssessment
from .document import Document, DocumentType, DocumentStatus
from .broker import LenderNetwork, LoanSubmission, RateQuote, BrokerCommission
from .lender import (
    UnderwritingPolicy,
    LoanPipeline,
    CreditDecision,
    LoanServicing,
    CovenantMonitoring,
    PortfolioAnalytics
)

__all__ = [
    # Base
    'Base',
    'TimestampMixin',
    
    # Core
    'User',
    'Organization',
    'LoanApplication',
    'LoanStatus',
    'LoanStage',
    
    # Borrower
    'Borrower',
    'Guarantor',
    
    # Property
    'Property',
    'PropertyFinancials',
    'RentRoll',
    
    # Financial
    'FinancialStatement',
    'FinancialRatios',
    'RiskAssessment',
    
    # Document
    'Document',
    'DocumentType',
    'DocumentStatus',
    
    # Broker
    'LenderNetwork',
    'LoanSubmission',
    'RateQuote',
    'BrokerCommission',
    
    # Lender
    'UnderwritingPolicy',
    'LoanPipeline',
    'CreditDecision',
    'LoanServicing',
    'CovenantMonitoring',
    'PortfolioAnalytics',
]
