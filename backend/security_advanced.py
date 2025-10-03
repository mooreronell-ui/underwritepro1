"""
Advanced Security Features
2FA, SSO, Advanced RBAC, and Security Enhancements
"""

import pyotp
import qrcode
import io
import base64
from typing import Dict, Optional, List
import uuid
from datetime import datetime, timedelta
from database_unified import get_db_connection
import hashlib
import secrets

class AdvancedSecurity:
    """Advanced security features for enterprise deployments"""
    
    def __init__(self):
        self.conn = get_db_connection()
    
    # Two-Factor Authentication (2FA)
    def enable_2fa(self, user_id: str) -> Dict:
        """Enable 2FA for a user and generate QR code"""
        # Generate secret key
        secret = pyotp.random_base32()
        
        # Create TOTP object
        totp = pyotp.TOTP(secret)
        
        # Generate provisioning URI for QR code
        provisioning_uri = totp.provisioning_uri(
            name=user_id,
            issuer_name="UnderwritePro"
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        # Store secret in database
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET two_factor_secret = %s, two_factor_enabled = FALSE
            WHERE id = %s
        """, (secret, user_id))
        self.conn.commit()
        
        return {
            "secret": secret,
            "qr_code": f"data:image/png;base64,{qr_code_base64}",
            "provisioning_uri": provisioning_uri
        }
    
    def verify_2fa_setup(self, user_id: str, token: str) -> bool:
        """Verify 2FA token during setup"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT two_factor_secret FROM users WHERE id = %s
        """, (user_id,))
        
        row = cursor.fetchone()
        if not row or not row[0]:
            return False
        
        secret = row[0]
        totp = pyotp.TOTP(secret)
        
        if totp.verify(token):
            # Enable 2FA
            cursor.execute("""
                UPDATE users SET two_factor_enabled = TRUE WHERE id = %s
            """, (user_id,))
            self.conn.commit()
            return True
        
        return False
    
    def verify_2fa_login(self, user_id: str, token: str) -> bool:
        """Verify 2FA token during login"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT two_factor_secret, two_factor_enabled 
            FROM users WHERE id = %s
        """, (user_id,))
        
        row = cursor.fetchone()
        if not row or not row[0] or not row[1]:
            return False
        
        secret = row[0]
        totp = pyotp.TOTP(secret)
        
        return totp.verify(token)
    
    def disable_2fa(self, user_id: str) -> bool:
        """Disable 2FA for a user"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET two_factor_enabled = FALSE, two_factor_secret = NULL
            WHERE id = %s
        """, (user_id,))
        self.conn.commit()
        return True
    
    def is_2fa_enabled(self, user_id: str) -> bool:
        """Check if 2FA is enabled for a user"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT two_factor_enabled FROM users WHERE id = %s
        """, (user_id,))
        
        row = cursor.fetchone()
        return row[0] if row else False
    
    # Backup Codes
    def generate_backup_codes(self, user_id: str, count: int = 10) -> List[str]:
        """Generate backup codes for 2FA recovery"""
        codes = []
        cursor = self.conn.cursor()
        
        for _ in range(count):
            code = secrets.token_hex(4).upper()
            code_hash = hashlib.sha256(code.encode()).hexdigest()
            codes.append(code)
            
            cursor.execute("""
                INSERT INTO user_backup_codes (id, user_id, code_hash, created_at)
                VALUES (%s, %s, %s, %s)
            """, (str(uuid.uuid4()), user_id, code_hash, datetime.utcnow()))
        
        self.conn.commit()
        return codes
    
    def verify_backup_code(self, user_id: str, code: str) -> bool:
        """Verify and consume a backup code"""
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT id FROM user_backup_codes
            WHERE user_id = %s AND code_hash = %s AND used_at IS NULL
        """, (user_id, code_hash))
        
        row = cursor.fetchone()
        if row:
            # Mark as used
            cursor.execute("""
                UPDATE user_backup_codes
                SET used_at = %s
                WHERE id = %s
            """, (datetime.utcnow(), row[0]))
            self.conn.commit()
            return True
        
        return False
    
    # Session Management
    def create_session(self, user_id: str, ip_address: str, user_agent: str) -> str:
        """Create a new user session"""
        session_id = str(uuid.uuid4())
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO user_sessions (id, user_id, ip_address, user_agent, 
                                      created_at, last_activity, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (session_id, user_id, ip_address, user_agent, datetime.utcnow(),
              datetime.utcnow(), datetime.utcnow() + timedelta(days=7)))
        
        self.conn.commit()
        return session_id
    
    def get_active_sessions(self, user_id: str) -> List[Dict]:
        """Get all active sessions for a user"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, ip_address, user_agent, created_at, last_activity
            FROM user_sessions
            WHERE user_id = %s AND expires_at > %s
            ORDER BY last_activity DESC
        """, (user_id, datetime.utcnow()))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                "session_id": row[0],
                "ip_address": row[1],
                "user_agent": row[2],
                "created_at": row[3].isoformat() if row[3] else None,
                "last_activity": row[4].isoformat() if row[4] else None
            })
        
        return sessions
    
    def revoke_session(self, session_id: str) -> bool:
        """Revoke a specific session"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE user_sessions
            SET expires_at = %s
            WHERE id = %s
        """, (datetime.utcnow(), session_id))
        self.conn.commit()
        return True
    
    def revoke_all_sessions(self, user_id: str, except_session: Optional[str] = None) -> int:
        """Revoke all sessions for a user except optionally one"""
        cursor = self.conn.cursor()
        
        if except_session:
            cursor.execute("""
                UPDATE user_sessions
                SET expires_at = %s
                WHERE user_id = %s AND id != %s
            """, (datetime.utcnow(), user_id, except_session))
        else:
            cursor.execute("""
                UPDATE user_sessions
                SET expires_at = %s
                WHERE user_id = %s
            """, (datetime.utcnow(), user_id))
        
        revoked_count = cursor.rowcount
        self.conn.commit()
        return revoked_count
    
    # Advanced Role-Based Access Control (RBAC)
    def create_role(self, name: str, permissions: List[str], 
                   description: Optional[str] = None) -> Dict:
        """Create a new role with permissions"""
        role_id = str(uuid.uuid4())
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO roles (id, name, description, permissions, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (role_id, name, description, str(permissions), datetime.utcnow()))
        
        self.conn.commit()
        
        return {
            "id": role_id,
            "name": name,
            "description": description,
            "permissions": permissions
        }
    
    def assign_role(self, user_id: str, role_id: str) -> bool:
        """Assign a role to a user"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO user_roles (id, user_id, role_id, assigned_at)
            VALUES (%s, %s, %s, %s)
        """, (str(uuid.uuid4()), user_id, role_id, datetime.utcnow()))
        self.conn.commit()
        return True
    
    def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if a user has a specific permission"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT r.permissions
            FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = %s
        """, (user_id,))
        
        for row in cursor.fetchall():
            permissions = eval(row[0]) if row[0] else []
            if permission in permissions or '*' in permissions:
                return True
        
        return False
    
    # Audit Logging
    def log_security_event(self, user_id: str, event_type: str, 
                          details: Dict, ip_address: Optional[str] = None) -> str:
        """Log a security event"""
        event_id = str(uuid.uuid4())
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO security_audit_log (id, user_id, event_type, details, 
                                           ip_address, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (event_id, user_id, event_type, str(details), ip_address, datetime.utcnow()))
        
        self.conn.commit()
        return event_id
    
    def get_security_events(self, user_id: Optional[str] = None, 
                           event_type: Optional[str] = None,
                           limit: int = 100) -> List[Dict]:
        """Get security audit events"""
        cursor = self.conn.cursor()
        
        query = "SELECT id, user_id, event_type, details, ip_address, created_at FROM security_audit_log WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = %s"
            params.append(user_id)
        
        if event_type:
            query += " AND event_type = %s"
            params.append(event_type)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        
        events = []
        for row in cursor.fetchall():
            events.append({
                "id": row[0],
                "user_id": row[1],
                "event_type": row[2],
                "details": eval(row[3]) if row[3] else {},
                "ip_address": row[4],
                "created_at": row[5].isoformat() if row[5] else None
            })
        
        return events
    
    # IP Whitelisting
    def add_ip_whitelist(self, organization_id: str, ip_address: str, 
                        description: Optional[str] = None) -> Dict:
        """Add an IP to the whitelist"""
        whitelist_id = str(uuid.uuid4())
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO ip_whitelist (id, organization_id, ip_address, description, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (whitelist_id, organization_id, ip_address, description, datetime.utcnow()))
        
        self.conn.commit()
        
        return {
            "id": whitelist_id,
            "ip_address": ip_address,
            "description": description
        }
    
    def check_ip_whitelist(self, organization_id: str, ip_address: str) -> bool:
        """Check if an IP is whitelisted"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM ip_whitelist
            WHERE organization_id = %s AND ip_address = %s
        """, (organization_id, ip_address))
        
        count = cursor.fetchone()[0]
        return count > 0
