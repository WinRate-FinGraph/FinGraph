from datetime import datetime, timezone

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ml.registry.model_registry import save_model_artifact
from app.models.label import Label
from app.models.qris import PaymentEvent


QRIS_FEATURES = [
    "amount", "expected_amount", "amount_difference", "amount_ratio", "payment_hour",
    "callback_delay_seconds", "payment_count_10m", "failed_count_30m", "payer_transaction_count",
    "payer_fraud_count", "payer_suspicious_count", "merchant_average_amount",
    "amount_deviation_from_merchant", "is_new_payer", "is_duplicate_reference", "is_cross_region",
    "is_cross_border", "merchant_risk", "outlet_risk", "qris_profile_match", "order_age_seconds", "payment_velocity",
]


def _metrics(model, x_test, y_test, sample_count: int) -> dict:
    probabilities = model.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    return {
        "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
        "f1": round(float(f1_score(y_test, predictions)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, probabilities)), 4),
        "sample_count": sample_count, "features": QRIS_FEATURES,
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "model_family": "logistic_regression", "data_source": "synthetic_qris_demo",
    }


def train_qris_demo_model(sample_count: int = 1200) -> dict:
    rng = np.random.default_rng(42)
    rows = []
    targets = []
    for _ in range(sample_count):
        expected = float(rng.choice([25_000, 50_000, 150_000, 350_000, 1_500_000]))
        mismatch = rng.random() < 0.16
        amount = expected * (rng.choice([0.1, 0.5, 1.5]) if mismatch else 1.0)
        callback_delay = int(rng.exponential(55))
        failures = int(rng.poisson(0.5)); velocity = int(rng.poisson(1.8))
        duplicate = int(rng.random() < 0.04); cross_region = int(rng.random() < 0.25); cross_border = int(rng.random() < 0.06)
        fraud = int(mismatch or duplicate or failures >= 4 or (velocity >= 8 and amount <= 50_000))
        row = {
            "amount": amount, "expected_amount": expected, "amount_difference": amount - expected,
            "amount_ratio": amount / expected, "payment_hour": int(rng.integers(0, 24)),
            "callback_delay_seconds": callback_delay, "payment_count_10m": velocity,
            "failed_count_30m": failures, "payer_transaction_count": int(rng.integers(1, 20)),
            "payer_fraud_count": fraud * int(rng.integers(0, 3)), "payer_suspicious_count": int(rng.integers(0, 3)),
            "merchant_average_amount": expected, "amount_deviation_from_merchant": abs(amount - expected) / expected,
            "is_new_payer": int(rng.random() < 0.3), "is_duplicate_reference": duplicate,
            "is_cross_region": cross_region, "is_cross_border": cross_border, "merchant_risk": 0.1,
            "outlet_risk": 0.1, "qris_profile_match": 1, "order_age_seconds": int(rng.integers(5, 3600)),
            "payment_velocity": velocity / 10,
        }
        rows.append([row[name] for name in QRIS_FEATURES]); targets.append(fraud)
    x = np.asarray(rows, dtype=float); y = np.asarray(targets, dtype=int)
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42, stratify=y)
    model = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42).fit(x_train, y_train)
    metrics = _metrics(model, x_test, y_test, sample_count)
    metrics["class_distribution"] = {"legitimate": int((y == 0).sum()), "fraud": int((y == 1).sum())}
    return save_model_artifact(model, None, metrics, "qris_demo", "logistic_regression")


def adaptive_status(db: Session) -> dict:
    labels = db.query(Label).filter(Label.payment_event_id.isnot(None), Label.label.in_(["fraud", "legitimate", "suspicious"])).all()
    distribution = {name: sum(1 for item in labels if item.label == name) for name in ("fraud", "legitimate", "suspicious")}
    usable = distribution["fraud"] + distribution["legitimate"]
    return {
        "labels_available": len(labels), "usable_binary_labels": usable,
        "labels_required": settings.QRIS_ADAPTIVE_MIN_LABELS,
        "ready_for_training": usable >= settings.QRIS_ADAPTIVE_MIN_LABELS and distribution["fraud"] > 0 and distribution["legitimate"] > 0,
        "class_distribution": distribution,
    }


def train_qris_adaptive(db: Session) -> dict:
    status = adaptive_status(db)
    if not status["ready_for_training"]:
        raise ValueError("Label valid belum cukup atau baru memiliki satu kelas")
    labels = db.query(Label).filter(Label.payment_event_id.isnot(None), Label.label.in_(["fraud", "legitimate"])).order_by(Label.created_at.asc()).all()
    rows = []; targets = []
    for label in labels:
        payment: PaymentEvent | None = label.payment_event
        features = (payment.scoring_explanation or {}).get("features") if payment else None
        if not features: continue
        rows.append([float(features.get(name, 0)) for name in QRIS_FEATURES]); targets.append(1 if label.label == "fraud" else 0)
    y = np.asarray(targets, dtype=int)
    if len(rows) < settings.QRIS_ADAPTIVE_MIN_LABELS or len(set(targets)) < 2:
        raise ValueError("Sample adaptive yang memiliki fitur belum cukup atau hanya satu kelas")
    x = np.asarray(rows, dtype=float)
    model = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42).fit(x, y)
    probabilities = model.predict_proba(x)[:, 1]; predictions = (probabilities >= 0.5).astype(int)
    metrics = {"accuracy": round(float(accuracy_score(y, predictions)), 4), "f1": round(float(f1_score(y, predictions)), 4), "sample_count": len(y), "features": QRIS_FEATURES, "training_timestamp": datetime.now(timezone.utc).isoformat(), "class_distribution": status["class_distribution"], "model_family": "adaptive_logistic_regression", "warning": "Evaluasi training-set untuk prototype; production memerlukan holdout temporal."}
    return save_model_artifact(model, None, metrics, "qris_adaptive", "logistic_regression")
