from datetime import datetime, timezone
from typing import List, Dict, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from scraper.database import get_session, ScrapedData, ScrapingTarget
from scraper.utils.logger import get_logger

logger = get_logger(__name__)


class SupabaseRepository:
    """
    Manages database interactions for retrieving and storing scraped data.

    This repository class handles:
      1) Establishing a connection to a PostgreSQL database via SQLAlchemy.
      2) Saving scraped data via an UPSERT operation on the 'scraped_data' table.
      3) Retrieving scraping targets from the 'scraping_targets' table.
    """

    def __init__(self):
        """
        Initializes the SupabaseRepository by creating a SQLAlchemy session.

        Raises:
            ValueError: If any required environment variable is missing.
            SQLAlchemyError: If unable to connect to the database.
        """
        self._session = None

        try:
            self._session = get_session()
            # Test connection by executing a simple query
            self._session.execute(text("SELECT 1"))
            logger.info("Database connection established successfully.")
        except SQLAlchemyError as e:
            logger.error(f"Error connecting to the database: {e}")
            if self._session:
                self._session.rollback()
            raise

    def save_scraped_data(self, data: Dict) -> None:
        """
        Inserts or updates scraped data in the 'scraped_data' table.

        Uses SQLAlchemy's merge() for UPSERT behavior based on the primary key.

        Args:
            data (Dict): A dictionary containing the fields to be saved or updated.
                Expected keys:
                - "hospital_id": str
                - "estimated_wait_time": int or None
                - "patients_waiting": int or None
                - "patients_in_treatment": int or None
                - "last_updated": datetime or str or None
                - "status": str (e.g., "online", "offline")
        """
        if self._session is None:
            logger.error("Cannot save data: no database session is available.")
            return

        hospital_id = data.get("hospital_id")

        try:
            logger.debug(f"Preparing to UPSERT data for hospital_id={hospital_id}: {data}")

            # Parse last_updated if it's a string
            last_updated = data.get("last_updated")
            if isinstance(last_updated, str):
                try:
                    last_updated = datetime.fromisoformat(last_updated)
                except ValueError:
                    last_updated = None

            # Create or update the ScrapedData record
            scraped_data = ScrapedData(
                hospital_id=hospital_id,
                estimated_wait_time=data.get("estimated_wait_time"),
                patients_waiting=data.get("patients_waiting"),
                patients_in_treatment=data.get("patients_in_treatment"),
                last_updated=last_updated,
                status=data.get("status"),
                updated_at=datetime.now(timezone.utc),
            )

            # merge() handles insert-or-update based on primary key
            self._session.merge(scraped_data)
            self._session.commit()

            logger.info(f"Data saved successfully for hospital_id={hospital_id}.")

        except SQLAlchemyError as e:
            logger.error(f"Error saving data to the database for hospital_id={hospital_id}: {e}")
            self._session.rollback()

    def get_target_data(self) -> List[Dict]:
        """
        Retrieves target entries from the 'scraping_targets' table.

        Returns:
            List[Dict]: A list of dictionaries, each representing a row from
                'scraping_targets', or an empty list if no rows are found or
                an error occurs.
        """
        if self._session is None:
            logger.error("Cannot retrieve target data: no database session is available.")
            return []

        try:
            targets = self._session.query(ScrapingTarget).all()

            if not targets:
                logger.info("No rows found in 'scraping_targets' table.")
                return []

            logger.info(f"Fetched {len(targets)} rows from 'scraping_targets' table.")

            # Convert ORM objects to dictionaries
            return [
                {
                    "hospital_id": target.hospital_id,
                    "url": target.url,
                    "action": target.action,
                    "scraping_instructions": target.scraping_instructions,
                }
                for target in targets
            ]

        except SQLAlchemyError as e:
            logger.error(f"Error downloading target data: {e}")
            return []

    def get_scraped_data(self, hospital_id: str) -> Optional[Dict]:
        """
        Retrieves scraped data for a specific hospital.

        Args:
            hospital_id: The hospital ID to look up.

        Returns:
            A dictionary with the scraped data, or None if not found.
        """
        if self._session is None:
            logger.error("Cannot retrieve data: no database session is available.")
            return None

        try:
            record = self._session.query(ScrapedData).filter_by(hospital_id=hospital_id).first()

            if not record:
                return None

            return {
                "hospital_id": record.hospital_id,
                "estimated_wait_time": record.estimated_wait_time,
                "patients_waiting": record.patients_waiting,
                "patients_in_treatment": record.patients_in_treatment,
                "last_updated": record.last_updated.isoformat() if record.last_updated else None,
                "status": record.status,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            }

        except SQLAlchemyError as e:
            logger.error(f"Error retrieving data for hospital_id={hospital_id}: {e}")
            return None

    def close(self) -> None:
        """Explicitly close the database session."""
        if self._session:
            self._session.close()
            logger.debug("Database session closed.")
            self._session = None

    def __del__(self):
        """
        Ensures the database session is closed gracefully
        when the SupabaseRepository object is garbage-collected.
        """
        self.close()

    def __enter__(self):
        """Support usage as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close session when exiting context."""
        self.close()
        return False
