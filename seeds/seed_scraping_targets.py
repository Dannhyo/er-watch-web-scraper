"""
Seed script for scraping_targets table.
PRIVATE - Do not commit to public repository.
"""
import csv
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from scraper.database import get_session, ScrapingTarget


def seed_scraping_targets(csv_path: str = "data/scraping_targets_rows.csv") -> int:
    """
    Seed scraping_targets table from CSV file.

    Args:
        csv_path: Path to the scraping_targets CSV file.

    Returns:
        Number of scraping targets seeded.
    """
    session = get_session()
    count = 0

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            # Read raw content and handle multiline URLs
            content = f.read()

        # Parse CSV handling potential newlines in fields
        lines = []
        current_line = ""
        in_quotes = False

        for char in content:
            if char == '"':
                in_quotes = not in_quotes
            if char == '\n' and not in_quotes:
                if current_line.strip():
                    lines.append(current_line)
                current_line = ""
            else:
                current_line += char
        if current_line.strip():
            lines.append(current_line)

        # Parse header
        header = lines[0].split(",")

        for line in lines[1:]:
            # Parse CSV line properly handling quoted fields
            row = parse_csv_line(line)
            if len(row) < 4:
                continue

            hospital_id = row[0].strip()
            url = row[1].strip()
            action = row[2].strip() if len(row) > 2 else None

            # Parse JSON scraping instructions
            scraping_instructions = None
            if len(row) > 3 and row[3]:
                try:
                    json_str = row[3].strip()
                    if json_str.startswith('"') and json_str.endswith('"'):
                        json_str = json_str[1:-1]
                    json_str = json_str.replace('""', '"')
                    scraping_instructions = json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"Warning: Could not parse JSON for {hospital_id}: {e}")
                    continue

            target = ScrapingTarget(
                hospital_id=hospital_id,
                url=url,
                action=action,
                scraping_instructions=scraping_instructions,
            )
            session.merge(target)
            count += 1

        session.commit()
        print(f"Seeded {count} scraping targets successfully.")
        return count

    except Exception as e:
        session.rollback()
        print(f"Error seeding scraping targets: {e}")
        raise
    finally:
        session.close()


def parse_csv_line(line: str) -> list:
    """Parse a CSV line handling quoted fields with commas."""
    result = []
    current = ""
    in_quotes = False

    for char in line:
        if char == '"':
            in_quotes = not in_quotes
            current += char
        elif char == ',' and not in_quotes:
            result.append(current.strip())
            current = ""
        else:
            current += char

    result.append(current.strip())
    return result


if __name__ == "__main__":
    seed_scraping_targets()
