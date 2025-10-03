-- Migration 007: Practice Mode and Gamification
-- This migration adds practice/simulation mode and gamification features

-- Add practice mode fields to deals table
ALTER TABLE deals ADD COLUMN IF NOT EXISTS is_practice BOOLEAN DEFAULT FALSE;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS practice_scenario_id VARCHAR(36);
ALTER TABLE deals ADD COLUMN IF NOT EXISTS practice_completed BOOLEAN DEFAULT FALSE;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS practice_score INT;

-- Practice Scenarios Table
CREATE TABLE IF NOT EXISTS practice_scenarios (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    difficulty VARCHAR(50) NOT NULL,
    -- 'beginner', 'intermediate', 'advanced'
    scenario_type VARCHAR(50) NOT NULL,
    -- 'retail_acquisition', 'office_refinance', 'multifamily_purchase', etc.
    learning_objectives TEXT[],
    expected_outcome TEXT,
    hints JSONB,
    scenario_data JSONB NOT NULL,
    -- Pre-filled borrower, property, financial data
    success_criteria JSONB,
    -- What constitutes success
    created_at TIMESTAMP DEFAULT NOW()
);

-- Practice Feedback Table
CREATE TABLE IF NOT EXISTS practice_feedback (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    deal_id VARCHAR(36) REFERENCES deals(id) ON DELETE CASCADE,
    scenario_id VARCHAR(36) REFERENCES practice_scenarios(id),
    ai_feedback TEXT,
    score INT CHECK (score >= 0 AND score <= 100),
    strengths TEXT[],
    areas_for_improvement TEXT[],
    recommendations TEXT[],
    completed_at TIMESTAMP DEFAULT NOW()
);

