"""Add scraped_data_history table for historical tracking

Revision ID: 20250126_010000
Revises: 20250126_000000
Create Date: 2025-01-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20250126_010000'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'scraped_data_history',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('hospital_id', sa.String(), nullable=False),
        sa.Column('estimated_wait_time', sa.SmallInteger(), nullable=True),
        sa.Column('patients_waiting', sa.SmallInteger(), nullable=True),
        sa.Column('patients_in_treatment', sa.SmallInteger(), nullable=True),
        sa.Column('last_updated', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('scraped_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    # Create indexes for efficient querying
    op.create_index('ix_scraped_data_history_hospital_id', 'scraped_data_history', ['hospital_id'])
    op.create_index('ix_scraped_data_history_scraped_at', 'scraped_data_history', ['scraped_at'])
    # Composite index for common query pattern (hospital + time range)
    op.create_index('ix_scraped_data_history_hospital_scraped', 'scraped_data_history', ['hospital_id', 'scraped_at'])


def downgrade() -> None:
    op.drop_index('ix_scraped_data_history_hospital_scraped', table_name='scraped_data_history')
    op.drop_index('ix_scraped_data_history_scraped_at', table_name='scraped_data_history')
    op.drop_index('ix_scraped_data_history_hospital_id', table_name='scraped_data_history')
    op.drop_table('scraped_data_history')
