import inspect
import io
import math
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, cast

import numpy as np
import pandas as pd
import xarray as xr

__all__ = [
    "format_datetime",
    "convert_netcdf_zip_response_to_xarray",
    "convert_timeseries_response_to_xarray",
    "normalize_netcdf_response_to_timeseries_xarray",
    "normalize_netcdf_dataset_to_timeseries_xarray",
    "format_time_args",
    "get_function_arg_names",
    "replace_dots_attrs_values",
]


def format_datetime(dt: datetime, time_format: str = "%Y-%m-%dT%H:%M:%SZ") -> str:
    """Format a datetime object to a string suitable for FEWS web services."""
    if not dt.tzinfo:
        raise ValueError("Datetime object must be timezone-aware.")
    dt = dt.astimezone(timezone.utc)
    return dt.strftime(time_format)


def convert_timeseries_response_to_xarray(
    response_content: dict[str, Any],
) -> xr.Dataset:
    """Convert FEWS PI_JSON time series content to an xarray dataset."""
    time_series = sorted(
        response_content.get("timeSeries", []),
        key=_pi_json_series_sort_key,
    )
    parameter_counts = Counter(
        replace_dots_attrs_values(ts.get("header", {})).get("parameterId", "unknown")
        for ts in time_series
        if ts.get("events", [])
    )

    dataset = xr.Dataset()
    used_names: set[str] = set()

    for index, ts in enumerate(time_series):
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
        parameter_id = header.get("parameterId", "unknown")
        variable_name = _get_timeseries_variable_name(
            parameter_id=parameter_id,
            header=header,
            index=index,
            parameter_counts=parameter_counts,
            used_names=used_names,
        )

        da = xr.DataArray(
            _normalize_series_values(df["value"].values),
            coords={"time": df["datetime"].values},
            dims=["time"],
            name=variable_name,
            attrs=_build_normalized_series_attrs(
                location_id=header.get("locationId"),
                parameter_id=parameter_id,
                station_name=header.get("stationName"),
                units=header.get("units"),
                latitude=_parse_optional_float(header.get("lat", header.get("y"))),
                longitude=_parse_optional_float(header.get("lon", header.get("x"))),
                elevation=_parse_optional_float(header.get("z")),
                time_values=df["datetime"].values,
                time_step_unit=header.get("timeStep", {}).get("unit"),
                time_step_multiplier=header.get("timeStep", {}).get("multiplier"),
            ),
        )

        dataset[variable_name] = da

    return dataset


def _get_timeseries_variable_name(
    *,
    parameter_id: str,
    header: dict[str, Any],
    index: int,
    parameter_counts: Counter[str],
    used_names: set[str],
) -> str:
    """Create a stable variable name for a PI_JSON time series member."""
    if parameter_counts[parameter_id] == 1 and parameter_id not in used_names:
        used_names.add(parameter_id)
        return parameter_id

    name_parts = [
        header.get("locationId"),
        header.get("stationName"),
        header.get("moduleInstanceId"),
        str(index),
    ]

    for part in name_parts:
        if not part:
            continue
        candidate = f"{parameter_id}__{_to_safe_name(str(part))}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate

    used_names.add(parameter_id)
    return parameter_id


def convert_netcdf_zip_response_to_xarray(response_content: bytes) -> xr.Dataset:
    """Convert FEWS NetCDF content (ZIP or raw NetCDF bytes) to xarray."""
    try:
        with zipfile.ZipFile(io.BytesIO(response_content)) as zip_file:
            netcdf_members = [
                member
                for member in zip_file.infolist()
                if not member.is_dir()
                and member.filename.lower().endswith((".nc", ".nc4", ".cdf"))
            ]
            if not netcdf_members:
                raise ValueError("ZIP response did not contain any .nc files.")

            datasets: list[xr.Dataset] = []
            member_names: list[str] = []
            with TemporaryDirectory() as temp_dir:
                for index, member in enumerate(netcdf_members):
                    extracted_path = _write_zip_member_to_temp_path(
                        zip_file, member, Path(temp_dir), index
                    )
                    with xr.open_dataset(extracted_path) as dataset:
                        datasets.append(dataset.load())
                        member_names.append(member.filename)
    except zipfile.BadZipFile:
        return _load_netcdf_dataset_from_bytes(response_content)

    if len(datasets) == 1:
        return datasets[0]

    try:
        return cast(
            xr.Dataset,
            xr.combine_by_coords(datasets, combine_attrs="override"),
        )
    except Exception:
        return _merge_netcdf_members_without_alignment(datasets, member_names)


