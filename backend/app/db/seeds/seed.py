"""Deterministic, additive and idempotent FinGraph QRIS demo seed."""

import uuid
from datetime import date, datetime, timedelta

from app.core.security import hash_password, payload_fingerprint, pseudonymize_payer
from app.db.session import SessionLocal
from app.models.alert import Alert
from app.models.audit_log import AuditLog
from app.models.country import Country
from app.models.label import Label
from app.models.qris import FederatedNode, FederatedRound, MerchantProfile, Order, Outlet, PaymentEvent, QRISProfile, Settlement
from app.models.user import User
from app.services.federated import run_fedavg_round
from app.services.graph_sync import sync_payment_to_graph
from app.services.qris_scoring import score_payment


NOW = datetime(2026, 7, 14, 10, 0, 0)

MERCHANTS = [
    ("merchant@fingraph.id", "Pemilik Warung", "MRC-SARI-SOLO", "Warung Makan Sari Solo", "Kuliner", "Surakarta", "Jawa Tengah", "OUT-SARI-01", "Sari Solo - Pasar Gede", "NMID-DEMO-SARI-001"),
    ("batik@fingraph.id", "Pemilik Batik", "MRC-BATIK-LAW", "Batik Laweyan Sejahtera", "Fesyen", "Surakarta", "Jawa Tengah", "OUT-BATIK-01", "Batik Laweyan", "NMID-DEMO-BATIK-001"),
    ("kerajinan@fingraph.id", "Pemilik Kerajinan", "MRC-KLEWER-KRJ", "Kerajinan Pasar Klewer", "Kerajinan", "Surakarta", "Jawa Tengah", "OUT-KRJ-01", "Kios Klewer", "NMID-DEMO-KRJ-001"),
]

SCENARIOS = [
    "normal_payment", "fake_receipt", "amount_mismatch", "duplicate_reference", "delayed_callback",
    "repeated_failures", "suspicious_network", "cross_region", "cross_border", "merchant_qris_mismatch",
    "reversed_payment", "rapid_micro_transactions",
]

LOCATIONS = [
    ("Surakarta", "Jawa Tengah", "ID"), ("Sukoharjo", "Jawa Tengah", "ID"),
    ("Yogyakarta", "DI Yogyakarta", "ID"), ("Jakarta", "DKI Jakarta", "ID"),
    ("Bandung", "Jawa Barat", "ID"), ("Surabaya", "Jawa Timur", "ID"),
    ("Kuala Lumpur", "Wilayah Persekutuan", "MY"), ("Bangkok", "Bangkok", "TH"),
    ("Singapore", "Singapore", "SG"),
]


def upsert_user(db, email: str, full_name: str, role: str, institution: str | None = None):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, full_name=full_name, role=role, institution_name=institution, hashed_password=hash_password("password123"))
        db.add(user); db.flush()
    else:
        user.role = role; user.full_name = full_name
    return user


def seed_users_and_merchants(db):
    admin = upsert_user(db, "admin@fingraph.id", "Admin FinGraph QRIS", "admin", "FinGraph Lab")
    analyst = upsert_user(db, "analyst@fingraph.id", "Analyst FinGraph QRIS", "analyst", "FinGraph Lab")
    merchants = []
    for email, owner, code, name, business_type, city, province, outlet_code, outlet_name, nmid in MERCHANTS:
        user = upsert_user(db, email, owner, "merchant", name)
        plan = "premium" if code == "MRC-SARI-SOLO" else "growth" if code == "MRC-BATIK-LAW" else "basic"
        merchant = db.query(MerchantProfile).filter(MerchantProfile.merchant_code == code).first()
        if not merchant:
            merchant = MerchantProfile(user_id=user.id, merchant_code=code, name=name, business_type=business_type, owner_name=owner, phone="+62-000-0000", address="Alamat usaha demo, tanpa data pribadi nyata", city=city, province=province, country_code="ID", risk_level="low", status="active", subscription_plan=plan, subscription_status="active", plan_changed_at=NOW, created_at=NOW, updated_at=NOW)
            db.add(merchant); db.flush()
        else:
            merchant.subscription_plan = plan
            merchant.subscription_status = "active"
        outlet = db.query(Outlet).filter(Outlet.outlet_code == outlet_code).first()
        if not outlet:
            outlet = Outlet(merchant_id=merchant.id, outlet_code=outlet_code, name=outlet_name, address="Lokasi outlet demo", city=city, status="active", created_at=NOW, updated_at=NOW)
            db.add(outlet); db.flush()
        payload = f"FINGRAPH-DEMO|NMID={nmid}|OUTLET={outlet_code}|TYPE=MPM_DYNAMIC|ACQUIRER=TrustPay Sandbox"
        qris = db.query(QRISProfile).filter(QRISProfile.nmid == nmid).first()
        if not qris:
            qris = QRISProfile(merchant_id=merchant.id, outlet_id=outlet.id, nmid=nmid, qris_type="MPM_DYNAMIC", acquirer_name="TrustPay Sandbox", masked_settlement_account=f"****{1000 + len(merchants):04d}", payload_hash=payload_fingerprint(payload), status="active", last_verified_at=NOW, created_at=NOW, updated_at=NOW)
            db.add(qris); db.flush()
        merchants.append((merchant, outlet, qris, payload))
    return admin, analyst, merchants


