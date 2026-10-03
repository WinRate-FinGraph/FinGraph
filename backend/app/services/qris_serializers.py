from app.models.alert import Alert
from app.models.qris import MerchantProfile, Order, Outlet, PaymentEvent, QRISProfile
from app.services.qris_scoring import analysis_confidence


def merchant_dict(merchant: MerchantProfile) -> dict:
    return {
        "id": str(merchant.id), "merchant_code": merchant.merchant_code, "name": merchant.name,
        "business_type": merchant.business_type, "owner_name": merchant.owner_name, "phone": merchant.phone,
        "address": merchant.address, "city": merchant.city, "province": merchant.province,
        "country_code": merchant.country_code, "risk_level": merchant.risk_level, "status": merchant.status,
        "subscription_plan": merchant.subscription_plan, "subscription_status": merchant.subscription_status,
        "plan_changed_at": merchant.plan_changed_at,
        "created_at": merchant.created_at, "updated_at": merchant.updated_at,
    }


def outlet_dict(outlet: Outlet) -> dict:
    return {
        "id": str(outlet.id), "merchant_id": str(outlet.merchant_id), "outlet_code": outlet.outlet_code,
        "name": outlet.name, "address": outlet.address, "city": outlet.city, "latitude": outlet.latitude,
        "longitude": outlet.longitude, "risk_level": outlet.risk_level, "status": outlet.status,
        "created_at": outlet.created_at, "updated_at": outlet.updated_at,
    }


def qris_dict(profile: QRISProfile) -> dict:
    return {
        "id": str(profile.id), "merchant_id": str(profile.merchant_id), "outlet_id": str(profile.outlet_id),
        "outlet_name": profile.outlet.name if profile.outlet else None, "nmid": profile.nmid,
        "qris_type": profile.qris_type, "acquirer_name": profile.acquirer_name,
        "masked_settlement_account": profile.masked_settlement_account, "payload_fingerprint": profile.payload_hash[:12],
        "status": profile.status, "last_verified_at": profile.last_verified_at,
        "created_at": profile.created_at, "updated_at": profile.updated_at,
        "verification_notice": "Pemeriksaan dilakukan terhadap profil QRIS yang tersimpan pada sistem FinGraph Mode Demo.",
    }


def order_dict(order: Order) -> dict:
    payments = order.payments or []
    latest_payment = max(
        payments,
        key=lambda item: (item.transaction_time, item.created_at, str(item.id)),
        default=None,
    )
    return {
        "id": str(order.id), "order_reference": order.order_reference, "merchant_id": str(order.merchant_id),
        "outlet_id": str(order.outlet_id), "outlet_name": order.outlet.name if order.outlet else None,
        "expected_amount": float(order.expected_amount), "currency": order.currency, "description": order.description,
        "customer_reference": order.customer_reference, "status": order.status, "expires_at": order.expires_at,
        "created_at": order.created_at, "updated_at": order.updated_at,
        "payment_count": len(payments),
        "latest_payment": {
            "id": str(latest_payment.id),
            "provider_reference": latest_payment.provider_reference,
            "payment_status": latest_payment.payment_status,
            "callback_received": latest_payment.callback_received,
            "risk_level": latest_payment.risk_level,
            "recommendation": latest_payment.recommendation,
            "transaction_time": latest_payment.transaction_time,
        } if latest_payment else None,
    }


