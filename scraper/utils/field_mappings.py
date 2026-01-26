"""
Centralized field name mappings for consistent data transformation across parsers.
"""

# Maps scraping instruction field names to database column names
FIELD_TO_DB_COLUMN = {
    "lastUpdated": "last_updated",
    "patientsWaiting": "patients_waiting",
    "patientsInTreatment": "patients_in_treatment",
    "estimatedWaitTime": "estimated_wait_time",
}


def map_field_to_db(field_name: str) -> str:
    """
    Maps a scraping instruction field name to its database column name.

    Args:
        field_name: The field name from scraping instructions (e.g., 'lastUpdated')

    Returns:
        The corresponding database column name (e.g., 'last_updated'),
        or the original field name if no mapping exists.
    """
    return FIELD_TO_DB_COLUMN.get(field_name, field_name)


def map_result_fields(result: dict) -> dict:
    """
    Maps all fields in a result dictionary to their database column names.

    Args:
        result: Dictionary with scraping instruction field names as keys

    Returns:
        New dictionary with database column names as keys
    """
    return {map_field_to_db(key): value for key, value in result.items()}
