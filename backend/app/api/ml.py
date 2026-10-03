from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user, require_roles
from app.core.config import settings
from app.models.user import User
from app.ml.baseline_model import FraudBaselineModel, get_model_status
from app.ml.registry.model_registry import (
    active_model_version,
    get_active_metrics,
    list_model_artifacts,
    pin_active_model,
    promote_model_artifact,
)
from app.models.model_training_job import ModelTrainingJob
from app.models.transaction import Transaction
from app.ml.continual.adaptive_trainer import (
    get_adaptive_learning_status,
    run_adaptive_retraining,
)
from app.ml.training.train_fingraph import train_fingraph_adaptive_model
from app.ml.training.train_qris import adaptive_status as qris_adaptive_status, train_qris_adaptive, train_qris_demo_model

router = APIRouter(prefix="/ml", tags=["Machine Learning"])


def _graph_model_summary(item: dict | None) -> dict | None:
    if item is None:
        return None
    fields = (
        "version", "created_at", "split_strategy", "split_warning", "dataset_rows",
        "epochs", "best_epoch", "hidden_dim", "learning_rate", "dropout",
        "weight_decay", "patience", "seed", "threshold", "test", "baseline_test", "test_warning",
    )
    return {key: item[key] for key in fields if key in item}


@router.get("/status")
def ml_status(current_user: User = Depends(get_current_user)):
    active_metrics = get_active_metrics()

    return {
        "baseline_model": get_model_status(),
        "active_tabular_model": active_metrics,
    }


@router.get("/metrics")
def get_ml_metrics(current_user: User = Depends(get_current_user)):
    active_metrics = get_active_metrics()

    if not active_metrics:
        return {
            "model_available": False,
            "message": "No trained tabular model available yet.",
        }

    return {
        "model_available": True,
        "active_model": active_metrics,
    }


@router.get("/models")
def get_ml_models(current_user: User = Depends(get_current_user)):
    return {
        "items": list_model_artifacts(),
    }


@router.post("/train-baseline")
def train_baseline_model(db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin"))):
    transactions = (
        db.query(Transaction)
        .order_by(Transaction.transaction_time.desc())
        .limit(1000)
        .all()
    )

    try:
        model = FraudBaselineModel()
        result = model.train(transactions)
        return result

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/train/paysim")
def train_paysim_model(
    model: str = Query(default="xgboost", pattern="^(xgboost|logistic)$"),
    limit_rows: int | None = Query(default=None, ge=10000),
    current_user: User = Depends(require_roles("admin")),
):
    from app.ml.training.train_paysim import train_paysim_logistic, train_paysim_xgboost
    try:
        if model == "logistic":
            result = train_paysim_logistic(limit_rows=limit_rows)
        else:
            result = train_paysim_xgboost(limit_rows=limit_rows)

        return {
            "message": "PaySim model trained successfully",
            "result": result,
        }

    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.get("/adaptive/status")
def adaptive_learning_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    legacy = get_adaptive_learning_status(db)
    return {"qris": qris_adaptive_status(db), "legacy_paysim": legacy}


@router.post("/adaptive/retrain")
def adaptive_retrain(
    force: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("analyst", "admin")),
):
    try:
        return run_adaptive_retraining(db=db, force=force)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/train/fingraph")
