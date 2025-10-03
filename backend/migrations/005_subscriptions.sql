-- Subscription and Billing Tables Migration

-- Subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    id VARCHAR(255) PRIMARY KEY,
    organization_id VARCHAR(255) NOT NULL,
    plan_tier VARCHAR(50) NOT NULL DEFAULT 'free',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    cancelled_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_org_id ON subscriptions(organization_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_customer ON subscriptions(stripe_customer_id);

-- Usage tracking table
CREATE TABLE IF NOT EXISTS usage_tracking (
    id VARCHAR(255) PRIMARY KEY,
    organization_id VARCHAR(255) NOT NULL,
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    deals_created INTEGER DEFAULT 0,
    ai_requests INTEGER DEFAULT 0,
    email_sends INTEGER DEFAULT 0,
    sms_sends INTEGER DEFAULT 0,
    document_storage_mb INTEGER DEFAULT 0,
    api_calls INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_usage_tracking_org_id ON usage_tracking(organization_id);
CREATE INDEX IF NOT EXISTS idx_usage_tracking_period ON usage_tracking(period_start, period_end);

-- Payment history table
CREATE TABLE IF NOT EXISTS payment_history (
    id VARCHAR(255) PRIMARY KEY,
    organization_id VARCHAR(255) NOT NULL,
    subscription_id VARCHAR(255),
    stripe_invoice_id VARCHAR(255),
    stripe_payment_intent_id VARCHAR(255),
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) NOT NULL,
    payment_method VARCHAR(50),
    paid_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_payment_history_org_id ON payment_history(organization_id);
CREATE INDEX IF NOT EXISTS idx_payment_history_subscription ON payment_history(subscription_id);
CREATE INDEX IF NOT EXISTS idx_payment_history_status ON payment_history(status);

-- Invoices table
CREATE TABLE IF NOT EXISTS invoices (
    id VARCHAR(255) PRIMARY KEY,
    organization_id VARCHAR(255) NOT NULL,
    subscription_id VARCHAR(255),
    stripe_invoice_id VARCHAR(255),
    invoice_number VARCHAR(100),
    amount_due DECIMAL(10, 2) NOT NULL,
    amount_paid DECIMAL(10, 2) DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) NOT NULL,
    invoice_pdf_url TEXT,
    due_date TIMESTAMP,
    paid_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_invoices_org_id ON invoices(organization_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);

-- Add subscription_id to organizations table if not exists
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS subscription_id VARCHAR(255);

-- Create default free subscriptions for existing organizations
INSERT INTO subscriptions (id, organization_id, plan_tier, status, current_period_start, current_period_end, created_at)
SELECT 
    gen_random_uuid()::text,
    id,
    'free',
    'active',
    NOW(),
    NOW() + INTERVAL '30 days',
    NOW()
FROM organizations
WHERE id NOT IN (SELECT organization_id FROM subscriptions)
ON CONFLICT DO NOTHING;
