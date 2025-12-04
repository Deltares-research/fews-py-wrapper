import inspect
from datetime import datetime, timezone
from typing import get_args, get_origin

import pandas as pd
import xarray as xr
from fews_openapi_py_client.types import Unset


def format_datetime(dt: datetime) -> str:
    """Format a datetime object to a string suitable for FEWS web services."""
    if not dt.tzinfo:
        raise ValueError("Datetime object must be timezone-aware.")
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


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


def get_parameter_models(func) -> dict:
    function_params = inspect.signature(func).parameters
    standard_types = (str, int, float, bool, list, dict, tuple, set, datetime)
    parameter_models = {}
    for param_name, param in function_params.items():
        if param_name == "client":
            continue
        annotation = param.annotation
        args = get_args(annotation)

        # Check if argument annotation contains standard types
        if contains_types(args, standard_types):
            continue

        arg_list = list(args)
        if Unset in arg_list:
            arg_list.remove(Unset)

        if not len(arg_list) == 1:
            raise ValueError(
                f"Expected two annotation arguments, but got"
                f" {len(arg_list)} for {param_name}"
            )

        m_dict = {}
        if "TRUE" in arg_list[0].__members__.keys():
            m_dict["is_bool"] = True
        else:
            m_dict["is_bool"] = False
        m_dict["model"] = arg_list[0]
        parameter_models[param_name] = m_dict
    return parameter_models


def contains_types(args, check_types):
    for arg in args:
        if arg in check_types:
            return True
        if isinstance(get_origin(arg), (type(list), type(tuple))):
            return contains_types(get_args(arg), check_types)
    return False


def update_api_call_kwargs(kwargs: dict, func: callable) -> dict:
    param_models = get_parameter_models(func)
    updated_kwargs = {}
    try:
        for key, value in kwargs.items():
            if key in param_models:
                if param_models[key]["is_bool"]:
                    updated_kwargs[key] = param_models[key]["model"](
                        convert_bools(value)
                    )
                else:
                    updated_kwargs[key] = param_models[key]["model"](value)
            else:
                updated_kwargs[key] = value
        return updated_kwargs
    except ValueError as e:
        raise ValueError(f"Invalid argument value: {e}") from e


def convert_bools(arg):
    if arg:
        return "true"
    return "false"
