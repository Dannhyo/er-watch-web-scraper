import asyncio
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

from scraper.scrapers.api_scraper import APIScraper
from scraper.scrapers.api_headless_scraper import APIHeadlessScraper
from scraper.scrapers.html_scraper import HTMLScraper
from scraper.scrapers.pbi_scraper import PBIScraper
from scraper.repository.supabase_repository import SupabaseRepository
from scraper.utils.logger import get_logger, set_hospital_context
from scraper.utils.http_client import close_session

logger = get_logger(__name__)


@dataclass
class ParsingWarning:
    """Warning for a field that returned None despite successful scrape."""
    hospital_id: str
    action: str
    url: str
    field: str
    raw_value: Optional[str] = None


@dataclass
class ScrapeResult:
    """Result of a single hospital scrape attempt."""
    hospital_id: str
    action: str
    url: str
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    defined_fields: Optional[List[str]] = None  # Fields defined in scraping_instructions


@dataclass
class RunSummary:
    """Summary of the entire scraper run."""
    total: int = 0
    successful: int = 0
    failed: int = 0
    failures: List[ScrapeResult] = field(default_factory=list)
    parsing_warnings: List[ParsingWarning] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.successful / self.total) * 100

    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def hospitals_with_null_fields(self) -> int:
        """Count unique hospitals that have at least one null field."""
        return len(set(w.hospital_id for w in self.parsing_warnings))