def _infer_netcdf_member_label(dataset: xr.Dataset, member_name: str) -> str:
    """Infer a stable label for a NetCDF member inside a FEWS ZIP response."""
    for key in ("locationId", "location_id", "stationId", "station_id", "id"):
        value = dataset.attrs.get(key)
        if isinstance(value, str) and value:
            return value

    for coord_name in ("location", "location_id", "locationId", "station_id"):
        if coord_name in dataset.coords and dataset[coord_name].size == 1:
            coord_value = dataset[coord_name].values.reshape(-1)[0]
            return str(coord_value)

    return Path(member_name).stem


def _merge_netcdf_members_without_alignment(
    datasets: list[xr.Dataset], member_names: list[str]
) -> xr.Dataset:
    """Merge NetCDF members after making conflicting dimensions member-specific."""
    labels = [
        _infer_netcdf_member_label(dataset, member_name)
        for dataset, member_name in zip(datasets, member_names, strict=True)
    ]
    varying_unindexed_dims = _get_varying_unindexed_dims(datasets)

    normalized_datasets = [
        _normalize_netcdf_member_dataset(dataset, label, varying_unindexed_dims)
        for dataset, label in zip(datasets, labels, strict=True)
    ]
    return cast(
        xr.Dataset,
        xr.merge(
            normalized_datasets,
            combine_attrs="override",
            compat="override",
        ),
    )


def _get_varying_unindexed_dims(datasets: list[xr.Dataset]) -> set[str]:
    """Return unindexed dimensions whose sizes differ between datasets."""
    dim_sizes: dict[str, set[int]] = {}
    for dataset in datasets:
        for raw_dim_name, dim_size in dataset.sizes.items():
            dim_name = str(raw_dim_name)
            if dim_name in dataset.indexes:
                continue
            dim_sizes.setdefault(dim_name, set()).add(dim_size)
    return {dim_name for dim_name, sizes in dim_sizes.items() if len(sizes) > 1}


def _normalize_netcdf_member_dataset(
    dataset: xr.Dataset, label: str, varying_unindexed_dims: set[str]
) -> xr.Dataset:
    """Rename conflicting dims and variables so FEWS members can be merged safely."""
    safe_label = _to_safe_name(label)
    renamed_dataset = dataset

    dim_renames = {
        dim_name: f"{dim_name}__{safe_label}"
        for dim_name in varying_unindexed_dims
        if dim_name in dataset.dims
    }
    if dim_renames:
        renamed_dataset = renamed_dataset.rename_dims(dim_renames)

    variable_renames = {
        variable_name: f"{variable_name}__{safe_label}"
        for variable_name in renamed_dataset.data_vars
    }
    if variable_renames:
        renamed_dataset = renamed_dataset.rename_vars(variable_renames)

    renamed_dataset = renamed_dataset.assign_attrs(
        {**renamed_dataset.attrs, "fews_member": label}
    )
    return renamed_dataset


def _to_safe_name(value: str) -> str:
    """Convert FEWS labels to names safe for xarray variables and dimensions."""
    return "".join(character if character.isalnum() else "_" for character in value)


def _load_netcdf_dataset_from_bytes(response_content: bytes) -> xr.Dataset:
    """Load raw NetCDF bytes into an xarray dataset."""
    with TemporaryDirectory() as temp_dir:
        netcdf_path = Path(temp_dir) / "fews_response.nc"
        netcdf_path.write_bytes(response_content)
        try:
            with xr.open_dataset(netcdf_path) as dataset:
                return dataset.load()
        except Exception as exc:
            raise ValueError(
                "Expected FEWS PI_NETCDF content as a ZIP archive or raw NetCDF bytes."
            ) from exc


def normalize_netcdf_response_to_timeseries_xarray(
    response_content: bytes,
) -> xr.Dataset:
    """Normalize FEWS PI_NETCDF content directly to the canonical time series shape."""
    series_specs: list[dict[str, Any]] = []

    for dataset, member_name in _load_netcdf_member_datasets(response_content):
        member_dataset = dataset.assign_attrs(
            {**dataset.attrs, "fews_member": Path(member_name).stem}
        )
        series_specs.extend(_collect_netcdf_series_specs(member_dataset))

    if not series_specs:
        return xr.Dataset()

    return _build_normalized_dataset_from_series_specs(series_specs)


