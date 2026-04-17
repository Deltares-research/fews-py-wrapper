from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import xarray as xr

from fews_py_wrapper.utils import (
    convert_netcdf_zip_response_to_xarray,
    format_datetime,
    format_time_args,
    get_function_arg_names,
)


def test_format_datetime():
    dt_aware = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    formatted = format_datetime(dt_aware)
    assert formatted == "2023-01-01T12:00:00Z"

    dt_non_aware = datetime(2023, 1, 1, 12, 0, 0)
    with pytest.raises(ValueError, match="Datetime object must be timezone-aware."):
        format_datetime(dt_non_aware)


def test_format_time_args():
    dt1 = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    dt2 = None
    dt3 = datetime(2023, 6, 1, 15, 30, 0, tzinfo=timezone.utc)

    formatted_args = format_time_args(dt1, dt2, dt3)
    assert formatted_args == [
        "2023-01-01T12:00:00Z",
        None,
        "2023-06-01T15:30:00Z",
    ]


def test_get_function_arg_names():
    def sample_function(arg1, arg2, kwarg1=None):
        pass

    arg_names = get_function_arg_names(sample_function)
    assert arg_names == ["arg1", "arg2", "kwarg1"]


def test_convert_netcdf_zip_response_to_xarray(
    netcdf_zip_response: bytes, netcdf_dataset: xr.Dataset
):
    datasets = convert_netcdf_zip_response_to_xarray(netcdf_zip_response)

    assert isinstance(datasets, list)
    assert len(datasets) == 1
    xr.testing.assert_identical(datasets[0], netcdf_dataset)


def test_convert_raw_netcdf_response_to_xarray_rejects_non_zip_payload(
    netcdf_dataset: xr.Dataset,
):
    with TemporaryDirectory() as temp_dir:
        netcdf_path = Path(temp_dir) / "timeseries.nc"
        netcdf_dataset.to_netcdf(netcdf_path, engine="netcdf4")
        raw_netcdf_response = netcdf_path.read_bytes()

    with pytest.raises(
        ValueError,
        match=(
            "Expected FEWS PI_NETCDF content as a ZIP archive containing NetCDF files"
        ),
    ):
        convert_netcdf_zip_response_to_xarray(raw_netcdf_response)


def test_convert_multi_member_netcdf_zip_response_to_xarray(
    multi_member_netcdf_zip_response: bytes,
):
    datasets = convert_netcdf_zip_response_to_xarray(multi_member_netcdf_zip_response)

    assert isinstance(datasets, list)
    assert len(datasets) == 2
    assert datasets[0].attrs["locationId"] == "Amanzimtoti_River_level"
    assert datasets[1].attrs["locationId"] == "Amanzimtoti_River_Mouth_level"
    assert datasets[0]["H_simulated"].values.tolist() == [1.0, 2.0]
    assert datasets[1]["H_simulated"].values.tolist() == [3.0, 4.0]


def test_convert_station_conflict_netcdf_zip_response_to_xarray(
    station_conflict_netcdf_zip_response: bytes,
):
    datasets = convert_netcdf_zip_response_to_xarray(
        station_conflict_netcdf_zip_response
    )

    assert isinstance(datasets, list)
    assert len(datasets) == 2
    assert datasets[0].attrs["locationId"] == "Amanzimtoti_River_level"
    assert datasets[1].attrs["locationId"] == "Amanzimtoti_River_Mouth_level"
    assert datasets[0].sizes["stations"] == 1
    assert datasets[1].sizes["stations"] == 2
    assert datasets[0]["H_simulated"].values.tolist() == [[1.0], [2.0]]
    assert datasets[1]["H_simulated"].values.tolist() == [[3.0, 4.0], [5.0, 6.0]]


def test_convert_netcdf_zip_response_to_xarray_rejects_invalid_zip():
    with pytest.raises(ValueError, match="Expected FEWS PI_NETCDF content"):
        convert_netcdf_zip_response_to_xarray(b"not-a-zip")
