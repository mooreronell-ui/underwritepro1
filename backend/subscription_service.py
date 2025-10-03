"""
Subscription Management Service
Handles Stripe integration, subscriptions, and usage tracking
"""

import os
import stripe
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import uuid
from database_unified import engine
import psycopg2
from subscription_plans import SUBSCRIPTION_PLANS, get_plan_limit, check_limit

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

class SubscriptionService:
    """Service for managing subscriptions and billing"""
    
    def __init__(self):
        self.conn = engine.raw_connection()
    
    # Subscription Management
    def create_subscription(self, organization_id: str, plan_tier: str, 
                          stripe_customer_id: Optional[str] = None) -> Dict:
        """Create a new subscription"""
        cursor = self.conn.cursor()
        subscription_id = str(uuid.uuid4())
        
        plan = SUBSCRIPTION_PLANS.get(plan_tier)
        if not plan:
            raise ValueError(f"Invalid plan tier: {plan_tier}")
        
        # Calculate billing dates
        start_date = datetime.utcnow()
        if plan["billing_period"] == "monthly":
            end_date = start_date + timedelta(days=30)
        elif plan["billing_period"] == "yearly":
            end_date = start_date + timedelta(days=365)
        else:
            end_date = start_date + timedelta(days=30)
        
        cursor.execute("""
            INSERT INTO subscriptions 
            (id, organization_id, plan_tier, status, stripe_customer_id, 
             stripe_subscription_id, current_period_start, current_period_end, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (subscription_id, organization_id, plan_tier, 'active', 
              stripe_customer_id, None, start_date, end_date, datetime.utcnow()))
        
        self.conn.commit()
        
        # Initialize usage tracking
        self._reset_usage_tracking(organization_id)
        
        return {
            "subscription_id": subscription_id,
            "plan_tier": plan_tier,
            "status": "active",
            "current_period_start": start_date.isoformat(),
            "current_period_end": end_date.isoformat()
        }
    
    def get_subscription(self, organization_id: str) -> Optional[Dict]:
        """Get current subscription for an organization"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, plan_tier, status, stripe_customer_id, stripe_subscription_id,
                   current_period_start, current_period_end, cancel_at_period_end
            FROM subscriptions
            WHERE organization_id = %s AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
        """, (organization_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            "subscription_id": row[0],
            "plan_tier": row[1],
            "status": row[2],
            "stripe_customer_id": row[3],
            "stripe_subscription_id": row[4],
            "current_period_start": row[5].isoformat() if row[5] else None,
            "current_period_end": row[6].isoformat() if row[6] else None,
            "cancel_at_period_end": row[7]
        }
    
    def upgrade_subscription(self, organization_id: str, new_plan_tier: str) -> Dict:
        """Upgrade subscription to a new plan"""
        current_sub = self.get_subscription(organization_id)
        if not current_sub:
            return self.create_subscription(organization_id, new_plan_tier)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE subscriptions
            SET plan_tier = %s, updated_at = %s
            WHERE organization_id = %s AND status = 'active'
        """, (new_plan_tier, datetime.utcnow(), organization_id))
        
        self.conn.commit()
        
        # If has Stripe subscription, update it
        if current_sub.get("stripe_subscription_id"):
            try:
                stripe.Subscription.modify(
                    current_sub["stripe_subscription_id"],
                    items=[{
                        'price': SUBSCRIPTION_PLANS[new_plan_tier]["stripe_price_id"]
                    }]
                )
            except Exception as e:
                print(f"Stripe update failed: {e}")
        
        return self.get_subscription(organization_id)
    
    def cancel_subscription(self, organization_id: str, immediate: bool = False) -> Dict:
        """Cancel a subscription"""
        cursor = self.conn.cursor()
        
        if immediate:
            cursor.execute("""
                UPDATE subscriptions
                SET status = 'cancelled', cancelled_at = %s
                WHERE organization_id = %s AND status = 'active'
            """, (datetime.utcnow(), organization_id))
        else:
            cursor.execute("""
                UPDATE subscriptions
                SET cancel_at_period_end = TRUE, updated_at = %s
                WHERE organization_id = %s AND status = 'active'
            """, (datetime.utcnow(), organization_id))
        
        self.conn.commit()
        return {"success": True, "immediate": immediate}
    
    # Usage Tracking
    def _reset_usage_tracking(self, organization_id: str):
        """Reset usage tracking for a new billing period"""
        cursor = self.conn.cursor()
        usage_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO usage_tracking 
            (id, organization_id, period_start, period_end, 
             deals_created, ai_requests, email_sends, sms_sends, 
             document_storage_mb, api_calls)
            VALUES (%s, %s, %s, %s, 0, 0, 0, 0, 0, 0)
        """, (usage_id, organization_id, datetime.utcnow(), 
              datetime.utcnow() + timedelta(days=30)))
        
        self.conn.commit()
    
    def get_usage(self, organization_id: str) -> Dict:
        """Get current usage for an organization"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT deals_created, ai_requests, email_sends, sms_sends,
                   document_storage_mb, api_calls, period_start, period_end
            FROM usage_tracking
            WHERE organization_id = %s
            ORDER BY period_start DESC
            LIMIT 1
        """, (organization_id,))
        
        row = cursor.fetchone()
        if not row:
            self._reset_usage_tracking(organization_id)
            return self.get_usage(organization_id)
        
        return {
            "deals_created": row[0] or 0,
            "ai_requests": row[1] or 0,
            "email_sends": row[2] or 0,
            "sms_sends": row[3] or 0,
            "document_storage_mb": row[4] or 0,
            "api_calls": row[5] or 0,
            "period_start": row[6].isoformat() if row[6] else None,
            "period_end": row[7].isoformat() if row[7] else None
        }
    
    def increment_usage(self, organization_id: str, metric: str, amount: int = 1):
        """Increment a usage metric"""
        cursor = self.conn.cursor()
        
        valid_metrics = ['deals_created', 'ai_requests', 'email_sends', 
                        'sms_sends', 'document_storage_mb', 'api_calls']
        
        if metric not in valid_metrics:
            raise ValueError(f"Invalid metric: {metric}")
        
        cursor.execute(f"""
            UPDATE usage_tracking
            SET {metric} = {metric} + %s
            WHERE organization_id = %s
              AND period_end > %s
        """, (amount, organization_id, datetime.utcnow()))
        
        self.conn.commit()
    
    def check_usage_limit(self, organization_id: str, limit_name: str, 
                         increment: int = 1) -> Dict:
        """Check if usage is within limits before allowing an action"""
        subscription = self.get_subscription(organization_id)
        if not subscription:
            return {"allowed": False, "reason": "No active subscription"}
        
        plan_tier = subscription["plan_tier"]
        usage = self.get_usage(organization_id)
        
        # Map limit names to usage metrics
        metric_map = {
            "deals_per_month": "deals_created",
            "ai_requests_per_month": "ai_requests",
            "email_sends_per_month": "email_sends",
            "sms_sends_per_month": "sms_sends",
            "api_calls_per_day": "api_calls"
        }
        
        metric = metric_map.get(limit_name)
        if not metric:
            return {"allowed": True}  # No tracking for this limit
        
        current_usage = usage.get(metric, 0)
        limit = get_plan_limit(plan_tier, limit_name)
        
        if limit == -1:  # Unlimited
            return {"allowed": True, "unlimited": True}
        
        if current_usage + increment > limit:
            return {
                "allowed": False,
                "reason": f"Limit exceeded: {current_usage}/{limit}",
                "current_usage": current_usage,
                "limit": limit,
                "upgrade_required": True
            }
        
        return {
            "allowed": True,
            "current_usage": current_usage,
            "limit": limit,
            "remaining": limit - current_usage
        }
    
    # Stripe Integration
    def create_stripe_customer(self, organization_id: str, email: str, 
                               name: str) -> Dict:
        """Create a Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={"organization_id": organization_id}
            )
            
            # Update subscription with customer ID
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE subscriptions
                SET stripe_customer_id = %s
                WHERE organization_id = %s AND status = 'active'
            """, (customer.id, organization_id))
            self.conn.commit()
            
            return {"customer_id": customer.id}
        except Exception as e:
            return {"error": str(e)}
    
    def create_checkout_session(self, organization_id: str, plan_tier: str, 
                                success_url: str, cancel_url: str) -> Dict:
        """Create a Stripe checkout session"""
        plan = SUBSCRIPTION_PLANS.get(plan_tier)
        if not plan or not plan.get("stripe_price_id"):
            return {"error": "Invalid plan or no Stripe price ID configured"}
        
        try:
            session = stripe.checkout.Session.create(
                mode='subscription',
                line_items=[{
                    'price': plan["stripe_price_id"],
                    'quantity': 1,
                }],
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=organization_id,
                metadata={"organization_id": organization_id, "plan_tier": plan_tier}
            )
            
            return {
                "checkout_url": session.url,
                "session_id": session.id
            }
        except Exception as e:
            return {"error": str(e)}
    
    def create_billing_portal_session(self, organization_id: str, 
                                      return_url: str) -> Dict:
        """Create a Stripe billing portal session"""
        subscription = self.get_subscription(organization_id)
        if not subscription or not subscription.get("stripe_customer_id"):
            return {"error": "No Stripe customer found"}
        
        try:
            session = stripe.billing_portal.Session.create(
                customer=subscription["stripe_customer_id"],
                return_url=return_url
            )
            
            return {"portal_url": session.url}
        except Exception as e:
            return {"error": str(e)}
    
    def handle_webhook(self, event_type: str, event_data: Dict) -> Dict:
        """Handle Stripe webhook events"""
        if event_type == "checkout.session.completed":
            return self._handle_checkout_completed(event_data)
        elif event_type == "customer.subscription.updated":
            return self._handle_subscription_updated(event_data)
        elif event_type == "customer.subscription.deleted":
            return self._handle_subscription_deleted(event_data)
        elif event_type == "invoice.payment_succeeded":
            return self._handle_payment_succeeded(event_data)
        elif event_type == "invoice.payment_failed":
            return self._handle_payment_failed(event_data)
        
        return {"handled": False}
    
    def _handle_checkout_completed(self, session: Dict) -> Dict:
        """Handle successful checkout"""
        organization_id = session.get("client_reference_id")
        subscription_id = session.get("subscription")
        customer_id = session.get("customer")
        
        if not organization_id:
            return {"error": "No organization_id in session"}
        
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE subscriptions
            SET stripe_subscription_id = %s, stripe_customer_id = %s, 
                status = 'active', updated_at = %s
            WHERE organization_id = %s
        """, (subscription_id, customer_id, datetime.utcnow(), organization_id))
        
        self.conn.commit()
        return {"success": True}
    
    def _handle_subscription_updated(self, subscription: Dict) -> Dict:
        """Handle subscription update"""
        # Update subscription status in database
        return {"success": True}
    
    def _handle_subscription_deleted(self, subscription: Dict) -> Dict:
        """Handle subscription cancellation"""
        customer_id = subscription.get("customer")
        
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE subscriptions
            SET status = 'cancelled', cancelled_at = %s
            WHERE stripe_customer_id = %s
        """, (datetime.utcnow(), customer_id))
        
        self.conn.commit()
        return {"success": True}
    
    def _handle_payment_succeeded(self, invoice: Dict) -> Dict:
        """Handle successful payment"""
        # Log successful payment
        return {"success": True}
    
    def _handle_payment_failed(self, invoice: Dict) -> Dict:
        """Handle failed payment"""
        # Send notification, update subscription status
        return {"success": True}
