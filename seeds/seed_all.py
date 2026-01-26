"""
Master seed script - seeds all tables in the correct order.
PRIVATE - Do not commit to public repository.

Usage:
    python -m seeds.seed_all
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from seeds.seed_hospitals import seed_hospitals
from seeds.seed_scraping_targets import seed_scraping_targets
from seeds.seed_sponsors import seed_sponsors


def seed_all():
    """Seed all tables in the correct order (respecting foreign keys)."""
    print("=" * 50)
    print("Starting database seeding...")
    print("=" * 50)

    # 1. Hospitals first (no dependencies)
    print("\n[1/3] Seeding hospitals...")
    hospitals_count = seed_hospitals()

    # 2. Scraping targets (depends on hospitals)
    print("\n[2/3] Seeding scraping targets...")
    targets_count = seed_scraping_targets()

    # 3. Sponsors (no dependencies)
    print("\n[3/3] Seeding sponsors...")
    sponsors_count = seed_sponsors()

    print("\n" + "=" * 50)
    print("Seeding complete!")
    print(f"  - Hospitals: {hospitals_count}")
    print(f"  - Scraping targets: {targets_count}")
    print(f"  - Sponsors: {sponsors_count}")
    print("=" * 50)


if __name__ == "__main__":
    seed_all()
