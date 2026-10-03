import csv
import io
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, merchant_scope_id, require_roles
from app.db.session import get_db
from app.models.alert import Alert
from app.models.qris import PaymentEvent
from app.models.user import User
from app.services.impact_dashboard import build_impact_dashboard
from app.services.subscriptions import plan_allows


router = APIRouter(prefix="/reports", tags=["Reports"])


def report_window(period: str):
    jakarta = ZoneInfo("Asia/Jakarta")
    now_local = datetime.now(jakarta)
    days = {"daily": 1, "weekly": 7, "monthly": 30}[period]
    start_local = now_local - timedelta(days=days)
    return (
        start_local.astimezone(timezone.utc).replace(tzinfo=None),
        now_local.astimezone(timezone.utc).replace(tzinfo=None),
    )


@router.get("/merchant-summary")
def merchant_summary(period: str = Query(default="daily", pattern="^(daily|weekly|monthly)$"), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    scope = merchant_scope_id(user, db)
    if scope and not plan_allows(user.merchant_profile.subscription_plan, "growth"):
        raise HTTPException(status_code=403, detail="Laporan lengkap tersedia mulai paket Growth.")
    if not scope: return {"detail": "Gunakan merchant_id pada laporan analyst"}
    start, end = report_window(period); query = db.query(PaymentEvent).filter(PaymentEvent.merchant_id == scope, PaymentEvent.transaction_time >= start, PaymentEvent.transaction_time <= end)
    total_value = float(query.with_entities(func.sum(PaymentEvent.amount)).scalar() or 0); risky_value = float(query.filter(PaymentEvent.risk_level == "high").with_entities(func.sum(PaymentEvent.amount)).scalar() or 0)
    return {"period": period, "start": start, "end": end, "payment_count": query.count(), "total_value": total_value, "verified_count": query.filter(PaymentEvent.risk_level == "low").count(), "review_count": query.filter(PaymentEvent.risk_level == "medium").count(), "high_risk_count": query.filter(PaymentEvent.risk_level == "high").count(), "alert_count": db.query(Alert).filter(Alert.merchant_id == scope, Alert.created_at >= start).count(), "risk_prevented_estimate": risky_value, "risk_prevented_note": "Estimasi nominal transaksi high-risk yang disarankan ditahan; bukan dana yang diblokir FinGraph."}


@router.get("/impact-dashboard")
def impact_dashboard(
    period: str = Query(default="30d", pattern="^(today|7d|30d|month|custom)$"),
    outlet_id: uuid.UUID | None = None,
    merchant_id: uuid.UUID | None = None,
    priority: str | None = Query(default=None, pattern="^(rendah|sedang|tinggi)$"),
    payment_status: str | None = Query(default=None, pattern="^(pending|success|failed|expired|reversed|refunded)$"),
    category: str | None = Query(default=None, max_length=80),
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scope = merchant_scope_id(user, db)
    if scope and not plan_allows(user.merchant_profile.subscription_plan, "growth"):
        raise HTTPException(status_code=403, detail="Laporan lengkap tersedia mulai paket Growth.")
    target_merchant = scope or merchant_id
    if target_merchant is None:
        raise HTTPException(status_code=422, detail="merchant_id wajib untuk laporan analyst/admin")
    return build_impact_dashboard(
        db,
        merchant_id=target_merchant,
        period=period,
        outlet_id=outlet_id,
        priority=priority,
        payment_status=payment_status,
        category=category,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.get("/payments.csv")
def export_payments(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(PaymentEvent); scope = merchant_scope_id(user, db)
    if scope and not plan_allows(user.merchant_profile.subscription_plan, "growth"):
        raise HTTPException(status_code=403, detail="Export laporan tersedia mulai paket Growth.")
    if scope: query = query.filter(PaymentEvent.merchant_id == scope)
    rows = query.order_by(PaymentEvent.transaction_time.desc()).limit(10000).all()
    stream = io.StringIO(); writer = csv.writer(stream); writer.writerow(["transaction_reference", "provider_reference", "amount", "currency", "payment_status", "risk_level", "fraud_score", "recommendation", "transaction_time"])
    for p in rows: writer.writerow([p.transaction_reference, p.provider_reference, float(p.amount), p.currency, p.payment_status, p.risk_level, p.fraud_score, p.recommendation, p.transaction_time.isoformat()])
    return StreamingResponse(iter([stream.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=fingraph-qris-payments.csv"})


@router.get("/investigation/{payment_id}")
def investigation_report(payment_id: str, user: User = Depends(require_roles("analyst", "admin")), db: Session = Depends(get_db)):
    payment = db.query(PaymentEvent).filter(PaymentEvent.id == payment_id).first()
    if not payment: return {"found": False}
    return {"found": True, "reference": payment.provider_reference, "merchant": payment.merchant.name, "payer_pseudonym": payment.payer_pseudonym, "scoring": payment.scoring_explanation, "alerts": [{"id": str(a.id), "status": a.status, "reason": a.reason} for a in payment.alerts], "labels": [{"label": l.label, "decision": l.merchant_decision, "created_at": l.created_at} for l in payment.labels]}
