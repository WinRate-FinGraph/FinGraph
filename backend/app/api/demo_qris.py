import hashlib
import logging
import time
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, merchant_scope_id
from app.core.config import settings
from app.core.security import canonical_json, payload_fingerprint, pseudonymize_payer, sign_pjp_payload, verify_pjp_signature
from app.db.session import get_db
from app.models.alert import Alert
from app.models.label import Label
from app.models.qris import MerchantProfile, Order, Outlet, PaymentEvent, QRISProfile
from app.models.user import User
from app.schemas.qris import OrderCreate, PaymentGenerateRequest
from app.services.audit import add_audit
from app.services.graph_sync import sync_payment_to_graph
from app.services.qris_scoring import score_payment
from app.services.qris_serializers import order_dict, payment_dict
from app.services.subscriptions import PLAN_CATALOG, normalize_plan


router = APIRouter(prefix="/demo/qris", tags=["Simulasi PJP QRIS"])
logger = logging.getLogger(__name__)

SCENARIOS = {
    "normal_payment": "Pembayaran sesuai dan callback valid; hasil risiko rendah.",
    "fake_receipt": "Klaim pembayaran tanpa callback resmi.",
    "amount_mismatch": "Pembayaran Rp150.000 untuk pesanan Rp1.500.000.",
    "duplicate_reference": "Upaya memakai ulang referensi penyedia.",
    "delayed_callback": "Callback datang lebih lambat dari batas normal.",
    "repeated_failures": "Beberapa percobaan gagal sebelum pembayaran berhasil.",
    "suspicious_network": "Payer pseudonym terhubung ke alert fraud sebelumnya.",
    "cross_region": "Pembayaran dari wilayah berbeda; bukan otomatis fraud.",
    "cross_border": "QRIS antarnegara simulasi untuk analisis lintas negara.",
    "merchant_qris_mismatch": "Identitas merchant/outlet/QR tidak cocok.",
    "reversed_payment": "Pembayaran dibalik setelah pesanan diproses.",
    "rapid_micro_transactions": "Banyak transaksi kecil dalam waktu singkat.",
}


def _resolve_order(db: Session, user: User, order_id) -> Order:
    query = db.query(Order).filter(Order.id == order_id)
    scope = merchant_scope_id(user, db)
    if scope:
        query = query.filter(Order.merchant_id == scope)
    order = query.first()
    if not order:
        raise HTTPException(status_code=404, detail="Pesanan tidak ditemukan atau bukan milik Anda")
    return order


def _make_payment(db: Session, order: Order, payload: PaymentGenerateRequest, scenario: str | None = None) -> PaymentEvent:
    merchant = order.merchant
    plan = PLAN_CATALOG[normalize_plan(merchant.subscription_plan)]
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_count = (
        db.query(PaymentEvent)
        .filter(
            PaymentEvent.merchant_id == order.merchant_id,
            PaymentEvent.transaction_time >= month_start,
        )
        .count()
    )
    if monthly_count >= plan["transaction_limit"]:
        raise HTTPException(
            status_code=409,
            detail=f"Limit {plan['transaction_limit']:,} transaksi per bulan untuk paket {plan['name']} telah tercapai.".replace(",", "."),
        )
    qris = db.query(QRISProfile).filter(QRISProfile.merchant_id == order.merchant_id, QRISProfile.outlet_id == order.outlet_id, QRISProfile.status == "active").first()
    if not qris:
        raise HTTPException(status_code=400, detail="Outlet belum memiliki profil QRIS aktif")
    provider_reference = payload.provider_reference or f"PJP-{uuid.uuid4().hex[:14].upper()}"
    if db.query(PaymentEvent).filter(PaymentEvent.provider_reference == provider_reference).first():
        raise HTTPException(status_code=409, detail="Provider reference sudah pernah digunakan")
    payment = PaymentEvent(
        transaction_reference=f"QRIS-{uuid.uuid4().hex[:14].upper()}", provider_reference=provider_reference,
        order_id=order.id, merchant_id=order.merchant_id, outlet_id=order.outlet_id, qris_profile_id=qris.id,
        payer_pseudonym=pseudonymize_payer(payload.payer_identifier), amount=payload.amount or float(order.expected_amount),
        expected_amount=order.expected_amount, currency=order.currency,
        category=order.merchant.business_type or "Umum", qris_type=qris.qris_type,
        acquirer_name=qris.acquirer_name, payment_status="pending", callback_received=False,
        source_city=payload.source_city, source_region=payload.source_region, source_country=payload.source_country.upper(),
        destination_city=order.outlet.city, destination_region=order.merchant.province,
        destination_country=order.merchant.country_code,
        is_cross_region=payload.source_region.lower() != order.merchant.province.lower(),
        is_cross_border=payload.source_country.upper() != order.merchant.country_code,
        raw_payload_hash=hashlib.sha256(b"pending").hexdigest(), scenario_name=scenario,
        transaction_time=datetime.utcnow(), recommendation="Menunggu konfirmasi penyedia pembayaran.",
    )
    db.add(payment); db.flush()
    return payment


