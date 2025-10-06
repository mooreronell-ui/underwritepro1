"""
Pydantic schemas for API validation and serialization
UnderwritePro - The Apple of Commercial Underwriting
"""

from .user import (
    UserBase, UserCreate, UserUpdate, UserResponse,
    OrganizationBase, OrganizationCreate, OrganizationUpdate, OrganizationResponse
)

from .loan import (
    LoanApplicationBase, LoanApplicationCreate, LoanApplicationUpdate, LoanApplicationResponse,
    LoanApplicationList, LoanApplicationDetail
)

from .borrower import (
    BorrowerBase, BorrowerCreate, BorrowerUpdate, BorrowerResponse,
    GuarantorBase, GuarantorCreate, GuarantorUpdate, GuarantorResponse
)

from .property import (
    PropertyBase, PropertyCreate, PropertyUpdate, PropertyResponse,
    PropertyFinancialsBase, PropertyFinancialsCreate, PropertyFinancialsResponse,
    RentRollBase, RentRollCreate, RentRollResponse
)

from .financial import (
    FinancialStatementBase, FinancialStatementCreate, FinancialStatementResponse,
    FinancialRatiosResponse,
    RiskAssessmentResponse
)

from .document import (
    DocumentBase, DocumentCreate, DocumentUpdate, DocumentResponse
)

__all__ = [
    # User
    'UserBase', 'UserCreate', 'UserUpdate', 'UserResponse',
    'OrganizationBase', 'OrganizationCreate', 'OrganizationUpdate', 'OrganizationResponse',
    
    # Loan
    'LoanApplicationBase', 'LoanApplicationCreate', 'LoanApplicationUpdate', 'LoanApplicationResponse',
    'LoanApplicationList', 'LoanApplicationDetail',
    
    # Borrower
    'BorrowerBase', 'BorrowerCreate', 'BorrowerUpdate', 'BorrowerResponse',
    'GuarantorBase', 'GuarantorCreate', 'GuarantorUpdate', 'GuarantorResponse',
    
    # Property
    'PropertyBase', 'PropertyCreate', 'PropertyUpdate', 'PropertyResponse',
    'PropertyFinancialsBase', 'PropertyFinancialsCreate', 'PropertyFinancialsResponse',
    'RentRollBase', 'RentRollCreate', 'RentRollResponse',
    
    # Financial
    'FinancialStatementBase', 'FinancialStatementCreate', 'FinancialStatementResponse',
    'FinancialRatiosResponse',
    'RiskAssessmentResponse',
    
    # Document
    'DocumentBase', 'DocumentCreate', 'DocumentUpdate', 'DocumentResponse',
]
