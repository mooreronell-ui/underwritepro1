"""
Workflow Automation Engine - Triggers and actions for automated processes
Part of UnderwritePro Enhanced Platform
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import json


# Pydantic Models

class WorkflowCreate(BaseModel):
    organization_id: str
    name: str
    description: Optional[str] = None
    trigger_type: str  # deal_created, document_uploaded, stage_changed, etc.
    trigger_config: Dict[str, Any]
    actions: List[Dict[str, Any]]  # List of actions with configs


class WorkflowAction(BaseModel):
    action_type: str  # send_email, send_sms, create_task, update_field, etc.
    action_config: Dict[str, Any]
    delay_minutes: int = 0


# Workflow Engine

class WorkflowEngine:
    """Handles workflow automation"""
    
    def __init__(self, db, communication_service=None):
        self.db = db
        self.communication_service = communication_service
        
        # Register action handlers
        self.action_handlers = {
            'send_email': self._handle_send_email,
            'send_sms': self._handle_send_sms,
            'create_task': self._handle_create_task,
            'update_deal_field': self._handle_update_deal_field,
            'create_conversation': self._handle_create_conversation,
            'log_touchpoint': self._handle_log_touchpoint,
            'wait': self._handle_wait
        }
    
    # Workflow Management
    
    def create_workflow(self, workflow: WorkflowCreate, created_by: str) -> Dict[str, Any]:
        """Create a new workflow"""
        # Insert workflow
        workflow_query = """
            INSERT INTO workflows (organization_id, name, description, trigger_type, trigger_config, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, name, trigger_type, is_active, created_at
        """
        result = self.db.execute_query(
            workflow_query,
            (workflow.organization_id, workflow.name, workflow.description, 
             workflow.trigger_type, json.dumps(workflow.trigger_config), created_by)
        )
        
        if not result:
            return None
        
        workflow_id = result[0]['id']
        
        # Insert actions
        for idx, action in enumerate(workflow.actions):
            action_query = """
                INSERT INTO workflow_actions (workflow_id, action_type, action_config, delay_minutes, order_index)
                VALUES (%s, %s, %s, %s, %s)
            """
            self.db.execute_query(
                action_query,
                (workflow_id, action['action_type'], json.dumps(action['action_config']), 
                 action.get('delay_minutes', 0), idx)
            )
        
        return result[0]
    
    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow with actions"""
        workflow_query = "SELECT * FROM workflows WHERE id = %s"
        workflow_result = self.db.execute_query(workflow_query, (workflow_id,))
        
        if not workflow_result:
            return None
        
        workflow = workflow_result[0]
        
        # Get actions
        actions_query = """
            SELECT * FROM workflow_actions 
            WHERE workflow_id = %s 
            ORDER BY order_index
        """
        actions = self.db.execute_query(actions_query, (workflow_id,))
        workflow['actions'] = actions
        
        return workflow
    
    def list_workflows(self, organization_id: str, is_active: bool = None) -> List[Dict[str, Any]]:
        """List workflows for organization"""
        if is_active is not None:
            query = "SELECT * FROM workflows WHERE organization_id = %s AND is_active = %s ORDER BY created_at DESC"
            params = (organization_id, is_active)
        else:
            query = "SELECT * FROM workflows WHERE organization_id = %s ORDER BY created_at DESC"
            params = (organization_id,)
        
        return self.db.execute_query(query, params)
    
    def activate_workflow(self, workflow_id: str) -> bool:
        """Activate a workflow"""
        query = "UPDATE workflows SET is_active = true WHERE id = %s"
        self.db.execute_query(query, (workflow_id,))
        return True
    
    def deactivate_workflow(self, workflow_id: str) -> bool:
        """Deactivate a workflow"""
        query = "UPDATE workflows SET is_active = false WHERE id = %s"
        self.db.execute_query(query, (workflow_id,))
        return True
    
    # Workflow Execution
    
    def trigger_workflows(self, trigger_type: str, entity_type: str, entity_id: str, trigger_data: Dict[str, Any]) -> List[str]:
        """Find and execute workflows matching the trigger"""
        # Find active workflows with matching trigger
        query = """
            SELECT * FROM workflows 
            WHERE trigger_type = %s AND is_active = true
        """
        workflows = self.db.execute_query(query, (trigger_type,))
        
        execution_ids = []
        
        for workflow in workflows:
            # Check if trigger conditions match
            if self._check_trigger_conditions(workflow, trigger_data):
                execution_id = self.execute_workflow(workflow['id'], entity_type, entity_id, trigger_data)
                if execution_id:
                    execution_ids.append(execution_id)
        
        return execution_ids
    
    def execute_workflow(self, workflow_id: str, entity_type: str, entity_id: str, context: Dict[str, Any]) -> Optional[str]:
        """Execute a workflow"""
        # Create execution record
        execution_query = """
            INSERT INTO workflow_executions (workflow_id, trigger_entity_type, trigger_entity_id, status, started_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        result = self.db.execute_query(
            execution_query,
            (workflow_id, entity_type, entity_id, 'running', datetime.now())
        )
        
        if not result:
            return None
        
        execution_id = result[0]['id']
        execution_log = []
        
        try:
            # Get workflow actions
            actions_query = """
                SELECT * FROM workflow_actions 
                WHERE workflow_id = %s 
                ORDER BY order_index
            """
            actions = self.db.execute_query(actions_query, (workflow_id,))
            
            # Execute each action
            for action in actions:
                action_result = self._execute_action(action, entity_type, entity_id, context)
                execution_log.append({
                    'action_type': action['action_type'],
                    'timestamp': datetime.now().isoformat(),
                    'result': action_result
                })
            
            # Update execution as completed
            update_query = """
                UPDATE workflow_executions 
                SET status = 'completed', completed_at = %s, execution_log = %s
                WHERE id = %s
            """
            self.db.execute_query(
                update_query,
                (datetime.now(), json.dumps(execution_log), execution_id)
            )
            
            return execution_id
            
        except Exception as e:
            # Update execution as failed
            update_query = """
                UPDATE workflow_executions 
                SET status = 'failed', completed_at = %s, error_message = %s, execution_log = %s
                WHERE id = %s
            """
            self.db.execute_query(
                update_query,
                (datetime.now(), str(e), json.dumps(execution_log), execution_id)
            )
            return None
    
    def _check_trigger_conditions(self, workflow: Dict[str, Any], trigger_data: Dict[str, Any]) -> bool:
        """Check if trigger conditions are met"""
        trigger_config = workflow.get('trigger_config', {})
        if isinstance(trigger_config, str):
            trigger_config = json.loads(trigger_config)
        
        # If no conditions, always trigger
        if not trigger_config or not trigger_config.get('conditions'):
            return True
        
        # Check each condition
        conditions = trigger_config.get('conditions', [])
        for condition in conditions:
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')
            
            if field not in trigger_data:
                return False
            
            actual_value = trigger_data[field]
            
            if operator == 'equals' and actual_value != value:
                return False
            elif operator == 'not_equals' and actual_value == value:
                return False
            elif operator == 'greater_than' and actual_value <= value:
                return False
            elif operator == 'less_than' and actual_value >= value:
                return False
            elif operator == 'contains' and value not in str(actual_value):
                return False
        
        return True
    
    def _execute_action(self, action: Dict[str, Any], entity_type: str, entity_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single action"""
        action_type = action['action_type']
        action_config = action.get('action_config', {})
        if isinstance(action_config, str):
            action_config = json.loads(action_config)
        
        # Get action handler
        handler = self.action_handlers.get(action_type)
        if not handler:
            return {'success': False, 'error': f'Unknown action type: {action_type}'}
        
        # Execute handler
        return handler(action_config, entity_type, entity_id, context)
    
    # Action Handlers
    
    def _handle_send_email(self, config: Dict[str, Any], entity_type: str, entity_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Send email action"""
        if not self.communication_service:
            return {'success': False, 'error': 'Communication service not available'}
        
        # Replace variables in template
        subject = self._replace_variables(config.get('subject', ''), context)
        body = self._replace_variables(config.get('body', ''), context)
        to_email = self._replace_variables(config.get('to_email', ''), context)
        
        from communication import EmailSend
        email = EmailSend(
            to_email=to_email,
            subject=subject,
            body_text=body,
            body_html=config.get('body_html')
        )
        
        return self.communication_service.send_email(email)
    
    def _handle_send_sms(self, config: Dict[str, Any], entity_type: str, entity_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Send SMS action"""
        if not self.communication_service:
            return {'success': False, 'error': 'Communication service not available'}
        
        body = self._replace_variables(config.get('body', ''), context)
        to_phone = self._replace_variables(config.get('to_phone', ''), context)
        
        from communication import SMSSend
        sms = SMSSend(
            to_phone=to_phone,
            body=body
        )
        
        return self.communication_service.send_sms(sms)
    
    def _handle_create_task(self, config: Dict[str, Any], entity_type: str, entity_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create task action"""
        title = self._replace_variables(config.get('title', ''), context)
        description = self._replace_variables(config.get('description', ''), context)
        
        query = """
            INSERT INTO tasks (organization_id, assigned_to, deal_id, title, description, 
                             task_type, priority, due_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        due_date = None
        if config.get('due_in_days'):
            due_date = datetime.now() + timedelta(days=config['due_in_days'])
        
        result = self.db.execute_query(
            query,
            (context.get('organization_id'), config.get('assigned_to'), 
             entity_id if entity_type == 'deal' else None,
             title, description, config.get('task_type', 'follow_up'),
             config.get('priority', 'medium'), due_date)
        )
        
        return {'success': True, 'task_id': result[0]['id']} if result else {'success': False}
    
    def _handle_update_deal_field(self, config: Dict[str, Any], entity_type: str, entity_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Update deal field action"""
        if entity_type != 'deal':
            return {'success': False, 'error': 'Can only update deal fields for deal entities'}
        
        field = config.get('field')
        value = self._replace_variables(str(config.get('value', '')), context)
        
        query = f"UPDATE deals SET {field} = %s, updated_at = %s WHERE id = %s"
        self.db.execute_query(query, (value, datetime.now(), entity_id))
        
        return {'success': True, 'field': field, 'value': value}
    
    def _handle_create_conversation(self, config: Dict[str, Any], entity_type: str, entity_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create conversation action"""
        if not self.communication_service:
            return {'success': False, 'error': 'Communication service not available'}
        
        subject = self._replace_variables(config.get('subject', ''), context)
        
        from communication import ConversationCreate
        conversation = ConversationCreate(
            deal_id=entity_id if entity_type == 'deal' else None,
            borrower_id=context.get('borrower_id'),
            subject=subject,
            assigned_to=config.get('assigned_to')
        )
        
        result = self.communication_service.create_conversation(conversation)
        return {'success': True, 'conversation_id': result['id']} if result else {'success': False}
    
    def _handle_log_touchpoint(self, config: Dict[str, Any], entity_type: str, entity_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Log touchpoint action"""
        description = self._replace_variables(config.get('description', ''), context)
        
        query = """
            INSERT INTO contact_touchpoints (borrower_id, user_id, touchpoint_type, description, occurred_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        
        result = self.db.execute_query(
            query,
            (context.get('borrower_id'), config.get('user_id'), 
             config.get('touchpoint_type', 'automated'), description, datetime.now())
        )
        
        return {'success': True, 'touchpoint_id': result[0]['id']} if result else {'success': False}
    
    def _handle_wait(self, config: Dict[str, Any], entity_type: str, entity_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Wait action (for delays between actions)"""
        # In a real implementation, this would schedule the next action
        # For now, just return success
        return {'success': True, 'waited_minutes': config.get('minutes', 0)}
    
    def _replace_variables(self, text: str, context: Dict[str, Any]) -> str:
        """Replace variables in text with context values"""
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            text = text.replace(placeholder, str(value))
        return text
    
    # Execution History
    
    def get_workflow_executions(self, workflow_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution history for a workflow"""
        query = """
            SELECT * FROM workflow_executions 
            WHERE workflow_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s
        """
        return self.db.execute_query(query, (workflow_id, limit))


# Pre-built Workflow Templates

class WorkflowTemplates:
    """Common workflow templates for commercial lending"""
    
    @staticmethod
    def new_deal_onboarding(organization_id: str, assigned_to: str) -> WorkflowCreate:
        """Workflow for new deal onboarding"""
        return WorkflowCreate(
            organization_id=organization_id,
            name="New Deal Onboarding",
            description="Automated onboarding sequence for new deals",
            trigger_type="deal_created",
            trigger_config={},
            actions=[
                {
                    "action_type": "send_email",
                    "action_config": {
                        "to_email": "{{borrower_email}}",
                        "subject": "Welcome to UnderwritePro - Let's Get Started!",
                        "body": "Dear {{borrower_name}},\n\nThank you for choosing us for your commercial loan. We're excited to work with you!\n\nNext steps:\n1. Review the document checklist\n2. Upload required documents\n3. Schedule a consultation call\n\nBest regards,\nThe UnderwritePro Team"
                    },
                    "delay_minutes": 0
                },
                {
                    "action_type": "create_task",
                    "action_config": {
                        "assigned_to": assigned_to,
                        "title": "Review new deal: {{deal_type}}",
                        "description": "New deal created for {{borrower_name}}. Loan amount: ${{loan_amount}}",
                        "task_type": "review",
                        "priority": "high",
                        "due_in_days": 1
                    },
                    "delay_minutes": 0
                },
                {
                    "action_type": "log_touchpoint",
                    "action_config": {
                        "touchpoint_type": "automated_email",
                        "description": "Sent welcome email"
                    },
                    "delay_minutes": 0
                }
            ]
        )
    
    @staticmethod
    def document_reminder(organization_id: str) -> WorkflowCreate:
        """Workflow to remind about missing documents"""
        return WorkflowCreate(
            organization_id=organization_id,
            name="Document Upload Reminder",
            description="Remind borrowers to upload missing documents",
            trigger_type="document_missing",
            trigger_config={
                "conditions": [
                    {"field": "days_since_request", "operator": "greater_than", "value": 3}
                ]
            },
            actions=[
                {
                    "action_type": "send_email",
                    "action_config": {
                        "to_email": "{{borrower_email}}",
                        "subject": "Reminder: Documents Needed for Your Loan Application",
                        "body": "Hi {{borrower_name}},\n\nWe're still waiting for some documents to complete your loan application.\n\nMissing documents:\n{{missing_documents}}\n\nPlease upload these at your earliest convenience to keep your application moving forward.\n\nBest regards"
                    },
                    "delay_minutes": 0
                },
                {
                    "action_type": "send_sms",
                    "action_config": {
                        "to_phone": "{{borrower_phone}}",
                        "body": "Hi {{borrower_name}}, friendly reminder: we need {{document_count}} documents for your loan. Upload at: {{portal_url}}"
                    },
                    "delay_minutes": 60
                }
            ]
        )
    
    @staticmethod
    def deal_approved(organization_id: str) -> WorkflowCreate:
        """Workflow for deal approval"""
        return WorkflowCreate(
            organization_id=organization_id,
            name="Deal Approved Notification",
            description="Notify borrower when deal is approved",
            trigger_type="stage_changed",
            trigger_config={
                "conditions": [
                    {"field": "new_stage", "operator": "equals", "value": "approved"}
                ]
            },
            actions=[
                {
                    "action_type": "send_email",
                    "action_config": {
                        "to_email": "{{borrower_email}}",
                        "subject": "Congratulations! Your Loan is Approved",
                        "body": "Dear {{borrower_name}},\n\nGreat news! Your loan application has been approved!\n\nLoan Amount: ${{loan_amount}}\nInterest Rate: {{interest_rate}}%\n\nNext steps:\n1. Review the term sheet\n2. Sign the commitment letter\n3. Schedule closing\n\nCongratulations!\nThe UnderwritePro Team"
                    },
                    "delay_minutes": 0
                },
                {
                    "action_type": "create_task",
                    "action_config": {
                        "assigned_to": "{{assigned_to}}",
                        "title": "Prepare closing documents for {{borrower_name}}",
                        "description": "Deal approved. Prepare closing documents and schedule closing date.",
                        "task_type": "closing_prep",
                        "priority": "high",
                        "due_in_days": 3
                    },
                    "delay_minutes": 0
                },
                {
                    "action_type": "log_touchpoint",
                    "action_config": {
                        "touchpoint_type": "approval_notification",
                        "description": "Sent approval notification"
                    },
                    "delay_minutes": 0
                }
            ]
        )


# Helper function

def get_workflow_engine(db, communication_service=None):
    """Factory function to create workflow engine"""
    return WorkflowEngine(db, communication_service)
