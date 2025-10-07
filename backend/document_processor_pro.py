"""
Enterprise Document Processing System
OCR, Data Extraction, and Intelligent Analysis for Commercial Lending
"""
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from datetime import datetime
import re
import json
from pydantic import BaseModel
from enum import Enum


class DocumentType(str, Enum):
    """Supported document types"""
    TAX_RETURN = "tax_return"
    FINANCIAL_STATEMENT = "financial_statement"
    BANK_STATEMENT = "bank_statement"
    RENT_ROLL = "rent_roll"
    APPRAISAL = "appraisal"
    PURCHASE_AGREEMENT = "purchase_agreement"
    BUSINESS_LICENSE = "business_license"
    PERSONAL_FINANCIAL_STATEMENT = "personal_financial_statement"
    CREDIT_REPORT = "credit_report"
    UNKNOWN = "unknown"


class ExtractionConfidence(str, Enum):
    """Confidence levels for extracted data"""
    HIGH = "high"  # 90%+
    MEDIUM = "medium"  # 70-89%
    LOW = "low"  # <70%


class ExtractedField(BaseModel):
    """Individual extracted field"""
    field_name: str
    value: Any
    confidence: ExtractionConfidence
    source_page: Optional[int] = None
    source_location: Optional[str] = None
    validation_status: str = "pending"  # pending, validated, flagged


class DocumentMetadata(BaseModel):
    """Document metadata"""
    document_id: str
    filename: str
    document_type: DocumentType
    upload_date: datetime
    page_count: int
    file_size_bytes: int
    mime_type: str
    processing_status: str  # uploaded, processing, completed, failed
    ocr_completed: bool = False
    extraction_completed: bool = False


class FinancialData(BaseModel):
    """Extracted financial data"""
    # Income Statement
    revenue: Optional[Decimal] = None
    gross_profit: Optional[Decimal] = None
    operating_expenses: Optional[Decimal] = None
    ebitda: Optional[Decimal] = None
    net_income: Optional[Decimal] = None
    
    # Balance Sheet
    total_assets: Optional[Decimal] = None
    total_liabilities: Optional[Decimal] = None
    current_assets: Optional[Decimal] = None
    current_liabilities: Optional[Decimal] = None
    cash: Optional[Decimal] = None
    accounts_receivable: Optional[Decimal] = None
    inventory: Optional[Decimal] = None
    
    # Cash Flow
    operating_cash_flow: Optional[Decimal] = None
    investing_cash_flow: Optional[Decimal] = None
    financing_cash_flow: Optional[Decimal] = None
    
    # Period
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    fiscal_year: Optional[int] = None


class PropertyData(BaseModel):
    """Extracted property data"""
    address: Optional[str] = None
    property_type: Optional[str] = None
    appraised_value: Optional[Decimal] = None
    square_footage: Optional[int] = None
    year_built: Optional[int] = None
    occupancy_rate: Optional[Decimal] = None
    net_operating_income: Optional[Decimal] = None
    cap_rate: Optional[Decimal] = None
    comparable_sales: Optional[List[Dict]] = None


class BorrowerData(BaseModel):
    """Extracted borrower data"""
    name: Optional[str] = None
    entity_type: Optional[str] = None
    tax_id: Optional[str] = None
    credit_score: Optional[int] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    years_in_business: Optional[int] = None


class DocumentAnalysisResult(BaseModel):
    """Complete document analysis result"""
    metadata: DocumentMetadata
    document_type: DocumentType
    extracted_fields: List[ExtractedField]
    financial_data: Optional[FinancialData] = None
    property_data: Optional[PropertyData] = None
    borrower_data: Optional[BorrowerData] = None
    raw_text: str
    key_findings: List[str]
    data_quality_score: int  # 0-100
    missing_fields: List[str]
    validation_errors: List[str]
    processing_time_seconds: float


