"""
Unified Database Module for UnderwritePro SaaS
Supports PostgreSQL with connection pooling and production features
"""
import os
import logging
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import QueuePool
from datetime import datetime
import uuid
import enum

logger = logging.getLogger(__name__)

# Database URL from environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://uwpro:uwpro_secure_2024@localhost/underwritepro"
)

# Production-grade engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,              # Number of connections to maintain
    max_overflow=40,           # Additional connections when pool is full
    pool_timeout=30,           # Seconds to wait for connection
    pool_recycle=3600,         # Recycle connections after 1 hour
    pool_pre_ping=True,        # Test connections before using
    echo=False,                # Set to True for SQL logging in dev
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()

# Enums
class UserRole(str, enum.Enum):
    broker = "broker"
    analyst = "analyst"
    approver = "approver"
    admin = "admin"

class PlanType(str, enum.Enum):
    starter = "starter"
    pro = "pro"
    enterprise = "enterprise"

class DealType(str, enum.Enum):
    purchase = "purchase"
    refi = "refi"

class DealStatus(str, enum.Enum):
    intake = "intake"
    parsing = "parsing"
    review = "review"
    underwriting = "underwriting"
    complete = "complete"

class EntityType(str, enum.Enum):
    individual = "individual"
    llc = "llc"
    corp = "corp"
    partnership = "partnership"

class DocumentType(str, enum.Enum):
    tax_return = "tax_return"
    financial_statement = "financial_statement"
    bank_statement = "bank_statement"
    appraisal = "appraisal"
    other = "other"

class ReportType(str, enum.Enum):
    executive_summary = "executive_summary"
    credit_memo = "credit_memo"
    stip_sheet = "stip_sheet"
    quick_look = "quick_look"

# Models
class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    plan = Column(String, default="starter")
    logo_url = Column(String, nullable=True)
    billing_id = Column(String, nullable=True)
    deal_limit = Column(Integer, default=10)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    users = relationship("User", back_populates="organization")
    deals = relationship("Deal", back_populates="organization")

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="broker")
    organization_id = Column(String, ForeignKey("organizations.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    organization = relationship("Organization", back_populates="users")
    deals = relationship("Deal", back_populates="created_by_user")

class Borrower(Base):
    __tablename__ = "borrowers"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    entity_type = Column(String, default="individual")
    tax_id = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    deals = relationship("Deal", back_populates="borrower")

class Deal(Base):
    __tablename__ = "deals"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, ForeignKey("organizations.id"), index=True)
    borrower_id = Column(String, ForeignKey("borrowers.id"), index=True)
    deal_type = Column(String, nullable=False)
    status = Column(String, default="intake", index=True)
    loan_amount = Column(Float, nullable=True)
    appraised_value = Column(Float, nullable=True)
    interest_rate = Column(Float, default=0.065)
    amortization_months = Column(Integer, default=240)
    balloon_months = Column(Integer, default=60)
    ltv_target = Column(Float, default=0.80)
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    organization = relationship("Organization", back_populates="deals")
    borrower = relationship("Borrower", back_populates="deals")
    created_by_user = relationship("User", back_populates="deals")
    documents = relationship("Document", back_populates="deal")
    underwriting_results = relationship("UnderwritingResult", back_populates="deal")
    reports = relationship("Report", back_populates="deal")
    financial_data = relationship("FinancialData", back_populates="deal")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    deal_id = Column(String, ForeignKey("deals.id"), index=True)
    document_type = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, default=0)
    uploaded_by = Column(String, ForeignKey("users.id"))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    parsed = Column(Boolean, default=False)
    parsed_data = Column(Text, nullable=True)  # JSON string
    confidence_score = Column(Float, nullable=True)
    
    deal = relationship("Deal", back_populates="documents")

class FinancialData(Base):
    __tablename__ = "financial_data"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    deal_id = Column(String, ForeignKey("deals.id"), index=True)
    year = Column(Integer, nullable=False)
    revenue = Column(Float, default=0)
    expenses = Column(Float, default=0)
    net_income = Column(Float, default=0)
    depreciation = Column(Float, default=0)
    amortization = Column(Float, default=0)
    interest_expense = Column(Float, default=0)
    one_time_expenses = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    deal = relationship("Deal", back_populates="financial_data")

class UnderwritingResult(Base):
    __tablename__ = "underwriting_results"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    deal_id = Column(String, ForeignKey("deals.id"), index=True)
    dscr_base = Column(Float, nullable=True)
    dscr_stressed = Column(Float, nullable=True)
    ltv = Column(Float, nullable=True)
    global_cash_flow = Column(Float, nullable=True)
    annual_debt_service = Column(Float, nullable=True)
    monthly_payment = Column(Float, nullable=True)
    liquidity_months = Column(Float, nullable=True)
    business_cash_flow = Column(Float, nullable=True)
    personal_income = Column(Float, nullable=True)
    addbacks = Column(Text, nullable=True)  # JSON string
    flags = Column(Text, nullable=True)  # JSON string
    calculation_trace = Column(Text, nullable=True)  # JSON string
    risk_rating = Column(String, nullable=True)
    recommendation = Column(Text, nullable=True)
    calculated_by = Column(String, ForeignKey("users.id"))
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    deal = relationship("Deal", back_populates="underwriting_results")

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    deal_id = Column(String, ForeignKey("deals.id"), index=True)
    report_type = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, default=0)
    generated_by = Column(String, ForeignKey("users.id"))
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    deal = relationship("Deal", back_populates="reports")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), index=True)
    event_type = Column(String, nullable=False)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    payload = Column(Text, nullable=True)  # JSON string
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

# Connection event listeners
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    logger.debug("Database connection established")

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    logger.debug("Connection checked out from pool")

# Database functions
def get_db():
    """
    Dependency function for FastAPI to get database session
    Automatically handles session lifecycle
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """
    Initialize database - create all tables
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise

def check_db_connection():
    """
    Check if database connection is working
    Returns True if successful, False otherwise
    """
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

def get_pool_status():
    """
    Get current connection pool status for monitoring
    """
    return {
        "pool_size": engine.pool.size(),
        "checked_in": engine.pool.checkedin(),
        "checked_out": engine.pool.checkedout(),
        "overflow": engine.pool.overflow(),
        "total_connections": engine.pool.size() + engine.pool.overflow()
    }
