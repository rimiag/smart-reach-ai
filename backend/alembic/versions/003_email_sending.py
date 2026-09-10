"""Phase 3: emails (send log) and suppressions tables

Revision ID: 003
Revises: 002
Create Date: 2026-09-09

MariaDB 10.1 compatible (TEXT instead of JSON, CURRENT_TIMESTAMP defaults).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    email_status_enum = mysql.ENUM("sent", "failed", "bounced", name="email_log_status")
    email_status_enum.create(op.get_bind(), checkfirst=True)

    suppression_reason_enum = mysql.ENUM(
        "unsubscribed", "bounced", "manual", name="suppression_reason"
    )
    suppression_reason_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "emails",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("to_email", sa.String(length=255), nullable=False),
        sa.Column("from_email", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", email_status_enum, nullable=False, server_default="sent"),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("message_id", sa.String(length=255), nullable=True),
        sa.Column("unsubscribe_token", sa.String(length=64), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_emails_campaign_id", "emails", ["campaign_id"])
    op.create_index("ix_emails_lead_id", "emails", ["lead_id"])
    op.create_index("ix_emails_user_id", "emails", ["user_id"])
    op.create_index("ix_emails_status", "emails", ["status"])

    op.create_table(
        "suppressions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=190), nullable=False),
        sa.Column("reason", suppression_reason_enum, nullable=False, server_default="manual"),
        sa.Column("lead_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "email", name="uq_suppression_user_email"),
    )
    op.create_index("ix_suppressions_user_id", "suppressions", ["user_id"])
    op.create_index("ix_suppressions_email", "suppressions", ["email"])


def downgrade() -> None:
    op.drop_table("suppressions")
    op.drop_table("emails")
    mysql.ENUM("unsubscribed", "bounced", "manual", name="suppression_reason").drop(
        op.get_bind(), checkfirst=True
    )
    mysql.ENUM("sent", "failed", "bounced", name="email_log_status").drop(
        op.get_bind(), checkfirst=True
    )