class Aggregator:
    """
    The Aggregator class orchestrates multiple scrapers to retrieve data
    from various sources and store the results using a Supabase repository.

    Attributes:
        scraping_targets (list): A list of dictionaries that define how and
            what to scrape. Each dictionary typically contains keys like
            "action" and "hospital_id".
        supabase_repo (SupabaseRepository): An instance of the SupabaseRepository
            for saving the scraped data.
    """

    # Concurrency limits by scraper type
    CONCURRENCY_LIMITS = {
        "api": 20,   # High concurrency for fast API calls
        "html": 20,  # High concurrency for HTML fetches
        "pbi": 3,    # Low concurrency for browser-based scraping
        "pbi_h": 3,  # Low concurrency for browser-based scraping with headers
        "api_h": 3,  # Low concurrency for headless browser API scraping
    }

    def __init__(self, scraping_targets):
        """
        Initializes the Aggregator with the scraping targets.

        Args:
            scraping_targets (list): A list of dictionaries specifying
                scraping parameters, including the "action" type and other details.
        """
        self.scraping_targets = scraping_targets
        try:
            self.supabase_repo = SupabaseRepository()
            logger.info("SupabaseRepository initialized successfully.")
        except ValueError as e:
            # This typically indicates missing environment variables or other init issues.
            logger.critical(f"Failed to initialize SupabaseRepository: {e}")
            self.supabase_repo = None

    # Mapping from scraping instruction field names to DB column names
    FIELD_NAME_MAP = {
        "lastUpdated": "last_updated",
        "patientsWaiting": "patients_waiting",
        "patientsInTreatment": "patients_in_treatment",
        "estimatedWaitTime": "estimated_wait_time",
    }

    async def _scrape_single(self, target: dict) -> ScrapeResult:
        """
        Scrape a single target and return the result.

        Args:
            target: Dictionary containing scraping target info

        Returns:
            ScrapeResult with success/failure info
        """
        action = target.get("action")
        hospital_id = target.get("hospital_id")
        url = target.get("url", "")
        scraping_instructions = target.get("scraping_instructions", {})

        # Set hospital context for logging
        set_hospital_context(hospital_id)

        # Get list of DB column names for fields defined in scraping_instructions
        defined_fields = [
            self.FIELD_NAME_MAP.get(field, field)
            for field in scraping_instructions.keys()
        ]

        logger.debug(f"Processing target: action={action}")

        try:
            # Select the scraper type based on the "action" field.
            if action == "api":
                scraper = APIScraper(target)
                data = await scraper.scrape()
            elif action == "html":
                scraper = HTMLScraper(target)
                data = await scraper.scrape()
            elif action == "pbi":
                scraper = PBIScraper(target)
                data = await scraper.scrape()
            elif action == "pbi_h":
                scraper = PBIScraper(target)
                data = await scraper.scrape(use_headers=True)
            elif action == "api_h":
                scraper = APIHeadlessScraper(target)
                data = await scraper.scrape()
            else:
                return ScrapeResult(
                    hospital_id=hospital_id,
                    action=action or "unknown",
                    url=url,
                    success=False,
                    error=f"Unsupported action type: '{action}'",
                    defined_fields=defined_fields
                )

            if not data:
                return ScrapeResult(
                    hospital_id=hospital_id,
                    action=action,
                    url=url,
                    success=False,
                    error="No data returned from scraper",
                    defined_fields=defined_fields
                )

            return ScrapeResult(
                hospital_id=hospital_id,
                action=action,
                url=url,
                success=True,
                data=data,
                defined_fields=defined_fields
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Scraping failed: {error_msg}")
            return ScrapeResult(
                hospital_id=hospital_id,
                action=action or "unknown",
                url=url,
                success=False,
                error=error_msg,
                defined_fields=defined_fields
            )
        finally:
            # Clear hospital context after scraping
            set_hospital_context(None)

    async def _scrape_batch(self, targets: List[dict], semaphore: asyncio.Semaphore) -> List[ScrapeResult]:
        """
        Scrape a batch of targets with concurrency control.

        Args:
            targets: List of scraping targets
            semaphore: Semaphore for concurrency control

        Returns:
            List of ScrapeResults
        """
        async def scrape_with_semaphore(target):
            async with semaphore:
                return await self._scrape_single(target)

        tasks = [scrape_with_semaphore(target) for target in targets]
        return await asyncio.gather(*tasks)

    async def run(self) -> RunSummary:
        """
        Executes the scraping workflow with concurrent execution:
          1. Validates the Supabase repository is initialized.
          2. Groups targets by action type for appropriate concurrency limits.
          3. Runs all scrapers concurrently within their limits.
          4. Stores results and tracks failures.

        Returns:
            RunSummary with statistics and failure details
        """
        summary = RunSummary(start_time=datetime.utcnow())

        # Check if the Supabase repository was successfully set up.
        if not self.supabase_repo:
            logger.error("Cannot proceed without a valid SupabaseRepository instance.")
            summary.end_time = datetime.utcnow()
            return summary

        logger.info(f"Starting concurrent scraping of {len(self.scraping_targets)} targets...")
        summary.total = len(self.scraping_targets)

        # Group targets by action type
        targets_by_action = {}
        for target in self.scraping_targets:
            action = target.get("action", "unknown")
            if action not in targets_by_action:
                targets_by_action[action] = []
            targets_by_action[action].append(target)

        # Create tasks for each action group with appropriate concurrency
        all_results = []
        batch_tasks = []

        for action, targets in targets_by_action.items():
            limit = self.CONCURRENCY_LIMITS.get(action, 5)
            semaphore = asyncio.Semaphore(limit)
            logger.info(f"Scraping {len(targets)} '{action}' targets with concurrency limit {limit}")
            batch_tasks.append(self._scrape_batch(targets, semaphore))

        # Run all batches concurrently
        batch_results = await asyncio.gather(*batch_tasks)
        for results in batch_results:
            all_results.extend(results)

        # Process results
        for result in all_results:
            if result.success:
                summary.successful += 1
                logger.info(f"Scraped data for hospital_id={result.hospital_id}: {result.data}")
                self.supabase_repo.save_scraped_data(result.data)

                # Check for null fields in successful scrapes (parsing warnings)
                # Only warn about fields that were actually defined in scraping_instructions
                if result.data and result.defined_fields:
                    for field_name in result.defined_fields:
                        if result.data.get(field_name) is None:
                            summary.parsing_warnings.append(ParsingWarning(
                                hospital_id=result.hospital_id,
                                action=result.action,
                                url=result.url,
                                field=field_name,
                            ))
            else:
                summary.failed += 1
                summary.failures.append(result)

                # Save offline status for failed scrapes
                error_data = {
                    "hospital_id": result.hospital_id,
                    "estimated_wait_time": None,
                    "patients_waiting": None,
                    "patients_in_treatment": None,
                    "last_updated": None,
                    "status": "offline",
                }
                self.supabase_repo.save_scraped_data(error_data)

        # Close the shared HTTP session
        await close_session()

        summary.end_time = datetime.utcnow()
        logger.info(f"Aggregator run complete. {summary.successful}/{summary.total} successful in {summary.duration_seconds:.1f}s")

        return summary
