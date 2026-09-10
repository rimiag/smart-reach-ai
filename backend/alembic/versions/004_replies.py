"""Phase 4: replies table

Revision ID: 004
Revises: 003
Create Date: 2026-09-10

MariaDB 10.1 compatible.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    reply_category_enum = mysql.ENUM(
        "interested",
        "not_interested",
        "need_more_info",
        "request_meeting",
        "pricing_request",
        "out_of_office",
        "unsubscribe",
        "wrong_contact",
        "other",
        name="reply_category",
    )
    reply_category_enum.create(op.get_bind(), checkfirst=True)

    reply_status_enum = mysql.ENUM("unread", "read", name="reply_status")
    reply_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "replies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("from_email", sa.String(length=255), nullable=False),
        sa.Column("from_name", sa.String(length=255), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("category", reply_category_enum, nullable=False, server_default="other"),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("classification_error", sa.String(length=255), nullable=True),
        sa.Column("status", reply_status_enum, nullable=False, server_default="unread"),
        sa.Column("in_reply_to", sa.String(length=191), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("in_reply_to", name="uq_replies_in_reply_to"),
    )
    op.create_index("ix_replies_campaign_id", "replies", ["campaign_id"])
    op.create_index("ix_replies_lead_id", "replies", ["lead_id"])
    op.create_index("ix_replies_user_id", "replies", ["user_id"])
    op.create_index("ix_replies_category", "replies", ["category"])


def downgrade() -> None:
    op.drop_table("replies")
    mysql.ENUM(
        "interested",
        "not_interested",
        "need_more_info",
        "request_meeting",
        "pricing_request",
        "out_of_office",
        "unsubscribe",
        "wrong_contact",
        "other",
        name="reply_category",
    ).drop(op.get_bind(), checkfirst=True)
    mysql.ENUM("unread", "read", name="reply_status").drop(op.get_bind(), checkfirst=True)
