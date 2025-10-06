"""
Subscription API Routes
Endpoints for subscription management, billing, and usage tracking
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel
from typing import Optional
from auth import get_current_user
from subscription_service import SubscriptionService
from subscription_plans import get_all_plans, get_plan_details, get_upgrade_path
import stripe
import os

router = APIRouter(prefix="/api/subscriptions", tags=["Subscriptions"])

# Request Models
class UpgradeRequest(BaseModel):
    plan_tier: str

class CheckoutRequest(BaseModel):
    plan_tier: str
    success_url: str
    cancel_url: str

# Subscription Endpoints
@router.get("/config")
async def get_stripe_config():
    """Get Stripe publishable key for frontend"""
    from stripe_config import get_publishable_key
    return {"publishable_key": get_publishable_key()}

@router.get("/plans")
async def get_plans():
    """Get all available subscription plans"""
    return {"plans": get_all_plans()}

@router.get("/current")
async def get_current_subscription(current_user: dict = Depends(get_current_user)):
    """Get current subscription for the user's organization"""
    service = SubscriptionService()
    subscription = service.get_subscription(current_user["organization_id"])
    
    if not subscription:
        # Create free subscription if none exists
        subscription = service.create_subscription(
            current_user["organization_id"], 
            "free"
        )
    
    # Add plan details
    plan = get_plan_details(subscription["plan_tier"])
    subscription["plan_details"] = plan
    
    return subscription

@router.get("/usage")
async def get_usage(current_user: dict = Depends(get_current_user)):
    """Get current usage for the user's organization"""
    service = SubscriptionService()
    subscription = service.get_subscription(current_user["organization_id"])
    usage = service.get_usage(current_user["organization_id"])
    
    if subscription:
        plan = get_plan_details(subscription["plan_tier"])
        usage["limits"] = plan["limits"]
        usage["plan_tier"] = subscription["plan_tier"]
    
    return usage

@router.post("/upgrade")
async def upgrade_subscription(
    request: UpgradeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Upgrade to a new plan"""
    service = SubscriptionService()
    
    # Verify upgrade path
    current_sub = service.get_subscription(current_user["organization_id"])
    if current_sub:
        upgrade_options = get_upgrade_path(current_sub["plan_tier"])
        if request.plan_tier not in upgrade_options:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot upgrade from {current_sub['plan_tier']} to {request.plan_tier}"
            )
    
    subscription = service.upgrade_subscription(
        current_user["organization_id"],
        request.plan_tier
    )
    
    return subscription

@router.post("/cancel")
async def cancel_subscription(
    immediate: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """Cancel subscription"""
    service = SubscriptionService()
    result = service.cancel_subscription(
        current_user["organization_id"],
        immediate=immediate
    )
    return result

# Stripe Integration Endpoints
@router.post("/checkout")
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create Stripe checkout session"""
    service = SubscriptionService()
    
    # Verify plan exists
    plan = get_plan_details(request.plan_tier)
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    if plan["price"] == 0:
        # Free plan, just create subscription directly
        subscription = service.create_subscription(
            current_user["organization_id"],
            request.plan_tier
        )
        return {"free_plan": True, "subscription": subscription}
    
    # Create checkout session
    result = service.create_checkout_session(
        current_user["organization_id"],
        request.plan_tier,
        request.success_url,
        request.cancel_url
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result

@router.post("/portal")
async def create_billing_portal(
    return_url: str,
    current_user: dict = Depends(get_current_user)
):
    """Create Stripe billing portal session"""
    service = SubscriptionService()
    result = service.create_billing_portal_session(
        current_user["organization_id"],
        return_url
    )
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    service = SubscriptionService()
    result = service.handle_webhook(event["type"], event["data"]["object"])
    
    return {"received": True, "handled": result.get("handled", True)}

# Usage Checking Endpoints
@router.post("/check-limit/{limit_name}")
async def check_limit(
    limit_name: str,
    increment: int = 1,
    current_user: dict = Depends(get_current_user)
):
    """Check if an action is within usage limits"""
    service = SubscriptionService()
    result = service.check_usage_limit(
        current_user["organization_id"],
        limit_name,
        increment
    )
    
    if not result["allowed"]:
        raise HTTPException(
            status_code=402,  # Payment Required
            detail=result
        )
    
    return result

@router.get("/upgrade-options")
async def get_upgrade_options(current_user: dict = Depends(get_current_user)):
    """Get available upgrade options"""
    service = SubscriptionService()
    subscription = service.get_subscription(current_user["organization_id"])
    
    if not subscription:
        current_plan = "free"
    else:
        current_plan = subscription["plan_tier"]
    
    upgrade_options = get_upgrade_path(current_plan)
    plans = []
    
    for plan_tier in upgrade_options:
        plan = get_plan_details(plan_tier)
        plans.append({
            "tier": plan_tier,
            "name": plan["name"],
            "price": plan["price"],
            "features": plan["features"],
            "limits": plan["limits"]
        })
    
    return {"current_plan": current_plan, "upgrade_options": plans}