def _callback_body(payment: PaymentEvent, status: str = "success") -> dict:
    return {
        "provider_reference": payment.provider_reference, "payment_status": status,
        "amount": float(payment.amount), "currency": payment.currency,
        "merchant_code": payment.merchant.merchant_code, "outlet_code": payment.outlet.outlet_code,
        "nmid": payment.qris_profile.nmid, "qr_fingerprint": payment.qris_profile.payload_hash,
        "timestamp": int(time.time()),
    }


def _create_alert_if_needed(db: Session, payment: PaymentEvent, result: dict):
    if payment.fraud_score < settings.QRIS_ALERT_MIN_SCORE:
        return None
    existing = db.query(Alert).filter(Alert.payment_event_id == payment.id, Alert.status.in_(["open", "investigating"])).first()
    if existing:
        existing.risk_score = payment.fraud_score
        existing.reason = "; ".join(result["reasons"])
        existing.recommendation = payment.recommendation
        return existing
    alert = Alert(
        merchant_id=payment.merchant_id, payment_event_id=payment.id, alert_type="qris_risk",
        severity="critical" if payment.fraud_score >= 0.90 else "high" if payment.risk_level == "high" else "medium",
        risk_score=payment.fraud_score, reason="; ".join(result["reasons"]), recommendation=payment.recommendation,
        status="open",
    )
    db.add(alert)
    return alert


@router.get("/scenarios")
def list_scenarios(user: User = Depends(get_current_user)):
    return {"demo_mode": True, "simulator": settings.PJP_SIMULATOR_NAME, "items": [{"name": name, "description": description} for name, description in SCENARIOS.items()]}


