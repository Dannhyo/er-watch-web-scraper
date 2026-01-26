import aiohttp
from urllib.parse import urlparse
from .base_scraper import BaseScraper
from scraper.parsers.api_parser import APIParser
from scraper.utils.logger import get_logger
from scraper.utils.http_client import get_session

logger = get_logger(__name__)


class APIScraper(BaseScraper):
    """
    A scraper class designed to retrieve data from an API endpoint
    and parse the result into a consistent data structure.

    Inherits from:
        BaseScraper (ABC): Provides the abstract interface and common
        data finalization logic via the `process_parsed_data` method.
    """

    async def scrape(self):
        """
        Fetches data from the API endpoint (self.url) using an async GET request,
        then determines the response content type and parses the data
        accordingly. If the server returns JSON, it is parsed as JSON;
        otherwise, the raw text content is parsed.

        Returns:
            dict or None:
                - A dictionary containing standardized data (e.g., hospital_id,
                  estimated_wait_time, etc.) if parsing is successful.
                - None if the request fails or no data can be parsed.

        Raises:
            Exception: Propagates exceptions with detailed error info for failure tracking.
        """
        logger.debug(f"Fetching API data from {self.url}")

        # 1) Make the async request to the specified URL
        try:
            session = await get_session()
            # Add Referer header based on the URL domain (some servers require this)
            parsed_url = urlparse(self.url)
            referer = f"{parsed_url.scheme}://{parsed_url.netloc}/"
            headers = {"Referer": referer}
            async with session.get(self.url, timeout=aiohttp.ClientTimeout(total=10), headers=headers) as response:
                response.raise_for_status()
                logger.debug(f"Received response from {self.url}")

                # 2) Inspect the Content-Type header to determine the response format.
                content_type = response.headers.get("Content-Type", "").lower()
                text = await response.text()

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

        # 3) Select the parsing approach based on JSON vs. text content.
        #    If the body starts with '{' or '[', we assume it's JSON,
        #    even if the content-type doesn't explicitly say so.
        if ("application/json" in content_type or
            text.strip().startswith("{") or
            text.strip().startswith("[")):
            # Parse as JSON using the APIParser.
            try:
                import json
                json_data = json.loads(text)
                parsed_data = APIParser(self.scraping_instructions).parse(json_data)
                logger.debug(f"Parsed JSON data: {parsed_data}")
            except ValueError as parse_err:
                error_msg = f"Failed to parse JSON response: {parse_err}"
                logger.error(error_msg)
                raise Exception(error_msg)
        else:
            # Otherwise, parse as plain text.
            parsed_data = APIParser(self.scraping_instructions).parse_plain_text(text)
            logger.debug(f"Parsed plain text data: {parsed_data}")

        return self.process_parsed_data(parsed_data)
