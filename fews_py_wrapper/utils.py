from datetime import datetime, timezone
import pandas as pd


def format_datetime(dt: datetime) -> str:
    """Format a datetime object to a string suitable for FEWS web services."""
    if not dt.tzinfo:
        raise ValueError("Datetime object must be timezone-aware.")
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def convert_timeseries_response_to_dataframe(response_content) -> pd.DataFrame:
    """Convert the timeseries response content to a pandas DataFrame."""
    pass
