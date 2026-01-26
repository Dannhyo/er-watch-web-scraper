"""
API scraper that uses Playwright (headless browser) to bypass bot protection,
then parses the response as JSON.
"""
import json
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from .base_scraper import BaseScraper
from scraper.parsers.api_parser import APIParser
from scraper.utils.logger import get_logger

logger = get_logger(__name__)


class APIHeadlessScraper(BaseScraper):
    """
    A scraper that uses a headless browser to fetch JSON data from
    URLs protected by Cloudflare or similar bot protection.
    """

    async def scrape(self):
        """
        Launches a headless Chromium browser to fetch JSON data,
        bypassing bot protection that blocks simple HTTP requests.

        Returns:
            dict or None: Parsed and processed data, or None on failure.

        Raises:
            Exception: Propagates exceptions with detailed error info.
        """
        logger.info(f"Starting headless API scraping for {self.url}")

        browser = None
        playwright = None

        try:
            # 1) Initialize Playwright and launch headless browser
            playwright = await async_playwright().start()
            logger.debug("Launching headless Chromium browser.")
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()

            # Set browser-like headers
            await page.set_extra_http_headers({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
            })

            # 2) Navigate to the URL
            logger.debug(f"Navigating to: {self.url}")
            response = await page.goto(self.url, wait_until="networkidle", timeout=30000)

            if response.status >= 400:
                error_msg = f"HTTP {response.status}"
                logger.error(f"Request failed: {error_msg}")
                raise Exception(error_msg)

            # 3) Get the page content - for JSON URLs, browser wraps it in HTML
            # The JSON is typically in a <pre> tag or as the body text
            content = await page.content()

            # Try to extract JSON from the page
            # First, try to get inner text which should be the raw JSON
            try:
                text = await page.inner_text("body")
            except Exception:
                # Fallback: extract from pre tag if present
                try:
                    text = await page.inner_text("pre")
                except Exception:
                    # Last resort: use the raw content and strip HTML
                    text = content

            logger.debug(f"Extracted text length: {len(text)}")

        except PlaywrightTimeoutError as e:
            error_msg = f"Playwright timeout: {e}"
            logger.error(f"API headless scrape failed: {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            if "HTTP" in str(e):
                raise
            error_msg = f"Browser error: {type(e).__name__}: {e}"
            logger.error(f"API headless scrape failed: {error_msg}")
            raise Exception(error_msg)
        finally:
            # 4) Always close browser and playwright
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

        # 5) Parse the JSON response
        try:
            json_data = json.loads(text.strip())
            parsed_data = APIParser(self.scraping_instructions).parse(json_data)
            logger.debug(f"Parsed JSON data: {parsed_data}")
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

        return self.process_parsed_data(parsed_data)
