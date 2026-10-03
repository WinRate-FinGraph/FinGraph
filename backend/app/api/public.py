from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.qris import MerchantProfile, Outlet, PaymentEvent
from app.models.user import User


router = APIRouter(prefix="/public", tags=["Public"])

ACTIVE_WINDOW_MINUTES = 15


def build_public_trust_summary(db: Session) -> dict:
    """Return anonymous, database-backed product adoption aggregates."""

    now = datetime.now(timezone.utc)
    active_since = now.replace(tzinfo=None) - timedelta(minutes=ACTIVE_WINDOW_MINUTES)

    registered_users = (
        db.query(func.count(User.id))
        .filter(User.is_active.is_(True))
        .scalar()
        or 0
    )
    active_users = (
        db.query(func.count(User.id))
        .filter(
            User.is_active.is_(True),
            User.last_activity_at.is_not(None),
            User.last_activity_at >= active_since,
        )
        .scalar()
        or 0
    )
    active_merchants = (
        db.query(func.count(MerchantProfile.id))
        .filter(MerchantProfile.status == "active")
        .scalar()
        or 0
    )
    active_outlets = (
        db.query(func.count(Outlet.id))
        .filter(Outlet.status == "active")
        .scalar()
        or 0
    )
    payment_totals = (
        db.query(
            func.count(PaymentEvent.id).label("total"),
            func.sum(
                case(
                    (
                        (PaymentEvent.payment_status == "success")
                        & (PaymentEvent.risk_level == "low"),
                        1,
                    ),
                    else_=0,
                )
            ).label("verified"),
        )
        .one()
    )
    payments_checked = int(payment_totals.total or 0)
    verified_payments = int(payment_totals.verified or 0)
    verification_rate = (
        round((verified_payments / payments_checked) * 100, 1)
        if payments_checked
        else 0.0
    )

    return {
        "registered_users": int(registered_users),
        "active_users": int(active_users),
        "active_merchants": int(active_merchants),
        "active_outlets": int(active_outlets),
        "payments_checked": payments_checked,
        "verified_payments": verified_payments,
        "verification_rate": verification_rate,
        "activity_window_minutes": ACTIVE_WINDOW_MINUTES,
        "updated_at": now,
        "data_scope": "Mode Demo" if settings.demo_mode else "Data aplikasi",
    }


@router.get("/trust-summary")
def public_trust_summary(db: Session = Depends(get_db)):
    return build_public_trust_summary(db)
