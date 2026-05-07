import io
import zipfile
from datetime import datetime, timezone

import pytest

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
    netcdf_zip_response: bytes,
):
    datasets = convert_netcdf_zip_response_to_xarray(netcdf_zip_response)

    assert isinstance(datasets, list)
    assert len(datasets) == 1
    dataset = datasets[0]
    assert dict(dataset.sizes) == {
        "time": 7,
        "nbnds": 2,
        "stations": 1,
        "analysis_time": 1,
    }
    assert list(dataset.data_vars) == ["time_bnds", "station_names", "H_simulated"]
    assert dataset["H_simulated"].values[:, 0].tolist() == pytest.approx(
        [0.214, 0.211, 0.209, 0.207, 0.207, 0.207, 0.208]
    )


def test_convert_raw_netcdf_response_to_xarray_rejects_non_zip_payload(
    netcdf_zip_response: bytes,
):
    with zipfile.ZipFile(io.BytesIO(netcdf_zip_response)) as zip_file:
        raw_netcdf_response = zip_file.read(zip_file.namelist()[0])

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
    assert len(datasets) == 21
    assert dict(datasets[0].sizes) == {"stations": 2, "time": 46}
    assert list(datasets[0].data_vars) == ["station_names", "C_obs_dir_depthavg"]
    assert dict(datasets[-1].sizes) == {
        "time": 26,
        "nbnds": 2,
        "stations": 361,
        "analysis_time": 1,
    }
    assert "warning_index" in datasets[-1].data_vars


def test_convert_varying_station_sizes_netcdf_zip_response_to_xarray(
    varying_station_sizes_netcdf_zip_response: bytes,
):
    datasets = convert_netcdf_zip_response_to_xarray(
        varying_station_sizes_netcdf_zip_response
    )

    assert isinstance(datasets, list)
    assert len(datasets) == 21
    station_sizes = {int(dataset.sizes["stations"]) for dataset in datasets}
    assert len(station_sizes) > 1
    assert {2, 30, 263, 322, 326, 361}.issubset(station_sizes)


def test_convert_netcdf_zip_response_to_xarray_rejects_invalid_zip():
    with pytest.raises(ValueError, match="Expected FEWS PI_NETCDF content"):
        convert_netcdf_zip_response_to_xarray(b"not-a-zip")
