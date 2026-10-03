from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlalchemy.orm import Session

from app.ml.registry.model_registry import save_model_artifact
from app.models.account import Account
from app.models.device import Device
from app.models.label import Label
from app.models.merchant import Merchant
from app.models.transaction import Transaction


def label_to_target(label: str) -> int:
    if label == "fraud":
        return 1
    return 0


def risk_level_to_number(risk_level: str | None) -> int:
    if risk_level == "high":
        return 2
    if risk_level == "medium":
        return 1
    return 0


def status_to_number(status: str | None) -> int:
    if status == "blocked":
        return 2
    if status == "flagged":
        return 1
    return 0


def build_fingraph_training_dataframe(db: Session) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    labelled_items = (
        db.query(Label, Transaction)
        .join(Transaction, Label.transaction_id == Transaction.id)
        .all()
    )

    for label, transaction in labelled_items:
        sender = (
            db.query(Account)
            .filter(Account.id == transaction.sender_account_id)
            .first()
        )

        receiver = (
            db.query(Account)
            .filter(Account.id == transaction.receiver_account_id)
            .first()
        )

        device = None
        if transaction.device_id:
            device = db.query(Device).filter(Device.id == transaction.device_id).first()

        merchant = None
        if transaction.merchant_id:
            merchant = (
                db.query(Merchant)
                .filter(Merchant.id == transaction.merchant_id)
                .first()
            )

        is_cross_border = transaction.source_country != transaction.destination_country

        rows.append(
            {
                "amount": float(transaction.amount),
                "currency": transaction.currency,
                "channel": transaction.channel,
                "source_country": transaction.source_country,
                "destination_country": transaction.destination_country,
                "is_cross_border": int(is_cross_border),
                "rule_fraud_score": float(transaction.fraud_score or 0),
                "transaction_status_num": status_to_number(transaction.status),
                "sender_risk_num": risk_level_to_number(sender.risk_level if sender else None),
                "receiver_risk_num": risk_level_to_number(receiver.risk_level if receiver else None),
                "device_risk_num": risk_level_to_number(device.risk_level if device else None),
                "device_is_blacklisted": int(device.is_blacklisted) if device else 0,
                "merchant_risk_num": risk_level_to_number(merchant.risk_level if merchant else None),
                "merchant_is_blacklisted": int(merchant.is_blacklisted) if merchant else 0,
                "label": label.label,
                "target": label_to_target(label.label),
            }
        )

    return pd.DataFrame(rows)


def build_fingraph_preprocessor() -> ColumnTransformer:
    categorical_features = [
        "currency",
        "channel",
        "source_country",
        "destination_country",
    ]

    numeric_features = [
        "amount",
        "is_cross_border",
        "rule_fraud_score",
        "transaction_status_num",
        "sender_risk_num",
        "receiver_risk_num",
        "device_risk_num",
        "device_is_blacklisted",
        "merchant_risk_num",
        "merchant_is_blacklisted",
    ]

    return ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), categorical_features),
            ("numeric", StandardScaler(), numeric_features),
        ]
    )


def evaluate_fingraph_model(
    model: Pipeline,
    x_test: pd.DataFrame,
    y_test: pd.Series,
    threshold: float = 0.5,
) -> dict[str, Any]:
    probabilities = model.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= threshold).astype(int)

    labels_present = sorted(set(y_test.tolist()) | set(predictions.tolist()))

    if len(labels_present) < 2:
        roc_auc = None
        pr_auc = None
        tn = fp = fn = tp = 0
    else:
        tn, fp, fn, tp = confusion_matrix(y_test, predictions).ravel()
        roc_auc = roc_auc_score(y_test, probabilities)
        pr_auc = average_precision_score(y_test, probabilities)

    precision = precision_score(y_test, predictions, zero_division=0)
    recall = recall_score(y_test, predictions, zero_division=0)
    f1 = f1_score(y_test, predictions, zero_division=0)

    if len(labels_present) < 2:
        false_positive_rate = 0
        false_negative_rate = 0
        confusion_payload = None
    else:
        false_positive_rate = fp / (fp + tn) if (fp + tn) else 0
        false_negative_rate = fn / (fn + tp) if (fn + tp) else 0
        confusion_payload = {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        }

    return {
        "threshold": threshold,
        "roc_auc": round(float(roc_auc), 6) if roc_auc is not None else None,
        "pr_auc": round(float(pr_auc), 6) if pr_auc is not None else None,
        "precision": round(float(precision), 6),
        "recall": round(float(recall), 6),
        "f1": round(float(f1), 6),
        "false_positive_rate": round(float(false_positive_rate), 6),
        "false_negative_rate": round(float(false_negative_rate), 6),
        "confusion_matrix": confusion_payload,
        "classification_report": classification_report(
            y_test,
            predictions,
            output_dict=True,
            zero_division=0,
        ),
    }


def train_fingraph_adaptive_model(
    db: Session,
    min_samples: int = 10,
) -> dict[str, Any]:
    df = build_fingraph_training_dataframe(db)

    if df.empty:
        raise ValueError("No labelled FinGraph transactions available.")

    if len(df) < min_samples:
        raise ValueError(
            f"Not enough labelled samples. Need at least {min_samples}, got {len(df)}."
        )

    fraud_count = int(df["target"].sum())
    legitimate_count = int((df["target"] == 0).sum())

    if fraud_count == 0 or legitimate_count == 0:
        raise ValueError(
            "Training requires both fraud and non-fraud labels. "
            f"fraud={fraud_count}, non_fraud={legitimate_count}"
        )

    feature_columns = [
        "amount",
        "currency",
        "channel",
        "source_country",
        "destination_country",
        "is_cross_border",
        "rule_fraud_score",
        "transaction_status_num",
        "sender_risk_num",
        "receiver_risk_num",
        "device_risk_num",
        "device_is_blacklisted",
        "merchant_risk_num",
        "merchant_is_blacklisted",
    ]

    x = df[feature_columns]
    y = df["target"].astype(int)

    # Kalau data masih sangat kecil, stratified split bisa gagal.
    # Untuk MVP, kalau sample < 20 kita train/evaluate pada data yang sama dengan warning metric.
    if len(df) < 20:
        x_train, x_test, y_train, y_test = x, x, y, y
        evaluation_mode = "train_set_evaluation_small_sample"
    else:
        x_train, x_test, y_train, y_test = train_test_split(
            x,
            y,
            test_size=0.25,
            random_state=42,
            stratify=y,
        )
        evaluation_mode = "holdout_split"

    model = Pipeline(
        steps=[
            ("preprocessor", build_fingraph_preprocessor()),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=150,
                    max_depth=6,
                    class_weight="balanced",
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    model.fit(x_train, y_train)

    metrics = evaluate_fingraph_model(model, x_test, y_test)

    metrics.update(
        {
            "dataset_rows": int(len(df)),
            "train_rows": int(len(x_train)),
            "test_rows": int(len(x_test)),
            "fraud_count": fraud_count,
            "legitimate_count": legitimate_count,
            "fraud_ratio": round(float(fraud_count / len(df)), 8),
            "features": feature_columns,
            "model_family": "random_forest",
            "evaluation_mode": evaluation_mode,
            "warning": (
                "Small sample internal model. Use as adaptive signal, not primary model."
                if len(df) < 50
                else None
            ),
        }
    )

    return save_model_artifact(
        model=model,
        preprocessor=None,
        metrics=metrics,
        dataset_name="fingraph_internal",
        model_name="adaptive_random_forest",
    )