def _load_netcdf_member_datasets(
    response_content: bytes,
) -> list[tuple[xr.Dataset, str]]:
    """Load each NetCDF member from a FEWS response while preserving member names."""
    try:
        with zipfile.ZipFile(io.BytesIO(response_content)) as zip_file:
            netcdf_members = [
                member
                for member in zip_file.infolist()
                if not member.is_dir()
                and member.filename.lower().endswith((".nc", ".nc4", ".cdf"))
            ]
            if not netcdf_members:
                raise ValueError("ZIP response did not contain any .nc files.")

            datasets: list[tuple[xr.Dataset, str]] = []
            with TemporaryDirectory() as temp_dir:
                for index, member in enumerate(netcdf_members):
                    extracted_path = _write_zip_member_to_temp_path(
                        zip_file, member, Path(temp_dir), index
                    )
                    with xr.open_dataset(extracted_path) as dataset:
                        datasets.append((dataset.load(), member.filename))
            return datasets
    except zipfile.BadZipFile:
        return [(_load_netcdf_dataset_from_bytes(response_content), "fews_response.nc")]


def _write_zip_member_to_temp_path(
    zip_file: zipfile.ZipFile,
    member: zipfile.ZipInfo,
    temp_dir: Path,
    index: int,
) -> Path:
    """Write a ZIP member to a controlled path under the temp directory."""
    extracted_path = temp_dir / f"member_{index}.nc"
    with zip_file.open(member) as src, extracted_path.open("wb") as dst:
        dst.write(src.read())
    return extracted_path


def normalize_netcdf_dataset_to_timeseries_xarray(dataset: xr.Dataset) -> xr.Dataset:
    """Normalize NetCDF-derived FEWS datasets to the PI_JSON-style xarray shape."""
    if _is_normalized_timeseries_dataset(dataset):
        return dataset

    series_specs = _collect_netcdf_series_specs(dataset)
    if not series_specs:
        return dataset

    return _build_normalized_dataset_from_series_specs(series_specs)


def _build_normalized_dataset_from_series_specs(
    series_specs: list[dict[str, Any]],
) -> xr.Dataset:
    """Build the canonical xarray dataset from normalized per-series specs."""
    sorted_specs = sorted(series_specs, key=_series_spec_sort_key)

    parameter_counts = Counter(spec["parameter_id"] for spec in sorted_specs)
    used_names: set[str] = set()
    normalized_dataset = xr.Dataset()

    for index, spec in enumerate(sorted_specs):
        variable_name = _get_timeseries_variable_name(
            parameter_id=spec["parameter_id"],
            header={
                "locationId": spec["location_id"],
                "stationName": spec["station_name"],
                "moduleInstanceId": spec["source_label"],
            },
            index=index,
            parameter_counts=parameter_counts,
            used_names=used_names,
        )
        normalized_dataset[variable_name] = xr.DataArray(
            spec["values"],
            coords={"time": spec["time_values"]},
            dims=["time"],
            attrs=_build_normalized_series_attrs(
                location_id=spec["location_id"],
                parameter_id=spec["parameter_id"],
                station_name=spec["station_name"],
                units=spec["units"],
                latitude=spec["latitude"],
                longitude=spec["longitude"],
                elevation=spec["elevation"],
                time_values=spec["time_values"],
            ),
        )

    return normalized_dataset


def _is_normalized_timeseries_dataset(dataset: xr.Dataset) -> bool:
    """Return True when a dataset already matches the wrapper's canonical shape."""
    if not dataset.data_vars:
        return True

    for variable in dataset.data_vars.values():
        if variable.dims != ("time",):
            return False
    return True