def seed_countries(db):
    values = [("ID", "Indonesia", "Asia Tenggara"), ("MY", "Malaysia", "Asia Tenggara"), ("TH", "Thailand", "Asia Tenggara"), ("SG", "Singapura", "Asia Tenggara")]
    for code, name, region in values:
        if not db.query(Country).filter(Country.code == code).first(): db.add(Country(code=code, name=name, region=region, risk_level="low", risk_score=0.15))


def ensure_order(db, index: int, merchant: MerchantProfile, outlet: Outlet, amount: float, scenario: str | None):
    reference = f"ORD-DEMO-{index:03d}"
    order = db.query(Order).filter(Order.order_reference == reference).first()
    if not order:
        order = Order(order_reference=reference, merchant_id=merchant.id, outlet_id=outlet.id, expected_amount=amount, currency="IDR", description=f"Pesanan demo {scenario or 'reguler'}", customer_reference=pseudonymize_payer(f"customer-{index}"), status="awaiting_payment", expires_at=NOW + timedelta(days=30), created_at=NOW - timedelta(hours=index), updated_at=NOW)
        db.add(order); db.flush()
    return order


def seed_orders_payments(db, merchants):
    payments = []
    for index in range(1, 61):
        merchant, outlet, qris, _ = merchants[(index - 1) % len(merchants)]
        scenario = SCENARIOS[index - 1] if index <= len(SCENARIOS) else ("normal_payment" if index % 5 else "cross_region")
        expected = 1_500_000.0 if scenario == "amount_mismatch" else 25_000.0 if scenario == "rapid_micro_transactions" else float([75_000, 150_000, 350_000, 850_000][index % 4])
        order = ensure_order(db, index, merchant, outlet, expected, scenario)
        provider_reference = f"PJP-DEMO-{index:04d}"
        payment = db.query(PaymentEvent).filter(PaymentEvent.provider_reference == provider_reference).first()
        if payment:
            payments.append(payment); continue
        source_city, source_region, source_country = LOCATIONS[index % len(LOCATIONS)]
        if scenario == "cross_region": source_city, source_region, source_country = ("Yogyakarta", "DI Yogyakarta", "ID")
        if scenario == "cross_border": source_city, source_region, source_country = ("Kuala Lumpur", "Wilayah Persekutuan", "MY")
        amount = 150_000.0 if scenario == "amount_mismatch" else expected
        callback = scenario != "fake_receipt"
        status = "reversed" if scenario == "reversed_payment" else "success"
        payment = PaymentEvent(
            transaction_reference=f"QRIS-DEMO-{index:04d}", provider_reference=provider_reference, order_id=order.id,
            merchant_id=merchant.id, outlet_id=outlet.id, qris_profile_id=qris.id,
            payer_pseudonym=pseudonymize_payer("network-payer" if scenario == "suspicious_network" else f"payer-{index % 18}"),
            amount=amount, expected_amount=expected, currency="IDR", category=merchant.business_type, qris_type=qris.qris_type,
            acquirer_name=qris.acquirer_name, payment_status="pending" if scenario == "fake_receipt" else status,
            callback_received=callback, callback_received_at=(NOW - timedelta(minutes=index)) if callback else None,
            callback_delay_seconds=(settings_tolerance() + 180) if scenario == "delayed_callback" else 8,
            source_city=source_city, source_region=source_region, source_country=source_country,
            destination_city=merchant.city, destination_region=merchant.province, destination_country=merchant.country_code,
            is_cross_region=source_region != merchant.province, is_cross_border=source_country != merchant.country_code,
            raw_payload_hash=payload_fingerprint(f"seed-callback-{index}"), status="received", scenario_name=scenario,
            claimed_paid=True, signature_valid=True if callback else None, transaction_time=NOW - timedelta(minutes=index * 17),
            created_at=NOW - timedelta(minutes=index * 17, seconds=8), updated_at=NOW,
        )
        if scenario == "reversed_payment": order.status = "completed"
        db.add(payment); db.flush()
        context = {
            "duplicate_reference": scenario == "duplicate_reference", "failed_count_30m": 4 if scenario == "repeated_failures" else 0,
            "payment_count_10m": 12 if scenario == "rapid_micro_transactions" else 1,
            "merchant_mismatch": scenario == "merchant_qris_mismatch", "outlet_mismatch": scenario == "merchant_qris_mismatch", "qris_mismatch": scenario == "merchant_qris_mismatch",
        }
        result = score_payment(db, payment, context)
        order.status = "paid" if payment.payment_status == "success" and payment.risk_level == "low" else "held" if payment.risk_level in {"medium", "high"} else order.status
        if payment.fraud_score >= 0.40:
            db.add(Alert(merchant_id=merchant.id, payment_event_id=payment.id, alert_type="qris_risk", severity="critical" if payment.fraud_score >= 0.90 else "high" if payment.risk_level == "high" else "medium", risk_score=payment.fraud_score, reason="; ".join(result["reasons"]), recommendation=payment.recommendation, status="open" if index % 3 else "investigating", created_at=payment.transaction_time))
        if index <= 18:
            label_value = "fraud" if payment.risk_level == "high" else "legitimate" if payment.risk_level == "low" else "suspicious"
            decision = "report" if label_value == "fraud" else "approve" if label_value == "legitimate" else "verify"
            db.add(Label(payment_event_id=payment.id, merchant_id=merchant.id, label=label_value, merchant_decision=decision, labelled_by="seed@fingraph.id", notes="Label sintetis deterministik untuk demo adaptive learning.", created_at=payment.transaction_time + timedelta(minutes=2)))
        if payment.payment_status == "success" and payment.risk_level == "low" and index <= 30:
            fee = round(amount * 0.007, 2)
            db.add(Settlement(merchant_id=merchant.id, payment_event_id=payment.id, settlement_reference=f"STL-DEMO-{index:04d}", gross_amount=amount, fee_amount=fee, net_amount=amount-fee, settlement_status="settled", settlement_date=date(2026, 7, 14), created_at=NOW))
        payments.append(payment)
    return payments