-- Gamification: User Points Table
CREATE TABLE IF NOT EXISTS user_points (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    total_points INT DEFAULT 0,
    level INT DEFAULT 1,
    level_name VARCHAR(50) DEFAULT 'Beginner',
    -- 'Beginner', 'Intermediate', 'Advanced', 'Expert', 'Master'
    points_to_next_level INT DEFAULT 100,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Gamification: Points Rules Table
CREATE TABLE IF NOT EXISTS gamification_rules (
    id VARCHAR(36) PRIMARY KEY,
    action VARCHAR(100) NOT NULL UNIQUE,
    -- 'complete_lesson', 'close_deal', 'help_community', 'practice_complete', etc.
    points INT NOT NULL,
    badge_id VARCHAR(36),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Gamification: User Badges Table
CREATE TABLE IF NOT EXISTS user_badges (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    badge_id VARCHAR(36) NOT NULL,
    badge_name VARCHAR(100) NOT NULL,
    badge_description TEXT,
    badge_icon VARCHAR(50),
    -- Emoji or icon name
    badge_category VARCHAR(50),
    -- 'learning', 'deals', 'community', 'milestone'
    earned_at TIMESTAMP DEFAULT NOW()
);

-- Gamification: Leaderboards Table
CREATE TABLE IF NOT EXISTS leaderboards (
    id VARCHAR(36) PRIMARY KEY,
    leaderboard_type VARCHAR(50) NOT NULL,
    -- 'monthly_deals', 'learning_progress', 'community_helper', 'total_points'
    period VARCHAR(50) NOT NULL,
    -- 'weekly', 'monthly', 'quarterly', 'all_time'
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    score INT NOT NULL,
    rank INT,
    period_start DATE,
    period_end DATE,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(leaderboard_type, period, user_id, period_start)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_practice_scenarios_difficulty ON practice_scenarios(difficulty);
CREATE INDEX IF NOT EXISTS idx_practice_scenarios_type ON practice_scenarios(scenario_type);
CREATE INDEX IF NOT EXISTS idx_practice_feedback_user ON practice_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_practice_feedback_scenario ON practice_feedback(scenario_id);
CREATE INDEX IF NOT EXISTS idx_deals_practice ON deals(is_practice);
CREATE INDEX IF NOT EXISTS idx_user_points_level ON user_points(level);
CREATE INDEX IF NOT EXISTS idx_user_badges_user ON user_badges(user_id);
CREATE INDEX IF NOT EXISTS idx_user_badges_category ON user_badges(badge_category);
CREATE INDEX IF NOT EXISTS idx_leaderboards_type_period ON leaderboards(leaderboard_type, period);
CREATE INDEX IF NOT EXISTS idx_leaderboards_rank ON leaderboards(rank);

-- Insert default gamification rules
INSERT INTO gamification_rules (id, action, points, description) VALUES
('rule-lesson', 'complete_lesson', 10, 'Complete a learning lesson'),
('rule-module', 'complete_module', 50, 'Complete a learning module'),
('rule-path', 'complete_path', 200, 'Complete a learning path'),
('rule-quiz', 'pass_quiz', 25, 'Pass a quiz'),
('rule-practice', 'complete_practice', 30, 'Complete a practice deal'),
('rule-deal', 'close_deal', 100, 'Close a real deal'),
('rule-community', 'help_community', 5, 'Help someone in the community'),
('rule-post', 'create_post', 2, 'Create a community post'),
('rule-login', 'daily_login', 1, 'Daily login streak'),
('rule-referral', 'successful_referral', 150, 'Successful referral');

-- Insert sample practice scenarios
INSERT INTO practice_scenarios (id, name, slug, description, difficulty, scenario_type, learning_objectives, expected_outcome, scenario_data, success_criteria) VALUES
('scenario-1', 'Retail Strip Center Acquisition', 'retail-strip-center', 
'A local investor wants to purchase a 10-unit retail strip center in a growing suburban area.', 
'beginner', 'retail_acquisition',
ARRAY['Understand retail property valuation', 'Calculate debt service coverage ratio', 'Assess tenant quality'],
'Successfully structure a loan with appropriate terms and identify key risks',
'{"property_type": "retail", "units": 10, "purchase_price": 2500000, "down_payment": 625000, "loan_amount": 1875000, "noi": 185000, "occupancy": 0.90}'::jsonb,
'{"min_dscr": 1.25, "max_ltv": 0.75, "risk_assessment": "moderate"}'::jsonb),

('scenario-2', 'Office Building Refinance', 'office-refinance',
'An established business owner wants to refinance their office building to access equity for expansion.',
'intermediate', 'office_refinance',
ARRAY['Evaluate refinance scenarios', 'Understand cash-out refinancing', 'Assess business performance'],
'Determine optimal loan structure and cash-out amount',
'{"property_type": "office", "current_value": 3200000, "current_loan": 1500000, "noi": 240000, "occupancy": 0.95, "cashout_needed": 500000}'::jsonb,
'{"min_dscr": 1.30, "max_ltv": 0.70, "cash_out_limit": 0.80}'::jsonb),

('scenario-3', 'Multifamily Purchase - Value Add', 'multifamily-value-add',
'Experienced investor wants to purchase a 24-unit apartment complex with renovation plans.',
'advanced', 'multifamily_purchase',
ARRAY['Analyze value-add opportunities', 'Project stabilized NOI', 'Structure construction/renovation financing'],
'Structure a loan that accounts for current condition and future value',
'{"property_type": "multifamily", "units": 24, "purchase_price": 4800000, "current_noi": 280000, "projected_noi": 420000, "renovation_cost": 600000, "occupancy": 0.75}'::jsonb,
'{"min_dscr_current": 1.15, "min_dscr_stabilized": 1.35, "max_ltc": 0.80}'::jsonb);

-- Add comments
COMMENT ON TABLE practice_scenarios IS 'Pre-built practice scenarios for learning';
COMMENT ON TABLE practice_feedback IS 'AI-generated feedback on practice deals';
COMMENT ON TABLE user_points IS 'User points and levels for gamification';
COMMENT ON TABLE gamification_rules IS 'Rules for awarding points';
COMMENT ON TABLE user_badges IS 'Badges earned by users';
COMMENT ON TABLE leaderboards IS 'Leaderboards for various metrics';
