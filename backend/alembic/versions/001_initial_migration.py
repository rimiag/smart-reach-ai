"""
Initial migration

Creates users, campaigns, and leads tables.
Revision ID: 001
Revises:
Create Date: 2026-08-18 23:55:00

Updated for MariaDB 10.1.x compatibility:
- Replaced JSON type with TEXT (JSON type not supported in MariaDB 10.1)
- Removed timezone support from DateTime (not supported in MariaDB 10.1)
- Changed now() to CURRENT_TIMESTAMP (better compatibility)
- Fixed ENUM drop syntax for MariaDB
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_role enum
    user_role_enum = mysql.ENUM('admin', 'user', name='user_role')
    user_role_enum.create(op.get_bind(), checkfirst=True)

    # Create users table (MariaDB 10.1 compatible)
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('role', user_role_enum, nullable=False, server_default='user'),
        # MariaDB 10.1 doesn't support timezone in DateTime
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # Create campaign_status enum
    campaign_status_enum = mysql.ENUM(
        'draft', 'researching', 'ready', 'active', 'paused', 'completed',
        name='campaign_status'
    )
    campaign_status_enum.create(op.get_bind(), checkfirst=True)

    # Create campaigns table (MariaDB 10.1 compatible)
    op.create_table(
        'campaigns',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', campaign_status_enum, nullable=False, server_default='draft'),
        # MariaDB 10.1: Use TEXT instead of JSON type
        sa.Column('keywords', sa.Text(), nullable=False),
        sa.Column('settings', sa.Text(), nullable=True),
        # MariaDB 10.1 doesn't support timezone in DateTime
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_campaigns_user_id', 'user_id')
    )

    # Create lead_status enum
    lead_status_enum = mysql.ENUM(
        'new', 'researching', 'qualified', 'review', 'approved', 'rejected',
        'scheduled', 'sent', 'replied', 'interested', 'not_interested',
        'unsubscribed', 'bounced', 'do_not_contact',
        name='lead_status'
    )
    lead_status_enum.create(op.get_bind(), checkfirst=True)

    # Create leads table (MariaDB 10.1 compatible)
    op.create_table(
        'leads',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('keyword', sa.String(length=255), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('contact_page_url', sa.Text(), nullable=True),
        sa.Column('organization_name', sa.String(length=255), nullable=False),
        sa.Column('website', sa.String(length=255), nullable=False),
        sa.Column('contact_name', sa.String(length=255), nullable=True),
        sa.Column('job_title', sa.String(length=255), nullable=True),
        sa.Column('department', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=255), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('lead_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ai_reasoning', sa.Text(), nullable=True),
        sa.Column('ai_research_summary', sa.Text(), nullable=True),
        sa.Column('status', lead_status_enum, nullable=False, server_default='new'),
        sa.Column('generated_email', sa.Text(), nullable=True),
        sa.Column('email_template_id', sa.Integer(), nullable=True),
        sa.Column('emails_sent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('messages_sent', sa.Integer(), nullable=False, server_default='0'),
        # MariaDB 10.1 doesn't support timezone in DateTime
        sa.Column('last_emailed_at', sa.DateTime(), nullable=True),
        sa.Column('last_contacted_at', sa.DateTime(), nullable=True),
        sa.Column('do_not_contact', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('opt_out', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('unsubscribed_at', sa.DateTime(), nullable=True),
        sa.Column('opt_out_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('discovered_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('qualified_at', sa.DateTime(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_leads_campaign_id', 'campaign_id'),
        sa.Index('ix_leads_user_id', 'user_id')
    )


def downgrade() -> None:
    # Drop tables first
    op.drop_index('ix_leads_user_id', table_name='leads')
    op.drop_index('ix_leads_campaign_id', table_name='leads')
    op.drop_table('leads')

    op.drop_index('ix_campaigns_user_id', table_name='campaigns')
    op.drop_table('campaigns')

    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')

    # Drop enums (MariaDB syntax)
    op.execute('DROP TYPE IF EXISTS lead_status')
    op.execute('DROP TYPE IF EXISTS campaign_status')
    op.execute('DROP TYPE IF EXISTS user_role')
