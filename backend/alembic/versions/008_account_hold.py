"""Account hold: users.account_status (new signups wait for admin approval)

Revision ID: 008
Revises: 007
Create Date: 2026-09-23

Not wired into the deploy (same policy as 001-007): fresh databases get the
column via create_all; existing databases get it via ensure_schema
(docker-entrypoint). server_default "active" backfills every existing user as
active - only the register endpoint creates held accounts.
"""

import sqlalchemy as sa

from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "account_status",
            sa.String(50),
            nullable=False,
            server_default="active",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "account_status")
