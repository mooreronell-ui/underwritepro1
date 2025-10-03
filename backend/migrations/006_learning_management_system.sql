-- Migration 006: Learning Management System (LMS)
-- This migration creates the complete LMS infrastructure

-- Learning Paths Table
CREATE TABLE IF NOT EXISTS learning_paths (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    target_audience VARCHAR(50) NOT NULL,
    -- 'commercial_lender', 'residential_lo', 'career_changer'
    duration_weeks INT,
    difficulty VARCHAR(50),
    -- 'beginner', 'intermediate', 'advanced'
    prerequisites TEXT[],
    learning_objectives TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Learning Modules Table
CREATE TABLE IF NOT EXISTS learning_modules (
    id VARCHAR(36) PRIMARY KEY,
    path_id VARCHAR(36) REFERENCES learning_paths(id) ON DELETE CASCADE,
    module_number INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    slug VARCHAR(200) NOT NULL,
    description TEXT,
    learning_objectives TEXT[],
    estimated_minutes INT,
    is_required BOOLEAN DEFAULT TRUE,
    unlock_criteria JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(path_id, module_number)
);

-- Learning Lessons Table
CREATE TABLE IF NOT EXISTS learning_lessons (
    id VARCHAR(36) PRIMARY KEY,
    module_id VARCHAR(36) REFERENCES learning_modules(id) ON DELETE CASCADE,
    lesson_number INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    slug VARCHAR(200) NOT NULL,
    lesson_type VARCHAR(50) NOT NULL,
    -- 'video', 'text', 'interactive', 'quiz', 'practice'
    content TEXT,
    video_url TEXT,
    video_duration_seconds INT,
    resources JSONB,
    -- Links, downloads, references
    estimated_minutes INT,
    is_required BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(module_id, lesson_number)
);

-- Quiz Questions Table
CREATE TABLE IF NOT EXISTS quiz_questions (
    id VARCHAR(36) PRIMARY KEY,
    lesson_id VARCHAR(36) REFERENCES learning_lessons(id) ON DELETE CASCADE,
    question_number INT NOT NULL,
    question_text TEXT NOT NULL,
    question_type VARCHAR(50) NOT NULL,
    -- 'multiple_choice', 'true_false', 'short_answer'
    options JSONB,
    -- For multiple choice
    correct_answer TEXT NOT NULL,
    explanation TEXT,
    points INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW()
);

-- User Learning Progress Table
CREATE TABLE IF NOT EXISTS user_learning_progress (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    path_id VARCHAR(36) REFERENCES learning_paths(id) ON DELETE CASCADE,
    module_id VARCHAR(36) REFERENCES learning_modules(id) ON DELETE CASCADE,
    lesson_id VARCHAR(36) REFERENCES learning_lessons(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'not_started',
    -- 'not_started', 'in_progress', 'completed'
    progress_percent INT DEFAULT 0,
    time_spent_minutes INT DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_accessed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, lesson_id)
);

-- Quiz Attempts Table
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    lesson_id VARCHAR(36) REFERENCES learning_lessons(id) ON DELETE CASCADE,
    attempt_number INT NOT NULL,
    score INT NOT NULL,
    max_score INT NOT NULL,
    passed BOOLEAN NOT NULL,
    answers JSONB NOT NULL,
    time_taken_seconds INT,
    completed_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, lesson_id, attempt_number)
);

-- User Achievements Table
CREATE TABLE IF NOT EXISTS user_achievements (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    achievement_type VARCHAR(50) NOT NULL,
    -- 'lesson_completed', 'module_completed', 'path_completed', 'quiz_passed', 'streak'
    achievement_name VARCHAR(100) NOT NULL,
    achievement_description TEXT,
    badge_icon VARCHAR(50),
    -- Emoji or icon name
    metadata JSONB,
    earned_at TIMESTAMP DEFAULT NOW()
);

-- User Certificates Table
CREATE TABLE IF NOT EXISTS user_certificates (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    path_id VARCHAR(36) REFERENCES learning_paths(id) ON DELETE CASCADE,
    certificate_number VARCHAR(50) UNIQUE NOT NULL,
    issued_at TIMESTAMP DEFAULT NOW(),
    certificate_url TEXT
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_learning_modules_path ON learning_modules(path_id);
CREATE INDEX IF NOT EXISTS idx_learning_lessons_module ON learning_lessons(module_id);
CREATE INDEX IF NOT EXISTS idx_quiz_questions_lesson ON quiz_questions(lesson_id);
CREATE INDEX IF NOT EXISTS idx_user_progress_user ON user_learning_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_user_progress_path ON user_learning_progress(user_id, path_id);
CREATE INDEX IF NOT EXISTS idx_user_progress_status ON user_learning_progress(user_id, status);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user ON quiz_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_achievements_user ON user_achievements(user_id);
CREATE INDEX IF NOT EXISTS idx_certificates_user ON user_certificates(user_id);

-- Add comments
COMMENT ON TABLE learning_paths IS 'Defines complete learning paths for different audiences';
COMMENT ON TABLE learning_modules IS 'Modules within learning paths';
COMMENT ON TABLE learning_lessons IS 'Individual lessons within modules';
COMMENT ON TABLE quiz_questions IS 'Quiz questions for assessments';
COMMENT ON TABLE user_learning_progress IS 'Tracks user progress through lessons';
COMMENT ON TABLE quiz_attempts IS 'Records quiz attempts and scores';
COMMENT ON TABLE user_achievements IS 'Badges and achievements earned by users';
COMMENT ON TABLE user_certificates IS 'Certificates issued upon path completion';
