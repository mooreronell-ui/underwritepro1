"""
Document Upload and OCR Service
Handles file uploads and prepares documents for OCR processing
"""

import os
import uuid
from pathlib import Path
from typing import Optional, Tuple, BinaryIO
from datetime import datetime
import mimetypes

from sqlalchemy.orm import Session
from fastapi import UploadFile

from models.document import Document, DocumentStatus
from schemas.document import DocumentCreate


class DocumentUploadService:
    """
    Service for handling document uploads and OCR preparation
    """
    
    # Allowed file types
    ALLOWED_EXTENSIONS = {
        'pdf': 'application/pdf',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'tiff': 'image/tiff',
        'tif': 'image/tiff',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xls': 'application/vnd.ms-excel',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }
    
    # Maximum file size (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    # Document type categories for OCR
    OCR_DOCUMENT_TYPES = [
        'financial_statement',
        'tax_return',
        'bank_statement',
        'rent_roll',
        'operating_statement',
        'invoice'
    ]
    
    def __init__(self, upload_dir: str = "/home/ubuntu/underwritepro1/backend/uploads"):
        """
        Initialize upload service
        
        Args:
            upload_dir: Base directory for file uploads
        """
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def upload_document(
        self,
        db: Session,
        file: UploadFile,
        loan_application_id: uuid.UUID,
        document_type: str,
        uploaded_by: uuid.UUID,
        description: Optional[str] = None
    ) -> Document:
        """
        Upload and save a document
        
        Args:
            db: Database session
            file: Uploaded file
            loan_application_id: Associated loan application ID
            document_type: Type of document
            uploaded_by: User ID who uploaded
            description: Optional description
        
        Returns:
            Created Document object
        
        Raises:
            ValueError: If file validation fails
        """
        # Validate file
        self._validate_file(file)
        
        # Generate unique filename
        file_extension = self._get_file_extension(file.filename)
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        
        # Create loan-specific directory
        loan_dir = self.upload_dir / str(loan_application_id)
        loan_dir.mkdir(parents=True, exist_ok=True)
        
        # Full file path
        file_path = loan_dir / unique_filename
        
        # Save file
        file_size = await self._save_file(file, file_path)
        
        # Determine if OCR is needed
        needs_ocr = document_type in self.OCR_DOCUMENT_TYPES and file_extension in ['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'tif']
        
        # Create document record
        document_data = DocumentCreate(
            loan_application_id=loan_application_id,
            document_type=document_type,
            file_name=file.filename,
            file_path=str(file_path),
            file_size=file_size,
            mime_type=file.content_type or self._get_mime_type(file.filename),
            uploaded_by=uploaded_by,
            description=description
        )
        
        document = Document(
            **document_data.model_dump(),
            status=DocumentStatus.PENDING_REVIEW,
            ocr_required=needs_ocr,
            ocr_status='pending' if needs_ocr else None
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Queue for OCR if needed
        if needs_ocr:
            # In production, this would queue the document for OCR processing
            # For now, we'll just mark it as ready for OCR
            pass
        
        return document
    
    def _validate_file(self, file: UploadFile) -> None:
        """
        Validate uploaded file
        
        Raises:
            ValueError: If validation fails
        """
        if not file.filename:
            raise ValueError("No filename provided")
        
        # Check file extension
        file_extension = self._get_file_extension(file.filename)
        if file_extension not in self.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"File type '.{file_extension}' not allowed. "
                f"Allowed types: {', '.join(self.ALLOWED_EXTENSIONS.keys())}"
            )
        
        # Check file size (if available)
        if hasattr(file, 'size') and file.size:
            if file.size > self.MAX_FILE_SIZE:
                max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
                raise ValueError(f"File size exceeds maximum of {max_mb}MB")
    
    async def _save_file(self, file: UploadFile, file_path: Path) -> int:
        """
        Save uploaded file to disk
        
        Returns:
            File size in bytes
        """
        file_size = 0
        
        with open(file_path, 'wb') as f:
            while chunk := await file.read(8192):  # Read in 8KB chunks
                f.write(chunk)
                file_size += len(chunk)
        
        # Validate file size after upload
        if file_size > self.MAX_FILE_SIZE:
            file_path.unlink()  # Delete file
            max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
            raise ValueError(f"File size exceeds maximum of {max_mb}MB")
        
        return file_size
    
    def _get_file_extension(self, filename: str) -> str:
        """Get file extension from filename"""
        return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type from filename"""
        file_extension = self._get_file_extension(filename)
        return self.ALLOWED_EXTENSIONS.get(file_extension, 'application/octet-stream')
    
    def delete_document_file(self, file_path: str) -> bool:
        """
        Delete physical file from disk
        
        Args:
            file_path: Path to file
        
        Returns:
            True if deleted, False if file not found
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def get_document_url(self, document: Document, base_url: str) -> str:
        """
        Generate URL for document access
        
        Args:
            document: Document object
            base_url: Base URL of the application
        
        Returns:
            Full URL to access document
        """
        return f"{base_url}/api/documents/{document.id}/download"


class OCRService:
    """
    Service for OCR processing of documents
    
    This is a placeholder for OCR integration. In production, this would integrate with:
    - AWS Textract
    - Google Cloud Vision API
    - Azure Form Recognizer
    - Or custom OCR solution
    """
    
    @staticmethod
    def extract_financial_data(file_path: str, document_type: str) -> Optional[dict]:
        """
        Extract financial data from document using OCR
        
        Args:
            file_path: Path to document file
            document_type: Type of document (determines extraction template)
        
        Returns:
            Extracted data dictionary or None if extraction fails
        
        Note: This is a placeholder. In production, this would call actual OCR service.
        """
        # Placeholder for OCR integration
        # In production, this would:
        # 1. Send document to OCR service
        # 2. Parse OCR results based on document type
        # 3. Extract structured data (revenue, expenses, ratios, etc.)
        # 4. Return structured data
        
        extraction_templates = {
            'financial_statement': {
                'fields': [
                    'revenue',
                    'cost_of_goods_sold',
                    'gross_profit',
                    'operating_expenses',
                    'ebitda',
                    'net_income',
                    'total_assets',
                    'total_liabilities',
                    'shareholders_equity'
                ]
            },
            'tax_return': {
                'fields': [
                    'gross_receipts',
                    'total_income',
                    'total_deductions',
                    'taxable_income',
                    'tax_year'
                ]
            },
            'bank_statement': {
                'fields': [
                    'account_number',
                    'statement_date',
                    'beginning_balance',
                    'ending_balance',
                    'total_deposits',
                    'total_withdrawals'
                ]
            },
            'rent_roll': {
                'fields': [
                    'unit_number',
                    'tenant_name',
                    'monthly_rent',
                    'lease_start',
                    'lease_end',
                    'occupancy_status'
                ]
            }
        }
        
        # Return template structure (in production, would return actual extracted data)
        template = extraction_templates.get(document_type)
        if template:
            return {
                'document_type': document_type,
                'extraction_status': 'pending',
                'fields': template['fields'],
                'data': {},  # Would contain actual extracted values
                'confidence': None,  # Would contain OCR confidence scores
                'requires_review': True
            }
        
        return None
    
    @staticmethod
    def update_ocr_status(
        db: Session,
        document_id: uuid.UUID,
        status: str,
        extracted_data: Optional[dict] = None,
        confidence_score: Optional[float] = None
    ) -> Document:
        """
        Update OCR status for a document
        
        Args:
            db: Database session
            document_id: Document ID
            status: OCR status (pending, processing, completed, failed)
            extracted_data: Extracted data from OCR
            confidence_score: OCR confidence score (0-100)
        
        Returns:
            Updated Document object
        """
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            raise ValueError("Document not found")
        
        document.ocr_status = status
        
        if extracted_data:
            document.ocr_extracted_data = extracted_data
        
        if confidence_score is not None:
            document.ocr_confidence = confidence_score
        
        if status == 'completed':
            document.ocr_processed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(document)
        
        return document
