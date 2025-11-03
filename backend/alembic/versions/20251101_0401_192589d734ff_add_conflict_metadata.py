"""add_conflict_metadata

Revision ID: 192589d734ff
Revises: 002
Create Date: 2025-11-01 04:01:14.529374

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '192589d734ff'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new conflict columns with defaults where needed
    # Add reason_code as nullable first
    op.add_column('conflicts', sa.Column('reason_code', sa.String(length=50), nullable=True))
    # Backfill existing rows with default
    op.execute("UPDATE conflicts SET reason_code = 'OTHER' WHERE reason_code IS NULL")
    # Then make it NOT NULL
    op.alter_column('conflicts', 'reason_code', existing_type=sa.String(length=50), nullable=False)
    op.add_column('conflicts', sa.Column('reason_detail', sa.Text(), nullable=True))
    op.add_column('conflicts', sa.Column('customer_name', sa.Text(), nullable=True))
    op.add_column('conflicts', sa.Column('project_name', sa.Text(), nullable=True))
    op.add_column('conflicts', sa.Column('activity_name', sa.Text(), nullable=True))
    op.add_column('conflicts', sa.Column('ticket_number', sa.Text(), nullable=True))
    op.add_column('conflicts', sa.Column('zammad_created_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('conflicts', sa.Column('zammad_entry_date', sa.Date(), nullable=True))
    op.add_column('conflicts', sa.Column('zammad_time_minutes', sa.Float(), nullable=True))
    op.add_column('conflicts', sa.Column('kimai_begin', sa.DateTime(timezone=True), nullable=True))
    op.add_column('conflicts', sa.Column('kimai_end', sa.DateTime(timezone=True), nullable=True))
    op.add_column('conflicts', sa.Column('kimai_duration_minutes', sa.Float(), nullable=True))
    op.add_column('conflicts', sa.Column('kimai_id', sa.Integer(), nullable=True))
    op.alter_column('conflicts', 'resolution_status',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('conflicts', 'resolved_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)
    op.alter_column('conflicts', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    op.create_index('idx_conflicts_reason_code', 'conflicts', ['reason_code'], unique=False)
    op.create_index('idx_conflicts_resolution_status', 'conflicts', ['resolution_status'], unique=False)
    op.create_index(op.f('ix_conflicts_conflict_type'), 'conflicts', ['conflict_type'], unique=False)
    op.create_index(op.f('ix_conflicts_reason_code'), 'conflicts', ['reason_code'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # Revert conflict changes
    op.drop_index(op.f('ix_conflicts_reason_code'), table_name='conflicts')
    op.drop_index(op.f('ix_conflicts_conflict_type'), table_name='conflicts')
    op.drop_index('idx_conflicts_resolution_status', table_name='conflicts')
    op.drop_index('idx_conflicts_reason_code', table_name='conflicts')
    op.alter_column('conflicts', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    op.alter_column('conflicts', 'resolved_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    op.alter_column('conflicts', 'resolution_status',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.drop_column('conflicts', 'kimai_id')
    op.drop_column('conflicts', 'kimai_duration_minutes')
    op.drop_column('conflicts', 'kimai_end')
    op.drop_column('conflicts', 'kimai_begin')
    op.drop_column('conflicts', 'zammad_time_minutes')
    op.drop_column('conflicts', 'zammad_entry_date')
    op.drop_column('conflicts', 'zammad_created_at')
    op.drop_column('conflicts', 'ticket_number')
    op.drop_column('conflicts', 'activity_name')
    op.drop_column('conflicts', 'project_name')
    op.drop_column('conflicts', 'customer_name')
    op.drop_column('conflicts', 'reason_detail')
    op.drop_column('conflicts', 'reason_code')
    # ### end Alembic commands ###
