"""Repair lease columns for databases that already recorded revision 0007.

Revision ID: 20261002_0008
Revises: 20261002_0007
"""

from alembic import op
import sqlalchemy as sa


revision = "20261002_0008"
down_revision = "20261002_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("model_training_jobs")}
    if "attempts" not in columns:
        op.add_column(
            "model_training_jobs",
            sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        )
    if "worker_id" not in columns:
        op.add_column("model_training_jobs", sa.Column("worker_id", sa.String(length=120), nullable=True))
    if "lease_expires_at" not in columns:
        op.add_column("model_training_jobs", sa.Column("lease_expires_at", sa.DateTime(), nullable=True))

    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("model_training_jobs")}
    if "uq_model_training_jobs_active_dataset" not in indexes:
        op.create_index(
            "uq_model_training_jobs_active_dataset",
            "model_training_jobs",
            ["dataset_name"],
            unique=True,
            postgresql_where=sa.text("status IN ('queued', 'running')"),
            sqlite_where=sa.text("status IN ('queued', 'running')"),
        )


def downgrade() -> None:
    # Revision 0007 defines these as canonical fields on fresh databases too.
    pass
