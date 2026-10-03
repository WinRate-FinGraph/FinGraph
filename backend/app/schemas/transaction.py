from uuid import UUID
from pydantic import BaseModel, Field


class TransactionCreate(BaseModel):
    sender_account_id: str
    receiver_account_id: str
    device_id: str | None = None
    merchant_id: str | None = None
    amount: float
    currency: str = "IDR"
    channel: str
    source_country: str
    destination_country: str
    ip_address: str | None = None



class TransactionCreateResponse(BaseModel):
    message: str
    transaction_id: str
    transaction_reference: str
    fraud_score: float
    risk_level: str
    status: str
    alert_created: bool

    ml_model_used: bool = False
    ml_score: float | None = None

    tabular_ml_model_used: bool = False
    tabular_ml_score: float | None = None
    tabular_model_version: str | None = None

    internal_ml_model_used: bool = False
    internal_ml_score: float | None = None
    internal_model_version: str | None = None

    ensemble_mode: str | None = None