"""Add merchant subscription plan metadata.

Revision ID: 20260723_0005
Revises: 20260723_0004
"""

from alembic import op
import sqlalchemy as sa


revision = "20260723_0005"
down_revision = "20260723_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "merchant_profiles",
        sa.Column("subscription_plan", sa.String(length=20), nullable=False, server_default="basic"),
    )
    op.add_column(
        "merchant_profiles",
        sa.Column("subscription_status", sa.String(length=20), nullable=False, server_default="active"),
    )
    op.add_column(
        "merchant_profiles",
        sa.Column("plan_changed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_merchant_profiles_subscription_plan", "merchant_profiles", ["subscription_plan"])

    # Existing hackathon demo accounts receive deterministic tiers. Other
    # existing and newly registered merchants remain on Basic by default.
    op.execute(
        """
        UPDATE merchant_profiles
        SET subscription_plan = CASE
            WHEN merchant_code = 'MRC-SARI-SOLO' THEN 'premium'
            WHEN merchant_code = 'MRC-BATIK-LAW' THEN 'growth'
            ELSE 'basic'
        END
        """
    )


def downgrade() -> None:
    op.drop_index("ix_merchant_profiles_subscription_plan", table_name="merchant_profiles")
    op.drop_column("merchant_profiles", "plan_changed_at")
    op.drop_column("merchant_profiles", "subscription_status")
    op.drop_column("merchant_profiles", "subscription_plan")
