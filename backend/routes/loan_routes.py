"""
Loan Application API Routes
RESTful endpoints for loan intake and management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from database_config import get_db
from models.loan import LoanStatus, LoanStage
from schemas.loan import (
    LoanApplicationCreate,
    LoanApplicationUpdate,
    LoanApplicationResponse,
    LoanApplicationList,
    LoanApplicationDetail,
    LoanApplicationStats
)
from services.loan_service import LoanApplicationService
from auth import get_current_user  # Assuming auth is implemented
from models.user import User

router = APIRouter(prefix="/api/loans", tags=["Loans"])


# ============================================================================
# Create Loan Application
# ============================================================================

@router.post(
    "",
    response_model=LoanApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new loan application",
    description="Create a new loan application in DRAFT status"
)
async def create_loan_application(
    loan_data: LoanApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new loan application.
    
    **Requirements:**
    - User must be authenticated
    - Loan amount must be positive
    - Organization must exist
    
    **Returns:**
    - Loan application with auto-generated application number
    - Status: DRAFT
    - Stage: INTAKE
    """
    try:
        # Verify organization access
        if loan_data.organization_id != current_user.organization_id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create loan for different organization"
            )
        
        loan = LoanApplicationService.create(
            db=db,
            loan_data=loan_data,
            created_by=current_user.id
        )
        
        return loan
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create loan application: {str(e)}"
        )


# ============================================================================
# Get Loan Applications (List)
# ============================================================================

