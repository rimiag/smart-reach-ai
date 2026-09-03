"""Create research_results table

Stores websites discovered by the search agent per campaign/keyword
(Iteration 1.4 - Search & Discovery).

Revision ID: 002
Revises: 001
Create Date: 2026-08-31 12:00:00

MariaDB 10.1.x compatible:
- JSON stored as TEXT (JSON type not supported in MariaDB 10.1)
- DateTime without timezone
- server_default CURRENT_TIMESTAMP
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create research_result_status enum
    research_result_status_enum = mysql.ENUM(
        'discovered', 'queued', 'crawling', 'crawled', 'skipped', 'failed',
        name='research_result_status'
    )
    research_result_status_enum.create(op.get_bind(), checkfirst=True)

    # Create research_results table (MariaDB 10.1 compatible)
    op.create_table(
        'research_results',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('keyword', sa.String(length=255), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=512), nullable=True),
        sa.Column('snippet', sa.Text(), nullable=True),
        sa.Column('status', research_result_status_enum,
                  server_default='discovered', nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=True),
        sa.Column('result_position', sa.Integer(), nullable=True),
        # MariaDB 10.1: Use TEXT instead of JSON type
        sa.Column('extra_data', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        # MariaDB 10.1 doesn't support timezone in DateTime
        sa.Column('created_at', sa.DateTime(),
                  server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(),
                  server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('crawled_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_research_results_campaign_id', 'campaign_id'),
        sa.Index('ix_research_results_user_id', 'user_id'),
        sa.Index('ix_research_results_domain', 'domain'),
        sa.Index('ix_research_results_status', 'status')
    )


def downgrade() -> None:
    op.drop_table('research_results')

    research_result_status_enum = mysql.ENUM(
        'discovered', 'queued', 'crawling', 'crawled', 'skipped', 'failed',
        name='research_result_status'
    )
    research_result_status_enum.drop(op.get_bind(), checkfirst=True)