class DocumentProcessorPro:
    """
    Enterprise-grade document processing system
    Handles OCR, data extraction, and validation for commercial lending documents
    """
    
    def __init__(self):
        self.supported_types = [doc_type.value for doc_type in DocumentType]
        
    def process_document(
        self,
        file_path: str,
        document_type: Optional[DocumentType] = None
    ) -> DocumentAnalysisResult:
        """
        Process a document and extract all relevant data
        
        Args:
            file_path: Path to the document file
            document_type: Optional document type hint
            
        Returns:
            DocumentAnalysisResult with complete analysis
        """
        start_time = datetime.now()
        
        # Step 1: Extract metadata
        metadata = self._extract_metadata(file_path)
        
        # Step 2: Perform OCR
        raw_text = self._perform_ocr(file_path)
        metadata.ocr_completed = True
        
        # Step 3: Classify document if type not provided
        if not document_type:
            document_type = self._classify_document(raw_text)
        
        # Step 4: Extract structured data based on document type
        extracted_fields = []
        financial_data = None
        property_data = None
        borrower_data = None
        
        if document_type == DocumentType.FINANCIAL_STATEMENT:
            financial_data, fields = self._extract_financial_statement(raw_text)
            extracted_fields.extend(fields)
        elif document_type == DocumentType.TAX_RETURN:
            financial_data, fields = self._extract_tax_return(raw_text)
            extracted_fields.extend(fields)
        elif document_type == DocumentType.APPRAISAL:
            property_data, fields = self._extract_appraisal(raw_text)
            extracted_fields.extend(fields)
        elif document_type == DocumentType.RENT_ROLL:
            property_data, fields = self._extract_rent_roll(raw_text)
            extracted_fields.extend(fields)
        elif document_type == DocumentType.BANK_STATEMENT:
            financial_data, fields = self._extract_bank_statement(raw_text)
            extracted_fields.extend(fields)
        elif document_type == DocumentType.CREDIT_REPORT:
            borrower_data, fields = self._extract_credit_report(raw_text)
            extracted_fields.extend(fields)
        
        metadata.extraction_completed = True
        metadata.processing_status = "completed"
        
        # Step 5: Validate extracted data
        validation_errors = self._validate_extracted_data(
            document_type, financial_data, property_data, borrower_data
        )
        
        # Step 6: Calculate data quality score
        data_quality_score = self._calculate_data_quality_score(
            extracted_fields, validation_errors
        )
        
        # Step 7: Identify missing fields
        missing_fields = self._identify_missing_fields(
            document_type, financial_data, property_data, borrower_data
        )
        
        # Step 8: Generate key findings
        key_findings = self._generate_key_findings(
            document_type, financial_data, property_data, borrower_data, extracted_fields
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return DocumentAnalysisResult(
            metadata=metadata,
            document_type=document_type,
            extracted_fields=extracted_fields,
            financial_data=financial_data,
            property_data=property_data,
            borrower_data=borrower_data,
            raw_text=raw_text[:5000],  # Truncate for storage
            key_findings=key_findings,
            data_quality_score=data_quality_score,
            missing_fields=missing_fields,
            validation_errors=validation_errors,
            processing_time_seconds=processing_time
        )
    
    def _extract_metadata(self, file_path: str) -> DocumentMetadata:
        """Extract document metadata"""
        import os
        
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        # Determine MIME type
        if file_path.endswith('.pdf'):
            mime_type = 'application/pdf'
        elif file_path.endswith(('.jpg', '.jpeg')):
            mime_type = 'image/jpeg'
        elif file_path.endswith('.png'):
            mime_type = 'image/png'
        else:
            mime_type = 'application/octet-stream'
        
        return DocumentMetadata(
            document_id=f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            filename=filename,
            document_type=DocumentType.UNKNOWN,
            upload_date=datetime.now(),
            page_count=1,  # Will be updated after OCR
            file_size_bytes=file_size,
            mime_type=mime_type,
            processing_status="processing"
        )
    
    def _perform_ocr(self, file_path: str) -> str:
        """
        Perform OCR on document
        In production, this would use Tesseract, AWS Textract, or Google Vision API
        """
        # For demo purposes, return simulated OCR text
        # In production, integrate with real OCR service
        
        if file_path.endswith('.pdf'):
            # Simulate PDF text extraction
            return self._simulate_pdf_text()
        else:
            # Simulate image OCR
            return self._simulate_image_ocr()
    
    def _simulate_pdf_text(self) -> str:
        """Simulate PDF text extraction for demo"""
        return """
        FINANCIAL STATEMENT
        ABC Manufacturing LLC
        For the Year Ended December 31, 2024
        
        INCOME STATEMENT
        Revenue                          $2,500,000
        Cost of Goods Sold              $1,500,000
        Gross Profit                     $1,000,000
        
        Operating Expenses
        Salaries & Wages                  $400,000
        Rent                              $120,000
        Utilities                          $50,000
        Marketing                          $80,000
        Total Operating Expenses          $650,000
        
        EBITDA                            $350,000
        Depreciation                       $75,000
        Amortization                       $25,000
        Interest Expense                   $50,000
        
        Net Income                        $200,000
        
        BALANCE SHEET
        ASSETS
        Current Assets
        Cash                              $300,000
        Accounts Receivable               $400,000
        Inventory                         $350,000
        Total Current Assets            $1,050,000
        
        Fixed Assets                      $800,000
        Total Assets                    $1,850,000
        
        LIABILITIES
        Current Liabilities
        Accounts Payable                  $250,000
        Short-term Debt                   $150,000
        Total Current Liabilities         $400,000
        
        Long-term Debt                    $600,000
        Total Liabilities               $1,000,000
        
        EQUITY                            $850,000
        """
    
    def _simulate_image_ocr(self) -> str:
        """Simulate image OCR for demo"""
        return "Simulated OCR text from image document"
    
    def _classify_document(self, text: str) -> DocumentType:
        """Classify document type based on content"""
        text_lower = text.lower()
        
        # Financial statement indicators
        if any(term in text_lower for term in ['income statement', 'balance sheet', 'cash flow', 'ebitda']):
            return DocumentType.FINANCIAL_STATEMENT
        
        # Tax return indicators
        if any(term in text_lower for term in ['form 1120', 'form 1065', 'tax return', 'irs']):
            return DocumentType.TAX_RETURN
        
        # Appraisal indicators
        if any(term in text_lower for term in ['appraisal report', 'appraised value', 'market value', 'comparable sales']):
            return DocumentType.APPRAISAL
        
        # Rent roll indicators
        if any(term in text_lower for term in ['rent roll', 'tenant', 'lease', 'occupancy']):
            return DocumentType.RENT_ROLL
        
        # Bank statement indicators
        if any(term in text_lower for term in ['bank statement', 'checking account', 'savings account', 'beginning balance']):
            return DocumentType.BANK_STATEMENT
        
        # Credit report indicators
        if any(term in text_lower for term in ['credit report', 'credit score', 'fico', 'experian', 'equifax', 'transunion']):
            return DocumentType.CREDIT_REPORT
        
        return DocumentType.UNKNOWN
    
    def _extract_financial_statement(self, text: str) -> Tuple[FinancialData, List[ExtractedField]]:
        """Extract data from financial statement"""
        fields = []
        
        # Extract revenue
        revenue = self._extract_currency_value(text, ['revenue', 'sales', 'total revenue'])
        if revenue:
            fields.append(ExtractedField(
                field_name="revenue",
                value=float(revenue),
                confidence=ExtractionConfidence.HIGH
            ))
        
        # Extract net income
        net_income = self._extract_currency_value(text, ['net income', 'net profit', 'bottom line'])
        if net_income:
            fields.append(ExtractedField(
                field_name="net_income",
                value=float(net_income),
                confidence=ExtractionConfidence.HIGH
            ))
        
        # Extract EBITDA
        ebitda = self._extract_currency_value(text, ['ebitda', 'operating income'])
        if ebitda:
            fields.append(ExtractedField(
                field_name="ebitda",
                value=float(ebitda),
                confidence=ExtractionConfidence.HIGH
            ))
        
        # Extract total assets
        total_assets = self._extract_currency_value(text, ['total assets'])
        if total_assets:
            fields.append(ExtractedField(
                field_name="total_assets",
                value=float(total_assets),
                confidence=ExtractionConfidence.HIGH
            ))
        
        # Extract total liabilities
        total_liabilities = self._extract_currency_value(text, ['total liabilities'])
        if total_liabilities:
            fields.append(ExtractedField(
                field_name="total_liabilities",
                value=float(total_liabilities),
                confidence=ExtractionConfidence.HIGH
            ))
        
        # Extract cash
        cash = self._extract_currency_value(text, ['cash', 'cash and equivalents'])
        if cash:
            fields.append(ExtractedField(
                field_name="cash",
                value=float(cash),
                confidence=ExtractionConfidence.HIGH
            ))
        
        financial_data = FinancialData(
            revenue=revenue,
            ebitda=ebitda,
            net_income=net_income,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            cash=cash
        )
        
        return financial_data, fields
    
    def _extract_tax_return(self, text: str) -> Tuple[FinancialData, List[ExtractedField]]:
        """Extract data from tax return"""
        # Similar to financial statement extraction
        return self._extract_financial_statement(text)
    
    def _extract_appraisal(self, text: str) -> Tuple[PropertyData, List[ExtractedField]]:
        """Extract data from appraisal report"""
        fields = []
        
        # Extract appraised value
        appraised_value = self._extract_currency_value(text, ['appraised value', 'market value', 'as-is value'])
        if appraised_value:
            fields.append(ExtractedField(
                field_name="appraised_value",
                value=float(appraised_value),
                confidence=ExtractionConfidence.HIGH
            ))
        
        # Extract square footage
        sqft = self._extract_number_value(text, ['square feet', 'sq ft', 'sqft', 'gross building area'])
        if sqft:
            fields.append(ExtractedField(
                field_name="square_footage",
                value=int(sqft),
                confidence=ExtractionConfidence.MEDIUM
            ))
        
        property_data = PropertyData(
            appraised_value=appraised_value,
            square_footage=int(sqft) if sqft else None
        )
        
        return property_data, fields
    
    def _extract_rent_roll(self, text: str) -> Tuple[PropertyData, List[ExtractedField]]:
        """Extract data from rent roll"""
        fields = []
        
        # Extract NOI
        noi = self._extract_currency_value(text, ['net operating income', 'noi', 'annual noi'])
        if noi:
            fields.append(ExtractedField(
                field_name="net_operating_income",
                value=float(noi),
                confidence=ExtractionConfidence.HIGH
            ))
        
        # Extract occupancy rate
        occupancy = self._extract_percentage_value(text, ['occupancy', 'occupied', 'occupancy rate'])
        if occupancy:
            fields.append(ExtractedField(
                field_name="occupancy_rate",
                value=float(occupancy),
                confidence=ExtractionConfidence.MEDIUM
            ))
        
        property_data = PropertyData(
            net_operating_income=noi,
            occupancy_rate=occupancy
        )
        
        return property_data, fields
    
    def _extract_bank_statement(self, text: str) -> Tuple[FinancialData, List[ExtractedField]]:
        """Extract data from bank statement"""
        fields = []
        
        # Extract ending balance (as cash)
        cash = self._extract_currency_value(text, ['ending balance', 'current balance', 'balance'])
        if cash:
            fields.append(ExtractedField(
                field_name="cash",
                value=float(cash),
                confidence=ExtractionConfidence.HIGH
            ))
        
        financial_data = FinancialData(cash=cash)
        
        return financial_data, fields
    
    def _extract_credit_report(self, text: str) -> Tuple[BorrowerData, List[ExtractedField]]:
        """Extract data from credit report"""
        fields = []
        
        # Extract credit score
        credit_score = self._extract_credit_score(text)
        if credit_score:
            fields.append(ExtractedField(
                field_name="credit_score",
                value=credit_score,
                confidence=ExtractionConfidence.HIGH
            ))
        
        borrower_data = BorrowerData(credit_score=credit_score)
        
        return borrower_data, fields
    
    def _extract_currency_value(self, text: str, keywords: List[str]) -> Optional[Decimal]:
        """Extract currency value from text"""
        for keyword in keywords:
            # Look for pattern like "Revenue $2,500,000" or "Revenue: $2,500,000"
            pattern = rf'{keyword}[:\s]+\$?([\d,]+(?:\.\d{{2}})?)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value_str = match.group(1).replace(',', '')
                try:
                    return Decimal(value_str)
                except:
                    continue
        return None
    
    def _extract_number_value(self, text: str, keywords: List[str]) -> Optional[float]:
        """Extract numeric value from text"""
        for keyword in keywords:
            pattern = rf'{keyword}[:\s]+([\d,]+(?:\.\d+)?)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value_str = match.group(1).replace(',', '')
                try:
                    return float(value_str)
                except:
                    continue
        return None
    
    def _extract_percentage_value(self, text: str, keywords: List[str]) -> Optional[Decimal]:
        """Extract percentage value from text"""
        for keyword in keywords:
            pattern = rf'{keyword}[:\s]+([\d.]+)%?'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value_str = match.group(1)
                try:
                    return Decimal(value_str) / 100  # Convert to decimal
                except:
                    continue
        return None
    
    def _extract_credit_score(self, text: str) -> Optional[int]:
        """Extract credit score from text"""
        # Look for FICO score pattern
        pattern = r'(?:fico|credit score)[:\s]+(\d{3})'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                score = int(match.group(1))
                if 300 <= score <= 850:  # Valid FICO range
                    return score
            except:
                pass
        return None
    
    def _validate_extracted_data(
        self,
        document_type: DocumentType,
        financial_data: Optional[FinancialData],
        property_data: Optional[PropertyData],
        borrower_data: Optional[BorrowerData]
    ) -> List[str]:
        """Validate extracted data for consistency and reasonableness"""
        errors = []
        
        if financial_data:
            # Check if liabilities exceed assets
            if financial_data.total_assets and financial_data.total_liabilities:
                if financial_data.total_liabilities > financial_data.total_assets:
                    errors.append("Total liabilities exceed total assets - possible data extraction error")
            
            # Check if revenue is reasonable compared to net income
            if financial_data.revenue and financial_data.net_income:
                if financial_data.net_income > financial_data.revenue:
                    errors.append("Net income exceeds revenue - data inconsistency")
                
                profit_margin = financial_data.net_income / financial_data.revenue
                if profit_margin > Decimal("0.5"):
                    errors.append("Profit margin exceeds 50% - verify extraction accuracy")
        
        if property_data:
            # Check if occupancy rate is valid
            if property_data.occupancy_rate:
                if property_data.occupancy_rate > Decimal("1.0"):
                    errors.append("Occupancy rate exceeds 100% - data error")
            
            # Check if cap rate is reasonable
            if property_data.cap_rate:
                if property_data.cap_rate < Decimal("0.02") or property_data.cap_rate > Decimal("0.20"):
                    errors.append("Cap rate outside typical range (2%-20%) - verify data")
        
        if borrower_data:
            # Check if credit score is valid
            if borrower_data.credit_score:
                if not (300 <= borrower_data.credit_score <= 850):
                    errors.append("Credit score outside valid FICO range (300-850)")
        
        return errors
    
    def _calculate_data_quality_score(
        self,
        extracted_fields: List[ExtractedField],
        validation_errors: List[str]
    ) -> int:
        """Calculate overall data quality score (0-100)"""
        if not extracted_fields:
            return 0
        
        # Start with base score
        score = 100
        
        # Deduct for low confidence fields
        low_confidence_count = sum(1 for f in extracted_fields if f.confidence == ExtractionConfidence.LOW)
        score -= low_confidence_count * 5
        
        # Deduct for validation errors
        score -= len(validation_errors) * 10
        
        # Bonus for high confidence fields
        high_confidence_count = sum(1 for f in extracted_fields if f.confidence == ExtractionConfidence.HIGH)
        score += min(high_confidence_count * 2, 20)  # Cap bonus at 20
        
        return max(0, min(100, score))
    
    def _identify_missing_fields(
        self,
        document_type: DocumentType,
        financial_data: Optional[FinancialData],
        property_data: Optional[PropertyData],
        borrower_data: Optional[BorrowerData]
    ) -> List[str]:
        """Identify critical missing fields"""
        missing = []
        
        if document_type == DocumentType.FINANCIAL_STATEMENT:
            if not financial_data or not financial_data.revenue:
                missing.append("Revenue")
            if not financial_data or not financial_data.net_income:
                missing.append("Net Income")
            if not financial_data or not financial_data.total_assets:
                missing.append("Total Assets")
        
        elif document_type == DocumentType.APPRAISAL:
            if not property_data or not property_data.appraised_value:
                missing.append("Appraised Value")
        
        elif document_type == DocumentType.CREDIT_REPORT:
            if not borrower_data or not borrower_data.credit_score:
                missing.append("Credit Score")
        
        return missing
    
    def _generate_key_findings(
        self,
        document_type: DocumentType,
        financial_data: Optional[FinancialData],
        property_data: Optional[PropertyData],
        borrower_data: Optional[BorrowerData],
        extracted_fields: List[ExtractedField]
    ) -> List[str]:
        """Generate key findings from extracted data"""
        findings = []
        
        findings.append(f"Document type identified: {document_type.value}")
        findings.append(f"Successfully extracted {len(extracted_fields)} data fields")
        
        if financial_data:
            if financial_data.revenue:
                findings.append(f"Annual revenue: ${financial_data.revenue:,.2f}")
            if financial_data.net_income:
                findings.append(f"Net income: ${financial_data.net_income:,.2f}")
                if financial_data.revenue:
                    margin = (financial_data.net_income / financial_data.revenue) * 100
                    findings.append(f"Profit margin: {margin:.1f}%")
        
        if property_data:
            if property_data.appraised_value:
                findings.append(f"Appraised value: ${property_data.appraised_value:,.2f}")
            if property_data.net_operating_income:
                findings.append(f"Net Operating Income: ${property_data.net_operating_income:,.2f}")
        
        if borrower_data:
            if borrower_data.credit_score:
                findings.append(f"Credit score: {borrower_data.credit_score}")
        
        # Add confidence summary
        high_conf = sum(1 for f in extracted_fields if f.confidence == ExtractionConfidence.HIGH)
        if high_conf > 0:
            findings.append(f"{high_conf} fields extracted with high confidence")
        
        return findings
