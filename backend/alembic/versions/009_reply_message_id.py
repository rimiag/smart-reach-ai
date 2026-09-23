"""Mailbox: store the inbound reply's own Message-ID

Revision ID: 009
Revises: 008
Create Date: 2026-09-23

Not wired into the deploy (same policy as 001-008): fresh databases get the
column via create_all; existing databases get it via ensure_schema
(docker-entrypoint). Nullable with no index - safe additive ALTER.
"""

import sqlalchemy as sa

from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("replies", sa.Column("message_id", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("replies", "message_id")
