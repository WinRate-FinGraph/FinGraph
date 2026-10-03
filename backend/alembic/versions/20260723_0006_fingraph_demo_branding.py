"""Rename local demo identities to the FinGraph brand.

Revision ID: 20260723_0006
Revises: 20260723_0005
"""

revision = "20260723_0006"
down_revision = "20260723_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Revision marker retained for databases that already applied this migration.
    pass


def downgrade() -> None:
    pass
