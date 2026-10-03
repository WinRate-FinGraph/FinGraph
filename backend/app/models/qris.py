import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class MerchantProfile(TimestampMixin, Base):
    __tablename__ = "merchant_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, index=True)
    merchant_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    business_type: Mapped[str] = mapped_column(String(100))
    owner_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    address: Mapped[str] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(100), index=True)
    province: Mapped[str] = mapped_column(String(100))
    country_code: Mapped[str] = mapped_column(String(3), default="ID")
    risk_level: Mapped[str] = mapped_column(String(20), default="low", index=True)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    subscription_plan: Mapped[str] = mapped_column(String(20), default="basic", nullable=False, index=True)
    subscription_status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    plan_changed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user = relationship("User", back_populates="merchant_profile")
    outlets = relationship("Outlet", back_populates="merchant")
    qris_profiles = relationship("QRISProfile", back_populates="merchant")
    orders = relationship("Order", back_populates="merchant")
    payments = relationship("PaymentEvent", back_populates="merchant")
    alerts = relationship("Alert", back_populates="merchant")


class Outlet(TimestampMixin, Base):
    __tablename__ = "outlets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("merchant_profiles.id"), index=True)
    outlet_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    address: Mapped[str] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(100), index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="low")
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)

    merchant = relationship("MerchantProfile", back_populates="outlets")
    qris_profiles = relationship("QRISProfile", back_populates="outlet")


class QRISProfile(TimestampMixin, Base):
    __tablename__ = "qris_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("merchant_profiles.id"), index=True)
    outlet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("outlets.id"), index=True)
    nmid: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    qris_type: Mapped[str] = mapped_column(String(30), default="MPM_DYNAMIC")
    acquirer_name: Mapped[str] = mapped_column(String(120))
    masked_settlement_account: Mapped[str] = mapped_column(String(80))
    payload_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    merchant = relationship("MerchantProfile", back_populates="qris_profiles")
    outlet = relationship("Outlet", back_populates="qris_profiles")


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_reference: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    merchant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("merchant_profiles.id"), index=True)
    outlet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("outlets.id"), index=True)
    expected_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="IDR")
    description: Mapped[str] = mapped_column(Text)
    customer_reference: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="awaiting_payment", index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    merchant = relationship("MerchantProfile", back_populates="orders")
    outlet = relationship("Outlet")
    payments = relationship("PaymentEvent", back_populates="order")

    __table_args__ = (
        Index("ix_orders_merchant_status", "merchant_id", "status"),
        Index("ix_orders_merchant_created", "merchant_id", "created_at"),
    )


class PaymentEvent(TimestampMixin, Base):
    __tablename__ = "payment_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_reference: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    provider_reference: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True, index=True)
    merchant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("merchant_profiles.id"), index=True)
    outlet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("outlets.id"), index=True)
    qris_profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qris_profiles.id"), index=True)
    payer_pseudonym: Mapped[str] = mapped_column(String(80), index=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    expected_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="IDR")
    payment_method: Mapped[str] = mapped_column(String(20), default="QRIS")
    category: Mapped[str] = mapped_column(String(80), default="Umum", nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="rendah", nullable=False, index=True)
    qris_type: Mapped[str] = mapped_column(String(30))
    acquirer_name: Mapped[str] = mapped_column(String(120))
    payment_status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    callback_received: Mapped[bool] = mapped_column(Boolean, default=False)
    callback_received_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    callback_delay_seconds: Mapped[int | None] = mapped_column(nullable=True)
    source_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_country: Mapped[str] = mapped_column(String(3), default="ID")
    destination_city: Mapped[str] = mapped_column(String(100))
    destination_region: Mapped[str] = mapped_column(String(100))
    destination_country: Mapped[str] = mapped_column(String(3), default="ID")
    is_cross_region: Mapped[bool] = mapped_column(Boolean, default=False)
    is_cross_border: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_payload_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="received", index=True)
    fraud_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(20), default="low", index=True)
    recommendation_code: Mapped[str] = mapped_column(String(50), default="VERIFY")
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_score: Mapped[float] = mapped_column(Float, default=0.0)
    tabular_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    adaptive_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    graph_score: Mapped[float] = mapped_column(Float, default=0.0)
    scoring_explanation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scenario_name: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    claimed_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    signature_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    replay_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    transaction_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    order = relationship("Order", back_populates="payments")
    merchant = relationship("MerchantProfile", back_populates="payments")
    outlet = relationship("Outlet")
    qris_profile = relationship("QRISProfile")
    alerts = relationship("Alert", back_populates="payment_event")
    labels = relationship("Label", back_populates="payment_event")

    __table_args__ = (
        Index("ix_payment_events_merchant_time", "merchant_id", "transaction_time"),
        Index("ix_payment_events_merchant_risk", "merchant_id", "risk_level"),
        Index("ix_payment_events_merchant_risk_time", "merchant_id", "risk_level", "transaction_time"),
        Index("ix_payment_events_merchant_priority_time", "merchant_id", "priority", "transaction_time"),
    )


class Settlement(Base):
    __tablename__ = "settlements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("merchant_profiles.id"), index=True)
    payment_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("payment_events.id"), nullable=True, index=True)
    settlement_reference: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    gross_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    fee_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    net_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    settlement_status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    settlement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FederatedNode(Base):
    __tablename__ = "federated_nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_name: Mapped[str] = mapped_column(String(120), unique=True)
    node_type: Mapped[str] = mapped_column(String(50), default="merchant_demo")
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("merchant_profiles.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="online")
    sample_count: Mapped[int] = mapped_column(default=0)
    last_round: Mapped[int] = mapped_column(default=0)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FederatedRound(Base):
    __tablename__ = "federated_rounds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_number: Mapped[int] = mapped_column(unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="completed")
    participant_count: Mapped[int] = mapped_column(default=0)
    total_samples: Mapped[int] = mapped_column(default=0)
    aggregation_method: Mapped[str] = mapped_column(String(30), default="FedAvg")
    global_metric_before: Mapped[float] = mapped_column(Float, default=0.0)
    global_metric_after: Mapped[float] = mapped_column(Float, default=0.0)
    participant_metadata: Mapped[list | None] = mapped_column(JSON, nullable=True)
    global_parameters: Mapped[list | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
