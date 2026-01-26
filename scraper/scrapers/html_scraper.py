import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from .base_scraper import BaseScraper
from scraper.parsers.html_parser import HTMLParser
from scraper.utils.logger import get_logger
from scraper.utils.http_client import get_session

logger = get_logger(__name__)


class HTMLScraper(BaseScraper):
    """
    A scraper class designed to retrieve and parse HTML content
    for 'html' type scraping targets.

    Inherits from:
        BaseScraper (ABC): Provides the abstract interface and a
        process_parsed_data hook for post-processing.
    """

    async def scrape(self):
        """
        Fetches and parses HTML content from the target URL (self.url)
        using aiohttp and BeautifulSoup library. Then it delegates parsing logic
        to the HTMLParser class, which uses self.scraping_instructions
        for extraction rules.

        Returns:
            dict or None:
                - A dictionary containing standardized data (e.g.,
                  hospital_id, estimated_wait_time, etc.) if parsing
                  succeeds.
                - None if the request fails or parsing yields no result.

        Raises:
            Exception: Propagates exceptions with detailed error info for failure tracking.
        """
        logger.debug(f"Starting HTML scrape for {self.url}")

        # 1) Send an async GET request to the target URL
        try:
            session = await get_session()
            # Add Referer header based on the URL domain (some servers require this)
            parsed_url = urlparse(self.url)
            referer = f"{parsed_url.scheme}://{parsed_url.netloc}/"
            headers = {"Referer": referer}
            async with session.get(self.url, timeout=aiohttp.ClientTimeout(total=10), headers=headers) as response:
                response.raise_for_status()
                logger.debug(f"Received HTML response from {self.url}")
                html_content = await response.text()

        except aiohttp.ClientResponseError as e:
            error_msg = f"HTTP {e.status} {e.message}"
            logger.error(f"Fetch error: {error_msg}")
            raise Exception(error_msg)
        except aiohttp.ClientError as e:
            error_msg = f"Connection error: {type(e).__name__}: {e}"
            logger.error(f"Fetch error: {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Request failed: {type(e).__name__}: {e}"
            logger.error(f"Fetch error: {error_msg}")
            raise Exception(error_msg)

        # 2) Parse the HTML response using BeautifulSoup.
        soup = BeautifulSoup(html_content, "html.parser")

        # 3) Use HTMLParser (custom parser) to extract relevant fields
        #    from the soup object based on scraping_instructions.
        parser = HTMLParser(self.scraping_instructions)
        parsed_data = parser.parse(soup)

        return self.process_parsed_data(parsed_data)
