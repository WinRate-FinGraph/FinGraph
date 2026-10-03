from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.ml.registry.model_registry import load_latest_model_by_dataset


@dataclass
class TabularScoringResult:
    tabular_ml_score: float
    tabular_risk_level: str
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


def build_paysim_like_features(
    amount: float,
    channel: str,
    source_country: str,
    destination_country: str,
    sender_risk_level: str,
    receiver_risk_level: str,
    device_risk_level: str = "low",
    device_is_blacklisted: bool = False,
    merchant_risk_level: str = "low",
    merchant_is_blacklisted: bool = False,
) -> dict[str, Any]:
    risk_boost = 1.0

    if sender_risk_level == "high":
        risk_boost += 0.45
    elif sender_risk_level == "medium":
        risk_boost += 0.20

    if receiver_risk_level == "high":
        risk_boost += 0.35
    elif receiver_risk_level == "medium":
        risk_boost += 0.15

    if device_risk_level == "high" or device_is_blacklisted:
        risk_boost += 0.45
    elif device_risk_level == "medium":
        risk_boost += 0.20

    if merchant_risk_level == "high" or merchant_is_blacklisted:
        risk_boost += 0.35
    elif merchant_risk_level == "medium":
        risk_boost += 0.15

    if source_country != destination_country:
        risk_boost += 0.25

    estimated_oldbalance_origin = max(float(amount) * risk_boost, float(amount) + 1)
    estimated_newbalance_origin = max(estimated_oldbalance_origin - float(amount), 0)

    estimated_oldbalance_dest = max(float(amount) * 0.15, 1)
    estimated_newbalance_dest = estimated_oldbalance_dest + float(amount)

    origin_balance_delta = estimated_oldbalance_origin - estimated_newbalance_origin
    dest_balance_delta = estimated_newbalance_dest - estimated_oldbalance_dest

    amount_to_old_origin_balance_ratio = (
        float(amount) / estimated_oldbalance_origin
        if estimated_oldbalance_origin
        else 0
    )

    amount_to_old_dest_balance_ratio = (
        float(amount) / estimated_oldbalance_dest
        if estimated_oldbalance_dest
        else 0
    )

    if channel in {"mobile_banking", "internet_banking"}:
        paysim_type = "TRANSFER"
    elif channel in {"payment_gateway", "e_wallet"}:
        paysim_type = "PAYMENT"
    elif channel == "atm":
        paysim_type = "CASH_OUT"
    else:
        paysim_type = "TRANSFER"

    return {
        "step": 1,
        "type": paysim_type,
        "amount": float(amount),
        "oldbalanceOrg": float(estimated_oldbalance_origin),
        "newbalanceOrig": float(estimated_newbalance_origin),
        "oldbalanceDest": float(estimated_oldbalance_dest),
        "newbalanceDest": float(estimated_newbalance_dest),
        "isFlaggedFraud": int(float(amount) >= 200_000_000),
        "origin_balance_delta": float(origin_balance_delta),
        "dest_balance_delta": float(dest_balance_delta),
        "amount_to_old_origin_balance_ratio": float(amount_to_old_origin_balance_ratio),
        "amount_to_old_dest_balance_ratio": float(amount_to_old_dest_balance_ratio),
        "origin_is_customer": 1,
        "dest_is_customer": 1,
        "dest_is_merchant": int(merchant_risk_level != "unknown"),
    }


def score_with_active_tabular_model(features: dict[str, Any]) -> TabularScoringResult:
    # IMPORTANT:
    # Do not load active_tabular_model.joblib here, because internal adaptive training
    # may overwrite the generic active model. PaySim scorer must load the latest
    # PaySim artifact only.
    artifact = load_latest_model_by_dataset("paysim")

    if artifact is None:
        return TabularScoringResult(
            tabular_ml_score=0.0,
            tabular_risk_level="unknown",
            used_model=False,
        )

    model = artifact["model"]
    preprocessor = artifact.get("preprocessor")

    row = pd.DataFrame([features])

    if preprocessor is not None:
        row_processed = preprocessor.transform(row)
        probability = float(model.predict_proba(row_processed)[:, 1][0])
    else:
        # Backward-compatible if artifact stores a full sklearn Pipeline.
        probability = float(model.predict_proba(row)[:, 1][0])

    probability = round(max(0.0, min(probability, 0.99)), 4)

    return TabularScoringResult(
        tabular_ml_score=probability,
        tabular_risk_level=risk_level_from_score(probability),
        used_model=True,
        model_version=artifact.get("version"),
        model_name=artifact.get("model_name"),
        dataset_name=artifact.get("dataset_name"),
    )