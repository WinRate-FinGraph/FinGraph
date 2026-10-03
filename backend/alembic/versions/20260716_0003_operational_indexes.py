"""Add operational pagination indexes.

Revision ID: 20260716_0003
Revises: 20260714_0002
"""

from alembic import op


revision = "20260716_0003"
down_revision = "20260714_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_orders_merchant_created", "orders", ["merchant_id", "created_at"])
    op.create_index("ix_payment_events_merchant_risk_time", "payment_events", ["merchant_id", "risk_level", "transaction_time"])
    op.create_index("ix_alerts_merchant_created", "alerts", ["merchant_id", "created_at"])
    op.create_index("ix_audit_logs_merchant_created", "audit_logs", ["merchant_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_merchant_created", table_name="audit_logs")
    op.drop_index("ix_alerts_merchant_created", table_name="alerts")
    op.drop_index("ix_payment_events_merchant_risk_time", table_name="payment_events")
    op.drop_index("ix_orders_merchant_created", table_name="orders")
