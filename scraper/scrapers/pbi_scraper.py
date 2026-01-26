import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from .base_scraper import BaseScraper
from scraper.parsers.html_parser import HTMLParser
from scraper.utils.logger import get_logger

logger = get_logger(__name__)


class PBIScraper(BaseScraper):
    """
    A scraper class specifically designed to handle pages rendered by Power BI (PBI).
    It uses Playwright to load dynamic content before parsing the resulting HTML with BeautifulSoup.

    Inherits from:
        BaseScraper (ABC): Provides abstract scrape method signature and
        a process_parsed_data hook for post-processing the scraped data.
    """

    async def scrape(self, use_headers=False):
        """
        Launches a headless Chromium browser using Playwright to load a
        Power BI-rendered page, then extracts and parses HTML content. This
        method helps handle dynamic or JavaScript-heavy pages that standard
        requests-based scraping might fail to parse correctly.

        Args:
            use_headers (bool, optional): If True, sets additional HTTP headers
                                          such as User-Agent or Accept-Language
                                          before navigating to the URL. Defaults to False.

        Returns:
            dict or None:
                - A dictionary with structured fields (e.g., estimated_wait_time,
                  patients_waiting, patients_in_treatment, etc.) if scraping succeeds.
                - None if any error occurs or the parsed data is empty.

        Raises:
            Exception: Propagates exceptions with detailed error info for failure tracking.
        """
        logger.info(f"Starting Power BI scraping for {self.url}")

        browser = None
        playwright = None

        try:
            # 1) Initialize the async Playwright context and launch headless Chromium.
            playwright = await async_playwright().start()
            logger.debug("Launching headless Chromium browser.")
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()

            # Optionally set custom headers (e.g., User-Agent).
            if use_headers:
                logger.debug("Applying additional HTTP headers for scraping.")
                await page.set_extra_http_headers({
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "en-US,en;q=0.9",
                    "Upgrade-Insecure-Requests": "1"
                })

            # 2) Navigate to the provided URL.
            logger.debug(f"Navigating to: {self.url}")
            await page.goto(self.url)

            # 3) Wait for the network to become idle, indicating that most
            #    dynamic content should be loaded.
            try:
                logger.debug("Waiting for Power BI visual to load...")
                await page.wait_for_load_state('networkidle', timeout=30_000)
                logger.debug("Power BI visual loaded successfully.")
            except PlaywrightTimeoutError:
                error_msg = "Timeout waiting for network idle (30s)"
                logger.error(error_msg)
                raise Exception(error_msg)

            # 4) Extract the fully rendered HTML content after JavaScript has executed.
            logger.debug("Extracting rendered HTML content from the page.")
            content = await page.content()

        except PlaywrightTimeoutError as e:
            error_msg = f"Playwright timeout: {e}"
            logger.error(f"PBI scrape failed: {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            # Re-raise with clear error message
            if "Timeout" in str(e):
                raise
            error_msg = f"Browser error: {type(e).__name__}: {e}"
            logger.error(f"PBI scrape failed: {error_msg}")
            raise Exception(error_msg)
        finally:
            # 5) Always close browser and playwright to free resources
            if browser:
                try:
                    await browser.close()
                    logger.debug("Browser closed successfully.")
                except Exception as close_err:
                    logger.warning(f"Error closing browser: {close_err}")
            if playwright:
                try:
                    await playwright.stop()
                    logger.debug("Playwright stopped successfully.")
                except Exception as stop_err:
                    logger.warning(f"Error stopping playwright: {stop_err}")

        # 6) Parse the retrieved HTML with BeautifulSoup and the custom HTMLParser.
        try:
            logger.debug("Converting rendered HTML content to a BeautifulSoup object.")
            soup = BeautifulSoup(content, "html.parser")

            logger.debug("Parsing the HTML content with the custom HTMLParser.")
            parser = HTMLParser(self.scraping_instructions)
            parsed_data = parser.parse(soup)

        except Exception as e:
            error_msg = f"HTML parsing failed: {type(e).__name__}: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

        return self.process_parsed_data(parsed_data)
