from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, merchant_scope_id, require_roles
from app.db.session import get_db
from app.models.qris import PaymentEvent
from app.models.user import User
from app.services.graph_sync import clear_graph, sync_payment_to_graph


router = APIRouter(prefix="/graph", tags=["QRIS Graph Intelligence"])


def postgres_graph(db: Session, user: User, limit: int, risk_level: str | None, entity_type: str | None, search: str | None):
    query = db.query(PaymentEvent); scope = merchant_scope_id(user, db)
    if scope: query = query.filter(PaymentEvent.merchant_id == scope)
    if risk_level: query = query.filter(PaymentEvent.risk_level == risk_level)
    if search:
        pattern = f"%{search}%"
        query = query.filter((PaymentEvent.provider_reference.ilike(pattern)) | (PaymentEvent.payer_pseudonym.ilike(pattern)))
    matching_payments = query.count()
    payments = query.order_by(PaymentEvent.fraud_score.desc(), PaymentEvent.transaction_time.desc(), PaymentEvent.id.desc()).limit(min(max(limit * 2, 20), 200)).all()
    nodes = {}; edges = []
    def node(node_id, kind, title, risk="low", **extra): nodes.setdefault(node_id, {"id": node_id, "label": kind, "title": title, "risk_level": risk, **extra})
    def edge(source, target, label, payment):
        key = f"{source}-{label}-{target}"
        existing = next((item for item in edges if item["id"] == key), None)
        if existing:
            existing["event_count"] += 1
            existing["first_seen"] = min(existing["first_seen"], payment.transaction_time)
            existing["last_seen"] = max(existing["last_seen"], payment.transaction_time)
            return
        edges.append({
            "id": key,
            "source": source,
            "target": target,
            "label": label,
            "event_count": 1,
            "first_seen": payment.transaction_time,
            "last_seen": payment.transaction_time,
            "evidence_payment_id": str(payment.id),
            "evidence_reference": payment.provider_reference,
            "source_type": "payment_events",
        })
    for p in payments:
        ids = {"payer": f"payer-{p.payer_pseudonym}", "payment": f"payment-{p.id}", "merchant": f"merchant-{p.merchant_id}", "outlet": f"outlet-{p.outlet_id}", "qris": f"qris-{p.qris_profile_id}", "pjp": f"pjp-{p.acquirer_name}", "region": f"region-{p.source_region}", "country": f"country-{p.source_country}"}
        node(ids["payer"], "Payer", p.payer_pseudonym, p.risk_level)
        node(ids["payment"], "Payment", p.provider_reference, p.risk_level, amount=float(p.amount), fraud_score=p.fraud_score, status=p.payment_status)
        node(ids["merchant"], "Merchant", p.merchant.name, p.merchant.risk_level)
        node(ids["outlet"], "Outlet", p.outlet.name, p.outlet.risk_level, city=p.outlet.city)
        node(ids["qris"], "QRISProfile", p.qris_profile.nmid, "low", qris_type=p.qris_type)
        node(ids["pjp"], "PJP", p.acquirer_name)
        node(ids["region"], "Region", p.source_region or "Tidak diketahui")
        node(ids["country"], "Country", p.source_country)
        edge(ids["payer"], ids["payment"], "PAYER_MADE_PAYMENT", p); edge(ids["payment"], ids["merchant"], "PAYMENT_TO_MERCHANT", p)
        edge(ids["merchant"], ids["outlet"], "MERCHANT_HAS_OUTLET", p); edge(ids["outlet"], ids["qris"], "OUTLET_USES_QRIS", p)
        edge(ids["payment"], ids["pjp"], "PAYMENT_VIA_PJP", p); edge(ids["payment"], ids["region"], "PAYMENT_FROM_REGION", p); edge(ids["payment"], ids["country"], "PAYMENT_FROM_COUNTRY", p)
        if p.order:
            order_id = f"order-{p.order_id}"; node(order_id, "Order", p.order.order_reference, p.risk_level); edge(ids["payment"], order_id, "PAYMENT_FOR_ORDER", p)
        for alert in p.alerts:
            alert_id = f"alert-{alert.id}"; node(alert_id, "Alert", alert.alert_type, alert.severity); edge(ids["payment"], alert_id, "LINKED_TO_ALERT", p)
    if entity_type:
        allowed = {item["id"] for item in nodes.values() if item["label"].lower() == entity_type.lower()}
        connected = {edge["source"] for edge in edges if edge["target"] in allowed} | {edge["target"] for edge in edges if edge["source"] in allowed} | allowed
        nodes = {key: value for key, value in nodes.items() if key in connected}; edges = [item for item in edges if item["source"] in nodes and item["target"] in nodes]
    all_nodes = list(nodes.values())
    total_nodes = len(all_nodes)
    total_edges = len(edges)
    risk_priority = {"high": 3, "medium": 2, "low": 1}
    type_priority = {"Payment": 3, "Alert": 3, "Payer": 2, "Merchant": 2, "Outlet": 2}
    all_nodes.sort(
        key=lambda item: (
            risk_priority.get(str(item.get("risk_level", "low")), 0),
            type_priority.get(str(item.get("label", "")), 1),
            str(item.get("id", "")),
        ),
        reverse=True,
    )
    returned_nodes = all_nodes[:limit]
    returned_ids = {item["id"] for item in returned_nodes}
    returned_edges = [item for item in edges if item["source"] in returned_ids and item["target"] in returned_ids]
    return {
        "nodes": returned_nodes,
        "edges": returned_edges,
        "returned_nodes": len(returned_nodes),
        "total_nodes": total_nodes,
        "returned_edges": len(returned_edges),
        "total_edges": total_edges,
        "matching_payments": matching_payments,
        "source": "postgresql_fallback",
        "truncated": total_nodes > len(returned_nodes),
        "privacy": "Payer ditampilkan sebagai pseudonym.",
    }


@router.get("")
def get_graph(limit: int = Query(default=50, ge=1, le=200), risk_level: str | None = None, entity_type: str | None = None, search: str | None = Query(default=None, max_length=120), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return postgres_graph(db, user, limit, risk_level, entity_type, search)


@router.get("/stats")
def graph_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = postgres_graph(db, user, 200, None, None, None)
    by_type = {}
    for item in data["nodes"]: by_type[item["label"]] = by_type.get(item["label"], 0) + 1
    return {"node_count": data["total_nodes"], "edge_count": data["total_edges"], "returned_nodes": data["returned_nodes"], "nodes_by_type": by_type, "fallback_available": True}


@router.post("/sync")
def sync_graph(user: User = Depends(require_roles("analyst", "admin")), db: Session = Depends(get_db)):
    payments = db.query(PaymentEvent).order_by(PaymentEvent.transaction_time.desc()).limit(500).all()
    try:
        clear_graph()
        for payment in payments: sync_payment_to_graph(payment)
        return {"message": "Graph QRIS berhasil disinkronkan", "synced_payments": len(payments), "neo4j_available": True}
    except Exception:
        return {"message": "Neo4j tidak tersedia; explorer tetap memakai fallback PostgreSQL", "synced_payments": 0, "neo4j_available": False}
