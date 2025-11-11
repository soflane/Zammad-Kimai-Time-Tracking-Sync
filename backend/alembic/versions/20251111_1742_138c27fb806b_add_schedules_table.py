"""add_schedules_table

Revision ID: 138c27fb806b
Revises: c1aef9eb831e
Create Date: 2025-11-11 17:42:29.622298

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = '138c27fb806b'
down_revision = 'c1aef9eb831e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'schedules',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('cron', sa.String(100), nullable=False),
        sa.Column('timezone', sa.String(50), nullable=False, server_default='UTC'),
        sa.Column('concurrency', sa.String(20), nullable=False, server_default='skip'),
        sa.Column('notifications', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False)
    )


def downgrade() -> None:
    op.drop_table('schedules')
