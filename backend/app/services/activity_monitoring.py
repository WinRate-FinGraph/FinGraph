from datetime import datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.qris import PaymentEvent
from app.models.user import User


ACTIVE_USER_WINDOW_MINUTES = 15
VALID_ACTIVITY_ROLES = {"merchant", "analyst", "admin", "system"}
ACTIVITY_CATEGORIES = {
    "authentication": {"login_user", "register_user"},
    "payment": {"create_order", "demo_create_order", "generate_demo_payment", "process_pjp_webhook", "reject_invalid_webhook_signature", "reject_replayed_webhook", "run_qris_demo_scenario", "match_payment_to_order", "update_order_status", "check_payment_not_found", "rescore_payment", "create_transaction"},
    "review": {"assign_alert", "update_alert_status", "create_payment_feedback"},
    "configuration": {"change_subscription_plan", "create_outlet", "create_qris_profile", "update_merchant_profile", "verify_qris_payload"},
    "model": {"register_federated_node", "run_federated_round"},
    "system": {"bootstrap_admin", "seed_merchant_demo", "seed_qris_demo"},
}


def activity_category(action: str) -> str:
    for category, actions in ACTIVITY_CATEGORIES.items():
        if action in actions:
            return category
    return "payment"


def filter_activity_category(query, category: str | None):
    if not category or category == "all":
        return query
    if category == "operational":
        return query.filter(AuditLog.action.notin_(ACTIVITY_CATEGORIES["authentication"]))
    actions = ACTIVITY_CATEGORIES.get(category)
    if actions is None:
        raise HTTPException(status_code=422, detail="Kategori aktivitas tidak valid")
    return query.filter(AuditLog.action.in_(actions))


