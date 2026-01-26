"""Initial schema - baseline migration for existing tables.

Revision ID: 001_initial
Revises: None
Create Date: 2025-01-26

This migration represents the existing database schema.
For existing databases, run: alembic stamp head
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create hospitals table
    op.create_table(
        "hospitals",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("classification", sa.String(), nullable=True),
        sa.Column("healthcare_network", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("street", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("postal_code", sa.String(), nullable=True),
        sa.Column("coordinates", sa.String(), nullable=True),  # PostgreSQL point stored as text
        sa.Column("website", sa.String(), nullable=True),
        sa.Column("phone_number", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", name="hospitals_id_key"),
    )

    # Create scraped_data table
    op.create_table(
        "scraped_data",
        sa.Column("hospital_id", sa.String(), nullable=False),
        sa.Column("estimated_wait_time", sa.SmallInteger(), nullable=True),
        sa.Column("patients_waiting", sa.SmallInteger(), nullable=True),
        sa.Column("patients_in_treatment", sa.SmallInteger(), nullable=True),
        sa.Column("last_updated", TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "status", sa.String(), nullable=True, server_default=sa.text("'active'")
        ),
        sa.Column(
            "updated_at",
            TIMESTAMP(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("hospital_id"),
        sa.UniqueConstraint("hospital_id", name="scraped_data_hospital_id_key"),
        sa.ForeignKeyConstraint(
            ["hospital_id"],
            ["hospitals.id"],
            name="scraped_data_hospital_id_fkey",
            ondelete="CASCADE",
        ),
    )

    # Create scraping_targets table
    op.create_table(
        "scraping_targets",
        sa.Column("hospital_id", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=True),
        sa.Column("scraping_instructions", JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("hospital_id"),
        sa.UniqueConstraint("hospital_id", name="scraping_targets_hospital_id_key"),
        sa.ForeignKeyConstraint(
            ["hospital_id"],
            ["hospitals.id"],
            name="scraping_targets_hospital_id_fkey",
            ondelete="CASCADE",
        ),
    )

    # Create sponsors table
    op.create_table(
        "sponsors",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("logo_url", sa.String(), nullable=True),
        sa.Column("link_url", sa.String(), nullable=False),
        sa.Column("link_text", sa.String(), nullable=True),
        sa.Column(
            "is_featured", sa.Boolean(), nullable=True, server_default=sa.text("false")
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")
        ),
        sa.Column("bg_color", sa.String(), nullable=True),
        sa.Column("text_color", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            TIMESTAMP(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("sponsors")
    op.drop_table("scraping_targets")
    op.drop_table("scraped_data")
    op.drop_table("hospitals")
