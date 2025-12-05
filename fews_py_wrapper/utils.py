import inspect
from datetime import datetime, timezone

import pandas as pd
import xarray as xr


def format_datetime(dt: datetime, time_format: str = "%Y-%m-%dT%H:%M:%SZ") -> str:
    """Format a datetime object to a string suitable for FEWS web services."""
    if not dt.tzinfo:
        raise ValueError("Datetime object must be timezone-aware.")
    dt = dt.astimezone(timezone.utc)
    return dt.strftime(time_format)


def convert_timeseries_response_to_xarray(
    response_content: dict,
) -> xr.Dataset:
    """Convert the timeseries response content to a pandas DataFrame."""
    datasets = []
    for ts in response_content.get("timeSeries", []):
        events = ts.get("events", [])
        header = ts.get("header", {})
        if not events:
            continue

        df = pd.DataFrame(events)
        df["datetime"] = pd.to_datetime(
            df["date"] + "T" + df["time"], format="%Y-%m-%dT%H:%M:%S"
        ).dt.tz_localize("UTC")

        # Handle missing values
        miss_val = float(header.get("missVal", "-999.0"))
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df["value"] = df["value"].replace(miss_val, float("nan"))

        # Replace dots in header values
        header = replace_dots_attrs_values(header)

        da = xr.DataArray(
            df["value"].values,
            coords={"time": df["datetime"].values},
            dims=["time"],
            name=header.get("parameterId", "unknown"),
            attrs={
                "location_id": header.get("locationId"),
                "parameter_id": header.get("parameterId"),
                "station_name": header.get("stationName"),
                "units": header.get("units"),
                "latitude": float(header.get("lat", "nan")),
                "longitude": float(header.get("lon", "nan")),
                "elevation": float(header.get("z", "nan")),
                "module_instance_id": header.get("moduleInstanceId"),
                "time_step_unit": header.get("timeStep", {}).get("unit"),
                "time_step_multiplier": header.get("timeStep", {}).get("multiplier"),
            },
        )
        # Add flag as coordinate
        if "flag" in df.columns:
            da = da.assign_coords(flag=("time", df["flag"].values))

        datasets.append(da.to_dataset())

    # Merge all datasets
    if len(datasets) == 1:
        return datasets[0]
    elif len(datasets) > 1:
        return xr.merge(datasets)
    else:
        return xr.Dataset()


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


def replace_dots_attrs_values(attrs: dict) -> dict:
    """Replace dots in attribute keys with underscores."""
    d = {}
    for key, value in attrs.items():
        if isinstance(value, dict):
            value = replace_dots_attrs_values(value)
        if isinstance(value, str):
            value = value.replace(".", "_")
        d[key] = value
    return d
