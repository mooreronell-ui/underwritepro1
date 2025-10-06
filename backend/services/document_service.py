"""
Document CRUD Service
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from pathlib import Path

from models.document import Document, DocumentStatus
from schemas.document import DocumentCreate, DocumentUpdate


class DocumentService:
    """Service for document operations"""
    
    @staticmethod
    def create(db: Session, document_data: DocumentCreate) -> Document:
        """Create new document"""
        document = Document(
            **document_data.model_dump(),
            status=DocumentStatus.PENDING_REVIEW
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        return document
    
    @staticmethod
    def get_by_id(db: Session, document_id: UUID) -> Optional[Document]:
        """Get document by ID"""
        return db.query(Document).filter(Document.id == document_id).first()
    
    @staticmethod
    def get_by_loan(
        db: Session,
        loan_id: UUID,
        document_type: Optional[str] = None,
        status: Optional[DocumentStatus] = None
    ) -> List[Document]:
        """Get all documents for a loan with optional filters"""
        query = db.query(Document).filter(Document.loan_application_id == loan_id)
        
        if document_type:
            query = query.filter(Document.document_type == document_type)
        
        if status:
            query = query.filter(Document.status == status)
        
        return query.order_by(Document.created_at.desc()).all()
    
    @staticmethod
    def update(
        db: Session,
        document_id: UUID,
        document_data: DocumentUpdate
    ) -> Optional[Document]:
        """Update document"""
        document = DocumentService.get_by_id(db, document_id)
        if not document:
            return None
        
        update_data = document_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(document, field, value)
        
        db.commit()
        db.refresh(document)
        return document
    
    @staticmethod
    def delete(db: Session, document_id: UUID) -> bool:
        """Delete document"""
        document = DocumentService.get_by_id(db, document_id)
        if not document:
            return False
        
        # Delete physical file
        try:
            file_path = Path(document.file_path)
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass  # Log error but don't fail
        
        db.delete(document)
        db.commit()
        return True
    
    @staticmethod
    def approve_document(
        db: Session,
        document_id: UUID,
        reviewed_by: UUID,
        review_notes: Optional[str] = None
    ) -> Optional[Document]:
        """Approve a document"""
        document = DocumentService.get_by_id(db, document_id)
        if not document:
            return None
        
        document.status = DocumentStatus.APPROVED
        document.reviewed_by = reviewed_by
        document.review_notes = review_notes
        
        from datetime import datetime
        document.reviewed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(document)
        return document
    
    @staticmethod
    def reject_document(
        db: Session,
        document_id: UUID,
        reviewed_by: UUID,
        review_notes: str
    ) -> Optional[Document]:
        """Reject a document"""
        document = DocumentService.get_by_id(db, document_id)
        if not document:
            return None
        
        document.status = DocumentStatus.REJECTED
        document.reviewed_by = reviewed_by
        document.review_notes = review_notes
        
        from datetime import datetime
        document.reviewed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(document)
        return document
    
    @staticmethod
    def get_document_counts(db: Session, loan_id: UUID) -> dict:
        """Get document counts by status for a loan"""
        from sqlalchemy import func
        
        counts = db.query(
            Document.status,
            func.count(Document.id)
        ).filter(
            Document.loan_application_id == loan_id
        ).group_by(Document.status).all()
        
        result = {
            'total': 0,
            'pending': 0,
            'approved': 0,
            'rejected': 0,
            'under_review': 0
        }
        
        for status, count in counts:
            result['total'] += count
            if status == DocumentStatus.PENDING_REVIEW:
                result['pending'] = count
            elif status == DocumentStatus.APPROVED:
                result['approved'] = count
            elif status == DocumentStatus.REJECTED:
                result['rejected'] = count
            elif status == DocumentStatus.UNDER_REVIEW:
                result['under_review'] = count
        
        return result
