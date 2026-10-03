from __future__ import annotations

from datetime import datetime
from typing import Any

import torch
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ml.graph.dataset import CanonicalPayment, GraphBuilder
from app.ml.graph.model import build_model
from app.ml.graph.training import _pyg_data
from app.ml.registry.model_registry import load_latest_model_by_dataset
from app.models.qris import PaymentEvent


def _row(payment: PaymentEvent) -> CanonicalPayment:
    return CanonicalPayment(
        payment_id=f"payment_{payment.transaction_reference}",
        timestamp=payment.transaction_time,
        payer_id=str(payment.payer_pseudonym),
        merchant_id=str(payment.merchant_id),
        outlet_id=str(payment.outlet_id),
        qris_id=str(payment.qris_profile_id),
        amount=float(payment.amount),
        payment_status=payment.payment_status,
        source_region=payment.source_region,
        source_country=payment.source_country,
        destination_region=payment.destination_region,
        destination_country=payment.destination_country,
        pjp_id=payment.acquirer_name or None,
    )


def score_qris_gnn(db: Session, payment: PaymentEvent, max_nodes: int | None = None) -> tuple[float | None, dict[str, Any]]:
    artifact = load_latest_model_by_dataset("qris_graph")
    if not artifact:
        return None, {"enabled": True, "fallback_reason": "qris_graphsage_artifact_missing"}
    try:
        model_payload = artifact["model"]
        query = db.query(PaymentEvent).filter(
            or_(
                PaymentEvent.payer_pseudonym == payment.payer_pseudonym,
                PaymentEvent.merchant_id == payment.merchant_id,
                PaymentEvent.outlet_id == payment.outlet_id,
                PaymentEvent.qris_profile_id == payment.qris_profile_id,
            )
        ).order_by(PaymentEvent.transaction_time.desc()).limit(max_nodes or settings.QRIS_GNN_MAX_NODES)
        rows = [_row(item) for item in query.all()]
        current = _row(payment)
        if not any(item.payment_id == current.payment_id for item in rows):
            rows.append(current)
        builder = GraphBuilder.from_schema(model_payload["graph_schema"])
        snapshot = builder.build(rows)
        data = _pyg_data(snapshot)
        model = build_model(model_payload["graph_schema"], model_payload.get("hidden_dim", 64), model_payload.get("dropout", 0.2))
        with torch.no_grad():
            model(data.x_dict, data.edge_index_dict)
        model.load_state_dict(model_payload["state_dict"])
        model.eval()
        with torch.no_grad():
            logits = model(data.x_dict, data.edge_index_dict)
            score = float(torch.softmax(logits, dim=1)[snapshot.payment_indices[current.payment_id], 1])
        return round(max(0.0, min(score, 1.0)), 4), {
            "enabled": True,
            "fallback_reason": None,
            "model_version": artifact.get("version"),
            "mode": snapshot.mode,
            "node_count": sum(value.shape[0] for value in snapshot.x_dict.values()),
        }
    except Exception:
        return None, {"enabled": True, "fallback_reason": "qris_graphsage_inference_failed"}
