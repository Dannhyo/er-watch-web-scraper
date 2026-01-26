import json
from .base_parser import BaseParser
from scraper.utils.logger import get_logger
from scraper.utils.data_formatter import DataFormatter
from scraper.utils.field_mappings import map_field_to_db

logger = get_logger(__name__)


class SelectorError(Exception):
    """Exception raised when a selector fails to find or extract data."""

    def __init__(self, field: str, data_path: str, reason: str, details: dict = None):
        self.field = field
        self.data_path = data_path
        self.reason = reason
        self.details = details or {}
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        msg = f"Selector failed for '{self.field}'\n"
        msg += f"       dataPath: {self.data_path}\n"
        msg += f"       {self.reason}"
        if self.details:
            for key, value in self.details.items():
                msg += f"\n       {key}: {value}"
        return msg


class APIParser(BaseParser):
    """
    A parser specialized for JSON and plain-text data originating from API responses.
    Inherits from BaseParser to leverage optional shared functionality.

    This class uses field-specific instructions (stored in 'scraping_instructions')
    to:
      1) Identify and extract data from JSON keys (with optional list indices).
      2) Convert raw strings into standardized types (e.g., integers, datetimes)
         via DataFormatter.
      3) Map parsed fields to a final schema (e.g., 'lastUpdated' → 'last_updated').
    """

    def parse(self, data):
        """
        Parses JSON data using the instructions in 'scraping_instructions'.

        Each field instruction may contain:
          - 'dataPath': A string path indicating how to navigate nested JSON objects/lists.
          - 'formatCode': A datetime format string (or other code) to guide parsing.
          - 'pattern': A regex pattern for advanced text matching.
          - 'unit': A unit of measure (e.g., 'minutes' or 'hours') for time-related parsing.

        Workflow:
          1) Validate that 'data' is not empty.
          2) For each field in 'scraping_instructions', extract a raw value via '_extract_data'.
          3) Convert the raw value to a string if necessary, then parse it with DataFormatter.
          4) Map the parsed result to a final schema key (e.g., 'lastUpdated' → 'last_updated').

        Args:
            data (dict): The JSON data to parse (e.g., the result of 'json.loads()').

        Returns:
            dict or None: A dictionary of parsed fields or None if no data was provided.

        Raises:
            SelectorError: If a required field cannot be extracted with detailed error info.
        """
        if not data:
            logger.error("APIParser received no JSON data to parse.")
            raise SelectorError(
                field="(root)",
                data_path="",
                reason="No JSON data provided to parse"
            )

        result = {}
        errors = []

        for key, field_instructions in self.scraping_instructions.items():
            # Extract relevant instructions
            data_path = field_instructions.get("dataPath")
            format_code = field_instructions.get("formatCode")
            pattern = field_instructions.get("pattern")
            unit = field_instructions.get("unit")

            try:
                # 1) Extract raw value from JSON using the data path
                raw_value = self._extract_data(data, data_path, key)

                # 2) Convert the raw value to a string if it's not None
                raw_str = str(raw_value) if raw_value is not None else None

                # 3) Parse/format the extracted string using DataFormatter
                parsed_value = DataFormatter.format_value(
                    field=key,
                    format_code=format_code,
                    raw_value=raw_str,
                    pattern=pattern,
                    unit=unit
                )

                # 4) Map the parsed value to final schema using centralized mappings
                db_column = map_field_to_db(key)
                result[db_column] = parsed_value

            except SelectorError as e:
                errors.append(e)
                logger.warning(str(e))

        # If all fields failed, raise the first error
        if errors and not result:
            raise errors[0]

        logger.debug(f"APIParser result: {result}")
        return result

    def parse_plain_text(self, text_data):
        """
        Parses raw text (non-JSON) data, typically a single-line or simple multiline string.

        Each field instruction in 'scraping_instructions' may still include:
          - 'formatCode': A string for date/time parsing or other format instructions.
          - 'pattern': A regex pattern for matching relevant parts of the text.
          - 'unit': A unit of measure (e.g., 'minutes' or 'hours') for time-related conversions.

        Since this is plain text, 'dataPath' is generally irrelevant, but
        it's retained for compatibility with the JSON-based approach.

        Workflow:
          1) Verify 'text_data' is not empty.
          2) For each field, ignore 'dataPath' and treat the entire text as 'raw_value'.
          3) Pass the raw value to DataFormatter for parsing.
          4) Map the parsed result to the final schema.

        Args:
            text_data (str): The plain text content to parse.

        Returns:
            dict or None: A dictionary of parsed fields or None if 'text_data' is empty.

        Raises:
            SelectorError: If the text data is empty or parsing fails.
        """
        if not text_data:
            logger.error("No text_data provided to parse_plain_text.")
            raise SelectorError(
                field="(root)",
                data_path="",
                reason="No text data provided to parse"
            )

        result = {}
        for key, field_instructions in self.scraping_instructions.items():
            # Extract relevant instructions
            format_code = field_instructions.get("formatCode")
            pattern = field_instructions.get("pattern")
            unit = field_instructions.get("unit")

            # In plain text mode, ignore 'dataPath'—just parse the entire text
            raw_str = text_data.strip() if text_data else None

            parsed_value = DataFormatter.format_value(
                field=key,
                format_code=format_code,
                raw_value=raw_str,
                pattern=pattern,
                unit=unit
            )

            # Map the parsed value to final schema using centralized mappings
            db_column = map_field_to_db(key)
            result[db_column] = parsed_value

        logger.debug(f"APIParser plain text result: {result}")
        return result

    def _extract_data(self, data, data_path, field_name):
        """
        Safely extracts a value from a JSON-like structure using a dot/bracket path.

        Examples:
          - data_path='sites[0].lastUpdate' => data["sites"][0]["lastUpdate"]
          - If data_path is empty, returns None and logs a warning.

        Args:
            data (dict): The JSON data from which values are extracted.
            data_path (str): A bracket/dot notation string specifying nested keys/indices.
            field_name (str): The field name being extracted (for error reporting).

        Returns:
            Any or None: The extracted value if the path is valid, otherwise None.

        Raises:
            SelectorError: If the data path is invalid or value cannot be extracted.
        """
        if not data_path:
            raise SelectorError(
                field=field_name,
                data_path="(empty)",
                reason="No dataPath provided in scraping instructions"
            )

        try:
            # Replace bracket notation with dots and split
            parts = [p for p in data_path.replace("[", ".").replace("]", "").split(".") if p]
            cur = data
            traversed = []

            # Traverse the JSON structure according to the parts
            for part in parts:
                traversed.append(part)
                if part.isdigit():  # Handle numeric list indices
                    idx = int(part)
                    if not isinstance(cur, list):
                        raise SelectorError(
                            field=field_name,
                            data_path=data_path,
                            reason=f"Expected list at '{'.'.join(traversed[:-1])}', got {type(cur).__name__}",
                            details={"traversed": ".".join(traversed[:-1])}
                        )
                    if idx >= len(cur):
                        raise SelectorError(
                            field=field_name,
                            data_path=data_path,
                            reason=f"Index {idx} out of bounds (list has {len(cur)} items)",
                            details={"traversed": ".".join(traversed[:-1]), "list_length": len(cur)}
                        )
                    cur = cur[idx]
                else:
                    if not isinstance(cur, dict):
                        raise SelectorError(
                            field=field_name,
                            data_path=data_path,
                            reason=f"Expected object at '{'.'.join(traversed[:-1])}', got {type(cur).__name__}",
                            details={"traversed": ".".join(traversed[:-1])}
                        )
                    if part not in cur:
                        available_keys = list(cur.keys())[:5]  # Show first 5 keys
                        raise SelectorError(
                            field=field_name,
                            data_path=data_path,
                            reason=f"Key '{part}' not found in object",
                            details={
                                "traversed": ".".join(traversed[:-1]) if traversed[:-1] else "(root)",
                                "available_keys": available_keys
                            }
                        )
                    cur = cur[part]

            logger.debug(f"Extracted value for field '{field_name}': {cur}")
            return cur

        except SelectorError:
            raise
        except (KeyError, IndexError, TypeError) as e:
            raise SelectorError(
                field=field_name,
                data_path=data_path,
                reason=f"Failed to extract data: {type(e).__name__}: {e}"
            )