@router.post("/create-order", status_code=201)
def demo_create_order(
    payload: OrderCreate,
    merchant_id: uuid.UUID | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scope = merchant_scope_id(user, db)
    target_id = scope or (merchant_id if user.role == "admin" else None)
    if not target_id:
        raise HTTPException(status_code=403, detail="Pilih merchant demo sebagai admin atau gunakan akun merchant")
    outlet = db.query(Outlet).filter(Outlet.id == payload.outlet_id, Outlet.merchant_id == target_id).first()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet bukan milik merchant")
    data = payload.model_dump(); customer = data.pop("customer_reference", None)
    order = Order(order_reference=f"ORD-{uuid.uuid4().hex[:12].upper()}", merchant_id=target_id, status="awaiting_payment", customer_reference=pseudonymize_payer(customer) if customer else None, **data)
    db.add(order); db.flush()
    add_audit(db, action="demo_create_order", entity_type="order", entity_id=str(order.id), description="Pesanan dibuat melalui Simulasi PJP.", user=user, merchant_id=target_id)
    db.commit(); db.refresh(order)
    return order_dict(order)


@router.post("/generate-payment", status_code=201)
def generate_payment(payload: PaymentGenerateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = _resolve_order(db, user, payload.order_id)
    payment = _make_payment(db, order, payload)
    callback = _callback_body(payment, payload.payment_status)
    add_audit(db, action="generate_demo_payment", entity_type="payment_event", entity_id=str(payment.id), description="Payment pending dibuat oleh Simulasi PJP; belum dianggap lunas sebelum webhook.", user=user, merchant_id=order.merchant_id)
    db.commit(); db.refresh(payment)
    try:
        signature = sign_pjp_payload(callback)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"payment": payment_dict(payment, detailed=True), "webhook": {"url": "/api/v1/demo/qris/webhook", "payload": callback, "signature": signature, "signature_header": "X-PJP-Signature"}, "demo_notice": "Payment ini berasal dari Simulasi PJP."}


@router.post("/webhook")
def pjp_webhook(
    payload: dict = Body(...), x_pjp_signature: str = Header(..., alias="X-PJP-Signature"),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    provider_reference = str(payload.get("provider_reference", ""))
    payment = db.query(PaymentEvent).filter(PaymentEvent.provider_reference == provider_reference).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Provider reference tidak dikenal")
    scope = merchant_scope_id(user, db)
    if scope and payment.merchant_id != scope:
        raise HTTPException(status_code=404, detail="Provider reference tidak dikenal")
    if not verify_pjp_signature(payload, x_pjp_signature):
        add_audit(db, action="reject_invalid_webhook_signature", entity_type="payment_event", entity_id=str(payment.id), description="Webhook ditolak karena signature HMAC tidak valid.", user=user, merchant_id=payment.merchant_id)
        db.commit()
        raise HTTPException(status_code=401, detail="Signature webhook tidak valid")
    try:
        callback_timestamp = int(payload["timestamp"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Timestamp callback wajib berupa Unix timestamp")
    age = abs(int(time.time()) - callback_timestamp)
    if age > settings.QRIS_WEBHOOK_TOLERANCE_SECONDS:
        payment.replay_detected = True
        add_audit(db, action="reject_replayed_webhook", entity_type="payment_event", entity_id=str(payment.id), description="Webhook ditolak karena melewati toleransi timestamp.", user=user, merchant_id=payment.merchant_id, metadata={"age_seconds": age})
        db.commit()
        raise HTTPException(status_code=408, detail="Webhook kedaluwarsa atau terindikasi replay")
    body_hash = hashlib.sha256(canonical_json(payload)).hexdigest()
    if payment.callback_received:
        if payment.raw_payload_hash == body_hash:
            return {"message": "Callback sudah diproses", "idempotent": True, "payment": payment_dict(payment, detailed=True)}
        raise HTTPException(status_code=409, detail="Callback berbeda untuk provider reference yang sudah diproses")
    required = {"payment_status", "amount", "merchant_code", "outlet_code", "nmid", "qr_fingerprint"}
    missing = sorted(required - payload.keys())
    if missing:
        raise HTTPException(status_code=422, detail=f"Field callback kurang: {', '.join(missing)}")
    now = datetime.utcnow()
    payment.callback_received = True; payment.callback_received_at = now
    payment.callback_delay_seconds = max(0, int((now - payment.created_at).total_seconds()))
    payment.signature_valid = True; payment.raw_payload_hash = body_hash
    payment.payment_status = str(payload["payment_status"]); payment.amount = float(payload["amount"])
    payment.claimed_paid = payment.payment_status == "success"
    context = {
        "merchant_mismatch": payload["merchant_code"] != payment.merchant.merchant_code,
        "outlet_mismatch": payload["outlet_code"] != payment.outlet.outlet_code,
        "qris_mismatch": payload["nmid"] != payment.qris_profile.nmid or payload["qr_fingerprint"] != payment.qris_profile.payload_hash,
    }
    result = score_payment(db, payment, context)
    if payment.order:
        payment.order.status = "paid" if payment.payment_status == "success" and payment.risk_level == "low" else "held" if payment.risk_level in {"medium", "high"} else payment.order.status
    alert = _create_alert_if_needed(db, payment, result)
    add_audit(db, action="process_pjp_webhook", entity_type="payment_event", entity_id=str(payment.id), description=f"Webhook valid diproses dengan risiko {payment.risk_level}.", user=user, merchant_id=payment.merchant_id, metadata={"alert_created": bool(alert), "risk_score": payment.fraud_score})
    db.commit(); db.refresh(payment)
    try:
        sync_payment_to_graph(payment)
    except Exception:
        logger.exception("Graph sync failed after processing payment %s", payment.id)
    return {"message": "Callback diproses", "idempotent": False, "payment": payment_dict(payment, detailed=True), "alert_created": bool(alert)}


@router.get("/status/{provider_reference}")
def demo_payment_status(provider_reference: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(PaymentEvent).filter(PaymentEvent.provider_reference == provider_reference)
    scope = merchant_scope_id(user, db)
    if scope: query = query.filter(PaymentEvent.merchant_id == scope)
    payment = query.first()
    if not payment: raise HTTPException(status_code=404, detail="Pembayaran tidak ditemukan")
    return {"simulator": settings.PJP_SIMULATOR_NAME, "demo_mode": True, "payment": payment_dict(payment, detailed=True)}


@router.post("/scenarios/{scenario_name}", status_code=201)
def run_scenario(
    scenario_name: str, merchant_id: uuid.UUID | None = Query(default=None),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    if scenario_name not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Skenario tidak dikenal")
    scope = merchant_scope_id(user, db)
    target_id = scope or merchant_id
    if not target_id:
        merchant = db.query(MerchantProfile).order_by(MerchantProfile.created_at.asc()).first()
    else:
        merchant = db.query(MerchantProfile).filter(MerchantProfile.id == target_id).first()
    if not merchant: raise HTTPException(status_code=404, detail="Merchant demo tidak ditemukan")
    outlet = db.query(Outlet).filter(Outlet.merchant_id == merchant.id).first()
    qris = db.query(QRISProfile).filter(QRISProfile.merchant_id == merchant.id, QRISProfile.outlet_id == outlet.id).first() if outlet else None
    if not outlet or not qris: raise HTTPException(status_code=400, detail="Merchant demo belum memiliki outlet dan QRIS")
    expected = 1_500_000.0 if scenario_name == "amount_mismatch" else 25_000.0 if scenario_name == "rapid_micro_transactions" else 350_000.0
    order = Order(order_reference=f"ORD-SCN-{uuid.uuid4().hex[:10].upper()}", merchant_id=merchant.id, outlet_id=outlet.id, expected_amount=expected, currency="IDR", description=f"Skenario {scenario_name}", status="awaiting_payment")
    db.add(order); db.flush()
    source = {"cross_region": ("Yogyakarta", "DI Yogyakarta", "ID"), "cross_border": ("Kuala Lumpur", "Wilayah Persekutuan", "MY")}.get(scenario_name, (merchant.city, merchant.province, "ID"))
    amount = 150_000.0 if scenario_name == "amount_mismatch" else expected
    request = PaymentGenerateRequest(order_id=order.id, amount=amount, payer_identifier="network-payer" if scenario_name == "suspicious_network" else f"payer-{scenario_name}", source_city=source[0], source_region=source[1], source_country=source[2])
    payment = _make_payment(db, order, request, scenario_name)
    context: dict = {}
    if scenario_name == "fake_receipt":
        payment.claimed_paid = True; payment.payment_status = "pending"
    else:
        payment.callback_received = True; payment.callback_received_at = datetime.utcnow(); payment.signature_valid = True
        payment.payment_status = "reversed" if scenario_name == "reversed_payment" else "success"; payment.claimed_paid = True
    if scenario_name == "duplicate_reference": context["duplicate_reference"] = True
    if scenario_name == "delayed_callback": payment.callback_delay_seconds = settings.QRIS_WEBHOOK_TOLERANCE_SECONDS + 180
    if scenario_name == "repeated_failures": context["failed_count_30m"] = 4
    if scenario_name == "rapid_micro_transactions": context["payment_count_10m"] = 12
    if scenario_name == "merchant_qris_mismatch": context.update(merchant_mismatch=True, outlet_mismatch=True, qris_mismatch=True)
    if scenario_name == "reversed_payment": order.status = "completed"
    if scenario_name == "suspicious_network":
        payment.scenario_name = "suspicious_network"
    result = score_payment(db, payment, context)
    if scenario_name == "cross_region" and payment.risk_level == "high":
        raise RuntimeError("Invariant scoring gagal: cross-region saja tidak boleh high")
    order.status = "paid" if payment.payment_status == "success" and payment.risk_level == "low" else "held" if payment.risk_level in {"medium", "high"} else order.status
    alert = _create_alert_if_needed(db, payment, result)
    add_audit(db, action="run_qris_demo_scenario", entity_type="payment_event", entity_id=str(payment.id), description=f"Skenario {scenario_name} dijalankan dalam Mode Demo.", user=user, merchant_id=merchant.id)
    db.commit(); db.refresh(payment)
    try:
        sync_payment_to_graph(payment)
    except Exception:
        logger.exception("Graph sync failed after running scenario for payment %s", payment.id)
    return {"scenario": scenario_name, "description": SCENARIOS[scenario_name], "payment": payment_dict(payment, detailed=True), "alert_created": bool(alert), "demo_mode": True}
