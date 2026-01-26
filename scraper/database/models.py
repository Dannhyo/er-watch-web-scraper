import uuid
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import (
    String,
    SmallInteger,
    Boolean,
    Text,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scraper.database.connection import Base


class Hospital(Base):
    """Hospital information table."""

    __tablename__ = "hospitals"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    slug: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True, index=True)
    region: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    classification: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    healthcare_network: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    street: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # PostgreSQL point type stored as string "(x,y)" - use raw SQL for geo queries
    coordinates: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships
    scraped_data: Mapped[Optional["ScrapedData"]] = relationship(
        "ScrapedData", back_populates="hospital", uselist=False, cascade="all, delete-orphan"
    )
    scraping_target: Mapped[Optional["ScrapingTarget"]] = relationship(
        "ScrapingTarget", back_populates="hospital", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Hospital(id={self.id!r}, name={self.name!r})>"


class ScrapedData(Base):
    """Scraped ER wait time data."""

    __tablename__ = "scraped_data"

    hospital_id: Mapped[str] = mapped_column(
        String, ForeignKey("hospitals.id", ondelete="CASCADE"), primary_key=True
    )
    estimated_wait_time: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    patients_waiting: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    patients_in_treatment: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    last_updated: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    status: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, server_default="active"
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, server_default=func.now()
    )

    # Relationships
    hospital: Mapped["Hospital"] = relationship("Hospital", back_populates="scraped_data")

    def __repr__(self) -> str:
        return f"<ScrapedData(hospital_id={self.hospital_id!r}, status={self.status!r})>"


class ScrapedDataHistory(Base):
    """Historical scraped ER wait time data."""

    __tablename__ = "scraped_data_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hospital_id: Mapped[str] = mapped_column(
        String, ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    estimated_wait_time: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    patients_waiting: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    patients_in_treatment: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    last_updated: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    # Relationships
    hospital: Mapped["Hospital"] = relationship("Hospital")

    def __repr__(self) -> str:
        return f"<ScrapedDataHistory(id={self.id!r}, hospital_id={self.hospital_id!r}, scraped_at={self.scraped_at!r})>"


class ScrapingTarget(Base):
    """Scraping target configuration for each hospital."""

    __tablename__ = "scraping_targets"

    hospital_id: Mapped[str] = mapped_column(
        String, ForeignKey("hospitals.id", ondelete="CASCADE"), primary_key=True
    )
    url: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    scraping_instructions: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )

    # Relationships
    hospital: Mapped["Hospital"] = relationship("Hospital", back_populates="scraping_target")

    def __repr__(self) -> str:
        return f"<ScrapingTarget(hospital_id={self.hospital_id!r}, action={self.action!r})>"


class Sponsor(Base):
    """Sponsor information for the platform."""

    __tablename__ = "sponsors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    link_url: Mapped[str] = mapped_column(String, nullable=False)
    link_text: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_featured: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True, server_default="false"
    )
    is_active: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True, server_default="true"
    )
    bg_color: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    text_color: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Sponsor(id={self.id!r}, name={self.name!r})>"