def activity_window(
    period: str,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    *,
    now: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Return a UTC-naive window to match timestamps stored by the application."""
    jakarta = ZoneInfo("Asia/Jakarta")
    current_local = (now.replace(tzinfo=timezone.utc) if now and now.tzinfo is None else now).astimezone(jakarta) if now else datetime.now(jakarta)
    end_local = current_local
    if period == "today":
        start_local = datetime.combine(current_local.date(), time.min, tzinfo=jakarta)
    elif period == "7d":
        start_local = current_local - timedelta(days=7)
    elif period == "30d":
        start_local = current_local - timedelta(days=30)
    elif period == "custom":
        if date_from is None or date_to is None:
            raise HTTPException(status_code=422, detail="date_from dan date_to wajib untuk periode custom")
        start_value = date_from.replace(tzinfo=timezone.utc) if date_from.tzinfo is None else date_from
        end_value = date_to.replace(tzinfo=timezone.utc) if date_to.tzinfo is None else date_to
        start_local = start_value.astimezone(jakarta)
        end_local = end_value.astimezone(jakarta)
        if start_local > end_local:
            raise HTTPException(status_code=422, detail="date_from tidak boleh setelah date_to")
        if end_local - start_local > timedelta(days=366):
            raise HTTPException(status_code=422, detail="Rentang aktivitas maksimal 366 hari")
    else:
        raise HTTPException(status_code=422, detail="Periode aktivitas tidak valid")
    return (
        start_local.astimezone(timezone.utc).replace(tzinfo=None),
        end_local.astimezone(timezone.utc).replace(tzinfo=None),
    )


def serialize_activity(log: AuditLog, impact: PaymentEvent | None = None) -> dict:
    item = {
        "id": str(log.id),
        "actor": log.actor,
        "actor_role": log.actor_role,
        "action": log.action,
        "category": activity_category(log.action),
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "description": log.description,
        "created_at": log.created_at,
        "impact": None,
    }
    if impact:
        item["impact"] = {
            "payment_id": str(impact.id),
            "provider_reference": impact.provider_reference,
            "amount": float(impact.amount),
            "currency": impact.currency,
            "status": impact.payment_status,
            "risk_level": impact.risk_level,
            "priority": impact.priority,
            "category": impact.category,
        }
    return item


def attach_payment_impacts(db: Session, logs: list[AuditLog]) -> list[dict]:
    payment_ids: set[UUID] = set()
    for log in logs:
        if log.entity_type != "payment_event" or not log.entity_id:
            continue
        try:
            payment_ids.add(UUID(log.entity_id))
        except (TypeError, ValueError, AttributeError):
            # Audit entities are polymorphic; a malformed/non-UUID entity must
            # not make the whole activity feed unavailable.
            continue
    payments = {}
    if payment_ids:
        payments = {
            str(item.id): item
            for item in db.query(PaymentEvent).filter(PaymentEvent.id.in_(payment_ids)).all()
        }
    return [serialize_activity(log, payments.get(log.entity_id or "")) for log in logs]


def activity_monitoring_payload(
    db: Session,
    *,
    period: str = "today",
    role: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    recent_limit: int = 10,
    merchant_id=None,
    category: str | None = None,
) -> dict:
    if role and role not in VALID_ACTIVITY_ROLES:
        raise HTTPException(status_code=422, detail="Role aktivitas tidak valid")

    start, end = activity_window(period, date_from, date_to)
    now = datetime.utcnow()
    today_start, today_end = activity_window("today")

    activity_query = db.query(AuditLog).filter(
        AuditLog.created_at >= start,
        AuditLog.created_at <= end,
    )
    today_query = db.query(AuditLog).filter(
        AuditLog.created_at >= today_start,
        AuditLog.created_at <= today_end,
    )
    if merchant_id is not None:
        activity_query = activity_query.filter(AuditLog.merchant_id == merchant_id)
        today_query = today_query.filter(AuditLog.merchant_id == merchant_id)
    if role:
        activity_query = activity_query.filter(AuditLog.actor_role == role)
        today_query = today_query.filter(AuditLog.actor_role == role)
    activity_query = filter_activity_category(activity_query, category)
    today_query = filter_activity_category(today_query, category)

    user_query = db.query(User).filter(User.is_active.is_(True))
    if role and role != "system":
        user_query = user_query.filter(User.role == role)
    elif role == "system":
        user_query = user_query.filter(User.id.is_(None))
    if merchant_id is not None:
        user_query = user_query.filter(User.merchant_profile.has(id=merchant_id))

    active_users = user_query.filter(
        User.last_activity_at.isnot(None),
        User.last_activity_at >= now - timedelta(minutes=ACTIVE_USER_WINDOW_MINUTES),
    ).count()
    total_users = user_query.count()
    active_merchants = (
        db.query(User)
        .filter(
            User.is_active.is_(True),
            User.role == "merchant",
            User.last_activity_at.isnot(None),
            User.last_activity_at >= now - timedelta(minutes=ACTIVE_USER_WINDOW_MINUTES),
        )
        .count()
    )
    if merchant_id is not None:
        active_merchants = active_users if role in (None, "merchant") else 0

    distribution_query = (
        activity_query.with_entities(AuditLog.actor_role, func.count(AuditLog.id))
        .group_by(AuditLog.actor_role)
        .all()
    )
    distribution = {name: 0 for name in ("merchant", "analyst", "admin", "system")}
    distribution.update({str(item_role): int(count) for item_role, count in distribution_query})

    recent_logs = (
        activity_query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(recent_limit)
        .all()
    )
    top_query = (
        activity_query.filter(AuditLog.user_id.isnot(None))
        .with_entities(AuditLog.actor, AuditLog.actor_role, func.count(AuditLog.id).label("activity_count"))
        .group_by(AuditLog.actor, AuditLog.actor_role)
        .order_by(func.count(AuditLog.id).desc(), AuditLog.actor.asc())
        .limit(5)
        .all()
    )

    return {
        "period": period,
        "role": role,
        "category": category or "all",
        "window": {"start": start, "end": end},
        "active_window_minutes": ACTIVE_USER_WINDOW_MINUTES,
        "active_users": active_users,
        "activities_today": today_query.count(),
        "total_users": total_users,
        "active_merchants": active_merchants,
        "activity_by_role": distribution,
        "recent_activities": attach_payment_impacts(db, recent_logs),
        "top_users": [
            {"actor": actor, "role": actor_role, "activity_count": int(count)}
            for actor, actor_role, count in top_query
        ],
    }
