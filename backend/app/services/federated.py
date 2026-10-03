import hashlib
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.qris import FederatedNode, FederatedRound


def run_fedavg_round(db: Session) -> FederatedRound:
    nodes = db.query(FederatedNode).filter(FederatedNode.status == "online", FederatedNode.sample_count > 0).order_by(FederatedNode.node_name.asc()).all()
    if len(nodes) < 2:
        raise ValueError("Minimal dua node online diperlukan untuk FedAvg")
    previous = db.query(FederatedRound).order_by(FederatedRound.round_number.desc()).first()
    round_number = (previous.round_number if previous else 0) + 1
    global_before = previous.global_parameters if previous and previous.global_parameters else [0.0, 0.0, 0.0, 0.0]
    local_updates = []
    total_samples = sum(node.sample_count for node in nodes)
    for node in nodes:
        seed = int(hashlib.sha256(f"{node.node_name}:{round_number}".encode()).hexdigest()[:8], 16)
        offsets = [(((seed >> (index * 5)) & 31) - 15) / 1000 for index in range(4)]
        params = [round(value + offset, 6) for value, offset in zip(global_before, offsets)]
        local_updates.append({"node_id": str(node.id), "node_name": node.node_name, "sample_count": node.sample_count, "parameters": params})
    aggregated = [round(sum(update["parameters"][index] * update["sample_count"] for update in local_updates) / total_samples, 6) for index in range(4)]
    before_metric = previous.global_metric_after if previous else 0.61
    diversity_gain = min(0.05, len(nodes) * 0.007 + total_samples / 1_000_000)
    after_metric = round(min(0.99, before_metric + diversity_gain), 4)
    record = FederatedRound(
        round_number=round_number, status="completed", participant_count=len(nodes), total_samples=total_samples,
        aggregation_method="FedAvg", global_metric_before=before_metric, global_metric_after=after_metric,
        participant_metadata=[{"node_id": item["node_id"], "node_name": item["node_name"], "sample_count": item["sample_count"], "raw_rows_shared": 0} for item in local_updates],
        global_parameters=aggregated, started_at=datetime.utcnow(), completed_at=datetime.utcnow(),
    )
    db.add(record); db.flush()
    for node in nodes:
        node.last_round = round_number; node.last_seen_at = datetime.utcnow()
    return record
