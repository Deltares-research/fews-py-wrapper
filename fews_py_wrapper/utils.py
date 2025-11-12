import inspect
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


def format_time_args(*args: None | datetime) -> list[None | str]:
    """Format a list of datetime arguments to strings suitable for web services."""
    formatted_args = []
    for dt in args:
        if dt is None:
            formatted_args.append(None)
        else:
            formatted_args.append(format_datetime(dt))
    return formatted_args


def get_function_arg_names(func) -> list[str]:
    """Get the argument names of a function."""
    return list(inspect.signature(func).parameters)
