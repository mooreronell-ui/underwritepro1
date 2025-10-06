"""
Database configuration and initialization for UnderwritePro
The Apple of Commercial Underwriting
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator

from models.base import Base

# Import all models to ensure they're registered with Base
from models import (
    User, Organization,
    LoanApplication,
    Borrower, Guarantor,
    Property, PropertyFinancials, RentRoll,
    FinancialStatement, FinancialRatios, RiskAssessment,
    Document,
    LenderNetwork, LoanSubmission, RateQuote, BrokerCommission,
    UnderwritingPolicy, LoanPipeline, CreditDecision, LoanServicing,
    CovenantMonitoring, PortfolioAnalytics
)


# Database URL configuration
def get_database_url() -> str:
    """
    Get database URL from environment variables
    Supports PostgreSQL (production) and SQLite (development)
    """
    # Check for PostgreSQL URL first (production)
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        # Render.com uses postgres:// but SQLAlchemy requires postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return database_url
    
    # Fall back to SQLite for development
    return "sqlite:///./underwritepro.db"


# Create engine
DATABASE_URL = get_database_url()
IS_SQLITE = DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    # SQLite configuration for development
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False  # Set to True for SQL debugging
    )
else:
    # PostgreSQL configuration for production
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before using
        pool_size=10,  # Connection pool size
        max_overflow=20,  # Allow up to 20 connections beyond pool_size
        echo=False  # Set to True for SQL debugging
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Initialize database - create all tables
    """
    print("🔧 Initializing UnderwritePro database...")
    print(f"📊 Database: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        print(f"📋 Tables created: {len(Base.metadata.tables)}")
        
        # Print table names
        for table_name in Base.metadata.tables.keys():
            print(f"   - {table_name}")
            
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        raise


def drop_all_tables():
    """
    Drop all tables - USE WITH CAUTION!
    Only for development/testing
    """
    if not IS_SQLITE:
        confirm = input("⚠️  WARNING: This will drop all tables in production database. Type 'YES' to confirm: ")
        if confirm != "YES":
            print("❌ Operation cancelled")
            return
    
    print("🗑️  Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("✅ All tables dropped")


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get database session
    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database session
    Usage:
        with get_db_context() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_database_connection() -> bool:
    """
    Check if database connection is working
    """
    try:
        from sqlalchemy import text
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


# Export commonly used items
__all__ = [
    'engine',
    'SessionLocal',
    'get_db',
    'get_db_context',
    'init_db',
    'drop_all_tables',
    'check_database_connection',
    'DATABASE_URL',
    'IS_SQLITE',
]


if __name__ == "__main__":
    """
    Run this script directly to initialize the database
    Usage: python database_config.py
    """
    print("=" * 60)
    print("UnderwritePro Database Initialization")
    print("The Apple of Commercial Underwriting")
    print("=" * 60)
    print()
    
    # Check connection
    print("🔍 Checking database connection...")
    if check_database_connection():
        print("✅ Database connection successful!")
    else:
        print("❌ Database connection failed!")
        exit(1)
    
    print()
    
    # Initialize database
    init_db()
    
    print()
    print("=" * 60)
    print("✨ Database initialization complete!")
    print("=" * 60)
