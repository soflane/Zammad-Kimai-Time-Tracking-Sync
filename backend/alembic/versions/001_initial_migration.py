"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2025-10-25 12:48:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('full_name', sa.String(), nullable=True),
    sa.Column('hashed_password', sa.String(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Create connectors table
    op.create_table('connectors',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('type', sa.String(), nullable=False),
    sa.Column('base_url', sa.String(), nullable=False),
    sa.Column('api_token', sa.String(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_connectors_id'), 'connectors', ['id'], unique=False)

    # Create activity_mappings table
    op.create_table('activity_mappings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('zammad_type_id', sa.Integer(), nullable=False),
    sa.Column('zammad_type_name', sa.String(), nullable=False),
    sa.Column('kimai_activity_id', sa.Integer(), nullable=False),
    sa.Column('kimai_activity_name', sa.String(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('zammad_type_id', 'kimai_activity_id', name='uq_zammad_kimai_mapping')
    )
    op.create_index(op.f('ix_activity_mappings_id'), 'activity_mappings', ['id'], unique=False)

    # Create sync_runs table
    op.create_table('sync_runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('entries_fetched', sa.Integer(), nullable=True),
    sa.Column('entries_synced', sa.Integer(), nullable=True),
    sa.Column('entries_failed', sa.Integer(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sync_runs_id'), 'sync_runs', ['id'], unique=False)

    # Create time_entries table
    op.create_table('time_entries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source', sa.String(), nullable=False),
    sa.Column('source_id', sa.String(), nullable=False),
    sa.Column('ticket_number', sa.String(), nullable=True),
    sa.Column('ticket_id', sa.Integer(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('time_minutes', sa.Float(), nullable=False),
    sa.Column('activity_type_id', sa.Integer(), nullable=True),
    sa.Column('activity_name', sa.String(), nullable=True),
    sa.Column('user_email', sa.String(), nullable=True),
    sa.Column('entry_date', sa.Date(), nullable=False),
    sa.Column('sync_status', sa.String(), nullable=True),
    sa.Column('kimai_id', sa.Integer(), nullable=True),
    sa.Column('last_sync_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source', 'source_id', name='uq_source_source_id')
    )
    op.create_index(op.f('ix_time_entries_entry_date'), 'time_entries', ['entry_date'], unique=False)
    op.create_index(op.f('ix_time_entries_id'), 'time_entries', ['id'], unique=False)
    op.create_index(op.f('ix_time_entries_source'), 'time_entries', ['source'], unique=False)
    op.create_index(op.f('ix_time_entries_sync_status'), 'time_entries', ['sync_status'], unique=False)

    # Create conflicts table
    op.create_table('conflicts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time_entry_id', sa.Integer(), nullable=True),
    sa.Column('conflict_type', sa.String(), nullable=False),
    sa.Column('zammad_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('kimai_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('resolution_status', sa.String(), nullable=True),
    sa.Column('resolution_action', sa.String(), nullable=True),
    sa.Column('resolved_at', sa.DateTime(), nullable=True),
    sa.Column('resolved_by', sa.String(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['time_entry_id'], ['time_entries.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conflicts_id'), 'conflicts', ['id'], unique=False)
    op.create_index(op.f('ix_conflicts_resolution_status'), 'conflicts', ['resolution_status'], unique=False)

    # Create audit_logs table
    op.create_table('audit_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('sync_run_id', sa.Integer(), nullable=True),
    sa.Column('action', sa.String(), nullable=False),
    sa.Column('entity_type', sa.String(), nullable=False),
    sa.Column('entity_id', sa.String(), nullable=True),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('status', sa.String(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('created_by', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['sync_run_id'], ['sync_runs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_table('audit_logs')
    
    op.drop_index(op.f('ix_conflicts_resolution_status'), table_name='conflicts')
    op.drop_index(op.f('ix_conflicts_id'), table_name='conflicts')
    op.drop_table('conflicts')
    
    op.drop_index(op.f('ix_time_entries_sync_status'), table_name='time_entries')
    op.drop_index(op.f('ix_time_entries_source'), table_name='time_entries')
    op.drop_index(op.f('ix_time_entries_id'), table_name='time_entries')
    op.drop_index(op.f('ix_time_entries_entry_date'), table_name='time_entries')
    op.drop_table('time_entries')
    
    op.drop_index(op.f('ix_sync_runs_id'), table_name='sync_runs')
    op.drop_table('sync_runs')
    
    op.drop_index(op.f('ix_activity_mappings_id'), table_name='activity_mappings')
    op.drop_table('activity_mappings')
    
    op.drop_index(op.f('ix_connectors_id'), table_name='connectors')
    op.drop_table('connectors')
    
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
