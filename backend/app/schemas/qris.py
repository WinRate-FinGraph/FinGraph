from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class MerchantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    business_type: str | None = Field(default=None, min_length=2, max_length=100)
    owner_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    province: str | None = Field(default=None, max_length=100)


class SubscriptionPlanUpdate(BaseModel):
    plan: Literal["basic", "growth", "premium"]


class OutletCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    address: str = Field(min_length=3, max_length=500)
    city: str = Field(min_length=2, max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class QRISProfileCreate(BaseModel):
    outlet_id: UUID
    nmid: str = Field(min_length=6, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    qris_type: Literal["MPM_STATIC", "MPM_DYNAMIC", "CPM"] = "MPM_DYNAMIC"
    acquirer_name: str = Field(min_length=2, max_length=120)
    settlement_account: str = Field(min_length=4, max_length=80)
    payload: str = Field(min_length=6, max_length=4096)


class QRISVerifyRequest(BaseModel):
    qris_profile_id: UUID | None = None
    payload: str = Field(min_length=6, max_length=4096)


class OrderCreate(BaseModel):
    outlet_id: UUID
    expected_amount: float = Field(gt=0, le=10_000_000_000)
    currency: str = Field(default="IDR", min_length=3, max_length=3)
    description: str = Field(min_length=2, max_length=500)
    customer_reference: str | None = Field(default=None, max_length=120)
    expires_at: datetime | None = None

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()


class OrderStatusUpdate(BaseModel):
    status: Literal["pending", "awaiting_payment", "paid", "held", "completed", "cancelled"]


class PaymentGenerateRequest(BaseModel):
    order_id: UUID
    amount: float | None = Field(default=None, gt=0, le=10_000_000_000)
    payer_identifier: str = Field(default="demo-payer", min_length=3, max_length=120)
    provider_reference: str | None = Field(default=None, min_length=6, max_length=100)
    source_city: str = Field(default="Surakarta", min_length=2, max_length=100)
    source_region: str = Field(default="Jawa Tengah", min_length=2, max_length=100)
    source_country: str = Field(default="ID", min_length=2, max_length=3)
    payment_status: Literal["pending", "success", "failed", "expired", "reversed", "refunded"] = "success"


class PaymentCheckRequest(BaseModel):
    provider_reference: str = Field(min_length=3, max_length=100)
    amount: float = Field(gt=0, le=10_000_000_000)
    order_reference: str | None = Field(default=None, max_length=80)
    transaction_time: datetime | None = None


class PaymentMatchRequest(BaseModel):
    order_id: UUID


class LabelQRISCreate(BaseModel):
    payment_event_id: UUID
    label: Literal["fraud", "legitimate", "suspicious"]
    merchant_decision: Literal["approve", "verify", "hold", "report"]
    notes: str | None = Field(default=None, max_length=1000)


class AlertStatusUpdate(BaseModel):
    status: Literal["open", "investigating", "resolved", "dismissed"]
    assigned_to: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)


class FederatedNodeCreate(BaseModel):
    node_name: str = Field(min_length=3, max_length=120)
    merchant_id: UUID | None = None
    sample_count: int = Field(default=100, ge=10, le=1_000_000)
