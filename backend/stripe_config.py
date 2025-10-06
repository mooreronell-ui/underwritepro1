"""
Stripe Configuration and Integration
Handles Stripe API initialization and payment processing
"""

import stripe
import os
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

# Initialize Stripe
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "pk_live_51SFLGMPQzy3lsrAroHYo62tbCGBjlDANoZvS1i7axNtRD342gg7jApQ4nLcCNIuCbPbkCz50jZVtT05h19qpy4U400PqfWrklP")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
    logger.info("Stripe initialized successfully")
else:
    logger.warning("STRIPE_SECRET_KEY not set - payment features will be disabled")

# Stripe Product and Price IDs
# These should match the products created in your Stripe Dashboard
STRIPE_PRODUCTS = {
    "starter": {
        "product_id": os.getenv("STRIPE_STARTER_PRODUCT_ID"),
        "price_id": os.getenv("STRIPE_STARTER_PRICE_ID"),
        "price": 49,
        "interval": "month"
    },
    "professional": {
        "product_id": os.getenv("STRIPE_PROFESSIONAL_PRODUCT_ID"),
        "price_id": os.getenv("STRIPE_PROFESSIONAL_PRICE_ID"),
        "price": 149,
        "interval": "month"
    },
    "enterprise": {
        "product_id": os.getenv("STRIPE_ENTERPRISE_PRODUCT_ID"),
        "price_id": os.getenv("STRIPE_ENTERPRISE_PRICE_ID"),
        "price": 499,
        "interval": "month"
    }
}

def create_checkout_session(
    plan_tier: str,
    customer_email: str,
    organization_id: str,
    success_url: str,
    cancel_url: str
) -> Optional[Dict]:
    """
    Create a Stripe Checkout session for subscription payment
    """
    if not STRIPE_SECRET_KEY:
        raise Exception("Stripe is not configured")
    
    product = STRIPE_PRODUCTS.get(plan_tier)
    if not product or not product.get("price_id"):
        raise Exception(f"No Stripe price configured for plan: {plan_tier}")
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': product["price_id"],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=customer_email,
            client_reference_id=organization_id,
            metadata={
                'organization_id': organization_id,
                'plan_tier': plan_tier
            },
            subscription_data={
                'metadata': {
                    'organization_id': organization_id,
                    'plan_tier': plan_tier
                }
            }
        )
        
        return {
            "session_id": session.id,
            "url": session.url
        }
    except Exception as e:
        logger.error(f"Failed to create checkout session: {e}")
        raise

def create_billing_portal_session(
    customer_id: str,
    return_url: str
) -> Optional[Dict]:
    """
    Create a Stripe billing portal session for subscription management
    """
    if not STRIPE_SECRET_KEY:
        raise Exception("Stripe is not configured")
    
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        
        return {
            "url": session.url
        }
    except Exception as e:
        logger.error(f"Failed to create billing portal session: {e}")
        raise

def get_customer_by_email(email: str) -> Optional[Dict]:
    """
    Find a Stripe customer by email
    """
    if not STRIPE_SECRET_KEY:
        return None
    
    try:
        customers = stripe.Customer.list(email=email, limit=1)
        if customers.data:
            return customers.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get customer: {e}")
        return None

def create_customer(email: str, name: str, organization_id: str) -> Optional[Dict]:
    """
    Create a new Stripe customer
    """
    if not STRIPE_SECRET_KEY:
        return None
    
    try:
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata={
                'organization_id': organization_id
            }
        )
        return customer
    except Exception as e:
        logger.error(f"Failed to create customer: {e}")
        return None

def cancel_subscription(subscription_id: str, immediate: bool = False) -> bool:
    """
    Cancel a Stripe subscription
    """
    if not STRIPE_SECRET_KEY:
        return False
    
    try:
        if immediate:
            stripe.Subscription.delete(subscription_id)
        else:
            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
        return True
    except Exception as e:
        logger.error(f"Failed to cancel subscription: {e}")
        return False

def get_publishable_key() -> str:
    """
    Get the Stripe publishable key for frontend use
    """
    return STRIPE_PUBLISHABLE_KEY
