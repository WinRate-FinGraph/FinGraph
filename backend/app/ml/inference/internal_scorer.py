from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.ml.registry.model_registry import load_latest_model_by_dataset


@dataclass
class InternalScoringResult:
    internal_ml_score: float
    internal_risk_level: str
    used_model: bool
    model_version: str | None = None
    model_name: str | None = None
    dataset_name: str | None = None


def risk_level_from_score(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


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


def build_fingraph_internal_features(
    amount: float,
    currency: str,
    channel: str,
    source_country: str,
    destination_country: str,
    rule_fraud_score: float,
    transaction_status: str,
    sender_risk_level: str,
    receiver_risk_level: str,
    device_risk_level: str = "low",
    device_is_blacklisted: bool = False,
    merchant_risk_level: str = "low",
    merchant_is_blacklisted: bool = False,
) -> dict[str, Any]:
    return {
        "amount": float(amount),
        "currency": currency,
        "channel": channel,
        "source_country": source_country,
        "destination_country": destination_country,
        "is_cross_border": int(source_country != destination_country),
        "rule_fraud_score": float(rule_fraud_score),
        "transaction_status_num": status_to_number(transaction_status),
        "sender_risk_num": risk_level_to_number(sender_risk_level),
        "receiver_risk_num": risk_level_to_number(receiver_risk_level),
        "device_risk_num": risk_level_to_number(device_risk_level),
        "device_is_blacklisted": int(device_is_blacklisted),
        "merchant_risk_num": risk_level_to_number(merchant_risk_level),
        "merchant_is_blacklisted": int(merchant_is_blacklisted),
    }


def score_with_internal_adaptive_model(
    features: dict[str, Any],
) -> InternalScoringResult:
    artifact = load_latest_model_by_dataset("fingraph_internal")

    if artifact is None:
        return InternalScoringResult(
            internal_ml_score=0.0,
            internal_risk_level="unknown",
            used_model=False,
        )

    model = artifact["model"]
    row = pd.DataFrame([features])

    probability = float(model.predict_proba(row)[:, 1][0])
    probability = round(max(0.0, min(probability, 0.99)), 4)

    return InternalScoringResult(
        internal_ml_score=probability,
        internal_risk_level=risk_level_from_score(probability),
        used_model=True,
        model_version=artifact.get("version"),
        model_name=artifact.get("model_name"),
        dataset_name=artifact.get("dataset_name"),
    )