def train_fingraph_model(
    min_samples: int = Query(default=10, ge=2),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    try:
        result = train_fingraph_adaptive_model(
            db=db,
            min_samples=min_samples,
        )

        return {
            "message": "FinGraph internal adaptive model trained successfully",
            "result": result,
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/train/elliptic-graphsage")
def train_elliptic_graphsage_model(
    limit_nodes: int | None = Query(default=20000, ge=1000),
    epochs: int = Query(default=5, ge=1, le=100),
    current_user: User = Depends(require_roles("admin")),
):
    from app.ml.training.train_elliptic_graphsage import train_elliptic_graphsage
    try:
        result = train_elliptic_graphsage(
            limit_nodes=limit_nodes,
            epochs=epochs,
        )

        return {
            "message": "Elliptic GraphSAGE model trained successfully",
            "result": result,
        }

    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/train/qris-graphsage", status_code=202)
def train_qris_graphsage_model(
    db: Session = Depends(get_db),
    limit_rows: int = Query(default=50000, ge=4, le=100000),
    epochs: int = Query(default=10, ge=1, le=100),
    hidden_dim: int = Query(default=64, ge=16, le=128),
    learning_rate: float = Query(default=0.003, ge=0.00001, le=0.01),
    dropout: float = Query(default=0.2, ge=0.0, le=0.6),
    weight_decay: float = Query(default=0.0001, ge=0.0, le=0.01),
    patience: int = Query(default=5, ge=1, le=10),
    seed: int = Query(default=42, ge=0, le=2147483647),
    current_user: User = Depends(require_roles("admin")),
):
    parameters = {
        "limit_rows": limit_rows,
        "epochs": epochs,
        "hidden_dim": hidden_dim,
        "learning_rate": learning_rate,
        "dropout": dropout,
        "weight_decay": weight_decay,
        "patience": patience,
        "seed": seed,
    }
    pin_active_model("qris_graph")
    job = ModelTrainingJob(
        dataset_name="qris_graph",
        status="queued",
        parameters=parameters,
        progress={"phase": "queued", "epoch": 0, "epochs": epochs},
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="QRIS GraphSAGE training already running") from None
    db.refresh(job)
    return {
        "job_id": str(job.id),
        "status": job.status,
        "parameters": job.parameters,
        "progress": job.progress,
        "attempts": job.attempts,
    }


@router.get("/graphsage/jobs/{job_id}")
def get_qris_graphsage_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    job = db.get(ModelTrainingJob, job_id)
    if job is None or job.dataset_name != "qris_graph":
        raise HTTPException(status_code=404, detail="Training job not found")
    return {
        "job_id": str(job.id),
        "status": job.status,
        "parameters": job.parameters,
        "progress": job.progress,
        "attempts": job.attempts,
        "result": job.result,
        "error": job.error,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }


@router.post("/train/qris-tabular")
def train_qris_tabular(
    sample_count: int = Query(default=1200, ge=200, le=100000),
    current_user: User = Depends(require_roles("admin")),
):
    return {"message": "Model QRIS demo berhasil dilatih", "result": train_qris_demo_model(sample_count)}


@router.post("/adaptive/qris-retrain")
def retrain_qris_adaptive(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("analyst", "admin")),
):
    try:
        return {"message": "Model adaptive QRIS berhasil dilatih", "result": train_qris_adaptive(db)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/graphsage/status")
def graphsage_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    artifacts = list_model_artifacts()
    qris_artifacts = [item for item in artifacts if item.get("dataset_name") == "qris_graph"]
    elliptic_artifacts = [item for item in artifacts if item.get("dataset_name") == "elliptic"]
    active_version = active_model_version("qris_graph")
    active = next((item for item in qris_artifacts if item.get("version") == active_version), None)
    active_job = None
    recent_jobs = []
    if current_user.role.lower() == "admin":
        active_job = (
            db.query(ModelTrainingJob)
            .filter(ModelTrainingJob.dataset_name == "qris_graph", ModelTrainingJob.status.in_(("queued", "running")))
            .order_by(ModelTrainingJob.created_at.desc())
            .first()
        )
        recent_jobs = (
            db.query(ModelTrainingJob)
            .filter(
                ModelTrainingJob.dataset_name == "qris_graph",
                ModelTrainingJob.status.in_(("completed", "failed")),
            )
            .order_by(ModelTrainingJob.created_at.desc())
            .limit(10)
            .all()
        )
    return {
        "prototype": True,
        "qris_enabled": settings.QRIS_GNN_ENABLED,
        "qris_scoring_active": settings.QRIS_GNN_ENABLED and active is not None,
        "gnn_final_weight": settings.QRIS_GNN_BLEND_WEIGHT,
        "model_available": active is not None,
        "active_model": _graph_model_summary(active),
        "qris_model_available": active is not None,
        "qris_active_model": _graph_model_summary(active),
        "candidates": [_graph_model_summary(item) for item in qris_artifacts if item.get("version") != active_version][:10],
        "active_job": {
            "job_id": str(active_job.id),
            "status": active_job.status,
            "parameters": active_job.parameters,
            "progress": active_job.progress,
            "attempts": active_job.attempts,
        } if active_job else None,
        "recent_jobs": [
            {
                "job_id": str(job.id),
                "status": job.status,
                "parameters": job.parameters,
                "progress": job.progress,
                "attempts": job.attempts,
                "result": job.result,
                "error": job.error,
                "created_at": job.created_at.isoformat(),
                "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            }
            for job in recent_jobs
        ],
        "elliptic_model_available": bool(elliptic_artifacts),
        "fallback": "legacy_ensemble",
        "note": "When enabled with an active artifact, GraphSAGE contributes its configured share of the final score; missing or failed inference falls back to the legacy ensemble.",
    }


@router.post("/graphsage/{version}/promote")
def promote_qris_graphsage_model(
    version: str,
    current_user: User = Depends(require_roles("admin")),
):
    try:
        artifact = promote_model_artifact("qris_graph", version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if artifact is None:
        raise HTTPException(status_code=404, detail="QRIS GraphSAGE candidate not found")
    return {"message": "QRIS GraphSAGE candidate promoted", "version": version, "metrics": artifact}
