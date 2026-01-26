"""Add slug column to hospitals table

Revision ID: 20250126_020000
Revises: 20250126_010000
Create Date: 2025-01-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250126_020000'
down_revision: Union[str, None] = '20250126_010000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add slug column to hospitals table
    op.add_column('hospitals', sa.Column('slug', sa.String(), nullable=True))
    # Create unique index on slug
    op.create_index('hospitals_slug_key', 'hospitals', ['slug'], unique=True)


def downgrade() -> None:
    op.drop_index('hospitals_slug_key', table_name='hospitals')
    op.drop_column('hospitals', 'slug')
