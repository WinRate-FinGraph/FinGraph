import time
import sys
import pytest

pytestmark = pytest.mark.skipif(sys.version_info >= (3, 13), reason="FastAPI/AnyIO sync TestClient dijalankan pada image Python 3.11; thread portal host Python 3.13 tidak kompatibel")

from app.core.security import sign_pjp_payload
from app.db.seeds.seed import run_seed
from app.db.session import SessionLocal
from app.models.qris import Order, PaymentEvent


def test_login_and_role(client, merchant_headers, analyst_headers, admin_headers):
    assert client.get("/api/v1/auth/me", headers=merchant_headers).json()["role"] == "merchant"
    assert client.get("/api/v1/auth/me", headers=analyst_headers).json()["role"] == "analyst"
    assert client.get("/api/v1/auth/me", headers=admin_headers).json()["role"] == "admin"
    assert client.post("/api/v1/ml/train/qris-tabular", headers=merchant_headers).status_code == 403
    graph_status = client.get("/api/v1/ml/graphsage/status", headers=admin_headers)
    assert graph_status.status_code == 200 and "qris_model_available" in graph_status.json()
    assert client.post("/api/v1/ml/train/qris-graphsage", headers=merchant_headers).status_code == 403


def test_merchant_ownership_isolation(client, merchant_headers, second_merchant_headers):
    payment_id = client.get("/api/v1/payments?limit=1", headers=merchant_headers).json()["items"][0]["id"]
    assert client.get(f"/api/v1/payments/{payment_id}", headers=second_merchant_headers).status_code == 404


def _create_order(client, headers, amount=350000):
    outlet = client.get("/api/v1/merchants/outlets", headers=headers).json()["items"][0]
    response = client.post("/api/v1/orders", headers=headers, json={"outlet_id": outlet["id"], "expected_amount": amount, "currency": "IDR", "description": "Pesanan test"})
    assert response.status_code == 201, response.text
    return response.json()


