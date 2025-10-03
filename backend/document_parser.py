import PyPDF2
import re
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel

class ParsedField(BaseModel):
    """A single parsed field from a document"""
    source: str
    line: str
    value: float
    confidence: float
    page: Optional[int] = None

class ParsedDocument(BaseModel):
    """Result of document parsing"""
    document_type: str
    fields: List[ParsedField]
    raw_text: str
    confidence_score: float

class DocumentParser:
    """Parse financial documents and extract structured data"""
    
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> Tuple[str, int]:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = len(pdf_reader.pages)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text, num_pages
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            return "", 0
    
    @staticmethod
    def parse_tax_return_1040(text: str) -> List[ParsedField]:
        """Parse IRS Form 1040 (Individual Tax Return)"""
        fields = []
        
        # Common patterns for 1040
        patterns = {
            "agi": [
                r"adjusted gross income.*?(\d{1,3}(?:,\d{3})*)",
                r"agi.*?(\d{1,3}(?:,\d{3})*)",
                r"line 11.*?(\d{1,3}(?:,\d{3})*)"
            ],
            "total_income": [
                r"total income.*?(\d{1,3}(?:,\d{3})*)",
                r"line 9.*?(\d{1,3}(?:,\d{3})*)"
            ],
            "wages": [
                r"wages.*?(\d{1,3}(?:,\d{3})*)",
                r"line 1.*?(\d{1,3}(?:,\d{3})*)"
            ],
            "business_income": [
                r"business income.*?(\d{1,3}(?:,\d{3})*)",
                r"schedule c.*?(\d{1,3}(?:,\d{3})*)"
            ]
        }
        
        for field_name, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value_str = match.group(1).replace(',', '')
                    try:
                        value = float(value_str)
                        fields.append(ParsedField(
                            source="1040",
                            line=field_name,
                            value=value,
                            confidence=0.85
                        ))
                        break
                    except ValueError:
                        continue
        
        return fields
    
    @staticmethod
    def parse_tax_return_1120(text: str) -> List[ParsedField]:
        """Parse IRS Form 1120 (Corporate Tax Return)"""
        fields = []
        
        patterns = {
            "gross_receipts": [
                r"gross receipts.*?(\d{1,3}(?:,\d{3})*)",
                r"line 1a.*?(\d{1,3}(?:,\d{3})*)"
            ],
            "total_income": [
                r"total income.*?(\d{1,3}(?:,\d{3})*)",
                r"line 11.*?(\d{1,3}(?:,\d{3})*)"
            ],
            "total_deductions": [
                r"total deductions.*?(\d{1,3}(?:,\d{3})*)",
                r"line 27.*?(\d{1,3}(?:,\d{3})*)"
            ],
            "taxable_income": [
                r"taxable income.*?(\d{1,3}(?:,\d{3})*)",
                r"line 28.*?(\d{1,3}(?:,\d{3})*)"
            ],
            "depreciation": [
                r"depreciation.*?(\d{1,3}(?:,\d{3})*)",
                r"line 20.*?(\d{1,3}(?:,\d{3})*)"
            ]
        }
        
        for field_name, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value_str = match.group(1).replace(',', '')
                    try:
                        value = float(value_str)
                        fields.append(ParsedField(
                            source="1120",
                            line=field_name,
                            value=value,
                            confidence=0.82
                        ))
                        break
                    except ValueError:
                        continue
        
        return fields
    
    @staticmethod
    def parse_financial_statement(text: str) -> List[ParsedField]:
        """Parse P&L or Balance Sheet"""
        fields = []
        
        # Income Statement patterns
        income_patterns = {
            "revenue": [
                r"(?:total\s+)?revenue.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
                r"(?:gross\s+)?sales.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
                r"income.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"
            ],
            "net_income": [
                r"net income.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
                r"net profit.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
                r"bottom line.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"
            ],
            "depreciation": [
                r"depreciation.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
                r"d&a.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"
            ],
            "amortization": [
                r"amortization.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"
            ],
            "interest_expense": [
                r"interest expense.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
                r"interest paid.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"
            ],
            "ebitda": [
                r"ebitda.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"
            ]
        }
        
        for field_name, pattern_list in income_patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value_str = match.group(1).replace(',', '')
                    try:
                        value = float(value_str)
                        fields.append(ParsedField(
                            source="P&L",
                            line=field_name,
                            value=value,
                            confidence=0.88
                        ))
                        break
                    except ValueError:
                        continue
        
        return fields
    
    @staticmethod
    def parse_bank_statement(text: str) -> List[ParsedField]:
        """Parse bank statement"""
        fields = []
        
        patterns = {
            "beginning_balance": [
                r"beginning balance.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
                r"opening balance.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"
            ],
            "ending_balance": [
                r"ending balance.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
                r"closing balance.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"
            ],
            "total_deposits": [
                r"total deposits.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"
            ],
            "total_withdrawals": [
                r"total withdrawals.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"
            ]
        }
        
        for field_name, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value_str = match.group(1).replace(',', '')
                    try:
                        value = float(value_str)
                        fields.append(ParsedField(
                            source="Bank Statement",
                            line=field_name,
                            value=value,
                            confidence=0.92
                        ))
                        break
                    except ValueError:
                        continue
        
        return fields
    
    @staticmethod
    def parse_document(file_path: str, document_type: str) -> ParsedDocument:
        """Main entry point for document parsing"""
        
        # Extract text from PDF
        text, num_pages = DocumentParser.extract_text_from_pdf(file_path)
        
        if not text:
            return ParsedDocument(
                document_type=document_type,
                fields=[],
                raw_text="",
                confidence_score=0.0
            )
        
        # Parse based on document type
        fields = []
        if "1040" in document_type.lower() or "individual" in document_type.lower():
            fields = DocumentParser.parse_tax_return_1040(text)
        elif "1120" in document_type.lower() or "corporate" in document_type.lower():
            fields = DocumentParser.parse_tax_return_1120(text)
        elif "p&l" in document_type.lower() or "income" in document_type.lower() or "financial" in document_type.lower():
            fields = DocumentParser.parse_financial_statement(text)
        elif "bank" in document_type.lower():
            fields = DocumentParser.parse_bank_statement(text)
        else:
            # Try all parsers
            fields.extend(DocumentParser.parse_tax_return_1040(text))
            fields.extend(DocumentParser.parse_tax_return_1120(text))
            fields.extend(DocumentParser.parse_financial_statement(text))
            fields.extend(DocumentParser.parse_bank_statement(text))
        
        # Calculate overall confidence
        if fields:
            avg_confidence = sum(f.confidence for f in fields) / len(fields)
        else:
            avg_confidence = 0.0
        
        return ParsedDocument(
            document_type=document_type,
            fields=fields,
            raw_text=text[:5000],  # First 5000 chars for reference
            confidence_score=round(avg_confidence, 2)
        )
    
    @staticmethod
    def extract_financial_data_from_parsed(parsed_docs: List[ParsedDocument]) -> Dict:
        """Extract and aggregate financial data from multiple parsed documents"""
        
        data = {
            "business_revenue": 0,
            "business_net_income": 0,
            "depreciation": 0,
            "amortization": 0,
            "interest_expense": 0,
            "personal_agi": 0,
            "k1_income": 0,
            "ending_balance": 0
        }
        
        for doc in parsed_docs:
            for field in doc.fields:
                line_lower = field.line.lower()
                
                if "revenue" in line_lower or "gross_receipts" in line_lower:
                    data["business_revenue"] = max(data["business_revenue"], field.value)
                elif "net_income" in line_lower or "net profit" in line_lower:
                    data["business_net_income"] = max(data["business_net_income"], field.value)
                elif "depreciation" in line_lower:
                    data["depreciation"] = max(data["depreciation"], field.value)
                elif "amortization" in line_lower:
                    data["amortization"] = max(data["amortization"], field.value)
                elif "interest" in line_lower:
                    data["interest_expense"] = max(data["interest_expense"], field.value)
                elif "agi" in line_lower:
                    data["personal_agi"] = max(data["personal_agi"], field.value)
                elif "ending_balance" in line_lower:
                    data["ending_balance"] = max(data["ending_balance"], field.value)
        
        return data
