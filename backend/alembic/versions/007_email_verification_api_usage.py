"""Email verification on users + api_usage_counters table

Revision ID: 007
Revises: 006
Create Date: 2026-09-22

Not wired into the deploy (same policy as 001-006): fresh databases get these
via create_all; existing databases get the columns via ensure_schema
(docker-entrypoint) and the table via create_all. is_verified keeps
server_default "1" so the additive ALTER backfills every existing user as
verified - nobody gets locked out.
"""

import sqlalchemy as sa

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_verified", sa.Boolean(), nullable=False, server_default=sa.text("1")
        ),
    )
    op.add_column(
        "users", sa.Column("verification_token", sa.String(64), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("verification_token_expires", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "api_usage_counters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "period", name="uq_api_usage_provider_period"),
    )


def downgrade() -> None:
    op.drop_table("api_usage_counters")
    op.drop_column("users", "verification_token_expires")
    op.drop_column("users", "verification_token")
    op.drop_column("users", "is_verified")
