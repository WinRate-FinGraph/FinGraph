import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, merchant_scope_id, require_roles
from app.db.session import get_db
from app.models.alert import Alert
from app.models.qris import Order, PaymentEvent
from app.models.user import User
from app.schemas.qris import PaymentCheckRequest
from app.services.audit import add_audit
from app.services.qris_scoring import score_payment
from app.services.qris_serializers import payment_dict
from app.core.config import settings
from app.api.pagination import page_response


router = APIRouter(prefix="/payments", tags=["QRIS Payments"])


def scoped_payment(db: Session, user: User, payment_id=None, provider_reference=None) -> PaymentEvent:
    query = db.query(PaymentEvent)
    if payment_id:
        query = query.filter(PaymentEvent.id == payment_id)
    if provider_reference:
        query = query.filter(PaymentEvent.provider_reference == provider_reference)
    scope = merchant_scope_id(user, db)
    if scope:
        query = query.filter(PaymentEvent.merchant_id == scope)
    payment = query.first()
    if not payment:
        raise HTTPException(status_code=404, detail="Pembayaran tidak ditemukan")
    return payment


@router.get("")
def list_payments(
    limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0),
    risk_level: str | None = Query(default=None, pattern="^(low|medium|high)$"),
    priority: str | None = Query(default=None, pattern="^(rendah|sedang|tinggi)$"),
    category: str | None = Query(default=None, max_length=80),
    payment_status: str | None = None, merchant_id: uuid.UUID | None = None,
    outlet_id: uuid.UUID | None = None, search: str | None = Query(default=None, max_length=120),
    date_from: datetime | None = None, date_to: datetime | None = None,
    ordering: str = Query(default="newest", pattern="^(newest|oldest|risk_desc|amount_desc)$"),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    query = db.query(PaymentEvent)
    scope = merchant_scope_id(user, db)
    if scope:
        query = query.filter(PaymentEvent.merchant_id == scope)
    elif merchant_id:
        query = query.filter(PaymentEvent.merchant_id == merchant_id)
    if risk_level:
        query = query.filter(PaymentEvent.risk_level == risk_level)
    if priority:
        query = query.filter(PaymentEvent.priority == priority)
    if category:
        query = query.filter(PaymentEvent.category == category)
    if payment_status:
        query = query.filter(PaymentEvent.payment_status == payment_status)
    if outlet_id:
        query = query.filter(PaymentEvent.outlet_id == outlet_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            PaymentEvent.provider_reference.ilike(pattern)
            | PaymentEvent.transaction_reference.ilike(pattern)
            | PaymentEvent.payer_pseudonym.ilike(pattern)
            | PaymentEvent.order.has(Order.order_reference.ilike(pattern))
        )
    if date_from:
        query = query.filter(PaymentEvent.transaction_time >= date_from)
    if date_to:
        query = query.filter(PaymentEvent.transaction_time <= date_to)
    total = query.count()
    order_columns = {
        "newest": (PaymentEvent.transaction_time.desc(), PaymentEvent.id.desc()),
        "oldest": (PaymentEvent.transaction_time.asc(), PaymentEvent.id.asc()),
        "risk_desc": (PaymentEvent.fraud_score.desc(), PaymentEvent.transaction_time.desc(), PaymentEvent.id.desc()),
        "amount_desc": (PaymentEvent.amount.desc(), PaymentEvent.transaction_time.desc(), PaymentEvent.id.desc()),
    }[ordering]
    items = query.order_by(*order_columns).offset(offset).limit(limit).all()
    return page_response(total=total, limit=limit, offset=offset, items=[payment_dict(item) for item in items])


