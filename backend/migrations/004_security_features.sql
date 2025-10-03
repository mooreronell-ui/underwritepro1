-- Security Features Migration
-- Adds tables for 2FA, sessions, RBAC, and audit logging

-- Add 2FA fields to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS two_factor_secret VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS two_factor_enabled BOOLEAN DEFAULT FALSE;

-- Backup codes for 2FA recovery
CREATE TABLE IF NOT EXISTS user_backup_codes (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    code_hash VARCHAR(255) NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- User sessions for session management
CREATE TABLE IF NOT EXISTS user_sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);

-- Roles for RBAC
CREATE TABLE IF NOT EXISTS roles (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    permissions TEXT,
    created_at TIMESTAMP NOT NULL
);

-- User role assignments
CREATE TABLE IF NOT EXISTS user_roles (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    role_id VARCHAR(255) NOT NULL,
    assigned_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    UNIQUE(user_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id);

-- Security audit log
CREATE TABLE IF NOT EXISTS security_audit_log (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255),
    event_type VARCHAR(100) NOT NULL,
    details TEXT,
    ip_address VARCHAR(50),
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_security_audit_log_user_id ON security_audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_security_audit_log_event_type ON security_audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_security_audit_log_created_at ON security_audit_log(created_at);

-- IP whitelist for organization-level IP restrictions
CREATE TABLE IF NOT EXISTS ip_whitelist (
    id VARCHAR(255) PRIMARY KEY,
    organization_id VARCHAR(255) NOT NULL,
    ip_address VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    UNIQUE(organization_id, ip_address)
);

CREATE INDEX IF NOT EXISTS idx_ip_whitelist_org_id ON ip_whitelist(organization_id);

-- Insert default roles
INSERT INTO roles (id, name, description, permissions, created_at)
VALUES 
    ('role-admin', 'Admin', 'Full system access', '["*"]', NOW()),
    ('role-underwriter', 'Underwriter', 'Can manage deals and borrowers', '["deals:read", "deals:write", "borrowers:read", "borrowers:write", "documents:read", "documents:write"]', NOW()),
    ('role-analyst', 'Analyst', 'Read-only access to deals and reports', '["deals:read", "borrowers:read", "documents:read", "reports:read"]', NOW()),
    ('role-viewer', 'Viewer', 'Basic read access', '["deals:read", "borrowers:read"]', NOW())
ON CONFLICT (name) DO NOTHING;