@router.get(
    "",
    response_model=List[LoanApplicationList],
    summary="List loan applications",
    description="Get list of loan applications with optional filters"
)
async def get_loan_applications(
    status: Optional[LoanStatus] = Query(None, description="Filter by status"),
    stage: Optional[LoanStage] = Query(None, description="Filter by stage"),
    assigned_to: Optional[UUID] = Query(None, description="Filter by assigned user"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of loan applications.
    
    **Filters:**
    - status: Filter by loan status
    - stage: Filter by loan stage
    - assigned_to: Filter by assigned user
    - skip/limit: Pagination
    
    **Access Control:**
    - Users see only their organization's loans
    - Admins can see all loans
    """
    organization_id = None if current_user.is_admin else current_user.organization_id
    
    loans = LoanApplicationService.get_all(
        db=db,
        organization_id=organization_id,
        status=status,
        stage=stage,
        assigned_to=assigned_to,
        skip=skip,
        limit=limit
    )
    
    # Add computed fields
    loan_list = []
    for loan in loans:
        loan_dict = {
            "id": loan.id,
            "application_number": loan.application_number,
            "loan_type": loan.loan_type,
            "loan_amount": loan.loan_amount,
            "status": loan.status,
            "stage": loan.stage,
            "borrower_name": loan.borrower.business_legal_name if loan.borrower else None,
            "property_address": loan.property_info.property_address if loan.property_info else None,
            "created_at": loan.created_at,
            "updated_at": loan.updated_at
        }
        loan_list.append(loan_dict)
    
    return loan_list


# ============================================================================
# Get Loan Application by ID
# ============================================================================

@router.get(
    "/{loan_id}",
    response_model=LoanApplicationResponse,
    summary="Get loan application by ID",
    description="Get detailed information about a specific loan application"
)
async def get_loan_application(
    loan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get loan application by ID.
    
    **Access Control:**
    - Users can only access their organization's loans
    - Admins can access all loans
    """
    organization_id = None if current_user.is_admin else current_user.organization_id
    
    loan = LoanApplicationService.get_by_id(
        db=db,
        loan_id=loan_id,
        organization_id=organization_id
    )
    
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan application not found"
        )
    
    return loan


# ============================================================================
# Get Loan Application with Details
# ============================================================================

@router.get(
    "/{loan_id}/details",
    response_model=LoanApplicationDetail,
    summary="Get loan application with all related data",
    description="Get loan application with borrower, property, financials, and documents"
)
async def get_loan_application_details(
    loan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get loan application with all related data (eager loaded).
    
    **Includes:**
    - Borrower information
    - Guarantors
    - Property details
    - Financial ratios
    - Risk assessment
    - Document count
    """
    organization_id = None if current_user.is_admin else current_user.organization_id
    
    loan = LoanApplicationService.get_with_details(
        db=db,
        loan_id=loan_id,
        organization_id=organization_id
    )
    
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan application not found"
        )
    
    # Build detailed response
    loan_detail = {
        **loan.__dict__,
        "borrower": loan.borrower.__dict__ if loan.borrower else None,
        "guarantors": [g.__dict__ for g in loan.guarantors] if loan.guarantors else [],
        "property_info": loan.property_info.__dict__ if loan.property_info else None,
        "financial_ratios": loan.financial_ratios.__dict__ if loan.financial_ratios else None,
        "risk_assessment": loan.risk_assessment.__dict__ if loan.risk_assessment else None,
        "documents_count": len(loan.documents) if loan.documents else 0
    }
    
    return loan_detail


# ============================================================================
# Update Loan Application
# ============================================================================

@router.put(
    "/{loan_id}",
    response_model=LoanApplicationResponse,
    summary="Update loan application",
    description="Update loan application fields"
)
async def update_loan_application(
    loan_id: UUID,
    loan_data: LoanApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update loan application.
    
    **Access Control:**
    - Users can only update their organization's loans
    - Admins can update all loans
    """
    organization_id = None if current_user.is_admin else current_user.organization_id
    
    loan = LoanApplicationService.update(
        db=db,
        loan_id=loan_id,
        loan_data=loan_data,
        organization_id=organization_id
    )
    
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan application not found"
        )
    
    return loan


# ============================================================================
# Delete Loan Application
# ============================================================================

@router.delete(
    "/{loan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete loan application",
    description="Delete a loan application (soft delete recommended in production)"
)
async def delete_loan_application(
    loan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete loan application.
    
    **Warning:** This is a hard delete. Consider implementing soft delete in production.
    
    **Access Control:**
    - Users can only delete their organization's loans
    - Admins can delete all loans
    """
    organization_id = None if current_user.is_admin else current_user.organization_id
    
    success = LoanApplicationService.delete(
        db=db,
        loan_id=loan_id,
        organization_id=organization_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan application not found"
        )
    
    return None


# ============================================================================
# Submit Loan Application
# ============================================================================

@router.post(
    "/{loan_id}/submit",
    response_model=LoanApplicationResponse,
    summary="Submit loan application",
    description="Submit loan application (DRAFT → SUBMITTED)"
)
async def submit_loan_application(
    loan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit loan application.
    
    **Status Change:**
    - DRAFT → SUBMITTED
    - Stage: INTAKE → DOCUMENT_COLLECTION
    - Sets submitted_at timestamp
    
    **Requirements:**
    - Loan must be in DRAFT status
    - User must have access to the loan
    """
    organization_id = None if current_user.is_admin else current_user.organization_id
    
    loan = LoanApplicationService.submit_loan(
        db=db,
        loan_id=loan_id,
        organization_id=organization_id
    )
    
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit loan. Loan not found or not in DRAFT status."
        )
    
    return loan


# ============================================================================
# Get Loan Statistics
# ============================================================================

@router.get(
    "/statistics/dashboard",
    response_model=LoanApplicationStats,
    summary="Get loan application statistics",
    description="Get dashboard statistics for loan applications"
)
async def get_loan_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get loan application statistics.
    
    **Includes:**
    - Total counts by status
    - Loan amounts (total, average)
    - Distribution by loan type
    - Distribution by status
    - Distribution by stage
    
    **Access Control:**
    - Users see only their organization's statistics
    - Admins see all statistics
    """
    organization_id = None if current_user.is_admin else current_user.organization_id
    
    stats = LoanApplicationService.get_statistics(
        db=db,
        organization_id=organization_id
    )
    
    return stats
