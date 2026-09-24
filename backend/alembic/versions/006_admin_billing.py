"""Admin panel: plan, billing_status, billing_notes on users

Revision ID: 006
Revises: 005
Create Date: 2026-09-14

Not wired into the deploy (same policy as 001-005): fresh databases get these
columns via create_all; existing databases get them via manual ALTER, see
DEPLOYMENT.md §4.8 "Admin bootstrap on staging".
"""

import sqlalchemy as sa

from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
    )
    op.add_column(
        "users",
        sa.Column("billing_status", sa.String(50), nullable=False, server_default="active"),
    )
    op.add_column("users", sa.Column("billing_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "billing_notes")
    op.drop_column("users", "billing_status")
    op.drop_column("users", "plan")