def _collect_netcdf_series_specs(dataset: xr.Dataset) -> list[dict[str, Any]]:
    """Extract per-series specifications from a raw FEWS NetCDF dataset."""
    series_specs: list[dict[str, Any]] = []

    for data_var_name, variable in dataset.data_vars.items():
        if not _is_netcdf_series_variable(variable):
            continue

        split_dims = [str(dim_name) for dim_name in variable.dims if dim_name != "time"]
        indexers = _build_dim_indexers(dataset, split_dims)

        for indexer in indexers:
            sliced_variable = variable.isel(indexer, drop=True)
            if sliced_variable.dims != ("time",):
                continue

            station_dim_name = next(
                (dim_name for dim_name in indexer if "station" in dim_name),
                None,
            )
            source_label = (
                _decode_scalar(dataset.attrs.get("fews_member")) or data_var_name
            )
            parameter_id = _infer_parameter_id(data_var_name, variable)
            location_id = (
                _extract_station_metadata(
                    dataset, "station_id", station_dim_name, indexer
                )
                or _decode_scalar(dataset.attrs.get("locationId"))
                or source_label
            )
            station_name = _extract_station_metadata(
                dataset, "station_names", station_dim_name, indexer
            ) or _extract_station_metadata(
                dataset, "station_name", station_dim_name, indexer
            )

            series_specs.append(
                {
                    "parameter_id": parameter_id,
                    "location_id": location_id,
                    "station_name": station_name,
                    "units": variable.attrs.get("units"),
                    "latitude": _extract_preferred_coordinate(
                        dataset, indexer, "y", "lat"
                    ),
                    "longitude": _extract_preferred_coordinate(
                        dataset, indexer, "x", "lon"
                    ),
                    "elevation": _extract_preferred_coordinate(dataset, indexer, "z"),
                    "source_label": source_label,
                    "time_values": sliced_variable["time"].values,
                    "time_step_multiplier": _infer_time_step_metadata(
                        sliced_variable["time"].values
                    )[1],
                    "values": _normalize_series_values(
                        sliced_variable.astype("float64").values
                    ),
                }
            )

    return series_specs


def _is_netcdf_series_variable(variable: xr.DataArray) -> bool:
    """Return True for numeric time series variables and False for ancillary data."""
    return "time" in variable.dims and pd.api.types.is_numeric_dtype(variable.dtype)


def _build_dim_indexers(
    dataset: xr.Dataset, dim_names: list[str]
) -> list[dict[str, int]]:
    """Build index selections for all non-time dimensions of a variable."""
    if not dim_names:
        return [{}]

    indexers: list[dict[str, int]] = [{}]
    for dim_name in dim_names:
        next_indexers: list[dict[str, int]] = []
        for indexer in indexers:
            for dim_index in range(dataset.sizes[dim_name]):
                next_indexer = dict(indexer)
                next_indexer[dim_name] = dim_index
                next_indexers.append(next_indexer)
        indexers = next_indexers
    return indexers


def _extract_station_metadata(
    dataset: xr.Dataset,
    coord_name: str,
    station_dim_name: str | None,
    indexer: dict[str, int],
) -> str | None:
    """Extract decoded station metadata from a coordinate when available."""
    if station_dim_name is None:
        return None

    variable: xr.DataArray | None = None
    if coord_name in dataset.coords:
        variable = dataset.coords[coord_name]
    elif coord_name in dataset.data_vars:
        variable = dataset[coord_name]

    if variable is None or station_dim_name not in variable.dims:
        return None

    coordinate_indexer = {station_dim_name: indexer[station_dim_name]}
    decoded_value = _decode_scalar(variable.isel(coordinate_indexer, drop=True).values)
    return decoded_value if isinstance(decoded_value, str) else None


def _extract_preferred_coordinate(
    dataset: xr.Dataset,
    indexer: dict[str, int],
    *coord_names: str,
) -> float | None:
    """Extract the first available numeric coordinate value for a series slice."""
    for coord_name in coord_names:
        if coord_name not in dataset.coords:
            continue

        coordinate = dataset.coords[coord_name]
        coordinate_indexer = {
            dim_name: dim_index
            for dim_name, dim_index in indexer.items()
            if dim_name in coordinate.dims
        }
        value = coordinate.isel(coordinate_indexer, drop=True).values
        parsed = _parse_optional_float(_decode_scalar(value))
        if parsed is not None:
            return parsed
    return None


def _infer_parameter_id(data_var_name: str, variable: xr.DataArray) -> str:
    """Infer the FEWS parameter identifier for a NetCDF data variable."""
    long_name = variable.attrs.get("long_name")
    if isinstance(long_name, str) and long_name and long_name != "time_bnds":
        return long_name.replace(".", "_")
    return data_var_name.split("__", maxsplit=1)[0]


