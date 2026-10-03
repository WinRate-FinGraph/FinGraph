import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Float, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id"),
        nullable=True,
    )
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchant_profiles.id"), nullable=True, index=True
    )
    payment_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payment_events.id"), nullable=True, index=True
    )

    alert_type: Mapped[str] = mapped_column(String(80), default="fraud_risk", nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)

    assigned_to: Mapped[str | None] = mapped_column(String(120), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    transaction = relationship("Transaction")
    payment_event = relationship("PaymentEvent", back_populates="alerts")
    merchant = relationship("MerchantProfile", back_populates="alerts")

    __table_args__ = (
        Index("ix_alerts_merchant_status", "merchant_id", "status"),
        Index("ix_alerts_merchant_created", "merchant_id", "created_at"),
    )
