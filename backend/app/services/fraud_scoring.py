from app.models.device import Device
from app.models.merchant import Merchant
from app.models.account import Account


def get_risk_level(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def get_transaction_status(score: float) -> str:
    if score >= 0.85:
        return "blocked"
    if score >= 0.60:
        return "flagged"
    return "approved"


def get_alert_severity(score: float) -> str:
    if score >= 0.85:
        return "critical"
    if score >= 0.70:
        return "high"
    if score >= 0.50:
        return "medium"
    return "low"


def calculate_fraud_score(
    amount: float,
    source_country: str,
    destination_country: str,
    sender_account: Account,
    receiver_account: Account,
    device: Device | None = None,
    merchant: Merchant | None = None,
) -> tuple[float, list[str]]:
    score = 0.08
    reasons: list[str] = []

    if amount >= 100_000_000:
        score += 0.35
        reasons.append("Very large transaction amount")
    elif amount >= 50_000_000:
        score += 0.25
        reasons.append("Large transaction amount")
    elif amount >= 10_000_000:
        score += 0.12
        reasons.append("Moderate high-value transaction")

    if source_country != destination_country:
        score += 0.18
        reasons.append("Cross-border transaction detected")

    if sender_account.risk_level == "high":
        score += 0.22
        reasons.append("Sender account has high risk level")
    elif sender_account.risk_level == "medium":
        score += 0.10
        reasons.append("Sender account has medium risk level")

    if receiver_account.risk_level == "high":
        score += 0.18
        reasons.append("Receiver account has high risk level")
    elif receiver_account.risk_level == "medium":
        score += 0.08
        reasons.append("Receiver account has medium risk level")

    if device:
        if device.is_blacklisted:
            score += 0.30
            reasons.append("Device is blacklisted")
        elif device.risk_level == "high":
            score += 0.22
            reasons.append("Device has high risk level")
        elif device.risk_level == "medium":
            score += 0.10
            reasons.append("Device has medium risk level")

    if merchant:
        if merchant.is_blacklisted:
            score += 0.25
            reasons.append("Merchant is blacklisted")
        elif merchant.risk_level == "high":
            score += 0.20
            reasons.append("Merchant has high risk level")
        elif merchant.risk_level == "medium":
            score += 0.08
            reasons.append("Merchant has medium risk level")

    final_score = max(0.01, min(round(score, 2), 0.99))

    if not reasons:
        reasons.append("No major suspicious pattern detected")

    return final_score, reasons