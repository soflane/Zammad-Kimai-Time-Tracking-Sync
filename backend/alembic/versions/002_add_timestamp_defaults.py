"""Add timestamp defaults

Revision ID: 002
Revises: 001
Create Date: 2025-10-25 13:03:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add default CURRENT_TIMESTAMP to created_at and updated_at columns
    # First update NULL values, then set defaults and NOT NULL constraint
    
    # Users table
    op.execute("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    op.execute("UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
    op.alter_column('users', 'created_at',
                    server_default=sa.text('CURRENT_TIMESTAMP'),
                    nullable=False)
    op.alter_column('users', 'updated_at',
                    server_default=sa.text('CURRENT_TIMESTAMP'),
                    nullable=False)
    
    # Connectors table
    op.execute("UPDATE connectors SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    op.execute("UPDATE connectors SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
    op.alter_column('connectors', 'created_at',
                    server_default=sa.text('CURRENT_TIMESTAMP'),
                    nullable=False)
    op.alter_column('connectors', 'updated_at',
                    server_default=sa.text('CURRENT_TIMESTAMP'),
                    nullable=False)
    
    # Activity mappings table
    op.execute("UPDATE activity_mappings SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    op.execute("UPDATE activity_mappings SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
    op.alter_column('activity_mappings', 'created_at',
                    server_default=sa.text('CURRENT_TIMESTAMP'),
                    nullable=False)
    op.alter_column('activity_mappings', 'updated_at',
                    server_default=sa.text('CURRENT_TIMESTAMP'),
                    nullable=False)
    
    # Sync runs table
    op.execute("UPDATE sync_runs SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    op.alter_column('sync_runs', 'created_at',
                    server_default=sa.text('CURRENT_TIMESTAMP'),
                    nullable=False)
    
    # Time entries table
    op.execute("UPDATE time_entries SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    op.execute("UPDATE time_entries SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
    op.alter_column('time_entries', 'created_at',
                    server_default=sa.text('CURRENT_TIMESTAMP'),
                    nullable=False)
    op.alter_column('time_entries', 'updated_at',
                    server_default=sa.text('CURRENT_TIMESTAMP'),
                    nullable=False)
    
    # Conflicts table
    op.execute("UPDATE conflicts SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    op.alter_column('conflicts', 'created_at',
                    server_default=sa.text('CURRENT_TIMESTAMP'),
                    nullable=False)
    
    # Audit logs table
    op.execute("UPDATE audit_logs SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    op.alter_column('audit_logs', 'created_at',
                    server_default=sa.text('CURRENT_TIMESTAMP'),
                    nullable=False)


def downgrade() -> None:
    # Remove defaults
    
    # Audit logs table
    op.alter_column('audit_logs', 'created_at',
                    server_default=None,
                    nullable=True)
    
    # Conflicts table
    op.alter_column('conflicts', 'created_at',
                    server_default=None,
                    nullable=True)
    
    # Time entries table
    op.alter_column('time_entries', 'updated_at',
                    server_default=None,
                    nullable=True)
    op.alter_column('time_entries', 'created_at',
                    server_default=None,
                    nullable=True)
    
    # Sync runs table
    op.alter_column('sync_runs', 'created_at',
                    server_default=None,
                    nullable=True)
    
    # Activity mappings table
    op.alter_column('activity_mappings', 'updated_at',
                    server_default=None,
                    nullable=True)
    op.alter_column('activity_mappings', 'created_at',
                    server_default=None,
                    nullable=True)
    
    # Connectors table
    op.alter_column('connectors', 'updated_at',
                    server_default=None,
                    nullable=True)
    op.alter_column('connectors', 'created_at',
                    server_default=None,
                    nullable=True)
    
    # Users table
    op.alter_column('users', 'updated_at',
                    server_default=None,
                    nullable=True)
    op.alter_column('users', 'created_at',
                    server_default=None,
                    nullable=True)
