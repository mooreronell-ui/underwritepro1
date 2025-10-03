"""
Enhanced Platform API Routes
Exposes communication, AI bots, and workflow features
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import sys

# Import services
from auth import get_current_user
from database_unified import get_db
from communication import (
    CommunicationService, get_communication_service,
    MessageCreate, ConversationCreate, EmailSend, SMSSend
)
from ai_bots import (
    AIBotService, get_ai_bot_service,
    AIBotRequest, ChatMessage
)
from workflows import (
    WorkflowEngine, get_workflow_engine,
    WorkflowCreate, WorkflowTemplates
)

# Create routers
communication_router = APIRouter(prefix="/api/communication", tags=["communication"])
ai_router = APIRouter(prefix="/api/ai", tags=["ai"])
workflow_router = APIRouter(prefix="/api/workflows", tags=["workflows"])


# ==================== Communication Routes ====================

@communication_router.get("/conversations")
async def list_conversations(
    deal_id: Optional[str] = None,
    borrower_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """List conversations with optional filters"""
    comm_service = get_communication_service(db)
    
    filters = {}
    if deal_id:
        filters['deal_id'] = deal_id
    if borrower_id:
        filters['borrower_id'] = borrower_id
    if status:
        filters['status'] = status
    
    conversations = comm_service.list_conversations(filters, limit, offset)
    return {"success": True, "conversations": conversations, "count": len(conversations)}


@communication_router.post("/conversations")
async def create_conversation(
    conversation: ConversationCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create a new conversation"""
    comm_service = get_communication_service(db)
    result = comm_service.create_conversation(conversation)
    
    if result:
        return {"success": True, "conversation": result}
    raise HTTPException(status_code=400, detail="Failed to create conversation")


@communication_router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get conversation details"""
    comm_service = get_communication_service(db)
    conversation = comm_service.get_conversation(conversation_id)
    
    if conversation:
        return {"success": True, "conversation": conversation}
    raise HTTPException(status_code=404, detail="Conversation not found")


@communication_router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get messages in a conversation"""
    comm_service = get_communication_service(db)
    messages = comm_service.get_conversation_messages(conversation_id, limit, offset)
    
    return {"success": True, "messages": messages, "count": len(messages)}


@communication_router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    message: MessageCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Send a message in a conversation"""
    comm_service = get_communication_service(db)
    message.conversation_id = conversation_id
    result = comm_service.create_message(message)
    
    if result:
        # If email or SMS, actually send it
        if message.channel == 'email':
            email = EmailSend(
                to_email=message.metadata.get('to_email', ''),
                subject=message.subject,
                body_text=message.body,
                body_html=message.html_body
            )
            send_result = comm_service.send_email(email)
            if send_result.get('success'):
                comm_service.mark_message_sent(result['id'])
        
        return {"success": True, "message": result}
    raise HTTPException(status_code=400, detail="Failed to send message")


@communication_router.post("/email/send")
async def send_email(
    email: EmailSend,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Send a standalone email"""
    comm_service = get_communication_service(db)
    result = comm_service.send_email(email)
    
    return result


