"""
Communication Service - Unified inbox, email, SMS, and messaging
Part of UnderwritePro Enhanced Platform
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr
import os
import json

# Email and SMS providers
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False


# Pydantic Models

class MessageCreate(BaseModel):
    conversation_id: Optional[str] = None
    sender_type: str  # 'user', 'borrower', 'system'
    sender_id: str
    recipient_type: str
    recipient_id: str
    channel: str  # 'email', 'sms', 'internal'
    subject: Optional[str] = None
    body: str
    html_body: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ConversationCreate(BaseModel):
    deal_id: Optional[str] = None
    borrower_id: Optional[str] = None
    subject: str
    assigned_to: Optional[str] = None


class EmailSend(BaseModel):
    to_email: EmailStr
    to_name: Optional[str] = None
    subject: str
    body_text: str
    body_html: Optional[str] = None
    from_email: Optional[EmailStr] = None
    from_name: Optional[str] = None


class SMSSend(BaseModel):
    to_phone: str
    body: str
    from_phone: Optional[str] = None


# Communication Service Class

class CommunicationService:
    """Handles all communication operations"""
    
    def __init__(self, db):
        self.db = db
        self.sendgrid_key = os.getenv('SENDGRID_API_KEY')
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_phone = os.getenv('TWILIO_PHONE_NUMBER')
        self.default_from_email = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@underwritepro.com')
        self.default_from_name = os.getenv('DEFAULT_FROM_NAME', 'UnderwritePro')
        
    # Conversation Management
    
    def create_conversation(self, conversation: ConversationCreate) -> Dict[str, Any]:
        """Create a new conversation"""
        query = """
            INSERT INTO conversations (deal_id, borrower_id, subject, assigned_to, last_message_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, deal_id, borrower_id, subject, status, assigned_to, created_at
        """
        result = self.db.execute_query(
            query,
            (conversation.deal_id, conversation.borrower_id, conversation.subject, 
             conversation.assigned_to, datetime.now())
        )
        return result[0] if result else None
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID"""
        query = """
            SELECT c.*, 
                   d.deal_type, d.loan_amount,
                   b.name as borrower_name, b.email as borrower_email,
                   u.full_name as assigned_to_name
            FROM conversations c
            LEFT JOIN deals d ON c.deal_id = d.id
            LEFT JOIN borrowers b ON c.borrower_id = b.id
            LEFT JOIN users u ON c.assigned_to = u.id
            WHERE c.id = %s
        """
        result = self.db.execute_query(query, (conversation_id,))
        return result[0] if result else None
    
    def list_conversations(self, filters: Dict[str, Any] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List conversations with optional filters"""
        where_clauses = []
        params = []
        
        if filters:
            if filters.get('deal_id'):
                where_clauses.append("c.deal_id = %s")
                params.append(filters['deal_id'])
            if filters.get('borrower_id'):
                where_clauses.append("c.borrower_id = %s")
                params.append(filters['borrower_id'])
            if filters.get('assigned_to'):
                where_clauses.append("c.assigned_to = %s")
                params.append(filters['assigned_to'])
            if filters.get('status'):
                where_clauses.append("c.status = %s")
                params.append(filters['status'])
        
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        query = f"""
            SELECT c.*, 
                   d.deal_type,
                   b.name as borrower_name,
                   u.full_name as assigned_to_name,
                   (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) as message_count
            FROM conversations c
            LEFT JOIN deals d ON c.deal_id = d.id
            LEFT JOIN borrowers b ON c.borrower_id = b.id
            LEFT JOIN users u ON c.assigned_to = u.id
            {where_sql}
            ORDER BY c.last_message_at DESC NULLS LAST, c.created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        
        return self.db.execute_query(query, tuple(params))
    
    def update_conversation(self, conversation_id: str, updates: Dict[str, Any]) -> bool:
        """Update conversation"""
        allowed_fields = ['subject', 'status', 'assigned_to']
        update_fields = []
        params = []
        
        for field in allowed_fields:
            if field in updates:
                update_fields.append(f"{field} = %s")
                params.append(updates[field])
        
        if not update_fields:
            return False
        
        update_fields.append("updated_at = %s")
        params.append(datetime.now())
        params.append(conversation_id)
        
        query = f"""
            UPDATE conversations 
            SET {', '.join(update_fields)}
            WHERE id = %s
        """
        self.db.execute_query(query, tuple(params))
        return True
    
    # Message Management
    
    def create_message(self, message: MessageCreate) -> Dict[str, Any]:
        """Create and optionally send a message"""
        # If no conversation_id, create one
        if not message.conversation_id:
            if message.channel == 'email':
                subject = message.subject or "New Message"
            else:
                subject = f"{message.channel.upper()} Message"
            
            conversation = self.create_conversation(ConversationCreate(
                deal_id=None,
                borrower_id=message.recipient_id if message.recipient_type == 'borrower' else None,
                subject=subject,
                assigned_to=message.recipient_id if message.recipient_type == 'user' else None
            ))
            message.conversation_id = conversation['id']
        
        # Insert message
        query = """
            INSERT INTO messages (conversation_id, sender_type, sender_id, recipient_type, 
                                recipient_id, channel, subject, body, html_body, status, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, conversation_id, sender_type, sender_id, channel, subject, body, status, created_at
        """
        result = self.db.execute_query(
            query,
            (message.conversation_id, message.sender_type, message.sender_id, message.recipient_type,
             message.recipient_id, message.channel, message.subject, message.body, message.html_body,
             'draft', json.dumps(message.metadata) if message.metadata else None)
        )
        
        if result:
            message_record = result[0]
            
            # Update conversation last_message_at
            self.db.execute_query(
                "UPDATE conversations SET last_message_at = %s WHERE id = %s",
                (datetime.now(), message.conversation_id)
            )
            
            return message_record
        return None
    
    def get_conversation_messages(self, conversation_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all messages in a conversation"""
        query = """
            SELECT m.*,
                   CASE 
                       WHEN m.sender_type = 'user' THEN u.full_name
                       WHEN m.sender_type = 'borrower' THEN b.name
                       ELSE 'System'
                   END as sender_name
            FROM messages m
            LEFT JOIN users u ON m.sender_type = 'user' AND m.sender_id = u.id
            LEFT JOIN borrowers b ON m.sender_type = 'borrower' AND m.sender_id = b.id
            WHERE m.conversation_id = %s
            ORDER BY m.created_at ASC
            LIMIT %s OFFSET %s
        """
        return self.db.execute_query(query, (conversation_id, limit, offset))
    
    def mark_message_sent(self, message_id: str, status: str = 'sent') -> bool:
        """Mark message as sent"""
        query = """
            UPDATE messages 
            SET status = %s, sent_at = %s
            WHERE id = %s
        """
        self.db.execute_query(query, (status, datetime.now(), message_id))
        return True
    
    def mark_message_delivered(self, message_id: str) -> bool:
        """Mark message as delivered"""
        query = """
            UPDATE messages 
            SET status = 'delivered', delivered_at = %s
            WHERE id = %s
        """
        self.db.execute_query(query, (datetime.now(), message_id))
        return True
    
    def mark_message_read(self, message_id: str) -> bool:
        """Mark message as read"""
        query = """
            UPDATE messages 
            SET status = 'read', read_at = %s
            WHERE id = %s
        """
        self.db.execute_query(query, (datetime.now(), message_id))
        return True
    
    # Email Sending
    
    def send_email(self, email: EmailSend) -> Dict[str, Any]:
        """Send email via SendGrid"""
        if not SENDGRID_AVAILABLE or not self.sendgrid_key:
            # Simulate sending for development
            return {
                'success': True,
                'message_id': 'simulated_' + str(datetime.now().timestamp()),
                'status': 'simulated',
                'note': 'SendGrid not configured, email simulated'
            }
        
        try:
            from_email_addr = email.from_email or self.default_from_email
            from_name = email.from_name or self.default_from_name
            
            message = Mail(
                from_email=Email(from_email_addr, from_name),
                to_emails=To(email.to_email, email.to_name),
                subject=email.subject,
                plain_text_content=Content("text/plain", email.body_text),
                html_content=Content("text/html", email.body_html or email.body_text)
            )
            
            sg = SendGridAPIClient(self.sendgrid_key)
            response = sg.send(message)
            
            return {
                'success': True,
                'message_id': response.headers.get('X-Message-Id'),
                'status_code': response.status_code
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # SMS Sending
    
    def send_sms(self, sms: SMSSend) -> Dict[str, Any]:
        """Send SMS via Twilio"""
        if not TWILIO_AVAILABLE or not self.twilio_account_sid:
            # Simulate sending for development
            return {
                'success': True,
                'message_sid': 'simulated_' + str(datetime.now().timestamp()),
                'status': 'simulated',
                'note': 'Twilio not configured, SMS simulated'
            }
        
        try:
            client = TwilioClient(self.twilio_account_sid, self.twilio_auth_token)
            from_phone = sms.from_phone or self.twilio_phone
            
            message = client.messages.create(
                body=sms.body,
                from_=from_phone,
                to=sms.to_phone
            )
            
            return {
                'success': True,
                'message_sid': message.sid,
                'status': message.status
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # Template Management
    
    def get_email_template(self, template_id: str = None, template_type: str = None, organization_id: str = None) -> Optional[Dict[str, Any]]:
        """Get email template by ID or type"""
        if template_id:
            query = "SELECT * FROM email_templates WHERE id = %s AND is_active = true"
            params = (template_id,)
        elif template_type and organization_id:
            query = "SELECT * FROM email_templates WHERE template_type = %s AND organization_id = %s AND is_active = true ORDER BY created_at DESC LIMIT 1"
            params = (template_type, organization_id)
        else:
            return None
        
        result = self.db.execute_query(query, params)
        return result[0] if result else None
    
    def render_email_template(self, template: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, str]:
        """Render email template with variables"""
        subject = template['subject']
        body_html = template['body_html']
        body_text = template.get('body_text', '')
        
        # Simple variable replacement
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            subject = subject.replace(placeholder, str(value))
            body_html = body_html.replace(placeholder, str(value))
            if body_text:
                body_text = body_text.replace(placeholder, str(value))
        
        return {
            'subject': subject,
            'body_html': body_html,
            'body_text': body_text or body_html
        }
    
    def get_sms_template(self, template_id: str = None, template_type: str = None, organization_id: str = None) -> Optional[Dict[str, Any]]:
        """Get SMS template by ID or type"""
        if template_id:
            query = "SELECT * FROM sms_templates WHERE id = %s AND is_active = true"
            params = (template_id,)
        elif template_type and organization_id:
            query = "SELECT * FROM sms_templates WHERE template_type = %s AND organization_id = %s AND is_active = true ORDER BY created_at DESC LIMIT 1"
            params = (template_type, organization_id)
        else:
            return None
        
        result = self.db.execute_query(query, params)
        return result[0] if result else None
    
    def render_sms_template(self, template: Dict[str, Any], variables: Dict[str, Any]) -> str:
        """Render SMS template with variables"""
        body = template['body']
        
        # Simple variable replacement
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            body = body.replace(placeholder, str(value))
        
        return body
    
    # Unified Inbox
    
    def get_unified_inbox(self, user_id: str, filters: Dict[str, Any] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get unified inbox for a user"""
        where_clauses = ["(c.assigned_to = %s OR m.recipient_id = %s)"]
        params = [user_id, user_id]
        
        if filters:
            if filters.get('status'):
                where_clauses.append("c.status = %s")
                params.append(filters['status'])
            if filters.get('channel'):
                where_clauses.append("m.channel = %s")
                params.append(filters['channel'])
            if filters.get('unread_only'):
                where_clauses.append("m.status != 'read'")
        
        where_sql = "WHERE " + " AND ".join(where_clauses)
        
        query = f"""
            SELECT DISTINCT ON (c.id) 
                   c.id as conversation_id, c.subject, c.status as conversation_status,
                   c.last_message_at, c.created_at as conversation_created_at,
                   m.id as last_message_id, m.body as last_message_body, 
                   m.channel, m.status as message_status, m.created_at as last_message_created_at,
                   b.name as borrower_name, b.email as borrower_email,
                   d.deal_type, d.loan_amount,
                   (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id AND status != 'read') as unread_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            LEFT JOIN borrowers b ON c.borrower_id = b.id
            LEFT JOIN deals d ON c.deal_id = d.id
            {where_sql}
            ORDER BY c.id, m.created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        
        return self.db.execute_query(query, tuple(params))


# Helper functions for API endpoints

def get_communication_service(db):
    """Factory function to create communication service"""
    return CommunicationService(db)