def settings_tolerance():
    from app.core.config import settings
    return settings.QRIS_WEBHOOK_TOLERANCE_SECONDS


def seed_federated(db, merchants):
    names = ["UMKM Kuliner Solo", "UMKM Fesyen Solo", "UMKM Kerajinan Solo"]
    for index, name in enumerate(names):
        node = db.query(FederatedNode).filter(FederatedNode.node_name == name).first()
        if not node:
            db.add(FederatedNode(node_name=name, node_type="merchant_demo", merchant_id=merchants[index][0].id, status="online", sample_count=120 + index * 40, last_round=0, last_seen_at=NOW, created_at=NOW))
    db.flush()
    if not db.query(FederatedRound).first(): run_fedavg_round(db)


def seed_audit(db, admin, merchants):
    entity_id = "fingraph-qris-seed-v1"
    if not db.query(AuditLog).filter(AuditLog.action == "seed_qris_demo", AuditLog.entity_id == entity_id).first():
        db.add(AuditLog(actor=admin.email, actor_role=admin.role, action="seed_qris_demo", entity_type="system", entity_id=entity_id, description="Dataset FinGraph QRIS Mode Demo diinisialisasi secara idempotent.", user_id=admin.id, metadata_json={"contains_real_personal_data": False}, created_at=NOW))
    for merchant, _, _, _ in merchants:
        key = f"seed-{merchant.merchant_code}"
        if not db.query(AuditLog).filter(AuditLog.action == "seed_merchant_demo", AuditLog.entity_id == key).first(): db.add(AuditLog(actor="system", actor_role="system", action="seed_merchant_demo", entity_type="merchant", entity_id=key, merchant_id=merchant.id, description="Merchant sintetis dibuat untuk demo lokal.", created_at=NOW))


def run_seed():
    db = SessionLocal()
    try:
        admin, analyst, merchants = seed_users_and_merchants(db)
        seed_countries(db); db.flush()
        payments = seed_orders_payments(db, merchants)
        seed_federated(db, merchants); seed_audit(db, admin, merchants)
        db.commit()
        synced = 0
        from app.core.config import settings
        if settings.SEED_GRAPH_SYNC:
            for payment in payments:
                try: sync_payment_to_graph(payment); synced += 1
                except Exception: break
        print("[✓] FinGraph QRIS seed siap (idempotent).")
        print(f"    Merchant: {len(merchants)} | Order: {db.query(Order).count()} | Payment: {db.query(PaymentEvent).count()} | Graph synced: {synced}")
    except Exception:
        db.rollback(); raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
