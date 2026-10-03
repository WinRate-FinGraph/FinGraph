import uuid
from datetime import date, datetime, timedelta

from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.qris import MerchantProfile, PaymentEvent
from app.models.user import User
from app.services.activity_monitoring import activity_monitoring_payload
from app.services.impact_dashboard import build_impact_dashboard
from app.api.public import build_public_trust_summary


def test_activity_distribution_uses_role_snapshot_and_period():
    db = SessionLocal()
    marker = uuid.uuid4().hex
    now = datetime.utcnow()
    merchant = db.query(User).filter(User.role == "merchant").first()
    original_role = merchant.role
    try:
        merchant.last_activity_at = now
        db.add_all(
            [
                AuditLog(actor=f"{marker}@merchant", actor_role="merchant", action="test_recent", entity_type="test", user_id=merchant.id, created_at=now),
                AuditLog(actor=f"{marker}@analyst", actor_role="analyst", action="test_recent", entity_type="test", created_at=now),
                AuditLog(actor=f"{marker}@merchant", actor_role="merchant", action="test_old", entity_type="test", created_at=now - timedelta(days=10)),
            ]
        )
        db.flush()

        today = activity_monitoring_payload(db, period="today")
        thirty = activity_monitoring_payload(db, period="30d")
        merchant_today = activity_monitoring_payload(db, period="today", role="merchant")
        assert today["activity_by_role"]["merchant"] >= 1
        assert today["activity_by_role"]["analyst"] >= 1
        assert thirty["activity_by_role"]["merchant"] > today["activity_by_role"]["merchant"]
        assert merchant_today["activity_by_role"]["analyst"] == 0
        assert merchant_today["active_users"] >= 1

        merchant.role = "analyst"
        db.flush()
        snapshot = db.query(AuditLog).filter(AuditLog.actor == f"{marker}@merchant").first()
        assert snapshot.actor_role == "merchant"
    finally:
        merchant.role = original_role
        db.rollback()
        db.close()


def test_impact_summary_counts_more_than_one_hundred_rows_without_load_cap():
    db = SessionLocal()
    merchant = db.query(MerchantProfile).first()
    template = db.query(PaymentEvent).filter(PaymentEvent.merchant_id == merchant.id).first()
    created = []
    try:
        for index in range(105):
            item = PaymentEvent(
                transaction_reference=f"TEST-IMPACT-{uuid.uuid4().hex}",
                provider_reference=f"TEST-PJP-{uuid.uuid4().hex}",
                order_id=template.order_id,
                merchant_id=template.merchant_id,
                outlet_id=template.outlet_id,
                qris_profile_id=template.qris_profile_id,
                payer_pseudonym=template.payer_pseudonym,
                amount=1000,
                expected_amount=1000,
                currency="IDR",
                payment_method="QRIS",
                category="Pengujian",
                priority="tinggi" if index % 2 else "rendah",
                qris_type=template.qris_type,
                acquirer_name=template.acquirer_name,
                payment_status="success",
                callback_received=True,
                source_country="ID",
                destination_city=template.destination_city,
                destination_region=template.destination_region,
                destination_country="ID",
                is_cross_region=False,
                is_cross_border=False,
                raw_payload_hash=uuid.uuid4().hex * 2,
                status="received",
                fraud_score=0.8 if index % 2 else 0.1,
                risk_level="high" if index % 2 else "low",
                recommendation_code="HOLD" if index % 2 else "APPROVE",
                transaction_time=datetime(2026, 7, 15, 12, 0) + timedelta(seconds=index),
            )
            db.add(item)
            created.append(item)
        db.flush()
        expected = (
            db.query(PaymentEvent)
            .filter(
                PaymentEvent.merchant_id == merchant.id,
                PaymentEvent.transaction_time >= datetime(2026, 7, 1),
                PaymentEvent.transaction_time <= datetime(2026, 7, 31, 23, 59, 59),
            )
            .count()
        )
        result = build_impact_dashboard(
            db,
            merchant_id=merchant.id,
            period="custom",
            date_from=date(2026, 7, 1),
            date_to=date(2026, 7, 31),
            limit=20,
        )
        assert result["metrics"]["payment_count"] == expected
        assert result["metrics"]["payment_count"] > 100
        assert len(result["items"]) == 20
    finally:
        db.rollback()
        db.close()


def test_public_trust_summary_uses_real_anonymous_database_aggregates():
    db = SessionLocal()
    try:
        result = build_public_trust_summary(db)
        assert result["registered_users"] == db.query(User).filter(User.is_active.is_(True)).count()
        assert result["active_merchants"] == db.query(MerchantProfile).filter(MerchantProfile.status == "active").count()
        assert result["payments_checked"] == db.query(PaymentEvent).count()
        assert result["verified_payments"] <= result["payments_checked"]
        assert 0 <= result["verification_rate"] <= 100
        assert result["activity_window_minutes"] == 15
        assert result["data_scope"] in {"Mode Demo", "Data aplikasi"}
        assert result["updated_at"].tzinfo is not None
    finally:
        db.close()
