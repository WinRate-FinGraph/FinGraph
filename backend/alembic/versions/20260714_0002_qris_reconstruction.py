"""Add FinGraph QRIS domain without deleting legacy platform data.

Revision ID: 20260714_0002
Revises: b81c16e70739
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260714_0002"
down_revision: Union[str, None] = "b81c16e70739"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE users SET role = CASE UPPER(role) WHEN 'ADMIN' THEN 'admin' WHEN 'ANALYST' THEN 'analyst' ELSE 'merchant' END")

    op.create_table(
        "merchant_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("merchant_code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("business_type", sa.String(100), nullable=False),
        sa.Column("owner_name", sa.String(120), nullable=False),
        sa.Column("phone", sa.String(40), nullable=True),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("province", sa.String(100), nullable=False),
        sa.Column("country_code", sa.String(3), server_default="ID", nullable=False),
        sa.Column("risk_level", sa.String(20), server_default="low", nullable=False),
        sa.Column("status", sa.String(30), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("merchant_code"),
        sa.UniqueConstraint("user_id"),
    )
    for column in ("user_id", "merchant_code", "name", "city", "risk_level", "status"):
        op.create_index(f"ix_merchant_profiles_{column}", "merchant_profiles", [column], unique=column in {"user_id", "merchant_code"})

    op.create_table(
        "outlets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("merchant_id", sa.UUID(), nullable=False),
        sa.Column("outlet_code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("risk_level", sa.String(20), server_default="low", nullable=False),
        sa.Column("status", sa.String(30), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchant_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("outlet_code"),
    )
    for column in ("merchant_id", "outlet_code", "city", "status"):
        op.create_index(f"ix_outlets_{column}", "outlets", [column], unique=column == "outlet_code")

    op.create_table(
        "qris_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("merchant_id", sa.UUID(), nullable=False),
        sa.Column("outlet_id", sa.UUID(), nullable=False),
        sa.Column("nmid", sa.String(80), nullable=False),
        sa.Column("qris_type", sa.String(30), server_default="MPM_DYNAMIC", nullable=False),
        sa.Column("acquirer_name", sa.String(120), nullable=False),
        sa.Column("masked_settlement_account", sa.String(80), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), server_default="active", nullable=False),
        sa.Column("last_verified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchant_profiles.id"]),
        sa.ForeignKeyConstraint(["outlet_id"], ["outlets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nmid"),
    )
    for column in ("merchant_id", "outlet_id", "nmid", "payload_hash", "status"):
        op.create_index(f"ix_qris_profiles_{column}", "qris_profiles", [column], unique=column == "nmid")

    op.create_table(
        "orders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_reference", sa.String(80), nullable=False),
        sa.Column("merchant_id", sa.UUID(), nullable=False),
        sa.Column("outlet_id", sa.UUID(), nullable=False),
        sa.Column("expected_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="IDR", nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("customer_reference", sa.String(80), nullable=True),
        sa.Column("status", sa.String(30), server_default="awaiting_payment", nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchant_profiles.id"]),
        sa.ForeignKeyConstraint(["outlet_id"], ["outlets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_reference"),
    )
    for column in ("order_reference", "merchant_id", "outlet_id", "status"):
        op.create_index(f"ix_orders_{column}", "orders", [column], unique=column == "order_reference")
    op.create_index("ix_orders_merchant_status", "orders", ["merchant_id", "status"])

    op.create_table(
        "payment_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("transaction_reference", sa.String(100), nullable=False),
        sa.Column("provider_reference", sa.String(100), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=True),
        sa.Column("merchant_id", sa.UUID(), nullable=False),
        sa.Column("outlet_id", sa.UUID(), nullable=False),
        sa.Column("qris_profile_id", sa.UUID(), nullable=False),
        sa.Column("payer_pseudonym", sa.String(80), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("expected_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(3), server_default="IDR", nullable=False),
        sa.Column("payment_method", sa.String(20), server_default="QRIS", nullable=False),
        sa.Column("qris_type", sa.String(30), nullable=False),
        sa.Column("acquirer_name", sa.String(120), nullable=False),
        sa.Column("payment_status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("callback_received", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("callback_received_at", sa.DateTime(), nullable=True),
        sa.Column("callback_delay_seconds", sa.Integer(), nullable=True),
        sa.Column("source_city", sa.String(100), nullable=True),
        sa.Column("source_region", sa.String(100), nullable=True),
        sa.Column("source_country", sa.String(3), server_default="ID", nullable=False),
        sa.Column("destination_city", sa.String(100), nullable=False),
        sa.Column("destination_region", sa.String(100), nullable=False),
        sa.Column("destination_country", sa.String(3), server_default="ID", nullable=False),
        sa.Column("is_cross_region", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_cross_border", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("raw_payload_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), server_default="received", nullable=False),
        sa.Column("fraud_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("risk_level", sa.String(20), server_default="low", nullable=False),
        sa.Column("recommendation_code", sa.String(50), server_default="VERIFY", nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("rule_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("tabular_score", sa.Float(), nullable=True),
        sa.Column("adaptive_score", sa.Float(), nullable=True),
        sa.Column("graph_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("scoring_explanation", sa.JSON(), nullable=True),
        sa.Column("scenario_name", sa.String(60), nullable=True),
        sa.Column("claimed_paid", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("signature_valid", sa.Boolean(), nullable=True),
        sa.Column("replay_detected", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("transaction_time", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchant_profiles.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["outlet_id"], ["outlets.id"]),
        sa.ForeignKeyConstraint(["qris_profile_id"], ["qris_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_reference"),
        sa.UniqueConstraint("transaction_reference"),
    )
    for column in ("transaction_reference", "provider_reference", "order_id", "merchant_id", "outlet_id", "qris_profile_id", "payer_pseudonym", "payment_status", "status", "risk_level", "scenario_name", "transaction_time"):
        op.create_index(f"ix_payment_events_{column}", "payment_events", [column], unique=column in {"transaction_reference", "provider_reference"})
    op.create_index("ix_payment_events_merchant_time", "payment_events", ["merchant_id", "transaction_time"])
    op.create_index("ix_payment_events_merchant_risk", "payment_events", ["merchant_id", "risk_level"])

    op.create_table(
        "settlements",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("merchant_id", sa.UUID(), nullable=False),
        sa.Column("payment_event_id", sa.UUID(), nullable=True),
        sa.Column("settlement_reference", sa.String(100), nullable=False),
        sa.Column("gross_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("fee_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("net_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("settlement_status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("settlement_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchant_profiles.id"]),
        sa.ForeignKeyConstraint(["payment_event_id"], ["payment_events.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("settlement_reference"),
    )
    for column in ("merchant_id", "payment_event_id", "settlement_reference", "settlement_status"):
        op.create_index(f"ix_settlements_{column}", "settlements", [column], unique=column == "settlement_reference")

    op.create_table(
        "federated_nodes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("node_name", sa.String(120), nullable=False),
        sa.Column("node_type", sa.String(50), server_default="merchant_demo", nullable=False),
        sa.Column("merchant_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(30), server_default="online", nullable=False),
        sa.Column("sample_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_round", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchant_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("node_name"),
    )
    op.create_index("ix_federated_nodes_merchant_id", "federated_nodes", ["merchant_id"])

    op.create_table(
        "federated_rounds",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), server_default="completed", nullable=False),
        sa.Column("participant_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_samples", sa.Integer(), server_default="0", nullable=False),
        sa.Column("aggregation_method", sa.String(30), server_default="FedAvg", nullable=False),
        sa.Column("global_metric_before", sa.Float(), server_default="0", nullable=False),
        sa.Column("global_metric_after", sa.Float(), server_default="0", nullable=False),
        sa.Column("participant_metadata", sa.JSON(), nullable=True),
        sa.Column("global_parameters", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("round_number"),
    )
    op.create_index("ix_federated_rounds_round_number", "federated_rounds", ["round_number"], unique=True)

    with op.batch_alter_table("alerts") as batch:
        batch.alter_column("transaction_id", existing_type=sa.UUID(), nullable=True)
        batch.add_column(sa.Column("merchant_id", sa.UUID(), nullable=True))
        batch.add_column(sa.Column("payment_event_id", sa.UUID(), nullable=True))
        batch.add_column(sa.Column("recommendation", sa.Text(), nullable=True))
        batch.create_foreign_key("fk_alerts_merchant_id", "merchant_profiles", ["merchant_id"], ["id"])
        batch.create_foreign_key("fk_alerts_payment_event_id", "payment_events", ["payment_event_id"], ["id"])
        batch.create_index("ix_alerts_merchant_id", ["merchant_id"])
        batch.create_index("ix_alerts_payment_event_id", ["payment_event_id"])
        batch.create_index("ix_alerts_merchant_status", ["merchant_id", "status"])

    with op.batch_alter_table("labels") as batch:
        batch.alter_column("transaction_id", existing_type=sa.UUID(), nullable=True)
        batch.add_column(sa.Column("payment_event_id", sa.UUID(), nullable=True))
        batch.add_column(sa.Column("merchant_id", sa.UUID(), nullable=True))
        batch.add_column(sa.Column("created_by_user_id", sa.UUID(), nullable=True))
        batch.add_column(sa.Column("merchant_decision", sa.String(30), nullable=True))
        batch.create_foreign_key("fk_labels_payment_event_id", "payment_events", ["payment_event_id"], ["id"])
        batch.create_foreign_key("fk_labels_merchant_id", "merchant_profiles", ["merchant_id"], ["id"])
        batch.create_foreign_key("fk_labels_created_by_user_id", "users", ["created_by_user_id"], ["id"])
        batch.create_index("ix_labels_payment_event_id", ["payment_event_id"])
        batch.create_index("ix_labels_merchant_id", ["merchant_id"])

    with op.batch_alter_table("audit_logs") as batch:
        batch.add_column(sa.Column("user_id", sa.UUID(), nullable=True))
        batch.add_column(sa.Column("merchant_id", sa.UUID(), nullable=True))
        batch.add_column(sa.Column("metadata_json", sa.JSON(), nullable=True))
        batch.create_foreign_key("fk_audit_logs_user_id", "users", ["user_id"], ["id"])
        batch.create_foreign_key("fk_audit_logs_merchant_id", "merchant_profiles", ["merchant_id"], ["id"])
        batch.create_index("ix_audit_logs_user_id", ["user_id"])
        batch.create_index("ix_audit_logs_merchant_id", ["merchant_id"])


def downgrade() -> None:
    with op.batch_alter_table("audit_logs") as batch:
        batch.drop_index("ix_audit_logs_merchant_id")
        batch.drop_index("ix_audit_logs_user_id")
        batch.drop_constraint("fk_audit_logs_merchant_id", type_="foreignkey")
        batch.drop_constraint("fk_audit_logs_user_id", type_="foreignkey")
        batch.drop_column("metadata_json")
        batch.drop_column("merchant_id")
        batch.drop_column("user_id")
    with op.batch_alter_table("labels") as batch:
        batch.drop_index("ix_labels_merchant_id")
        batch.drop_index("ix_labels_payment_event_id")
        batch.drop_constraint("fk_labels_created_by_user_id", type_="foreignkey")
        batch.drop_constraint("fk_labels_merchant_id", type_="foreignkey")
        batch.drop_constraint("fk_labels_payment_event_id", type_="foreignkey")
        batch.drop_column("merchant_decision")
        batch.drop_column("created_by_user_id")
        batch.drop_column("merchant_id")
        batch.drop_column("payment_event_id")
        batch.alter_column("transaction_id", existing_type=sa.UUID(), nullable=False)
    with op.batch_alter_table("alerts") as batch:
        batch.drop_index("ix_alerts_merchant_status")
        batch.drop_index("ix_alerts_payment_event_id")
        batch.drop_index("ix_alerts_merchant_id")
        batch.drop_constraint("fk_alerts_payment_event_id", type_="foreignkey")
        batch.drop_constraint("fk_alerts_merchant_id", type_="foreignkey")
        batch.drop_column("recommendation")
        batch.drop_column("payment_event_id")
        batch.drop_column("merchant_id")
        batch.alter_column("transaction_id", existing_type=sa.UUID(), nullable=False)
    for table in ("federated_rounds", "federated_nodes", "settlements", "payment_events", "orders", "qris_profiles", "outlets", "merchant_profiles"):
        op.drop_table(table)
    op.execute("UPDATE users SET role = UPPER(role)")
