"""
Usage Enforcement Middleware
Automatically enforces subscription limits on API endpoints
"""

from fastapi import HTTPException
from functools import wraps
from subscription_service import SubscriptionService

def require_limit(limit_name: str, increment: int = 1):
    """
    Decorator to enforce subscription limits on endpoints
    
    Usage:
        @require_limit("deals_per_month")
        async def create_deal(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs
            current_user = kwargs.get("current_user")
            if not current_user:
                # Try to find it in args
                for arg in args:
                    if isinstance(arg, dict) and "organization_id" in arg:
                        current_user = arg
                        break
            
            if not current_user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
            
            # Check limit
            service = SubscriptionService()
            result = service.check_usage_limit(
                current_user["organization_id"],
                limit_name,
                increment
            )
            
            if not result["allowed"]:
                raise HTTPException(
                    status_code=402,  # Payment Required
                    detail={
                        "error": "Subscription limit exceeded",
                        "limit_name": limit_name,
                        "current_usage": result.get("current_usage"),
                        "limit": result.get("limit"),
                        "upgrade_required": True,
                        "message": f"You've reached your plan limit for {limit_name}. Please upgrade to continue."
                    }
                )
            
            # Increment usage after successful check
            try:
                # Map limit names to metrics
                metric_map = {
                    "deals_per_month": "deals_created",
                    "ai_requests_per_month": "ai_requests",
                    "email_sends_per_month": "email_sends",
                    "sms_sends_per_month": "sms_sends",
                    "api_calls_per_day": "api_calls"
                }
                
                metric = metric_map.get(limit_name)
                if metric:
                    service.increment_usage(
                        current_user["organization_id"],
                        metric,
                        increment
                    )
            except Exception as e:
                print(f"Failed to increment usage: {e}")
            
            # Call original function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

def check_feature_access(feature_name: str):
    """
    Decorator to check if a plan has access to a specific feature
    
    Usage:
        @check_feature_access("custom_branding")
        async def update_branding(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                for arg in args:
                    if isinstance(arg, dict) and "organization_id" in arg:
                        current_user = arg
                        break
            
            if not current_user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
            
            # Get subscription and check feature access
            service = SubscriptionService()
            subscription = service.get_subscription(current_user["organization_id"])
            
            if not subscription:
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": "No active subscription",
                        "upgrade_required": True
                    }
                )
            
            from subscription_plans import get_plan_details
            plan = get_plan_details(subscription["plan_tier"])
            
            if not plan["limits"].get(feature_name, False):
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": "Feature not available in your plan",
                        "feature": feature_name,
                        "current_plan": subscription["plan_tier"],
                        "upgrade_required": True,
                        "message": f"The {feature_name} feature is not available in your current plan. Please upgrade to access this feature."
                    }
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
