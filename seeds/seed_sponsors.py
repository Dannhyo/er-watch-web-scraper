"""
Seed script for sponsors table.
PRIVATE - Do not commit to public repository.
"""
import csv
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from scraper.database import get_session, Sponsor


def seed_sponsors(csv_path: str = "data/sponsors_rows.csv") -> int:
    """
    Seed sponsors table from CSV file.

    Args:
        csv_path: Path to the sponsors CSV file.

    Returns:
        Number of sponsors seeded.
    """
    session = get_session()
    count = 0

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                sponsor = Sponsor(
                    id=uuid.UUID(row["id"]),
                    name=row["name"],
                    description=row["description"],
                    logo_url=row["logo_url"] or None,
                    link_url=row["link_url"],
                    link_text=row["link_text"] or None,
                    is_featured=row["is_featured"].lower() == "true" if row["is_featured"] else False,
                    is_active=row["is_active"].lower() == "true" if row["is_active"] else True,
                    bg_color=row["bg_color"] or None,
                    text_color=row["text_color"] or None,
                )
                session.merge(sponsor)
                count += 1

        session.commit()
        print(f"Seeded {count} sponsors successfully.")
        return count

    except Exception as e:
        session.rollback()
        print(f"Error seeding sponsors: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_sponsors()
