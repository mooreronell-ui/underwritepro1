"""
Security utilities for input validation, sanitization, and protection
"""
import re
import bleach
from typing import Optional
from pydantic import BaseModel, EmailStr, validator, Field
from fastapi import HTTPException

# ==================== Input Validation Models ====================

class UserRegistration(BaseModel):
    """Validated user registration data"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=100)
    organization_name: str = Field(..., min_length=1, max_length=100)
    
    @validator('password')
    def password_strength(cls, v):
        """Ensure password meets minimum requirements"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v
    
    @validator('full_name', 'organization_name')
    def sanitize_text(cls, v):
        """Sanitize text input to prevent XSS"""
        return bleach.clean(v, strip=True)

class DealCreate(BaseModel):
    """Validated deal creation data"""
    borrower_name: str = Field(..., min_length=1, max_length=200)
    entity_type: str = Field(..., pattern=r'^(individual|llc|corporation|partnership)$')
    deal_type: str = Field(..., pattern=r'^(purchase|refinance)$')
    loan_amount: float = Field(..., gt=0, lt=1000000000)  # Max $1B
    appraised_value: float = Field(..., gt=0, lt=1000000000)
    interest_rate: float = Field(..., gt=0, lt=1)  # 0-100%
    
    @validator('borrower_name')
    def sanitize_borrower_name(cls, v):
        """Sanitize borrower name"""
        return bleach.clean(v, strip=True)

class DocumentUpload(BaseModel):
    """Validated document upload metadata"""
    document_type: str = Field(..., pattern=r'^(tax_return|pl_statement|bank_statement|other)$')

# ==================== Security Headers ====================

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    # Temporarily disabled CSP for debugging
    # "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin"
}

# ==================== File Validation ====================

ALLOWED_FILE_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx'}
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
}

def validate_file_upload(filename: str, content_type: str, file_size: int, max_size_mb: int = 10):
    """
    Validate uploaded file
    
    Args:
        filename: Name of the file
        content_type: MIME type
        file_size: Size in bytes
        max_size_mb: Maximum allowed size in MB
    
    Raises:
        HTTPException if validation fails
    """
    # Check file extension
    ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_FILE_EXTENSIONS)}"
        )
    
    # Check MIME type
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type"
        )
    
    # Check file size
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {max_size_mb}MB"
        )
    
    # Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename"
        )
    
    return True

# ==================== SQL Injection Prevention ====================

def sanitize_sql_input(value: str) -> str:
    """
    Basic sanitization for SQL inputs
    Note: SQLAlchemy ORM already provides protection, this is extra layer
    """
    # Remove potentially dangerous characters
    dangerous_chars = [';', '--', '/*', '*/', 'xp_', 'sp_', 'DROP', 'DELETE', 'INSERT', 'UPDATE']
    for char in dangerous_chars:
        if char in value.upper():
            raise HTTPException(
                status_code=400,
                detail="Invalid input detected"
            )
    return value

# ==================== Rate Limit Helpers ====================

def get_rate_limit_key(request, endpoint: str) -> str:
    """
    Generate rate limit key based on user IP and endpoint
    """
    client_ip = request.client.host
    return f"{endpoint}:{client_ip}"

# ==================== Password Policy ====================

class PasswordPolicy:
    """Password policy enforcement"""
    
    MIN_LENGTH = 8
    MAX_LENGTH = 100
    REQUIRE_UPPERCASE = False
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = False
    
    @classmethod
    def validate(cls, password: str) -> tuple[bool, Optional[str]]:
        """
        Validate password against policy
        
        Returns:
            (is_valid, error_message)
        """
        if len(password) < cls.MIN_LENGTH:
            return False, f"Password must be at least {cls.MIN_LENGTH} characters"
        
        if len(password) > cls.MAX_LENGTH:
            return False, f"Password must be at most {cls.MAX_LENGTH} characters"
        
        if cls.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if cls.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if cls.REQUIRE_DIGIT and not re.search(r'[0-9]', password):
            return False, "Password must contain at least one digit"
        
        if cls.REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
        
        return True, None

# ==================== Email Validation ====================

def validate_email(email: str) -> bool:
    """
    Validate email format
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# ==================== CSRF Protection ====================

def generate_csrf_token() -> str:
    """Generate CSRF token"""
    import secrets
    return secrets.token_urlsafe(32)

def validate_csrf_token(token: str, expected: str) -> bool:
    """Validate CSRF token"""
    return token == expected
