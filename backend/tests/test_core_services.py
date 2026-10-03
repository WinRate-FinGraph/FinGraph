import sys
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import get_current_user
from app.core.security import create_access_token, decode_access_token, pseudonymize_payer, sign_pjp_payload, verify_password, verify_pjp_signature
from app.db.seeds.seed import run_seed
from app.db.session import SessionLocal
from app.ml.training.train_qris import adaptive_status
from app.models.alert import Alert
from app.models.label import Label
from app.models.qris import FederatedRound, MerchantProfile, Order, PaymentEvent
from app.models.user import User
from app.services.federated import run_fedavg_round
from app.core.config import settings
from app.services import qris_scoring
from app.services.qris_scoring import analysis_confidence, score_payment
from app.api.graph import postgres_graph
from app.api.cross_border import route_semantics
from app.api.health import expected_migration_head


def test_auth_hash_jwt_and_pseudonymization():
    db = SessionLocal(); user = db.query(User).filter_by(email="merchant@fingraph.id").one()
    assert verify_password("password123", user.hashed_password)
    token = create_access_token(str(user.id), {"role": user.role})
    assert decode_access_token(token)["role"] == "merchant"
    authenticated = get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), db)
    assert authenticated.id == user.id
    malformed = create_access_token("not-a-uuid", {"role": user.role})
    with pytest.raises(HTTPException) as error:
        get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=malformed), db)
    assert error.value.status_code == 401
    assert pseudonymize_payer("081234") == pseudonymize_payer("081234")
    assert "081234" not in pseudonymize_payer("081234")
    db.close()


def test_hmac_signature_validation():
    payload = {"provider_reference": "PJP-TEST", "amount": 350000, "timestamp": 123}
    signature = sign_pjp_payload(payload)
    assert verify_pjp_signature(payload, signature)
    assert not verify_pjp_signature({**payload, "amount": 1}, signature)


def test_seed_scenarios_scoring_floors_and_range():
    db = SessionLocal()
    mismatch = db.query(PaymentEvent).filter_by(scenario_name="amount_mismatch").first()
    duplicate = db.query(PaymentEvent).filter_by(scenario_name="duplicate_reference").first()
    cross_region = db.query(PaymentEvent).filter_by(scenario_name="cross_region").first()
    assert mismatch.fraud_score >= 0.90 and mismatch.risk_level == "high"
    assert "AMOUNT_MISMATCH" in mismatch.scoring_explanation["explanation_codes"]
    assert duplicate.risk_level == "high"
    assert cross_region.risk_level != "high"
    assert all(0 <= item.fraud_score <= 1 for item in db.query(PaymentEvent).all())
    assert db.query(Alert).filter(Alert.payment_event_id == mismatch.id).count() == 1
    db.close()


def test_missing_model_falls_back_without_crash_and_graph_heuristic_runs(monkeypatch):
    monkeypatch.setattr(settings, "QRIS_GNN_ENABLED", False)
    db = SessionLocal(); payment = db.query(PaymentEvent).filter_by(scenario_name="normal_payment").first()
    result = score_payment(db, payment)
    assert "rule_guard" in result["models_used"] and "graph_heuristic" in result["models_used"]
    assert result["tabular_score"] is None
    assert result["gnn_score"] is None
    assert result["gnn_metadata"]["fallback_reason"] == "disabled"
    assert 0 <= result["graph_score"] <= 1
    assert 0 <= result["confidence_score"] <= 1
    assert result["analysis_mode"] == "rule_graph_fallback"
    db.rollback(); db.close()


def test_gnn_contributes_configured_share_of_final_score(monkeypatch):
    monkeypatch.setattr(settings, "QRIS_GNN_ENABLED", True)
    monkeypatch.setattr(settings, "QRIS_GNN_BLEND_WEIGHT", 0.5)
    monkeypatch.setattr(qris_scoring, "build_behavior_features", lambda *_: {})
    monkeypatch.setattr(
        qris_scoring,
        "evaluate_critical_rules",
        lambda *_: [{"contribution": 0.1, "severity": "low", "code": "PAYMENT_VERIFIED", "reason": "ok"}],
    )
    monkeypatch.setattr(qris_scoring, "heuristic_graph_score", lambda *_: (0.2, {}))
    monkeypatch.setattr(
        qris_scoring,
        "_artifact_score",
        lambda dataset, _: ({"qris_demo": 0.4, "qris_adaptive": 0.6}[dataset], "test-model"),
    )
    monkeypatch.setitem(
        sys.modules,
        "app.ml.graph.inference",
        SimpleNamespace(score_qris_gnn=lambda *_: (0.8, {"model_version": "test-gnn"})),
    )
    db = SessionLocal()
    payment = db.query(PaymentEvent).filter_by(scenario_name="normal_payment").first()
    try:
        result = qris_scoring.score_payment(db, payment)
        legacy = 0.1 * 0.35 + 0.4 * 0.30 + 0.2 * 0.25 + 0.6 * 0.10
        assert result["legacy_ensemble_score"] == round(legacy, 4)
        assert result["gnn_final_weight"] == 0.5
        assert result["final_score"] == round(legacy * 0.5 + 0.8 * 0.5, 4)
        assert result["analysis_mode"] == "ensemble_gnn"
        assert "qris_graphsage" in result["models_used"]
    finally:
        db.rollback()
        db.close()