def _generate(client, headers, order_id, amount=None):
    payload = {"order_id": order_id, "payer_identifier": "payer-test", "source_city": "Surakarta", "source_region": "Jawa Tengah", "source_country": "ID", "payment_status": "success"}
    if amount is not None: payload["amount"] = amount
    response = client.post("/api/v1/demo/qris/generate-payment", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_order_and_normal_signed_webhook(client, merchant_headers):
    order = _create_order(client, merchant_headers)
    generated = _generate(client, merchant_headers, order["id"])
    webhook = generated["webhook"]
    response = client.post("/api/v1/demo/qris/webhook", headers={**merchant_headers, "X-PJP-Signature": webhook["signature"]}, json=webhook["payload"])
    assert response.status_code == 200, response.text
    body = response.json(); assert body["payment"]["risk_level"] == "low"; assert body["payment"]["recommendation_code"] == "APPROVE"
    checked = client.post(
        "/api/v1/payments/check",
        headers=merchant_headers,
        json={"provider_reference": webhook["payload"]["provider_reference"], "amount": 350001, "order_reference": order["order_reference"]},
    )
    assert checked.status_code == 200
    assert checked.json()["amount_match"] is False
    assert checked.json()["risk_result"]["recommendation_code"] == "DO_NOT_RELEASE_GOODS"
    assert "AMOUNT_MISMATCH" in checked.json()["risk_result"]["explanation_codes"]
    duplicate = client.post("/api/v1/demo/qris/webhook", headers={**merchant_headers, "X-PJP-Signature": webhook["signature"]}, json=webhook["payload"])
    assert duplicate.status_code == 200 and duplicate.json()["idempotent"] is True


def test_invalid_signature_and_replayed_webhook(client, merchant_headers):
    order = _create_order(client, merchant_headers); generated = _generate(client, merchant_headers, order["id"]); payload = generated["webhook"]["payload"]
    assert client.post("/api/v1/demo/qris/webhook", headers={**merchant_headers, "X-PJP-Signature": "bad"}, json=payload).status_code == 401
    payload["timestamp"] = int(time.time()) - 9999
    assert client.post("/api/v1/demo/qris/webhook", headers={**merchant_headers, "X-PJP-Signature": sign_pjp_payload(payload)}, json=payload).status_code == 408


def test_demo_risk_scenarios_and_alerts(client, merchant_headers):
    mismatch = client.post("/api/v1/demo/qris/scenarios/amount_mismatch", headers=merchant_headers).json()
    assert mismatch["payment"]["risk_level"] == "high" and mismatch["payment"]["fraud_score"] >= 0.90
    assert "AMOUNT_MISMATCH" in mismatch["payment"]["scoring"]["explanation_codes"]
    assert mismatch["alert_created"] is True
    fake = client.post("/api/v1/demo/qris/scenarios/fake_receipt", headers=merchant_headers).json()
    assert fake["payment"]["risk_level"] == "high"
    duplicate = client.post("/api/v1/demo/qris/scenarios/duplicate_reference", headers=merchant_headers).json()
    assert duplicate["payment"]["risk_level"] == "high"
    cross_region = client.post("/api/v1/demo/qris/scenarios/cross_region", headers=merchant_headers).json()
    assert cross_region["payment"]["risk_level"] != "high"
    assert all(0 <= item["payment"]["fraud_score"] <= 1 for item in (mismatch, fake, duplicate, cross_region))


def test_label_transition_adaptive_graph_cross_border(client, merchant_headers, analyst_headers):
    payment = client.get("/api/v1/payments?risk_level=high&limit=1", headers=merchant_headers).json()["items"][0]
    response = client.post("/api/v1/labels", headers=merchant_headers, json={"payment_event_id": payment["id"], "label": "fraud", "merchant_decision": "report", "notes": "Test report"})
    assert response.status_code == 201 and response.json()["order_status"] == "held"
    adaptive = client.get("/api/v1/ml/adaptive/status", headers=analyst_headers)
    assert adaptive.status_code == 200 and adaptive.json()["qris"]["labels_available"] > 0
    graph = client.get("/api/v1/graph?limit=10", headers=merchant_headers)
    assert graph.status_code == 200 and graph.json()["source"] == "postgresql_fallback" and graph.json()["nodes"]
    summary = client.get("/api/v1/cross-border/summary", headers=analyst_headers).json()
    assert summary["cross_region_payments"] > 0 and summary["cross_border_payments"] > 0


def test_merchant_cannot_bypass_verified_payment_state(client, merchant_headers):
    order = _create_order(client, merchant_headers)
    forced = client.patch(
        f"/api/v1/orders/{order['id']}/status",
        headers=merchant_headers,
        json={"status": "paid"},
    )
    assert forced.status_code == 409

    fake = client.post(
        "/api/v1/demo/qris/scenarios/fake_receipt",
        headers=merchant_headers,
    ).json()
    feedback = client.post(
        "/api/v1/labels",
        headers=merchant_headers,
        json={
            "payment_event_id": fake["payment"]["id"],
            "label": "legitimate",
            "merchant_decision": "approve",
            "notes": "Merchant review is not provider confirmation",
        },
    )
    assert feedback.status_code == 201
    assert feedback.json()["payment_status"] == "pending"
    assert feedback.json()["order_status"] != "paid"
    assert feedback.json()["alert_status"] != "dismissed"
    detail = client.get(f"/api/v1/payments/{fake['payment']['id']}", headers=merchant_headers).json()
    assert detail["latest_feedback"]["merchant_decision"] == "approve"
    order = client.get(f"/api/v1/orders/{fake['payment']['order_id']}", headers=merchant_headers).json()
    assert order["latest_payment"]["payment_status"] == "pending"
    assert order["latest_payment"]["callback_received"] is False

    alerts = client.get("/api/v1/alerts?status=active&limit=100", headers=merchant_headers).json()["items"]
    alert = next(item for item in alerts if item["payment_event_id"] == fake["payment"]["id"])
    dismissed = client.patch(
        f"/api/v1/alerts/{alert['id']}/status",
        headers=merchant_headers,
        json={"status": "dismissed"},
    )
    assert dismissed.status_code == 403


def test_fedavg_round(client, admin_headers):
    before = client.get("/api/v1/federated/status", headers=admin_headers).json()["last_round"]["round_number"]
    response = client.post("/api/v1/federated/rounds/run", headers=admin_headers)
    assert response.status_code == 200, response.text
    data = response.json(); assert data["round_number"] == before + 1; assert data["aggregation_method"] == "FedAvg"; assert data["raw_data_shared"] == 0; assert data["global_metric_after"] >= data["global_metric_before"]


def test_seed_is_idempotent():
    db = SessionLocal()
    before = (db.query(Order).count(), db.query(PaymentEvent).count()); db.close()
    run_seed()
    db = SessionLocal(); after = (db.query(Order).count(), db.query(PaymentEvent).count()); db.close()
    assert before == after


def test_server_side_pagination_and_stable_order(client, merchant_headers, analyst_headers):
    first = client.get("/api/v1/payments?limit=5&offset=0", headers=merchant_headers).json()
    second = client.get("/api/v1/payments?limit=5&offset=5", headers=merchant_headers).json()
    assert first["page"] == 1 and second["page"] == 2
    assert first["total_pages"] >= 2 and first["total"] >= 10
    assert {item["id"] for item in first["items"]}.isdisjoint({item["id"] for item in second["items"]})
    audit = client.get("/api/v1/audit-logs?limit=5&offset=0&ordering=newest", headers=analyst_headers).json()
    assert audit["limit"] == 5 and len(audit["items"]) <= 5


def test_graph_limit_metadata_and_cross_border_route_semantics(client, analyst_headers):
    graph = client.get("/api/v1/graph?limit=10", headers=analyst_headers).json()
    assert graph["returned_nodes"] <= 10 and graph["total_nodes"] >= graph["returned_nodes"]
    ids = {item["id"] for item in graph["nodes"]}
    assert all(edge["source"] in ids and edge["target"] in ids for edge in graph["edges"])
    assert all({"event_count", "first_seen", "last_seen", "evidence_payment_id", "source_type"} <= edge.keys() for edge in graph["edges"])
    routes = client.get("/api/v1/cross-border/routes", headers=analyst_headers).json()["items"]
    assert all(item["route_status"] in {"normal", "monitor", "high"} for item in routes)
    assert all(not (item["average_fraud_score"] < .4 and item["high_risk_count"] == 0 and item["route_status"] == "high") for item in routes)


def test_admin_activity_monitoring_rbac_filters_and_real_data(client, merchant_headers, analyst_headers, admin_headers):
    assert client.get("/api/v1/admin/activity-monitoring", headers=merchant_headers).status_code == 403
    assert client.get("/api/v1/admin/activity-monitoring", headers=analyst_headers).status_code == 403

    initial = client.get("/api/v1/admin/activity-monitoring?period=today", headers=admin_headers)
    assert initial.status_code == 200, initial.text
    before = initial.json()["activities_today"]

    login = client.post("/api/v1/auth/login", json={"email": "merchant@fingraph.id", "password": "password123"})
    assert login.status_code == 200
    after = client.get("/api/v1/admin/activity-monitoring?period=today&role=merchant", headers=admin_headers).json()
    assert after["activities_today"] >= 1
    assert after["activity_by_role"]["merchant"] >= 1
    assert after["activity_by_role"]["analyst"] == 0
    assert after["activity_by_role"]["admin"] == 0
    assert after["recent_activities"][0]["actor_role"] == "merchant"
    assert client.get("/api/v1/admin/activity-monitoring?period=today", headers=admin_headers).json()["activities_today"] >= before + 1

    wider = client.get("/api/v1/admin/activity-monitoring?period=30d", headers=admin_headers).json()
    assert sum(wider["activity_by_role"].values()) >= sum(after["activity_by_role"].values())
    authentication = client.get("/api/v1/admin/activity-monitoring?period=today&activity_category=authentication", headers=admin_headers).json()
    assert authentication["recent_activities"]
    assert all(item["category"] == "authentication" for item in authentication["recent_activities"])
    operational = client.get("/api/v1/admin/activity-monitoring?period=today&activity_category=operational", headers=admin_headers).json()
    assert all(item["category"] != "authentication" for item in operational["recent_activities"])


def test_admin_can_create_custom_demo_event_for_selected_merchant(client, admin_headers, analyst_headers):
    merchant = client.get("/api/v1/merchants?limit=1", headers=admin_headers).json()["items"][0]
    outlet = client.get(f"/api/v1/merchants/outlets?merchant_id={merchant['id']}", headers=admin_headers).json()["items"][0]
    payload = {"outlet_id": outlet["id"], "expected_amount": 275000, "currency": "IDR", "description": "Custom Demo Lab"}
    denied = client.post(f"/api/v1/demo/qris/create-order?merchant_id={merchant['id']}", headers=analyst_headers, json=payload)
    assert denied.status_code == 403
    created = client.post(f"/api/v1/demo/qris/create-order?merchant_id={merchant['id']}", headers=admin_headers, json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["merchant_id"] == merchant["id"]


def test_impact_filters_and_explicit_category_priority(client, merchant_headers):
    all_data = client.get("/api/v1/reports/impact-dashboard?period=30d&limit=100", headers=merchant_headers)
    assert all_data.status_code == 200, all_data.text
    body = all_data.json()
    assert body["metrics"]["payment_count"] > 0
    assert all(item["category"] and item["priority"] in {"rendah", "sedang", "tinggi"} for item in body["items"])

    high = client.get("/api/v1/reports/impact-dashboard?period=30d&priority=tinggi&limit=100", headers=merchant_headers).json()
    assert high["metrics"]["payment_count"] <= body["metrics"]["payment_count"]
    assert all(item["priority"] == "tinggi" for item in high["items"])

    outlets = client.get("/api/v1/merchants/outlets", headers=merchant_headers).json()["items"]
    scoped = client.get(f"/api/v1/reports/impact-dashboard?period=30d&outlet_id={outlets[0]['id']}", headers=merchant_headers).json()
    assert scoped["filters"]["outlet_id"] == outlets[0]["id"]

    dashboard = client.get(f"/api/v1/merchants/dashboard?period=30d&outlet_id={outlets[0]['id']}&priority=tinggi", headers=merchant_headers).json()
    assert dashboard["impact"]["filters"]["priority"] == "tinggi"
    assert dashboard["today"]["payment_count"] == dashboard["impact"]["metrics"]["payment_count"]


def test_subscription_catalog_and_demo_entitlements(client, merchant_headers, analyst_headers):
    me = client.get("/api/v1/auth/me", headers=merchant_headers)
    assert me.status_code == 200
    assert me.json()["subscription_plan"] == "premium"
    assert me.json()["subscription"]["monthly_price"] == 149_000

    catalog = client.get("/api/v1/merchants/subscription", headers=merchant_headers)
    assert catalog.status_code == 200
    assert catalog.json()["checkout_available"] is False
    assert catalog.json()["demo_change_available"] is True

    changed = client.patch(
        "/api/v1/merchants/subscription",
        headers=merchant_headers,
        json={"plan": "growth"},
    )
    assert changed.status_code == 200
    assert changed.json()["current"]["code"] == "growth"
    assert client.get("/api/v1/auth/me", headers=merchant_headers).json()["subscription_plan"] == "growth"

    # Seed keeps the primary demo credential on Premium for repeatable demos.
    run_seed()
    assert client.get("/api/v1/auth/me", headers=merchant_headers).json()["subscription_plan"] == "premium"
    assert client.get("/api/v1/merchants/subscription", headers=analyst_headers).status_code == 403
