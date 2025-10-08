"""
Create Master Admin Account
Run this once to create the master admin user
"""

import sys
import os
from getpass import getpass

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from database_unified import get_db, User, Organization, init_db
from auth import get_password_hash
import uuid
from datetime import datetime

def create_master_admin():
    """Create the master admin account"""
    
    print("🍎 UNDERWRITEPRO - CREATE MASTER ADMIN")
    print("=" * 50)
    
    # Get admin details
    email = input("\nAdmin Email: ").strip()
    if not email:
        print("❌ Email is required")
        return
    
    full_name = input("Admin Full Name: ").strip()
    if not full_name:
        print("❌ Full name is required")
        return
    
    password = getpass("Admin Password (min 8 chars): ")
    if len(password) < 8:
        print("❌ Password must be at least 8 characters")
        return
    
    password_confirm = getpass("Confirm Password: ")
    if password != password_confirm:
        print("❌ Passwords don't match")
        return
    
    print("\n🔄 Creating master admin account...")
    
    try:
        # Initialize database
        init_db()
        
        # Get database session
        db = next(get_db())
        
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.email == email).first()
        if existing_admin:
            print(f"❌ User with email {email} already exists")
            
            # Offer to upgrade to admin
            upgrade = input("\nUpgrade existing user to admin? (yes/no): ").strip().lower()
            if upgrade == "yes":
                existing_admin.role = "admin"
                db.commit()
                print(f"✅ User {email} upgraded to admin!")
                return
            else:
                return
        
        # Create admin organization
        org = Organization(
            id=str(uuid.uuid4()),
            name="UnderwritePro Admin",
            plan_type="enterprise",
            created_at=datetime.utcnow()
        )
        db.add(org)
        db.flush()
        
        # Create admin user
        admin = User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=get_password_hash(password),
            full_name=full_name,
            role="admin",
            organization_id=org.id,
            created_at=datetime.utcnow()
        )
        db.add(admin)
        db.commit()
        
        print("\n" + "=" * 50)
        print("✅ MASTER ADMIN CREATED SUCCESSFULLY!")
        print("=" * 50)
        print(f"\n📧 Email: {email}")
        print(f"👤 Name: {full_name}")
        print(f"🔐 Role: admin")
        print(f"🏢 Organization: UnderwritePro Admin")
        print(f"\n🚀 You can now log in at:")
        print(f"   https://underwritepro-backend.onrender.com/#/login")
        print(f"\n📊 Access admin dashboard at:")
        print(f"   https://underwritepro-backend.onrender.com/#/admin")
        print("\n" + "=" * 50)
        
    except Exception as e:
        print(f"\n❌ Error creating admin: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_master_admin()
