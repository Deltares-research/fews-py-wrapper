import inspect
import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

import xarray as xr

__all__ = [
    "format_datetime",
    "convert_netcdf_zip_response_to_xarray",
    "format_time_args",
    "get_function_arg_names",
]


def format_datetime(dt: datetime, time_format: str = "%Y-%m-%dT%H:%M:%SZ") -> str:
    """Format a datetime object to a string suitable for FEWS web services."""
    if not dt.tzinfo:
        raise ValueError("Datetime object must be timezone-aware.")
    dt = dt.astimezone(timezone.utc)
    return dt.strftime(time_format)


def convert_netcdf_zip_response_to_xarray(response_content: bytes) -> list[xr.Dataset]:
    """Convert FEWS NetCDF content (ZIP or raw NetCDF bytes) to xarray datasets.

    ZIP responses are returned as one loaded dataset per NetCDF member, in the
    same order as the ZIP archive. Raw NetCDF bytes are returned as a single-item
    list.
    """
    datasets = _load_netcdf_member_datasets(response_content)
    if not datasets:
        raise ValueError("FEWS PI_NETCDF response did not contain any NetCDF datasets.")
    return datasets


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


def _load_netcdf_member_datasets(response_content: bytes) -> list[xr.Dataset]:
    """Load each NetCDF member from a FEWS response."""
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
            with TemporaryDirectory() as temp_dir:
                for index, member in enumerate(netcdf_members):
                    extracted_path = _write_zip_member_to_temp_path(
                        zip_file, member, Path(temp_dir), index
                    )
                    with xr.open_dataset(extracted_path) as dataset:
                        datasets.append(dataset.load())
            return datasets
    except zipfile.BadZipFile:
        return [_load_netcdf_dataset_from_bytes(response_content)]


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