@router.post("/check")
def check_payment(payload: PaymentCheckRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    scope = merchant_scope_id(user, db)
    query = db.query(PaymentEvent).filter(PaymentEvent.provider_reference == payload.provider_reference)
    if scope:
        query = query.filter(PaymentEvent.merchant_id == scope)
    payment = query.first()
    if not payment:
        add_audit(db, action="check_payment_not_found", entity_type="payment_event", entity_id=None, description="Reference pembayaran tidak ditemukan pada simulator.", user=user, merchant_id=scope, metadata={"reference_suffix": payload.provider_reference[-6:]})
        db.commit()
        return {
            "found": False, "provider_status": "not_found", "amount_match": False,
            "risk_result": {
                "final_score": 0.95,
                "confidence_score": 0.98,
                "confidence_basis": "critical_rule_confirmation",
                "analysis_mode": "rule_graph_fallback",
                "risk_level": "high",
                "recommendation_code": "DO_NOT_RELEASE_GOODS",
                "recommendation": "Jangan serahkan barang. Pembayaran belum dapat diverifikasi.",
                "reasons": ["Konfirmasi resmi dari simulator PJP tidak ditemukan."],
            },
            "demo_notice": "Status berasal dari Simulasi PJP, bukan jaringan QRIS nyata.",
        }
    amount_match = abs(float(payment.amount) - payload.amount) < 1
    order_match = payload.order_reference is None or (payment.order and payment.order.order_reference == payload.order_reference)
    serialized = payment_dict(payment, detailed=True)
    risk_result = dict(serialized["scoring"])
    check_reasons = list(risk_result.get("reasons", []))
    check_codes = list(risk_result.get("explanation_codes", []))
    if not amount_match:
        check_codes.append("AMOUNT_MISMATCH")
        check_reasons.append(
            f"Nominal yang diperiksa Rp{payload.amount:,.0f} tidak sesuai dengan catatan PJP Rp{float(payment.amount):,.0f}."
        )
    if not order_match:
        check_codes.append("ORDER_MISMATCH")
        check_reasons.append("Referensi pesanan tidak sesuai dengan catatan pembayaran.")
    if not amount_match or not order_match:
        risk_result.update(
            final_score=max(float(risk_result.get("final_score", 0)), 0.95),
            risk_level="high",
            recommendation_code="DO_NOT_RELEASE_GOODS",
            recommendation="Jangan serahkan barang. Fakta pembayaran yang diperiksa tidak sesuai.",
            reasons=check_reasons,
            explanation_codes=check_codes,
            critical_rule_floor=max(float(risk_result.get("critical_rule_floor", 0)), 0.95),
        )
    return {"found": True, "provider_status": payment.payment_status, "amount_match": amount_match, "order_match": order_match, "payment": serialized, "risk_result": risk_result, "demo_notice": "Status berasal dari Simulasi PJP, bukan jaringan QRIS nyata."}


@router.get("/status/{provider_reference}")
def verification_status(provider_reference: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    payment = scoped_payment(db, user, provider_reference=provider_reference)
    return {"provider_reference": payment.provider_reference, "payment_status": payment.payment_status, "callback_received": payment.callback_received, "risk_level": payment.risk_level, "recommendation": payment.recommendation, "demo_mode": settings.demo_mode}


@router.get("/{payment_id}")
def payment_detail(payment_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return payment_dict(scoped_payment(db, user, payment_id=payment_id), detailed=True)


@router.get("/{payment_id}/explanation")
def payment_explanation(payment_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    payment = scoped_payment(db, user, payment_id=payment_id)
    return payment.scoring_explanation or {"message": "Penjelasan belum tersedia", "fallback": "rule_guard"}


@router.post("/{payment_id}/rescore")
def rescore_payment(payment_id: uuid.UUID, user: User = Depends(require_roles("analyst", "admin")), db: Session = Depends(get_db)):
    payment = scoped_payment(db, user, payment_id=payment_id)
    result = score_payment(db, payment)
    if payment.fraud_score >= 0.40 and not db.query(Alert).filter(Alert.payment_event_id == payment.id, Alert.status.in_(["open", "investigating"])).first():
        db.add(Alert(merchant_id=payment.merchant_id, payment_event_id=payment.id, alert_type="qris_risk", severity="high" if payment.risk_level == "high" else "medium", risk_score=payment.fraud_score, reason="; ".join(result["reasons"]), recommendation=payment.recommendation, status="open"))
    add_audit(db, action="rescore_payment", entity_type="payment_event", entity_id=str(payment.id), description="Pembayaran dihitung ulang oleh analyst/admin.", user=user, merchant_id=payment.merchant_id)
    db.commit(); db.refresh(payment)
    return payment_dict(payment, detailed=True)
