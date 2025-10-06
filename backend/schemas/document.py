"""
Document Pydantic schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from uuid import UUID


# ============================================================================
# Document Schemas
# ============================================================================

class DocumentBase(BaseModel):
    """Base document schema"""
    document_type: str = Field(..., max_length=100)
    document_name: str = Field(..., min_length=1, max_length=255)
    year: Optional[int] = Field(None, ge=1900, le=2100)
    category: Optional[str] = Field(None, max_length=50)


class DocumentCreate(DocumentBase):
    """Schema for creating document"""
    loan_application_id: UUID
    file_path: str = Field(..., max_length=500)
    file_size: Optional[int] = None
    mime_type: Optional[str] = Field(None, max_length=100)
    uploaded_by: Optional[UUID] = None


class DocumentUpdate(BaseModel):
    """Schema for updating document"""
    document_type: Optional[str] = None
    document_name: Optional[str] = None
    year: Optional[int] = None
    category: Optional[str] = None
    status: Optional[str] = None
    review_notes: Optional[str] = None
    ocr_completed: Optional[bool] = None
    extracted_data: Optional[Dict] = None


class DocumentResponse(DocumentBase):
    """Schema for document response"""
    id: UUID
    loan_application_id: UUID
    file_path: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    status: str
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    ocr_completed: bool = False
    extracted_data: Optional[Dict] = None
    uploaded_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    is_reviewed: bool = False
    is_approved: bool = False
    file_size_mb: float = 0.0
    
    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    """Schema for document upload response"""
    id: UUID
    document_name: str
    file_path: str
    file_size_mb: float
    status: str
    message: str = "Document uploaded successfully"