@communication_router.post("/sms/send")
async def send_sms(
    sms: SMSSend,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Send a standalone SMS"""
    comm_service = get_communication_service(db)
    result = comm_service.send_sms(sms)
    
    return result


@communication_router.get("/inbox")
async def get_unified_inbox(
    status: Optional[str] = None,
    channel: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get unified inbox for current user"""
    comm_service = get_communication_service(db)
    
    filters = {}
    if status:
        filters['status'] = status
    if channel:
        filters['channel'] = channel
    if unread_only:
        filters['unread_only'] = True
    
    inbox = comm_service.get_unified_inbox(current_user['id'], filters, limit, offset)
    return {"success": True, "inbox": inbox, "count": len(inbox)}


# ==================== AI Bot Routes ====================

@ai_router.post("/chat")
async def chat_with_bot(
    request: AIBotRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Chat with an AI bot"""
    ai_service = get_ai_bot_service(db)
    response = ai_service.chat_with_bot(request, current_user['id'])
    
    return response


@ai_router.post("/onboarding/checklist")
async def generate_onboarding_checklist(
    deal_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Generate document checklist for deal"""
    ai_service = get_ai_bot_service(db)
    bot = ai_service.get_bot('cassie_onboarding')
    
    # Get deal data
    deal_query = "SELECT * FROM deals WHERE id = %s"
    deal_data = db.execute_query(deal_query, (deal_id,))
    
    if not deal_data:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    result = bot.generate_document_checklist(deal_data[0])
    return result


@ai_router.post("/document/summarize")
async def summarize_document(
    document_text: str,
    document_type: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Summarize a financial document"""
    ai_service = get_ai_bot_service(db)
    bot = ai_service.get_bot('sage_summarizer')
    
    result = bot.summarize_financial_statement(document_text, document_type)
    return result


@ai_router.post("/risk/analyze")
async def analyze_deal_risk(
    deal_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Perform comprehensive risk analysis"""
    ai_service = get_ai_bot_service(db)
    bot = ai_service.get_bot('remy_risk')
    
    result = bot.analyze_deal_risk(deal_id)
    return result


@ai_router.post("/relationship/score")
async def calculate_relationship_score(
    borrower_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Calculate relationship health score"""
    ai_service = get_ai_bot_service(db)
    bot = ai_service.get_bot('axel_relationship')
    
    result = bot.calculate_relationship_score(borrower_id)
    return result


@ai_router.post("/negotiation/suggest")
async def suggest_negotiation_strategy(
    deal_id: str,
    borrower_request: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get negotiation strategy suggestion"""
    ai_service = get_ai_bot_service(db)
    bot = ai_service.get_bot('aurora_negotiation')
    
    # Get deal data
    deal_query = "SELECT * FROM deals WHERE id = %s"
    deal_data = db.execute_query(deal_query, (deal_id,))
    
    if not deal_data:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    result = bot.suggest_negotiation_strategy(deal_data[0], borrower_request)
    return result


@ai_router.post("/offer/generate")
async def generate_term_sheet(
    deal_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Generate professional term sheet"""
    ai_service = get_ai_bot_service(db)
    bot = ai_service.get_bot('titan_offer')
    
    # Get deal data with borrower info
    deal_query = """
        SELECT d.*, b.name as borrower_name
        FROM deals d
        LEFT JOIN borrowers b ON d.borrower_id = b.id
        WHERE d.id = %s
    """
    deal_data = db.execute_query(deal_query, (deal_id,))
    
    if not deal_data:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    result = bot.generate_term_sheet(deal_data[0])
    return result


@ai_router.get("/recommendations")
async def get_recommendations(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    status: str = 'pending',
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get AI recommendations for current user"""
    ai_service = get_ai_bot_service(db)
    recommendations = ai_service.get_recommendations(
        current_user['id'], entity_type, entity_id, status
    )
    
    return {"success": True, "recommendations": recommendations, "count": len(recommendations)}


@ai_router.put("/recommendations/{recommendation_id}")
async def update_recommendation(
    recommendation_id: str,
    status: str,
    feedback: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Accept or reject a recommendation"""
    query = """
        UPDATE ai_recommendations 
        SET status = %s, user_feedback = %s, resolved_at = %s
        WHERE id = %s AND user_id = %s
    """
    from datetime import datetime
    db.execute_query(query, (status, feedback, datetime.now(), recommendation_id, current_user['id']))
    
    return {"success": True, "status": status}


# ==================== Workflow Routes ====================

@workflow_router.get("")
async def list_workflows(
    is_active: Optional[bool] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """List workflows for organization"""
    workflow_engine = get_workflow_engine(db)
    workflows = workflow_engine.list_workflows(current_user['organization_id'], is_active)
    
    return {"success": True, "workflows": workflows, "count": len(workflows)}


@workflow_router.post("")
async def create_workflow(
    workflow: WorkflowCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create a new workflow"""
    workflow_engine = get_workflow_engine(db)
    result = workflow_engine.create_workflow(workflow, current_user['id'])
    
    if result:
        return {"success": True, "workflow": result}
    raise HTTPException(status_code=400, detail="Failed to create workflow")


@workflow_router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get workflow details"""
    workflow_engine = get_workflow_engine(db)
    workflow = workflow_engine.get_workflow(workflow_id)
    
    if workflow:
        return {"success": True, "workflow": workflow}
    raise HTTPException(status_code=404, detail="Workflow not found")


@workflow_router.post("/{workflow_id}/activate")
async def activate_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Activate a workflow"""
    workflow_engine = get_workflow_engine(db)
    workflow_engine.activate_workflow(workflow_id)
    
    return {"success": True, "message": "Workflow activated"}


@workflow_router.post("/{workflow_id}/deactivate")
async def deactivate_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Deactivate a workflow"""
    workflow_engine = get_workflow_engine(db)
    workflow_engine.deactivate_workflow(workflow_id)
    
    return {"success": True, "message": "Workflow deactivated"}


@workflow_router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    entity_type: str,
    entity_id: str,
    context: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Manually execute a workflow"""
    comm_service = get_communication_service(db)
    workflow_engine = get_workflow_engine(db, comm_service)
    
    execution_id = workflow_engine.execute_workflow(workflow_id, entity_type, entity_id, context)
    
    if execution_id:
        return {"success": True, "execution_id": execution_id}
    raise HTTPException(status_code=400, detail="Failed to execute workflow")


@workflow_router.get("/{workflow_id}/executions")
async def get_workflow_executions(
    workflow_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get workflow execution history"""
    workflow_engine = get_workflow_engine(db)
    executions = workflow_engine.get_workflow_executions(workflow_id, limit)
    
    return {"success": True, "executions": executions, "count": len(executions)}


@workflow_router.get("/templates/list")
async def list_workflow_templates(
    current_user: dict = Depends(get_current_user)
):
    """List available workflow templates"""
    templates = [
        {
            "id": "new_deal_onboarding",
            "name": "New Deal Onboarding",
            "description": "Automated onboarding sequence for new deals",
            "trigger_type": "deal_created"
        },
        {
            "id": "document_reminder",
            "name": "Document Upload Reminder",
            "description": "Remind borrowers to upload missing documents",
            "trigger_type": "document_missing"
        },
        {
            "id": "deal_approved",
            "name": "Deal Approved Notification",
            "description": "Notify borrower when deal is approved",
            "trigger_type": "stage_changed"
        }
    ]
    
    return {"success": True, "templates": templates}


@workflow_router.post("/templates/{template_id}/create")
async def create_from_template(
    template_id: str,
    assigned_to: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create workflow from template"""
    workflow_engine = get_workflow_engine(db)
    
    # Get template
    if template_id == "new_deal_onboarding":
        workflow = WorkflowTemplates.new_deal_onboarding(
            current_user['organization_id'],
            assigned_to or current_user['id']
        )
    elif template_id == "document_reminder":
        workflow = WorkflowTemplates.document_reminder(current_user['organization_id'])
    elif template_id == "deal_approved":
        workflow = WorkflowTemplates.deal_approved(current_user['organization_id'])
    else:
        raise HTTPException(status_code=404, detail="Template not found")
    
    result = workflow_engine.create_workflow(workflow, current_user['id'])
    
    if result:
        return {"success": True, "workflow": result}
    raise HTTPException(status_code=400, detail="Failed to create workflow from template")


# Export routers
__all__ = ['communication_router', 'ai_router', 'workflow_router']