def payment_dict(payment: PaymentEvent, detailed: bool = False) -> dict:
    explanation = payment.scoring_explanation or {}
    confidence_score = explanation.get("confidence_score")
    if confidence_score is None:
        confidence_score = analysis_confidence(
            rule_score=float(payment.rule_score or 0),
            graph_score=float(payment.graph_score or 0),
            tabular_score=float(payment.tabular_score) if payment.tabular_score is not None else None,
            adaptive_score=float(payment.adaptive_score) if payment.adaptive_score is not None else None,
            strongest_severity=(
                "critical"
                if float(payment.fraud_score or 0) >= 0.90
                else "high"
                if float(payment.fraud_score or 0) >= 0.75
                else "medium"
                if float(payment.fraud_score or 0) >= 0.40
                else None
            ),
        )
    analysis_mode = explanation.get("analysis_mode") or (
        "ensemble_ai"
        if payment.tabular_score is not None or payment.adaptive_score is not None
        else "rule_graph_fallback"
    )
    data = {
        "id": str(payment.id), "transaction_reference": payment.transaction_reference,
        "provider_reference": payment.provider_reference, "order_id": str(payment.order_id) if payment.order_id else None,
        "order_reference": payment.order.order_reference if payment.order else None,
        "merchant_id": str(payment.merchant_id), "merchant_name": payment.merchant.name if payment.merchant else None,
        "outlet_id": str(payment.outlet_id), "outlet_name": payment.outlet.name if payment.outlet else None,
        "qris_profile_id": str(payment.qris_profile_id), "payer_pseudonym": payment.payer_pseudonym,
        "amount": float(payment.amount), "expected_amount": float(payment.expected_amount) if payment.expected_amount is not None else None,
        "currency": payment.currency, "payment_method": payment.payment_method,
        "category": payment.category, "priority": payment.priority, "qris_type": payment.qris_type,
        "acquirer_name": payment.acquirer_name, "payment_status": payment.payment_status,
        "callback_received": payment.callback_received, "callback_received_at": payment.callback_received_at,
        "callback_delay_seconds": payment.callback_delay_seconds, "source_city": payment.source_city,
        "source_region": payment.source_region, "source_country": payment.source_country,
        "destination_city": payment.destination_city, "destination_region": payment.destination_region,
        "destination_country": payment.destination_country, "is_cross_region": payment.is_cross_region,
        "is_cross_border": payment.is_cross_border, "status": payment.status, "fraud_score": payment.fraud_score,
        "confidence_score": confidence_score, "analysis_mode": analysis_mode,
        "risk_level": payment.risk_level, "recommendation_code": payment.recommendation_code,
        "recommendation": payment.recommendation, "scenario_name": payment.scenario_name,
        "transaction_time": payment.transaction_time, "created_at": payment.created_at, "updated_at": payment.updated_at,
    }
    if detailed:
        latest_feedback = max(
            payment.labels or [],
            key=lambda item: (item.created_at, str(item.id)),
            default=None,
        )
        data["scoring"] = {
            **explanation,
            "final_score": payment.fraud_score, "risk_level": payment.risk_level,
            "recommendation": payment.recommendation,
            "reasons": explanation.get("reasons", []),
            "models_used": explanation.get("models_used", ["rule_guard", "graph_heuristic"]),
            "confidence_score": confidence_score,
            "confidence_basis": explanation.get("confidence_basis", "agreement_between_available_signals"),
            "analysis_mode": analysis_mode,
        }
        data["timeline"] = [
            {"event": "payment_created", "at": payment.created_at, "label": "Pembayaran dibuat"},
            *([{"event": "callback_received", "at": payment.callback_received_at, "label": "Konfirmasi penyedia pembayaran diterima"}] if payment.callback_received_at else []),
            {"event": "scored", "at": payment.updated_at, "label": "Tingkat risiko dihitung"},
            *([{"event": "human_feedback", "at": latest_feedback.created_at, "label": "Keputusan manusia dicatat"}] if latest_feedback else []),
        ]
        data["latest_feedback"] = {
            "label": latest_feedback.label,
            "merchant_decision": latest_feedback.merchant_decision,
            "labelled_by": latest_feedback.labelled_by,
            "notes": latest_feedback.notes,
            "created_at": latest_feedback.created_at,
        } if latest_feedback else None
    return data


def alert_dict(alert: Alert) -> dict:
    return {
        "id": str(alert.id), "merchant_id": str(alert.merchant_id) if alert.merchant_id else None,
        "payment_event_id": str(alert.payment_event_id) if alert.payment_event_id else None,
        "transaction_id": str(alert.transaction_id) if alert.transaction_id else None,
        "alert_type": alert.alert_type, "severity": alert.severity, "risk_score": alert.risk_score,
        "reason": alert.reason, "recommendation": alert.recommendation, "status": alert.status,
        "assigned_to": alert.assigned_to, "created_at": alert.created_at, "resolved_at": alert.resolved_at,
        "payment": payment_dict(alert.payment_event, detailed=True) if alert.payment_event else None,
    }
