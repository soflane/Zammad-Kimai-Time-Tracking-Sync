"""add_ip_tracking_to_audit_logs

Revision ID: c1aef9eb831e
Revises: 3f5d305feae7
Create Date: 2025-11-10 03:03:19.100028

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1aef9eb831e'
down_revision = '3f5d305feae7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add ip_address column (VARCHAR(45) to support IPv6)
    op.add_column('audit_logs', sa.Column('ip_address', sa.String(45), nullable=True))
    
    # Add user_agent column
    op.add_column('audit_logs', sa.Column('user_agent', sa.Text(), nullable=True))
    
    # Add index on (ip_address, created_at) for efficient filtering of access logs by IP
    op.create_index('idx_audit_logs_ip_created', 'audit_logs', ['ip_address', 'created_at'])


def downgrade() -> None:
    # Drop index first
    op.drop_index('idx_audit_logs_ip_created', table_name='audit_logs')
    
    # Drop columns
    op.drop_column('audit_logs', 'user_agent')
    op.drop_column('audit_logs', 'ip_address')
