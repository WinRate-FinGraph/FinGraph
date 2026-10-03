"""Persist QRIS GraphSAGE training jobs.

Revision ID: 20261002_0007
Revises: 20260723_0006
"""

from alembic import op
import sqlalchemy as sa


revision = "20261002_0007"
down_revision = "20260723_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_training_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dataset_name", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("worker_id", sa.String(length=120), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("progress", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_model_training_jobs_active_dataset",
        "model_training_jobs",
        ["dataset_name"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
        sqlite_where=sa.text("status IN ('queued', 'running')"),
    )


def downgrade() -> None:
    op.drop_index("uq_model_training_jobs_active_dataset", table_name="model_training_jobs")
    op.drop_table("model_training_jobs")
