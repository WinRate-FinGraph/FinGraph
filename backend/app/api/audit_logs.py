from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, merchant_scope_id
from app.api.pagination import page_response
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.activity_monitoring import (
    activity_monitoring_payload,
    activity_window,
    attach_payment_impacts,
    filter_activity_category,
)
from app.services.subscriptions import plan_allows


router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("")
def get_audit_logs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    action: str | None = None,
    entity_type: str | None = Query(default=None, max_length=80),
    entity_id: str | None = Query(default=None, max_length=120),
    search: str | None = Query(default=None, max_length=120),
    ordering: str = Query(default="newest", pattern="^(newest|oldest)$"),
    period: str = Query(default="30d", pattern="^(today|7d|30d|custom)$"),
    role: str | None = Query(default=None, pattern="^(merchant|analyst|admin|system)$"),
    activity_category: str = Query(default="all", pattern="^(all|operational|authentication|payment|review|configuration|model|system)$"),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    start, end = activity_window(period, date_from, date_to)
    query = db.query(AuditLog).filter(AuditLog.created_at >= start, AuditLog.created_at <= end)
    scope = merchant_scope_id(user, db)
    if scope:
        if not plan_allows(user.merchant_profile.subscription_plan, "growth"):
            raise HTTPException(status_code=403, detail="Action Log tersedia mulai paket Growth.")
        query = query.filter(AuditLog.merchant_id == scope)
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if role:
        query = query.filter(AuditLog.actor_role == role)
    query = filter_activity_category(query, activity_category)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                AuditLog.actor.ilike(pattern),
                AuditLog.action.ilike(pattern),
                AuditLog.entity_type.ilike(pattern),
                AuditLog.entity_id.ilike(pattern),
                AuditLog.description.ilike(pattern),
            )
        )
    total = query.count()
    order_columns = (
        (AuditLog.created_at.desc(), AuditLog.id.desc())
        if ordering == "newest"
        else (AuditLog.created_at.asc(), AuditLog.id.asc())
    )
    logs = query.order_by(*order_columns).offset(offset).limit(limit).all()
    response = page_response(
        total=total,
        limit=limit,
        offset=offset,
        items=attach_payment_impacts(db, logs),
    )
    monitoring = activity_monitoring_payload(
        db,
        period=period,
        role=role,
        date_from=date_from,
        date_to=date_to,
        recent_limit=5,
        merchant_id=scope,
        category=activity_category,
    )
    response.update(
        {
            "summary": {
                "active_users": monitoring["active_users"],
                "activities_today": monitoring["activities_today"],
                "total_users": monitoring["total_users"],
                "active_merchants": monitoring["active_merchants"],
            },
            "activity_by_role": monitoring["activity_by_role"],
            "top_users": monitoring["top_users"],
            "window": monitoring["window"],
        }
    )
    return response
