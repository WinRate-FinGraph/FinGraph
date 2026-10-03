from __future__ import annotations

from datetime import timedelta
from statistics import pstdev
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ml.registry.model_registry import load_latest_model_by_dataset
from app.models.alert import Alert
from app.models.label import Label
from app.models.qris import MerchantProfile, PaymentEvent


RECOMMENDATIONS = {
    "APPROVE": "Status PJP berhasil, data utama sesuai, dan risiko FinGraph rendah.",
    "VERIFY": "Periksa kembali pembayaran sebelum memproses pesanan.",
    "HOLD": "Tahan pesanan sementara hingga pembayaran dikonfirmasi.",
    "DO_NOT_RELEASE_GOODS": "Jangan serahkan barang. Pembayaran belum dapat diverifikasi.",
    "REPORT_AND_HOLD": "Tahan pesanan dan laporkan transaksi untuk pemeriksaan.",
}

SEVERITY_FLOORS = {"medium": 0.50, "high": 0.75, "critical": 0.90}


def _rule(code: str, reason: str, contribution: float, severity: str, action: str) -> dict[str, Any]:
    return {
        "code": code,
        "reason": reason,
        "contribution": contribution,
        "severity": severity,
        "recommended_action": action,
    }


def evaluate_critical_rules(payment: PaymentEvent, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    context = context or {}
    rules: list[dict[str, Any]] = []
    amount = float(payment.amount)
    expected = float(payment.expected_amount) if payment.expected_amount is not None else None

    if payment.claimed_paid and not payment.callback_received:
        rules.append(_rule("CALLBACK_NOT_FOUND", "Konfirmasi resmi dari simulator PJP tidak ditemukan. Jangan percaya screenshot saja.", 0.95, "critical", "DO_NOT_RELEASE_GOODS"))
    if payment.claimed_paid and payment.payment_status != "success":
        rules.append(_rule("PAYMENT_NOT_SUCCESS", f"Status pembayaran adalah {payment.payment_status}, bukan berhasil.", 0.90, "critical", "DO_NOT_RELEASE_GOODS"))
    if expected is not None and abs(amount - expected) >= 1:
        rules.append(_rule("AMOUNT_MISMATCH", f"Nominal pembayaran Rp{amount:,.0f} tidak sesuai dengan total pesanan Rp{expected:,.0f}.", 0.95, "critical", "DO_NOT_RELEASE_GOODS"))
    if context.get("duplicate_reference") or payment.scenario_name == "duplicate_reference":
        rules.append(_rule("DUPLICATE_PROVIDER_REFERENCE", "Referensi penyedia pembayaran telah digunakan sebelumnya.", 0.92, "critical", "REPORT_AND_HOLD"))
    if context.get("merchant_mismatch"):
        rules.append(_rule("MERCHANT_ID_MISMATCH", "Identitas merchant pada callback tidak sesuai dengan profil QRIS.", 0.98, "critical", "DO_NOT_RELEASE_GOODS"))
    if context.get("outlet_mismatch"):
        rules.append(_rule("OUTLET_MISMATCH", "Identitas outlet pada callback tidak sesuai.", 0.95, "critical", "DO_NOT_RELEASE_GOODS"))
    if context.get("qris_mismatch"):
        rules.append(_rule("QR_FINGERPRINT_MISMATCH", "Fingerprint QR tidak cocok dengan QRIS yang terdaftar.", 0.95, "critical", "DO_NOT_RELEASE_GOODS"))
    if payment.replay_detected or context.get("replay_detected"):
        rules.append(_rule("CALLBACK_REPLAY", "Timestamp callback kedaluwarsa atau terindikasi replay.", 0.90, "critical", "REPORT_AND_HOLD"))
    if payment.payment_status in {"reversed", "refunded"} and payment.order and payment.order.status in {"paid", "completed"}:
        rules.append(_rule("PAYMENT_REVERSED_AFTER_PROCESSING", "Pembayaran dibalik setelah pesanan diproses.", 0.88, "high", "REPORT_AND_HOLD"))
    if (payment.callback_delay_seconds or 0) > settings.QRIS_WEBHOOK_TOLERANCE_SECONDS:
        rules.append(_rule("DELAYED_CALLBACK", f"Callback diterima setelah {payment.callback_delay_seconds or 0} detik; batas normal {settings.QRIS_WEBHOOK_TOLERANCE_SECONDS} detik.", 0.55, "medium", "VERIFY"))
    if context.get("failed_count_30m", 0) >= 3:
        rules.append(_rule("REPEATED_FAILURES", f"Terdapat {context['failed_count_30m']} percobaan gagal dalam 30 menit sebelum pembayaran ini.", 0.60, "medium", "VERIFY"))
    if context.get("payment_count_10m", 0) >= 6 and amount <= 50_000:
        rules.append(_rule("RAPID_MICRO_TRANSACTIONS", f"Terdapat {context['payment_count_10m']} transaksi dalam 10 menit dengan nominal Rp{amount:,.0f}.", 0.58, "medium", "VERIFY"))
    if payment.is_cross_border:
        rules.append(_rule("CROSS_BORDER_SIGNAL", "Pembayaran lintas negara memerlukan konteks tambahan, namun bukan otomatis fraud.", 0.18, "low", "VERIFY"))
    elif payment.is_cross_region:
        rules.append(_rule("CROSS_REGION_SIGNAL", "Pembayaran berasal dari wilayah berbeda; sinyal ini tidak otomatis berisiko tinggi.", 0.10, "low", "APPROVE"))
    if not rules:
        rules.append(_rule("PAYMENT_VERIFIED", "Konfirmasi pembayaran diterima dan data utama sesuai profil QRIS.", 0.08, "low", "APPROVE"))
    return rules


def build_behavior_features(db: Session, payment: PaymentEvent) -> dict[str, float | int]:
    ten_minutes_ago = payment.transaction_time - timedelta(minutes=10)
    thirty_minutes_ago = payment.transaction_time - timedelta(minutes=30)
    payer_query = db.query(PaymentEvent).filter(PaymentEvent.payer_pseudonym == payment.payer_pseudonym)
    payer_count = payer_query.count()
    payment_count_10m = payer_query.filter(PaymentEvent.transaction_time >= ten_minutes_ago).count()
    failed_count_30m = payer_query.filter(PaymentEvent.transaction_time >= thirty_minutes_ago, PaymentEvent.payment_status == "failed").count()
    payer_fraud_count = db.query(Label).join(PaymentEvent, Label.payment_event_id == PaymentEvent.id).filter(PaymentEvent.payer_pseudonym == payment.payer_pseudonym, Label.label == "fraud").count()
    payer_suspicious_count = db.query(Label).join(PaymentEvent, Label.payment_event_id == PaymentEvent.id).filter(PaymentEvent.payer_pseudonym == payment.payer_pseudonym, Label.label == "suspicious").count()
    merchant_average = db.query(func.avg(PaymentEvent.amount)).filter(PaymentEvent.merchant_id == payment.merchant_id, PaymentEvent.id != payment.id).scalar()
    average = float(merchant_average or payment.expected_amount or payment.amount or 0)
    amount = float(payment.amount)
    expected = float(payment.expected_amount) if payment.expected_amount is not None else amount
    return {
        "amount": amount,
        "expected_amount": expected,
        "amount_difference": amount - expected,
        "amount_ratio": amount / expected if expected else 0.0,
        "payment_hour": payment.transaction_time.hour,
        "callback_delay_seconds": payment.callback_delay_seconds or 0,
        "payment_count_10m": payment_count_10m,
        "failed_count_30m": failed_count_30m,
        "payer_transaction_count": payer_count,
        "payer_fraud_count": payer_fraud_count,
        "payer_suspicious_count": payer_suspicious_count,
        "merchant_average_amount": average,
        "amount_deviation_from_merchant": abs(amount - average) / max(average, 1),
        "is_new_payer": int(payer_count <= 1),
        "is_duplicate_reference": int(payment.scenario_name == "duplicate_reference"),
        "is_cross_region": int(payment.is_cross_region),
        "is_cross_border": int(payment.is_cross_border),
        "merchant_risk": {"low": 0.1, "medium": 0.5, "high": 0.9}.get(payment.merchant.risk_level, 0.1),
        "outlet_risk": {"low": 0.1, "medium": 0.5, "high": 0.9}.get(payment.outlet.risk_level, 0.1),
        "qris_profile_match": 1,
        "order_age_seconds": max(0, int((payment.transaction_time - payment.order.created_at).total_seconds())) if payment.order else 0,
        "payment_velocity": payment_count_10m / 10.0,
    }


def heuristic_graph_score(db: Session, payment: PaymentEvent) -> tuple[float, dict[str, Any]]:
    payer_payments = db.query(PaymentEvent).filter(PaymentEvent.payer_pseudonym == payment.payer_pseudonym)
    degree = payer_payments.count()
    merchant_count = payer_payments.with_entities(PaymentEvent.merchant_id).distinct().count()
    alert_count = db.query(Alert).join(PaymentEvent, Alert.payment_event_id == PaymentEvent.id).filter(PaymentEvent.payer_pseudonym == payment.payer_pseudonym).count()
    fraud_neighbors = db.query(Label).join(PaymentEvent, Label.payment_event_id == PaymentEvent.id).filter(PaymentEvent.payer_pseudonym == payment.payer_pseudonym, Label.label == "fraud").count()
    ratio = fraud_neighbors / max(degree, 1)
    score = min(0.99, 0.04 + min(degree, 20) * 0.01 + min(merchant_count, 5) * 0.05 + min(alert_count, 5) * 0.10 + ratio * 0.45)
    if payment.scenario_name == "suspicious_network":
        score = max(score, 0.86)
    return round(score, 4), {
        "degree": degree,
        "connected_merchants": merchant_count,
        "connected_alerts": alert_count,
        "fraud_neighbor_ratio": round(ratio, 4),
        "cluster_risk": "high" if score >= 0.70 else "medium" if score >= 0.40 else "low",
    }


def _artifact_score(dataset: str, features: dict[str, Any]) -> tuple[float | None, str | None]:
    artifact = load_latest_model_by_dataset(dataset)
    if not artifact:
        return None, None
    model = artifact["model"]
    feature_list = artifact.get("feature_list") or artifact.get("features")
    if feature_list is None:
        feature_list = list(features)
    row = [[float(features.get(name, 0)) for name in feature_list]]
    try:
        score = float(model.predict_proba(row)[0][1])
    except Exception:
        return None, None
    return round(max(0.0, min(score, 1.0)), 4), artifact.get("version")


def risk_level(score: float) -> str:
    if score >= settings.QRIS_HIGH_THRESHOLD:
        return "high"
    if score >= settings.QRIS_LOW_THRESHOLD:
        return "medium"
    return "low"


def analysis_confidence(
    *,
    rule_score: float,
    graph_score: float,
    tabular_score: float | None,
    adaptive_score: float | None,
    gnn_score: float | None = None,
    strongest_severity: str | None = None,
) -> float:
    """Estimate decision consistency, not a calibrated fraud probability."""

    signals = [float(rule_score), float(graph_score)]
    signals.extend(
        float(score)
        for score in (tabular_score, adaptive_score, gnn_score)
        if score is not None
    )
    agreement = 1.0 - min(pstdev(signals) * 2.0, 1.0)
    confidence = 0.55 + (agreement * 0.45)
    if strongest_severity == "critical":
        confidence = max(confidence, 0.95)
    elif strongest_severity == "high":
        confidence = max(confidence, 0.90)
    elif strongest_severity == "medium":
        confidence = max(confidence, 0.78)
    return round(max(0.0, min(confidence, 1.0)), 4)


def score_payment(db: Session, payment: PaymentEvent, context: dict[str, Any] | None = None) -> dict[str, Any]:
    features = build_behavior_features(db, payment)
    merged_context = {**features, **(context or {})}
    rules = evaluate_critical_rules(payment, merged_context)
    rule_score = min(1.0, max(rule["contribution"] for rule in rules))
    heuristic_score, graph_features = heuristic_graph_score(db, payment)
    gnn_score = None
    gnn_metadata: dict[str, Any] = {"enabled": settings.QRIS_GNN_ENABLED, "fallback_reason": "disabled"}
    if settings.QRIS_GNN_ENABLED:
        try:
            from app.ml.graph.inference import score_qris_gnn

            gnn_score, gnn_metadata = score_qris_gnn(db, payment, settings.QRIS_GNN_MAX_NODES)
        except Exception:
            gnn_metadata = {"enabled": True, "fallback_reason": "qris_graphsage_inference_failed"}
    gnn_final_weight = settings.QRIS_GNN_BLEND_WEIGHT if gnn_score is not None else 0.0
    graph_score = heuristic_score
    graph_features = {
        **graph_features,
        "heuristic_score": heuristic_score,
        "gnn_score": gnn_score,
        "gnn_final_weight": gnn_final_weight,
        "gnn": gnn_metadata,
    }
    tabular_score, tabular_version = _artifact_score("qris_demo", features)
    adaptive_score, adaptive_version = _artifact_score("qris_adaptive", features)

    legacy_ensemble_score = rule_score * 0.35 + (tabular_score or 0.0) * 0.30 + graph_score * 0.25 + (adaptive_score or 0.0) * 0.10
    weighted = legacy_ensemble_score
    if gnn_score is not None:
        weighted = (1 - gnn_final_weight) * legacy_ensemble_score + gnn_final_weight * gnn_score
    strongest_severity = next((severity for severity in ("critical", "high", "medium") if any(r["severity"] == severity for r in rules)), None)
    critical_floor = SEVERITY_FLOORS.get(strongest_severity or "", 0.0)
    final_score = round(max(critical_floor, weighted), 4)
    final_score = max(0.0, min(final_score, 1.0))
    level = risk_level(final_score)

    codes = {rule["code"] for rule in rules}
    if "NETWORK_RISK" in codes or max(graph_score, gnn_score or 0.0) >= 0.75:
        recommendation_code = "REPORT_AND_HOLD"
    elif level == "high":
        recommendation_code = "DO_NOT_RELEASE_GOODS"
    elif level == "medium" and ({"CALLBACK_NOT_FOUND", "PAYMENT_NOT_SUCCESS"} & codes):
        recommendation_code = "HOLD"
    elif level == "medium":
        recommendation_code = "VERIFY"
    else:
        recommendation_code = "APPROVE"

    models_used = ["rule_guard", "graph_heuristic"]
    if tabular_score is not None:
        models_used.append("qris_tabular")
    if adaptive_score is not None:
        models_used.append("adaptive")
    if gnn_score is not None and gnn_final_weight > 0:
        models_used.append("qris_graphsage")
    confidence_score = analysis_confidence(
        rule_score=rule_score,
        graph_score=graph_score,
        tabular_score=tabular_score,
        adaptive_score=adaptive_score,
        gnn_score=gnn_score if gnn_final_weight > 0 else None,
        strongest_severity=strongest_severity,
    )
    analysis_mode = (
        "ensemble_gnn"
        if gnn_score is not None and gnn_final_weight > 0
        else "ensemble_ai"
        if tabular_score is not None or adaptive_score is not None
        else "rule_graph_fallback"
    )

    result = {
        "final_score": final_score,
        "risk_level": level,
        "recommendation_code": recommendation_code,
        "recommendation": RECOMMENDATIONS[recommendation_code],
        "rule_score": round(rule_score, 4),
        "tabular_score": tabular_score,
        "adaptive_score": adaptive_score,
        "graph_score": graph_score,
        "legacy_ensemble_score": round(legacy_ensemble_score, 4),
        "gnn_score": gnn_score,
        "gnn_final_weight": gnn_final_weight,
        "gnn_metadata": gnn_metadata,
        "models_used": models_used,
        "confidence_score": confidence_score,
        "confidence_basis": "agreement_between_available_signals",
        "analysis_mode": analysis_mode,
        "reasons": [rule["reason"] for rule in rules],
        "explanation_codes": [rule["code"] for rule in rules],
        "rules": rules,
        "features": features,
        "graph_features": graph_features,
        "model_versions": {"tabular": tabular_version, "adaptive": adaptive_version, "graphsage": gnn_metadata.get("model_version")},
        "ensemble_mode": (
            "gnn_weighted_final_blend_with_legacy_35_30_25_10_and_critical_floor"
            if gnn_score is not None and gnn_final_weight > 0
            else "weighted_35_30_25_10_with_critical_floor"
        ),
        "critical_rule_floor": critical_floor,
    }
    payment.fraud_score = final_score
    payment.risk_level = level
    payment.priority = {"low": "rendah", "medium": "sedang", "high": "tinggi"}[level]
    payment.recommendation_code = recommendation_code
    payment.recommendation = result["recommendation"]
    payment.rule_score = result["rule_score"]
    payment.tabular_score = tabular_score
    payment.adaptive_score = adaptive_score
    payment.graph_score = graph_score
    payment.scoring_explanation = result
    return result
