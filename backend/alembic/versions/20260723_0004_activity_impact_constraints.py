"""Add user activity monitoring and impact classification fields.

Revision ID: 20260723_0004
Revises: 20260716_0003
"""

from alembic import op
import sqlalchemy as sa


revision = "20260723_0004"
down_revision = "20260716_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("last_activity_at", sa.DateTime(), nullable=True))
    op.create_index("ix_users_last_activity_at", "users", ["last_activity_at"])

    op.add_column(
        "audit_logs",
        sa.Column("actor_role", sa.String(length=30), nullable=False, server_default="system"),
    )
    op.execute(
        """
        UPDATE audit_logs
        SET actor_role = users.role
        FROM users
        WHERE audit_logs.user_id = users.id
        """
    )
    op.create_index("ix_audit_logs_actor_role", "audit_logs", ["actor_role"])
    op.create_index("ix_audit_logs_role_created", "audit_logs", ["actor_role", "created_at"])
    op.create_index("ix_audit_logs_user_created", "audit_logs", ["user_id", "created_at"])

    op.add_column(
        "payment_events",
        sa.Column("category", sa.String(length=80), nullable=False, server_default="Umum"),
    )
    op.add_column(
        "payment_events",
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="rendah"),
    )
    op.execute(
        """
        UPDATE payment_events
        SET category = merchant_profiles.business_type
        FROM merchant_profiles
        WHERE payment_events.merchant_id = merchant_profiles.id
        """
    )
    op.execute(
        """
        UPDATE payment_events
        SET priority = CASE
            WHEN risk_level = 'high' THEN 'tinggi'
            WHEN risk_level = 'medium' THEN 'sedang'
            ELSE 'rendah'
        END
        """
    )
    op.create_index("ix_payment_events_category", "payment_events", ["category"])
    op.create_index("ix_payment_events_priority", "payment_events", ["priority"])
    op.create_index(
        "ix_payment_events_merchant_priority_time",
        "payment_events",
        ["merchant_id", "priority", "transaction_time"],
    )


def downgrade() -> None:
    op.drop_index("ix_payment_events_merchant_priority_time", table_name="payment_events")
    op.drop_index("ix_payment_events_priority", table_name="payment_events")
    op.drop_index("ix_payment_events_category", table_name="payment_events")
    op.drop_column("payment_events", "priority")
    op.drop_column("payment_events", "category")

    op.drop_index("ix_audit_logs_user_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_role_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_role", table_name="audit_logs")
    op.drop_column("audit_logs", "actor_role")

    op.drop_index("ix_users_last_activity_at", table_name="users")
    op.drop_column("users", "last_activity_at")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "is_active")
