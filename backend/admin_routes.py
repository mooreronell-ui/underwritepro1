"""
Admin Dashboard Routes - Master Admin Only
Apple-Grade Backend Administration
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from database_unified import get_db, User, Organization, Deal, AuditLog
from auth import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])

# ==================== MODELS ====================

class AdminStats(BaseModel):
    total_users: int
    total_organizations: int
    total_deals: int
    active_users_today: int
    deals_this_month: int
    revenue_this_month: float
    avg_deal_size: float
    system_health: str

class UserDetail(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    organization_name: str
    created_at: datetime
    last_login: Optional[datetime]
    deal_count: int
    is_active: bool

class DealDetail(BaseModel):
    id: str
    borrower_name: str
    loan_amount: float
    property_address: str
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime

class SystemHealth(BaseModel):
    database: str
    api_response_time: float
    error_rate: float
    uptime_percentage: float
    active_connections: int

# ==================== MIDDLEWARE ====================

def verify_admin(current_user: User = Depends(get_current_user)):
    """Verify user is an admin"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return current_user

# ==================== ROUTES ====================

@router.get("/stats", response_model=AdminStats)
async def get_admin_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(verify_admin)
):
    """Get comprehensive admin statistics"""
    try:
        # Total counts
        total_users = db.query(func.count(User.id)).scalar()
        total_orgs = db.query(func.count(Organization.id)).scalar()
        total_deals = db.query(func.count(Deal.id)).scalar()
        
        # Active users today
        today = datetime.utcnow().date()
        active_today = db.query(func.count(User.id)).filter(
            func.date(User.last_login) == today
        ).scalar()
        
        # Deals this month
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        deals_this_month = db.query(func.count(Deal.id)).filter(
            Deal.created_at >= month_start
        ).scalar()
        
        # Revenue calculations (assuming loan_amount field)
        total_loan_amount = db.query(func.sum(Deal.loan_amount)).scalar() or 0
        avg_deal_size = total_loan_amount / total_deals if total_deals > 0 else 0
        
        # Assuming 1% revenue per deal
        revenue_this_month = (
            db.query(func.sum(Deal.loan_amount)).filter(
                Deal.created_at >= month_start
            ).scalar() or 0
        ) * 0.01
        
        return AdminStats(
            total_users=total_users,
            total_organizations=total_orgs,
            total_deals=total_deals,
            active_users_today=active_today or 0,
            deals_this_month=deals_this_month or 0,
            revenue_this_month=revenue_this_month,
            avg_deal_size=avg_deal_size,
            system_health="healthy"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@router.get("/users", response_model=List[UserDetail])
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(verify_admin)
):
    """Get all users with details"""
    try:
        query = db.query(User).join(Organization)
        
        if search:
            query = query.filter(
                (User.email.contains(search)) |
                (User.full_name.contains(search))
            )
        
        users = query.offset(skip).limit(limit).all()
        
        result = []
        for user in users:
            deal_count = db.query(func.count(Deal.id)).filter(
                Deal.created_by_id == user.id
            ).scalar()
            
            result.append(UserDetail(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                organization_name=user.organization.name if user.organization else "N/A",
                created_at=user.created_at,
                last_login=user.last_login,
                deal_count=deal_count or 0,
                is_active=getattr(user, 'is_active', True)
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get users: {str(e)}")

@router.get("/deals", response_model=List[DealDetail])
async def get_all_deals(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(verify_admin)
):
    """Get all deals with details"""
    try:
        query = db.query(Deal).join(User, Deal.created_by_id == User.id)
        
        if status:
            query = query.filter(Deal.status == status)
        
        deals = query.order_by(desc(Deal.created_at)).offset(skip).limit(limit).all()
        
        result = []
        for deal in deals:
            result.append(DealDetail(
                id=deal.id,
                borrower_name=deal.borrower.name if deal.borrower else "N/A",
                loan_amount=deal.loan_amount or 0,
                property_address=deal.property_address or "N/A",
                status=deal.status,
                created_by=deal.created_by_user.full_name if deal.created_by_user else "N/A",
                created_at=deal.created_at,
                updated_at=deal.updated_at
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get deals: {str(e)}")

@router.post("/users/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(verify_admin)
):
    """Activate or deactivate a user"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Toggle is_active if it exists
        if hasattr(user, 'is_active'):
            user.is_active = not user.is_active
            db.commit()
            
            return {
                "success": True,
                "user_id": user_id,
                "is_active": user.is_active
            }
        else:
            raise HTTPException(status_code=400, detail="User model doesn't support activation")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to toggle status: {str(e)}")

@router.post("/users/{user_id}/change-role")
async def change_user_role(
    user_id: str,
    new_role: str,
    db: Session = Depends(get_db),
    admin: User = Depends(verify_admin)
):
    """Change a user's role"""
    try:
        valid_roles = ["broker", "analyst", "approver", "admin"]
        if new_role not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.role = new_role
        db.commit()
        
        return {
            "success": True,
            "user_id": user_id,
            "new_role": new_role
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to change role: {str(e)}")

@router.get("/system-health", response_model=SystemHealth)
async def get_system_health(
    db: Session = Depends(get_db),
    admin: User = Depends(verify_admin)
):
    """Get system health metrics"""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "healthy"
        
        # Get active connections (simplified)
        active_connections = 1  # Would need actual connection pool stats
        
        # Calculate error rate from audit logs (last hour)
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        total_requests = db.query(func.count(AuditLog.id)).filter(
            AuditLog.timestamp >= hour_ago
        ).scalar() or 1
        
        error_requests = db.query(func.count(AuditLog.id)).filter(
            AuditLog.timestamp >= hour_ago,
            AuditLog.action.contains("error")
        ).scalar() or 0
        
        error_rate = (error_requests / total_requests) * 100 if total_requests > 0 else 0
        
        return SystemHealth(
            database=db_status,
            api_response_time=0.15,  # Would measure actual response times
            error_rate=error_rate,
            uptime_percentage=99.95,  # Would track actual uptime
            active_connections=active_connections
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get health: {str(e)}")

@router.get("/audit-logs")
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(verify_admin)
):
    """Get audit logs"""
    try:
        query = db.query(AuditLog)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        
        logs = query.order_by(desc(AuditLog.timestamp)).offset(skip).limit(limit).all()
        
        return [{
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "details": log.details,
            "timestamp": log.timestamp
        } for log in logs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")

@router.delete("/deals/{deal_id}")
async def delete_deal(
    deal_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(verify_admin)
):
    """Delete a deal (admin only)"""
    try:
        deal = db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        db.delete(deal)
        db.commit()
        
        return {"success": True, "deal_id": deal_id, "message": "Deal deleted"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete deal: {str(e)}")
