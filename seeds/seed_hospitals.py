"""
Seed script for hospitals table.
PRIVATE - Do not commit to public repository.
"""
import csv
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from scraper.database import get_session, Hospital


def seed_hospitals(csv_path: str = "data/hospitals_rows.csv") -> int:
    """
    Seed hospitals table from CSV file.

    Args:
        csv_path: Path to the hospitals CSV file.

    Returns:
        Number of hospitals seeded.
    """
    session = get_session()
    count = 0

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                hospital = Hospital(
                    id=row["id"],
                    region=row["region"] or None,
                    classification=row["classification"] or None,
                    healthcare_network=row["healthcare_network"] or None,
                    name=row["name"] or None,
                    street=row["street"] or None,
                    city=row["city"] or None,
                    postal_code=row["postal_code"] or None,
                    coordinates=row["coordinates"] or None,
                    website=row["website"] or None,
                    phone_number=row["phone_number"] or None,
                )
                session.merge(hospital)
                count += 1

        session.commit()
        print(f"Seeded {count} hospitals successfully.")
        return count

    except Exception as e:
        session.rollback()
        print(f"Error seeding hospitals: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_hospitals()
