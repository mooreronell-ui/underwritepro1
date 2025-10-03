#!/usr/bin/env python3
"""
Migration script to move data from SQLite to PostgreSQL
"""
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import models from old database
from database import Base as OldBase, User, Organization, Borrower, Deal, Document, UnderwritingResult, Report, AuditLog

# SQLite database
SQLITE_URL = "sqlite:///./underwritepro.db"
POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql://uwpro:uwpro_secure_pass_2025@localhost/underwritepro")

def migrate():
    """Migrate data from SQLite to PostgreSQL"""
    
    # Create engines
    sqlite_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    postgres_engine = create_engine(POSTGRES_URL)
    
    # Create sessions
    SqliteSession = sessionmaker(bind=sqlite_engine)
    PostgresSession = sessionmaker(bind=postgres_engine)
    
    sqlite_session = SqliteSession()
    postgres_session = PostgresSession()
    
    try:
        # Create all tables in PostgreSQL
        logger.info("Creating PostgreSQL tables...")
        OldBase.metadata.create_all(postgres_engine)
        logger.info("✓ Tables created")
        
        # Check if SQLite database exists
        if not os.path.exists("underwritepro.db"):
            logger.info("No SQLite database found. Starting with fresh PostgreSQL database.")
            return True
        
        # Migrate Organizations
        logger.info("Migrating organizations...")
        orgs = sqlite_session.query(Organization).all()
        for org in orgs:
            # Check if already exists
            existing = postgres_session.query(Organization).filter_by(id=org.id).first()
            if not existing:
                postgres_session.merge(org)
        postgres_session.commit()
        logger.info(f"✓ Migrated {len(orgs)} organizations")
        
        # Migrate Users
        logger.info("Migrating users...")
        users = sqlite_session.query(User).all()
        for user in users:
            existing = postgres_session.query(User).filter_by(id=user.id).first()
            if not existing:
                postgres_session.merge(user)
        postgres_session.commit()
        logger.info(f"✓ Migrated {len(users)} users")
        
        # Migrate Borrowers
        logger.info("Migrating borrowers...")
        borrowers = sqlite_session.query(Borrower).all()
        for borrower in borrowers:
            existing = postgres_session.query(Borrower).filter_by(id=borrower.id).first()
            if not existing:
                postgres_session.merge(borrower)
        postgres_session.commit()
        logger.info(f"✓ Migrated {len(borrowers)} borrowers")
        
        # Migrate Deals
        logger.info("Migrating deals...")
        deals = sqlite_session.query(Deal).all()
        for deal in deals:
            existing = postgres_session.query(Deal).filter_by(id=deal.id).first()
            if not existing:
                postgres_session.merge(deal)
        postgres_session.commit()
        logger.info(f"✓ Migrated {len(deals)} deals")
        
        # Migrate Documents
        logger.info("Migrating documents...")
        documents = sqlite_session.query(Document).all()
        for doc in documents:
            existing = postgres_session.query(Document).filter_by(id=doc.id).first()
            if not existing:
                postgres_session.merge(doc)
        postgres_session.commit()
        logger.info(f"✓ Migrated {len(documents)} documents")
        
        # Migrate Underwriting Results
        logger.info("Migrating underwriting results...")
        results = sqlite_session.query(UnderwritingResult).all()
        for result in results:
            existing = postgres_session.query(UnderwritingResult).filter_by(id=result.id).first()
            if not existing:
                postgres_session.merge(result)
        postgres_session.commit()
        logger.info(f"✓ Migrated {len(results)} underwriting results")
        
        # Migrate Reports
        logger.info("Migrating reports...")
        reports = sqlite_session.query(Report).all()
        for report in reports:
            existing = postgres_session.query(Report).filter_by(id=report.id).first()
            if not existing:
                postgres_session.merge(report)
        postgres_session.commit()
        logger.info(f"✓ Migrated {len(reports)} reports")
        
        # Migrate Audit Logs
        logger.info("Migrating audit logs...")
        logs = sqlite_session.query(AuditLog).all()
        for log in logs:
            existing = postgres_session.query(AuditLog).filter_by(id=log.id).first()
            if not existing:
                postgres_session.merge(log)
        postgres_session.commit()
        logger.info(f"✓ Migrated {len(logs)} audit logs")
        
        logger.info("✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        postgres_session.rollback()
        return False
    finally:
        sqlite_session.close()
        postgres_session.close()

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