def test_gnn_missing_model_uses_legacy_score_and_critical_floor(monkeypatch):
    monkeypatch.setattr(settings, "QRIS_GNN_ENABLED", True)
    monkeypatch.setattr(qris_scoring, "build_behavior_features", lambda *_: {})
    monkeypatch.setattr(
        qris_scoring,
        "evaluate_critical_rules",
        lambda *_: [{"contribution": 0.95, "severity": "critical", "code": "AMOUNT_MISMATCH", "reason": "mismatch"}],
    )
    monkeypatch.setattr(qris_scoring, "heuristic_graph_score", lambda *_: (0.2, {}))
    monkeypatch.setattr(qris_scoring, "_artifact_score", lambda *_: (None, None))
    monkeypatch.setitem(
        sys.modules,
        "app.ml.graph.inference",
        SimpleNamespace(score_qris_gnn=lambda *_: (None, {"fallback_reason": "qris_graphsage_artifact_missing"})),
    )
    db = SessionLocal()
    payment = db.query(PaymentEvent).filter_by(scenario_name="normal_payment").first()
    try:
        result = qris_scoring.score_payment(db, payment)
        assert result["gnn_final_weight"] == 0
        assert result["gnn_metadata"]["fallback_reason"] == "qris_graphsage_artifact_missing"
        assert result["final_score"] == 0.95
    finally:
        db.rollback()
        db.close()


def test_analysis_confidence_measures_signal_agreement_and_critical_rules():
    aligned = analysis_confidence(
        rule_score=0.12,
        graph_score=0.14,
        tabular_score=0.13,
        adaptive_score=None,
    )
    divergent = analysis_confidence(
        rule_score=0.10,
        graph_score=0.90,
        tabular_score=0.45,
        adaptive_score=None,
    )
    critical = analysis_confidence(
        rule_score=0.95,
        graph_score=0.20,
        tabular_score=None,
        adaptive_score=None,
        strongest_severity="critical",
    )
    assert aligned > divergent
    assert critical >= 0.95


def test_merchant_data_is_separated_and_feedback_adaptive_available():
    db = SessionLocal(); merchants = db.query(MerchantProfile).order_by(MerchantProfile.name).all()
    assert len(merchants) == 3 and len({item.user_id for item in merchants}) == 3
    first_ids = {p.id for p in db.query(PaymentEvent).filter(PaymentEvent.merchant_id == merchants[0].id)}
    second_ids = {p.id for p in db.query(PaymentEvent).filter(PaymentEvent.merchant_id == merchants[1].id)}
    assert first_ids.isdisjoint(second_ids)
    status = adaptive_status(db)
    assert status["labels_available"] >= 10 and status["class_distribution"]["fraud"] > 0
    db.close()


def test_cross_border_seed_and_fedavg_math():
    db = SessionLocal()
    assert db.query(PaymentEvent).filter(PaymentEvent.is_cross_region.is_(True)).count() > 0
    assert db.query(PaymentEvent).filter(PaymentEvent.is_cross_border.is_(True)).count() > 0
    before = db.query(FederatedRound).order_by(FederatedRound.round_number.desc()).first()
    record = run_fedavg_round(db)
    assert record.round_number == before.round_number + 1 and record.aggregation_method == "FedAvg"
    assert record.global_metric_after >= record.global_metric_before
    weights = record.global_parameters
    assert len(weights) == 4 and all(isinstance(value, float) for value in weights)
    db.rollback(); db.close()


def test_seed_idempotency():
    db = SessionLocal(); before = (db.query(User).count(), db.query(Order).count(), db.query(PaymentEvent).count(), db.query(Label).count()); db.close()
    run_seed()
    db = SessionLocal(); after = (db.query(User).count(), db.query(Order).count(), db.query(PaymentEvent).count(), db.query(Label).count()); db.close()
    assert before == after


def test_graph_fallback_honors_node_limit_and_edges_are_closed():
    db = SessionLocal(); analyst = db.query(User).filter_by(email="analyst@fingraph.id").one()
    result = postgres_graph(db, analyst, 10, None, None, None)
    ids = {node["id"] for node in result["nodes"]}
    assert result["returned_nodes"] <= 10
    assert result["returned_nodes"] == len(result["nodes"])
    assert result["total_nodes"] >= result["returned_nodes"]
    assert result["truncated"] is True
    assert all(edge["source"] in ids and edge["target"] in ids for edge in result["edges"])
    db.close()


def test_cross_border_route_semantics_do_not_equate_geography_with_fraud():
    status, reason, rate = route_semantics(0.19, 0, 10)
    assert status == "normal" and rate == 0 and "konteks" in reason
    status, _, rate = route_semantics(0.31, 1, 10)
    assert status == "monitor" and rate == 0.1
    status, _, rate = route_semantics(0.72, 1, 10)
    assert status == "high" and rate == 0.1


def test_health_expected_migration_is_single_head():
    assert expected_migration_head() == "20260723_0006"
