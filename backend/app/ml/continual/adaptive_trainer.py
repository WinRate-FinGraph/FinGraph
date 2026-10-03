from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.ml.registry.model_registry import get_active_metrics
from app.models.label import Label


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def count_labels_since_last_training(db: Session) -> int:
    active_metrics = get_active_metrics()

    if not active_metrics:
        return db.query(Label).count()

    last_trained_at = _parse_datetime(active_metrics.get("created_at"))

    if not last_trained_at:
        return db.query(Label).count()

    return (
        db.query(Label)
        .filter(Label.created_at > last_trained_at)
        .count()
    )


def get_adaptive_learning_status(db: Session) -> dict[str, Any]:
    active_metrics = get_active_metrics()
    new_labels = count_labels_since_last_training(db)

    min_labels = settings.ADAPTIVE_RETRAIN_MIN_LABELS

    return {
        "adaptive_learning_enabled": True,
        "active_model": active_metrics,
        "new_labels_since_last_training": new_labels,
        "min_labels_required": min_labels,
        "ready_for_retraining": new_labels >= min_labels,
        "recommended_action": (
            "retrain"
            if new_labels >= min_labels
            else f"collect {min_labels - new_labels} more labels"
        ),
    }


def run_adaptive_retraining(
    db: Session,
    force: bool = False,
) -> dict[str, Any]:
    from app.ml.training.train_paysim import train_paysim_xgboost
    new_labels = count_labels_since_last_training(db)
    min_labels = settings.ADAPTIVE_RETRAIN_MIN_LABELS

    if not force and new_labels < min_labels:
        return {
            "retrained": False,
            "reason": "Not enough new labels for adaptive retraining",
            "new_labels_since_last_training": new_labels,
            "min_labels_required": min_labels,
        }

    result = train_paysim_xgboost(
        limit_rows=settings.ADAPTIVE_RETRAIN_LIMIT_ROWS,
    )

    return {
        "retrained": True,
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "new_labels_since_last_training": new_labels,
        "min_labels_required": min_labels,
        "training_result": result,
    }
