"""
Subscription Plans and Limits
Defines pricing tiers and usage limits for the platform
"""

from enum import Enum
from typing import Dict, Optional

class PlanTier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

# Subscription Plan Definitions
SUBSCRIPTION_PLANS = {
    "free": {
        "name": "Free Trial",
        "price": 0,
        "billing_period": "monthly",
        "stripe_price_id": None,
        "limits": {
            "deals_per_month": 5,
            "active_deals": 3,
            "users": 1,
            "borrowers": 10,
            "ai_requests_per_month": 50,
            "document_storage_mb": 100,
            "workflows": 2,
            "email_sends_per_month": 50,
            "sms_sends_per_month": 0,
            "calendar_appointments": 10,
            "api_calls_per_day": 100,
            "custom_branding": False,
            "priority_support": False,
            "advanced_analytics": False,
            "white_label": False
        },
        "features": [
            "5 deals per month",
            "1 user",
            "Basic AI assistants (50 requests/month)",
            "100 MB document storage",
            "Email support",
            "Core underwriting features"
        ]
    },
    "starter": {
        "name": "Starter",
        "price": 49,
        "billing_period": "monthly",
        "stripe_price_id": "price_starter_monthly",  # Replace with actual Stripe price ID
        "limits": {
            "deals_per_month": 50,
            "active_deals": 25,
            "users": 3,
            "borrowers": 100,
            "ai_requests_per_month": 500,
            "document_storage_mb": 5000,  # 5 GB
            "workflows": 10,
            "email_sends_per_month": 500,
            "sms_sends_per_month": 100,
            "calendar_appointments": 100,
            "api_calls_per_day": 1000,
            "custom_branding": False,
            "priority_support": False,
            "advanced_analytics": True,
            "white_label": False
        },
        "features": [
            "50 deals per month",
            "3 users",
            "All AI assistants (500 requests/month)",
            "5 GB document storage",
            "10 custom workflows",
            "Email & SMS communication",
            "Advanced analytics",
            "Calendar scheduling",
            "Email support"
        ]
    },
    "professional": {
        "name": "Professional",
        "price": 149,
        "billing_period": "monthly",
        "stripe_price_id": "price_professional_monthly",  # Replace with actual Stripe price ID
        "limits": {
            "deals_per_month": 200,
            "active_deals": 100,
            "users": 10,
            "borrowers": 500,
            "ai_requests_per_month": 2000,
            "document_storage_mb": 20000,  # 20 GB
            "workflows": 50,
            "email_sends_per_month": 2000,
            "sms_sends_per_month": 500,
            "calendar_appointments": 500,
            "api_calls_per_day": 5000,
            "custom_branding": True,
            "priority_support": True,
            "advanced_analytics": True,
            "white_label": False
        },
        "features": [
            "200 deals per month",
            "10 users",
            "Unlimited AI assistants (2000 requests/month)",
            "20 GB document storage",
            "50 custom workflows",
            "Unlimited email & SMS",
            "Advanced analytics & reporting",
            "Calendar scheduling",
            "Custom branding",
            "Priority support",
            "API access"
        ]
    },
    "enterprise": {
        "name": "Enterprise",
        "price": 499,
        "billing_period": "monthly",
        "stripe_price_id": "price_enterprise_monthly",  # Replace with actual Stripe price ID
        "limits": {
            "deals_per_month": -1,  # Unlimited
            "active_deals": -1,  # Unlimited
            "users": -1,  # Unlimited
            "borrowers": -1,  # Unlimited
            "ai_requests_per_month": -1,  # Unlimited
            "document_storage_mb": -1,  # Unlimited
            "workflows": -1,  # Unlimited
            "email_sends_per_month": -1,  # Unlimited
            "sms_sends_per_month": -1,  # Unlimited
            "calendar_appointments": -1,  # Unlimited
            "api_calls_per_day": -1,  # Unlimited
            "custom_branding": True,
            "priority_support": True,
            "advanced_analytics": True,
            "white_label": True
        },
        "features": [
            "Unlimited deals",
            "Unlimited users",
            "Unlimited AI assistants",
            "Unlimited document storage",
            "Unlimited workflows",
            "Unlimited email & SMS",
            "Advanced analytics & reporting",
            "Calendar scheduling",
            "Custom branding",
            "White-label option",
            "Dedicated account manager",
            "Priority support (24/7)",
            "Custom integrations",
            "SLA guarantee",
            "API access"
        ]
    }
}

def get_plan_details(plan_tier: str) -> Optional[Dict]:
    """Get details for a specific plan"""
    return SUBSCRIPTION_PLANS.get(plan_tier)

def get_plan_limit(plan_tier: str, limit_name: str) -> Optional[int]:
    """Get a specific limit for a plan"""
    plan = SUBSCRIPTION_PLANS.get(plan_tier)
    if not plan:
        return None
    return plan["limits"].get(limit_name)

def check_limit(plan_tier: str, limit_name: str, current_usage: int) -> bool:
    """Check if usage is within plan limits"""
    limit = get_plan_limit(plan_tier, limit_name)
    if limit is None:
        return False
    if limit == -1:  # Unlimited
        return True
    return current_usage < limit

def get_all_plans() -> Dict:
    """Get all available plans"""
    return SUBSCRIPTION_PLANS

def get_upgrade_path(current_plan: str) -> list:
    """Get available upgrade options"""
    plan_order = ["free", "starter", "professional", "enterprise"]
    current_index = plan_order.index(current_plan) if current_plan in plan_order else 0
    return plan_order[current_index + 1:] if current_index < len(plan_order) - 1 else []
