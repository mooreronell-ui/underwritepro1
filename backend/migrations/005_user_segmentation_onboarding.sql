-- Migration 005: User Segmentation and Multi-Path Onboarding
-- This migration adds user segmentation, onboarding tracking, and personalization features

-- Add user segmentation fields to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS user_type VARCHAR(50);
-- Options: 'commercial_lender', 'residential_lo_active', 'residential_lo_former', 'career_changer'

ALTER TABLE users ADD COLUMN IF NOT EXISTS user_subtype VARCHAR(50);
-- For career_changers: 'realtor', 'financial_advisor', 'consultant', 'entrepreneur', 'other'

ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT FALSE;

ALTER TABLE users ADD COLUMN IF NOT EXISTS learning_path VARCHAR(50);
-- Options: 'advanced', 'transition', 'beginner'

ALTER TABLE users ADD COLUMN IF NOT EXISTS experience_level VARCHAR(50);
-- Options: 'expert', 'intermediate', 'beginner'

ALTER TABLE users ADD COLUMN IF NOT EXISTS goals TEXT;

ALTER TABLE users ADD COLUMN IF NOT EXISTS years_of_experience INT;

ALTER TABLE users ADD COLUMN IF NOT EXISTS current_volume_annual DECIMAL(15,2);

ALTER TABLE users ADD COLUMN IF NOT EXISTS target_income_annual DECIMAL(15,2);

-- Create onboarding progress tracking table
CREATE TABLE IF NOT EXISTS onboarding_progress (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    step_number INT NOT NULL,
    step_name VARCHAR(100) NOT NULL,
    step_data JSONB,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_onboarding_user ON onboarding_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_onboarding_completed ON onboarding_progress(user_id, completed);

-- Create onboarding templates table
CREATE TABLE IF NOT EXISTS onboarding_templates (
    id VARCHAR(36) PRIMARY KEY,
    template_name VARCHAR(100) NOT NULL,
    user_type VARCHAR(50) NOT NULL,
    steps JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert default onboarding templates
INSERT INTO onboarding_templates (id, template_name, user_type, steps) VALUES
('template-commercial', 'Commercial Lender Onboarding', 'commercial_lender', 
'[
    {"step": 1, "name": "welcome", "title": "Welcome to UnderwritePro", "required": true},
    {"step": 2, "name": "business_info", "title": "Tell us about your business", "required": true},
    {"step": 3, "name": "import_deals", "title": "Import existing deals (optional)", "required": false},
    {"step": 4, "name": "connect_tools", "title": "Connect your tools (optional)", "required": false},
    {"step": 5, "name": "platform_tour", "title": "Platform tour", "required": true},
    {"step": 6, "name": "first_deal", "title": "Create your first deal", "required": true}
]'::jsonb),

('template-residential', 'Residential LO Onboarding', 'residential_lo_active', 
'[
    {"step": 1, "name": "welcome", "title": "Welcome to Commercial Lending", "required": true},
    {"step": 2, "name": "lo_background", "title": "Your LO background", "required": true},
    {"step": 3, "name": "goals", "title": "Your commercial lending goals", "required": true},
    {"step": 4, "name": "network", "title": "Your existing network", "required": false},
    {"step": 5, "name": "learning_path", "title": "Your learning path", "required": true},
    {"step": 6, "name": "first_practice", "title": "Your first practice deal", "required": true}
]'::jsonb),

('template-career-changer', 'Career Changer Onboarding', 'career_changer', 
'[
    {"step": 1, "name": "welcome", "title": "Welcome to Your New Career", "required": true},
    {"step": 2, "name": "background", "title": "Your background", "required": true},
    {"step": 3, "name": "why_commercial", "title": "Why commercial lending?", "required": true},
    {"step": 4, "name": "assets", "title": "Your network and skills", "required": false},
    {"step": 5, "name": "learning_path", "title": "Your learning path", "required": true},
    {"step": 6, "name": "first_lesson", "title": "Complete your first lesson", "required": true}
]'::jsonb);

-- Add comments for documentation
COMMENT ON COLUMN users.user_type IS 'Type of user: commercial_lender, residential_lo_active, residential_lo_former, career_changer';
COMMENT ON COLUMN users.user_subtype IS 'Subtype for career changers: realtor, financial_advisor, consultant, entrepreneur, other';
COMMENT ON COLUMN users.learning_path IS 'Assigned learning path: advanced, transition, beginner';
COMMENT ON TABLE onboarding_progress IS 'Tracks user progress through onboarding steps';
COMMENT ON TABLE onboarding_templates IS 'Defines onboarding flows for different user types';
