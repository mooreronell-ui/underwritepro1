from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean, Text, Enum, ForeignKey, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid
import enum

# Database URL - using SQLite for MVP, can switch to PostgreSQL
DATABASE_URL = "sqlite:///./underwritepro.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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

# Database initialization
def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
