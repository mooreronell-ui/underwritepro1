#!/usr/bin/env python3
"""
Test script to verify all imports work before deployment
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("Testing imports...")

try:
    print("✓ Testing standard library imports...")
    import json
    import logging
    import uuid
    from datetime import datetime
    print("  ✓ Standard library OK")
    
    print("✓ Testing FastAPI...")
    from fastapi import FastAPI
    print("  ✓ FastAPI OK")
    
    print("✓ Testing Pydantic...")
    from pydantic import BaseModel
    print("  ✓ Pydantic OK")
    
    print("✓ Testing SQLAlchemy...")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    print("  ✓ SQLAlchemy OK")
    
    print("✓ Testing authentication libraries...")
    from jose import jwt
    import bcrypt
    from passlib.hash import bcrypt as passlib_bcrypt
    print("  ✓ Auth libraries OK")
    
    print("✓ Testing document processing...")
    import PyPDF2
    print("  ✓ PyPDF2 OK")
    
    print("✓ Testing report generation...")
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate
    print("  ✓ ReportLab OK")
    
    print("✓ Testing external services...")
    import openai
    import stripe
    import redis
    print("  ✓ External services OK")
    
    print("✓ Testing security libraries...")
    import pyotp
    import qrcode
    import bleach
    print("  ✓ Security libraries OK")
    
    print("✓ Testing utilities...")
    import requests
    import psutil
    from dotenv import load_dotenv
    print("  ✓ Utilities OK")
    
    print("\n✅ ALL IMPORTS SUCCESSFUL!")
    print("\nNow testing local module imports...")
    
    # Test local imports
    os.chdir('backend')
    
    print("✓ Testing database_unified...")
    from database_unified import get_db, User
    print("  ✓ database_unified OK")
    
    print("✓ Testing auth...")
    from auth import create_access_token
    print("  ✓ auth OK")
    
    print("✓ Testing underwriting...")
    from underwriting import UnderwritingEngine
    print("  ✓ underwriting OK")
    
    print("✓ Testing document_parser...")
    from document_parser import DocumentParser
    print("  ✓ document_parser OK")
    
    print("✓ Testing report_generator...")
    from report_generator import ReportGenerator
    print("  ✓ report_generator OK")
    
    print("✓ Testing security...")
    from security import validate_file_upload
    print("  ✓ security OK")
    
    print("\n✅ ALL LOCAL MODULE IMPORTS SUCCESSFUL!")
    print("\n🎉 Application is ready for deployment!")
    
except ImportError as e:
    print(f"\n❌ IMPORT ERROR: {e}")
    print(f"\nMissing package. Please add to requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    sys.exit(1)
