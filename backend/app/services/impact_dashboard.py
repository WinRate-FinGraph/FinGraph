from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.qris import Outlet, PaymentEvent
from app.services.qris_serializers import payment_dict


VALID_IMPACT_PERIODS = {"today", "7d", "30d", "month", "custom"}
VALID_PRIORITIES = {"rendah", "sedang", "tinggi"}


def impact_window(
    period: str,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[datetime, datetime]:
    jakarta = ZoneInfo("Asia/Jakarta")
    now_local = datetime.now(jakarta)
    if period == "today":
        start_date = now_local.date()
        end_date = start_date
    elif period == "7d":
        end_date = now_local.date()
        start_date = end_date - timedelta(days=6)
    elif period == "30d":
        end_date = now_local.date()
        start_date = end_date - timedelta(days=29)
    elif period == "month":
        end_date = now_local.date()
        start_date = end_date.replace(day=1)
    elif period == "custom":
        if date_from is None or date_to is None:
            raise HTTPException(status_code=422, detail="date_from dan date_to wajib untuk periode custom")
        if date_from > date_to:
            raise HTTPException(status_code=422, detail="date_from tidak boleh setelah date_to")
        if date_to - date_from > timedelta(days=366):
            raise HTTPException(status_code=422, detail="Rentang laporan maksimal 366 hari")
        start_date, end_date = date_from, date_to
    else:
        raise HTTPException(status_code=422, detail="Periode laporan tidak valid")
    return (
        datetime.combine(start_date, time.min, tzinfo=jakarta).astimezone(timezone.utc).replace(tzinfo=None),
        datetime.combine(end_date, time.max, tzinfo=jakarta).astimezone(timezone.utc).replace(tzinfo=None),
    )


def build_impact_dashboard(
    db: Session,
    *,
    merchant_id,
    period: str,
    outlet_id=None,
    priority: str | None = None,
    payment_status: str | None = None,
    category: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    if priority and priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=422, detail="Prioritas tidak valid")
    start, end = impact_window(period, date_from, date_to)
    query = db.query(PaymentEvent).filter(
        PaymentEvent.merchant_id == merchant_id,
        PaymentEvent.transaction_time >= start,
        PaymentEvent.transaction_time <= end,
    )
    if outlet_id:
        query = query.filter(PaymentEvent.outlet_id == outlet_id)
    if priority:
        query = query.filter(PaymentEvent.priority == priority)
    if payment_status:
        query = query.filter(PaymentEvent.payment_status == payment_status)
    if category:
        query = query.filter(PaymentEvent.category == category)

    total = query.count()
    total_value = float(query.with_entities(func.sum(PaymentEvent.amount)).scalar() or 0)
    success_count = query.filter(PaymentEvent.payment_status == "success").count()
    verified_count = query.filter(
        PaymentEvent.payment_status == "success",
        PaymentEvent.priority == "rendah",
    ).count()
    review_count = query.filter(PaymentEvent.priority == "sedang").count()
    held_count = query.filter(PaymentEvent.priority == "tinggi").count()
    hold_value = float(
        query.filter(PaymentEvent.priority == "tinggi")
        .with_entities(func.sum(PaymentEvent.amount))
        .scalar()
        or 0
    )

    daily_rows = (
        query.with_entities(
            func.date(PaymentEvent.transaction_time).label("day"),
            func.count(PaymentEvent.id).label("payment_count"),
            func.sum(PaymentEvent.amount).label("transaction_value"),
        )
        .group_by(func.date(PaymentEvent.transaction_time))
        .order_by(func.date(PaymentEvent.transaction_time))
        .all()
    )
    priority_rows = (
        query.with_entities(PaymentEvent.priority, func.count(PaymentEvent.id))
        .group_by(PaymentEvent.priority)
        .all()
    )
    priority_distribution = {"rendah": 0, "sedang": 0, "tinggi": 0}
    priority_distribution.update({str(name): int(count) for name, count in priority_rows})

    top_outlet = (
        query.join(Outlet, PaymentEvent.outlet_id == Outlet.id)
        .with_entities(Outlet.name, func.sum(PaymentEvent.amount).label("value"))
        .group_by(Outlet.id, Outlet.name)
        .order_by(func.sum(PaymentEvent.amount).desc())
        .first()
    )
    resolved_alerts = (
        db.query(Alert)
        .filter(
            Alert.merchant_id == merchant_id,
            Alert.created_at >= start,
            Alert.created_at <= end,
            Alert.status.in_(["resolved", "dismissed"]),
        )
        .count()
    )

    priority_order = case(
        (PaymentEvent.priority == "tinggi", 3),
        (PaymentEvent.priority == "sedang", 2),
        else_=1,
    )
    detail_items = (
        query.order_by(priority_order.desc(), PaymentEvent.transaction_time.desc(), PaymentEvent.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    risk_items = (
        query.filter(PaymentEvent.priority.in_(["sedang", "tinggi"]))
        .order_by(priority_order.desc(), PaymentEvent.transaction_time.desc())
        .limit(5)
        .all()
    )

    categories = [
        row[0]
        for row in query.with_entities(PaymentEvent.category)
        .distinct()
        .order_by(PaymentEvent.category)
        .all()
    ]
    return {
        "period": period,
        "filters": {
            "outlet_id": str(outlet_id) if outlet_id else None,
            "priority": priority,
            "payment_status": payment_status,
            "category": category,
        },
        "window": {"start": start, "end": end},
        "metrics": {
            "payment_count": total,
            "transaction_value": total_value,
            "successful_count": success_count,
            "verified_count": verified_count,
            "review_count": review_count,
            "held_count": held_count,
            "verified_percent": round((verified_count / total) * 100) if total else 0,
            "recommended_hold_value": hold_value,
        },
        "timeline": [
            {
                "date": str(day),
                "payment_count": int(payment_count),
                "transaction_value": float(transaction_value or 0),
            }
            for day, payment_count, transaction_value in daily_rows
        ],
        "priority_distribution": priority_distribution,
        "insights": {
            "top_outlet": top_outlet[0] if top_outlet else None,
            "top_outlet_value": float(top_outlet[1]) if top_outlet else 0,
            "resolved_alerts": resolved_alerts,
        },
        "available_categories": categories,
        "items": [payment_dict(item) for item in detail_items],
        "risk_items": [payment_dict(item) for item in risk_items],
        "total": total,
        "limit": limit,
        "offset": offset,
        "page": (offset // limit) + 1,
        "total_pages": (total + limit - 1) // limit if total else 0,
    }
