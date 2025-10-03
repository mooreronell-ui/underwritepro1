-- UnderwritePro Enhanced Platform - Database Schema
-- Version: 3.0.0 (Corrected for VARCHAR IDs)
-- Date: October 2, 2025

-- Communication Hub Tables

CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    deal_id VARCHAR REFERENCES deals(id) ON DELETE CASCADE,
    borrower_id VARCHAR REFERENCES borrowers(id) ON DELETE CASCADE,
    subject VARCHAR(500),
    status VARCHAR(50) DEFAULT 'active',
    last_message_at TIMESTAMP,
    assigned_to VARCHAR REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    conversation_id VARCHAR REFERENCES conversations(id) ON DELETE CASCADE,
    sender_type VARCHAR(50),
    sender_id VARCHAR,
    recipient_type VARCHAR(50),
    recipient_id VARCHAR,
    channel VARCHAR(50),
    subject VARCHAR(500),
    body TEXT,
    html_body TEXT,
    status VARCHAR(50) DEFAULT 'draft',
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    read_at TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS message_attachments (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    message_id VARCHAR REFERENCES messages(id) ON DELETE CASCADE,
    filename VARCHAR(500),
    file_path VARCHAR(1000),
    file_size INTEGER,
    mime_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Workflow Automation Tables

CREATE TABLE IF NOT EXISTS workflows (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    organization_id VARCHAR REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    trigger_type VARCHAR(100) NOT NULL,
    trigger_config JSONB,
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workflow_actions (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    workflow_id VARCHAR REFERENCES workflows(id) ON DELETE CASCADE,
    action_type VARCHAR(100) NOT NULL,
    action_config JSONB NOT NULL,
    delay_minutes INTEGER DEFAULT 0,
    order_index INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workflow_executions (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    workflow_id VARCHAR REFERENCES workflows(id) ON DELETE CASCADE,
    trigger_entity_type VARCHAR(50),
    trigger_entity_id VARCHAR,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    execution_log JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Calendar & Scheduling Tables

CREATE TABLE IF NOT EXISTS calendars (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    organization_id VARCHAR REFERENCES organizations(id) ON DELETE CASCADE,
    user_id VARCHAR REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    calendar_type VARCHAR(50) DEFAULT 'individual',
    is_active BOOLEAN DEFAULT true,
    settings JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS appointments (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    calendar_id VARCHAR REFERENCES calendars(id) ON DELETE CASCADE,
    deal_id VARCHAR REFERENCES deals(id) ON DELETE SET NULL,
    borrower_id VARCHAR REFERENCES borrowers(id) ON DELETE SET NULL,
    assigned_to VARCHAR REFERENCES users(id) ON DELETE SET NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    appointment_type VARCHAR(100),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    location VARCHAR(500),
    meeting_url VARCHAR(1000),
    status VARCHAR(50) DEFAULT 'scheduled',
    reminder_sent BOOLEAN DEFAULT false,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS appointment_reminders (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    appointment_id VARCHAR REFERENCES appointments(id) ON DELETE CASCADE,
    reminder_type VARCHAR(50) NOT NULL,
    send_minutes_before INTEGER NOT NULL,
    sent_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- AI Bot Tables

CREATE TABLE IF NOT EXISTS ai_conversations (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR REFERENCES users(id) ON DELETE CASCADE,
    bot_type VARCHAR(100) NOT NULL,
    context_entity_type VARCHAR(50),
    context_entity_id VARCHAR,
    conversation_history JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_recommendations (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR REFERENCES users(id) ON DELETE CASCADE,
    bot_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id VARCHAR,
    recommendation_type VARCHAR(100),
    recommendation_data JSONB,
    confidence_score DECIMAL(3,2),
    status VARCHAR(50) DEFAULT 'pending',
    user_feedback TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

-- Relationship Management Tables

CREATE TABLE IF NOT EXISTS contact_touchpoints (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    borrower_id VARCHAR REFERENCES borrowers(id) ON DELETE CASCADE,
    user_id VARCHAR REFERENCES users(id) ON DELETE SET NULL,
    touchpoint_type VARCHAR(100) NOT NULL,
    description TEXT,
    occurred_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS relationship_scores (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    borrower_id VARCHAR REFERENCES borrowers(id) ON DELETE CASCADE,
    engagement_score INTEGER CHECK (engagement_score >= 0 AND engagement_score <= 100),
    satisfaction_score INTEGER CHECK (satisfaction_score >= 0 AND satisfaction_score <= 100),
    risk_score INTEGER CHECK (risk_score >= 0 AND risk_score <= 100),
    last_contact_date TIMESTAMP,
    next_recommended_contact TIMESTAMP,
    score_factors JSONB,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(borrower_id)
);

-- Enhanced Pipeline Tables

CREATE TABLE IF NOT EXISTS pipeline_stages (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    organization_id VARCHAR REFERENCES organizations(id) ON DELETE CASCADE,
    pipeline_name VARCHAR(200) NOT NULL,
    stage_name VARCHAR(200) NOT NULL,
    stage_order INTEGER NOT NULL,
    automation_rules JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(organization_id, pipeline_name, stage_order)
);

CREATE TABLE IF NOT EXISTS deal_stage_history (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    deal_id VARCHAR REFERENCES deals(id) ON DELETE CASCADE,
    from_stage VARCHAR(200),
    to_stage VARCHAR(200) NOT NULL,
    changed_by VARCHAR REFERENCES users(id) ON DELETE SET NULL,
    changed_at TIMESTAMP DEFAULT NOW(),
    duration_in_stage INTEGER,
    notes TEXT
);

-- Tasks & Activities

CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    organization_id VARCHAR REFERENCES organizations(id) ON DELETE CASCADE,
    assigned_to VARCHAR REFERENCES users(id) ON DELETE SET NULL,
    created_by VARCHAR REFERENCES users(id) ON DELETE SET NULL,
    deal_id VARCHAR REFERENCES deals(id) ON DELETE CASCADE,
    borrower_id VARCHAR REFERENCES borrowers(id) ON DELETE SET NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    task_type VARCHAR(100),
    priority VARCHAR(50) DEFAULT 'medium',
    status VARCHAR(50) DEFAULT 'pending',
    due_date TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Email Templates

CREATE TABLE IF NOT EXISTS email_templates (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    organization_id VARCHAR REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    body_html TEXT NOT NULL,
    body_text TEXT,
    template_type VARCHAR(100),
    variables JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- SMS Templates

CREATE TABLE IF NOT EXISTS sms_templates (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    organization_id VARCHAR REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    template_type VARCHAR(100),
    variables JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create Indexes

CREATE INDEX IF NOT EXISTS idx_conversations_deal ON conversations(deal_id);
CREATE INDEX IF NOT EXISTS idx_conversations_borrower ON conversations(borrower_id);
CREATE INDEX IF NOT EXISTS idx_conversations_assigned ON conversations(assigned_to);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status);
CREATE INDEX IF NOT EXISTS idx_messages_sent_at ON messages(sent_at);

CREATE INDEX IF NOT EXISTS idx_workflows_org ON workflows(organization_id);
CREATE INDEX IF NOT EXISTS idx_workflows_active ON workflows(is_active);

CREATE INDEX IF NOT EXISTS idx_workflow_executions_workflow ON workflow_executions(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_status ON workflow_executions(status);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_entity ON workflow_executions(trigger_entity_type, trigger_entity_id);

CREATE INDEX IF NOT EXISTS idx_appointments_calendar ON appointments(calendar_id);
CREATE INDEX IF NOT EXISTS idx_appointments_deal ON appointments(deal_id);
CREATE INDEX IF NOT EXISTS idx_appointments_assigned ON appointments(assigned_to);
CREATE INDEX IF NOT EXISTS idx_appointments_time ON appointments(start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);

CREATE INDEX IF NOT EXISTS idx_ai_conversations_user ON ai_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_conversations_bot ON ai_conversations(bot_type);

CREATE INDEX IF NOT EXISTS idx_ai_recommendations_user ON ai_recommendations(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_recommendations_entity ON ai_recommendations(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_ai_recommendations_status ON ai_recommendations(status);

CREATE INDEX IF NOT EXISTS idx_touchpoints_borrower ON contact_touchpoints(borrower_id);
CREATE INDEX IF NOT EXISTS idx_touchpoints_occurred ON contact_touchpoints(occurred_at);

CREATE INDEX IF NOT EXISTS idx_relationship_scores_borrower ON relationship_scores(borrower_id);

CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_tasks_deal ON tasks(deal_id);
CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_org ON tasks(organization_id);

CREATE INDEX IF NOT EXISTS idx_email_templates_org ON email_templates(organization_id);
CREATE INDEX IF NOT EXISTS idx_email_templates_type ON email_templates(template_type);

CREATE INDEX IF NOT EXISTS idx_sms_templates_org ON sms_templates(organization_id);
CREATE INDEX IF NOT EXISTS idx_sms_templates_type ON sms_templates(template_type);
