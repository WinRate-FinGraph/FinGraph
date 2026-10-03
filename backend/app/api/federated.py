from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.qris import FederatedNode, FederatedRound, MerchantProfile
from app.models.user import User
from app.schemas.qris import FederatedNodeCreate
from app.services.audit import add_audit
from app.services.federated import run_fedavg_round


router = APIRouter(prefix="/federated", tags=["Federated Learning Prototype"])


def node_dict(node: FederatedNode) -> dict:
    return {"id": str(node.id), "node_name": node.node_name, "node_type": node.node_type, "merchant_id": str(node.merchant_id) if node.merchant_id else None, "status": node.status, "sample_count": node.sample_count, "last_round": node.last_round, "last_seen_at": node.last_seen_at, "created_at": node.created_at}


def round_dict(item: FederatedRound) -> dict:
    return {"id": str(item.id), "round_number": item.round_number, "status": item.status, "participant_count": item.participant_count, "total_samples": item.total_samples, "aggregation_method": item.aggregation_method, "global_metric_before": item.global_metric_before, "global_metric_after": item.global_metric_after, "participants": item.participant_metadata or [], "started_at": item.started_at, "completed_at": item.completed_at, "raw_data_shared": 0}


@router.get("/nodes")
def list_nodes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(FederatedNode).order_by(FederatedNode.node_name.asc()).all()
    return {"total": len(items), "items": [node_dict(item) for item in items]}


@router.get("/rounds")
def list_rounds(limit: int = Query(default=20, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(FederatedRound).order_by(FederatedRound.round_number.desc()).limit(limit).all()
    return {"total": len(items), "items": [round_dict(item) for item in items]}


@router.get("/status")
def status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    nodes = db.query(FederatedNode).count(); latest = db.query(FederatedRound).order_by(FederatedRound.round_number.desc()).first()
    return {"prototype": True, "aggregation_method": "FedAvg", "registered_nodes": nodes, "last_round": round_dict(latest) if latest else None, "privacy_message": "0 data mentah dibagikan", "implementation": "Simulator internal FedAvg yang menghitung rata-rata parameter berbobot jumlah sample."}


@router.get("/privacy-summary")
def privacy_summary(user: User = Depends(get_current_user)):
    return {"raw_rows_shared": 0, "shared": ["parameter model lokal", "jumlah sample", "metrik agregat"], "not_shared": ["baris transaksi", "identitas pembayar", "payload callback"], "limitation": "Prototype belum menerapkan secure aggregation atau differential privacy."}


@router.post("/nodes", status_code=201)
def register_node(payload: FederatedNodeCreate, user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    if db.query(FederatedNode).filter(FederatedNode.node_name == payload.node_name).first(): raise HTTPException(status_code=409, detail="Nama node sudah digunakan")
    if payload.merchant_id and not db.query(MerchantProfile).filter(MerchantProfile.id == payload.merchant_id).first(): raise HTTPException(status_code=404, detail="Merchant tidak ditemukan")
    node = FederatedNode(node_name=payload.node_name, merchant_id=payload.merchant_id, sample_count=payload.sample_count, status="online")
    db.add(node); db.flush(); add_audit(db, action="register_federated_node", entity_type="federated_node", entity_id=str(node.id), description="Node demo federated didaftarkan.", user=user, merchant_id=payload.merchant_id)
    db.commit(); db.refresh(node); return node_dict(node)


@router.post("/rounds/run")
def run_round(user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    try: item = run_fedavg_round(db)
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc))
    add_audit(db, action="run_federated_round", entity_type="federated_round", entity_id=str(item.id), description=f"FedAvg round {item.round_number} selesai tanpa berbagi data mentah.", user=user)
    db.commit(); db.refresh(item); return round_dict(item)