def _build_normalized_series_attrs(
    *,
    location_id: str | None,
    parameter_id: str,
    station_name: str | None,
    units: str | None,
    latitude: float | None,
    longitude: float | None,
    elevation: float | None,
    time_values: Any,
    time_step_unit: str | None = None,
    time_step_multiplier: str | int | None = None,
) -> dict[str, Any]:
    """Build the canonical per-series attrs shared by JSON and NetCDF paths."""
    inferred_unit, inferred_multiplier = _infer_time_step_metadata(time_values)

    attrs = {
        "location_id": location_id,
        "parameter_id": parameter_id,
        "station_name": station_name,
        "units": units,
        "latitude": latitude,
        "longitude": longitude,
        "elevation": None if elevation in (None, 0.0) else elevation,
        "time_step_unit": time_step_unit or inferred_unit,
        "time_step_multiplier": _parse_optional_int(time_step_multiplier)
        if time_step_multiplier is not None
        else inferred_multiplier,
    }
    return {key: value for key, value in attrs.items() if value is not None}


def _infer_time_step_metadata(time_values: Any) -> tuple[str | None, int | None]:
    """Infer a FEWS-style time step description from an array of timestamps."""
    if len(time_values) < 2:
        return None, None

    time_index = pd.DatetimeIndex(time_values)
    deltas = time_index.to_series().diff().dropna().unique()
    if len(deltas) != 1:
        return None, None

    delta = deltas[0]
    if not isinstance(delta, pd.Timedelta):
        return None, None

    delta_seconds = int(delta.total_seconds())
    if delta_seconds <= 0:
        return None, None
    return "second", delta_seconds


def _parse_optional_float(value: Any) -> float | None:
    """Convert a scalar value to float when possible."""
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed):
        return None
    return parsed


def _parse_optional_int(value: Any) -> int | None:
    """Convert a scalar value to int when possible."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _decode_scalar(value: Any) -> object:
    """Decode bytes and NumPy scalar containers to plain Python values."""
    if hasattr(value, "item") and not isinstance(value, (bytes, str)):
        try:
            value = cast(object, value.item())
        except ValueError:
            pass
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def format_time_args(*args: None | datetime) -> list[None | str]:
    """Format a list of datetime arguments to strings suitable for web services."""
    formatted_args: list[str | None] = []
    for dt in args:
        if dt is None:
            formatted_args.append(None)
        else:
            formatted_args.append(format_datetime(dt))
    return formatted_args


def get_function_arg_names(func: Callable[..., Any]) -> list[str]:
    """Get the argument names of a function."""
    return list(inspect.signature(func).parameters)


def replace_dots_attrs_values(attrs: dict[str, Any]) -> dict[str, Any]:
    """Replace dots in attribute keys with underscores."""
    d = {}
    for key, value in attrs.items():
        if isinstance(value, dict):
            value = replace_dots_attrs_values(value)
        if isinstance(value, str) and not _looks_like_number(value):
            value = value.replace(".", "_")
        d[key] = value
    return d


def _pi_json_series_sort_key(
    time_series: dict[str, Any],
) -> tuple[int, str, str, str, str]:
    """Return a stable ordering for PI_JSON series across FEWS formats."""
    header = time_series.get("header", {})
    time_step = header.get("timeStep", {})
    time_step_multiplier = _parse_optional_int(time_step.get("multiplier")) or 0
    return (
        -time_step_multiplier,
        str(header.get("locationId") or ""),
        str(header.get("stationName") or ""),
        str(header.get("moduleInstanceId") or ""),
        str(header.get("parameterId") or ""),
    )


def _series_spec_sort_key(spec: dict[str, Any]) -> tuple[int, str, str, str, str]:
    """Return a stable ordering for normalized series regardless of source format."""
    time_step_multiplier = _parse_optional_int(spec.get("time_step_multiplier")) or 0
    return (
        -time_step_multiplier,
        str(spec.get("location_id") or ""),
        str(spec.get("station_name") or ""),
        str(spec.get("source_label") or ""),
        str(spec.get("parameter_id") or ""),
    )


def _looks_like_number(value: str) -> bool:
    """Return True when a string represents a numeric scalar."""
    try:
        float(value)
    except ValueError:
        return False
    return True


def _normalize_series_values(values: Any) -> np.ndarray:
    """Return canonical float64 series values with stable decimal precision."""
    return np.round(np.asarray(values, dtype="float64"), decimals=7)
