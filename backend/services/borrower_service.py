"""
Borrower and Guarantor CRUD Service
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from models.borrower import Borrower, Guarantor
from schemas.borrower import (
    BorrowerCreate,
    BorrowerUpdate,
    GuarantorCreate,
    GuarantorUpdate
)


class BorrowerService:
    """Service for borrower operations"""
    
    @staticmethod
    def create(db: Session, borrower_data: BorrowerCreate) -> Borrower:
        """Create new borrower"""
        borrower = Borrower(**borrower_data.model_dump())
        db.add(borrower)
        db.commit()
        db.refresh(borrower)
        return borrower
    
    @staticmethod
    def get_by_id(db: Session, borrower_id: UUID) -> Optional[Borrower]:
        """Get borrower by ID"""
        return db.query(Borrower).filter(Borrower.id == borrower_id).first()
    
    @staticmethod
    def get_by_loan(db: Session, loan_id: UUID) -> Optional[Borrower]:
        """Get borrower by loan application ID"""
        return db.query(Borrower).filter(
            Borrower.loan_application_id == loan_id
        ).first()
    
    @staticmethod
    def update(
        db: Session,
        borrower_id: UUID,
        borrower_data: BorrowerUpdate
    ) -> Optional[Borrower]:
        """Update borrower"""
        borrower = BorrowerService.get_by_id(db, borrower_id)
        if not borrower:
            return None
        
        update_data = borrower_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(borrower, field, value)
        
        db.commit()
        db.refresh(borrower)
        return borrower
    
    @staticmethod
    def delete(db: Session, borrower_id: UUID) -> bool:
        """Delete borrower"""
        borrower = BorrowerService.get_by_id(db, borrower_id)
        if not borrower:
            return False
        
        db.delete(borrower)
        db.commit()
        return True


class GuarantorService:
    """Service for guarantor operations"""
    
    @staticmethod
    def create(db: Session, guarantor_data: GuarantorCreate) -> Guarantor:
        """Create new guarantor"""
        guarantor = Guarantor(**guarantor_data.model_dump())
        db.add(guarantor)
        db.commit()
        db.refresh(guarantor)
        return guarantor
    
    @staticmethod
    def get_by_id(db: Session, guarantor_id: UUID) -> Optional[Guarantor]:
        """Get guarantor by ID"""
        return db.query(Guarantor).filter(Guarantor.id == guarantor_id).first()
    
    @staticmethod
    def get_by_loan(db: Session, loan_id: UUID) -> List[Guarantor]:
        """Get all guarantors for a loan"""
        return db.query(Guarantor).filter(
            Guarantor.loan_application_id == loan_id
        ).all()
    
    @staticmethod
    def update(
        db: Session,
        guarantor_id: UUID,
        guarantor_data: GuarantorUpdate
    ) -> Optional[Guarantor]:
        """Update guarantor"""
        guarantor = GuarantorService.get_by_id(db, guarantor_id)
        if not guarantor:
            return None
        
        update_data = guarantor_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(guarantor, field, value)
        
        db.commit()
        db.refresh(guarantor)
        return guarantor
    
    @staticmethod
    def delete(db: Session, guarantor_id: UUID) -> bool:
        """Delete guarantor"""
        guarantor = GuarantorService.get_by_id(db, guarantor_id)
        if not guarantor:
            return False
        
        db.delete(guarantor)
        db.commit()
        return True
