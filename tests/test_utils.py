from datetime import datetime, timezone

import numpy as np
import pytest
import xarray as xr

from fews_py_wrapper.utils import (
    convert_netcdf_zip_response_to_xarray,
    convert_timeseries_response_to_xarray,
    format_datetime,
    format_time_args,
    get_function_arg_names,
    normalize_netcdf_dataset_to_timeseries_xarray,
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


def test_convert_timeseries_response_to_xarray(timeseries_response: dict):
    ds = convert_timeseries_response_to_xarray(timeseries_response)

    assert isinstance(ds, xr.Dataset)
    assert ds.time.min().values == np.datetime64("2025-03-14T10:00:00.000000000")
    assert ds.time.max().values == np.datetime64("2025-03-14T13:25:00.000000000")
    assert "P_obs_rate" in ds.data_vars


def test_convert_timeseries_response_to_xarray_disambiguates_duplicate_parameters():
    response = {
        "timeSeries": [
            {
                "header": {
                    "parameterId": "H.simulated",
                    "locationId": "Amanzimtoti_River_level",
                    "units": "m",
                },
                "events": [
                    {"date": "2025-03-14", "time": "10:00:00", "value": "1.0"},
                    {"date": "2025-03-14", "time": "11:00:00", "value": "2.0"},
                ],
            },
            {
                "header": {
                    "parameterId": "H.simulated",
                    "locationId": "Amanzimtoti_River_Mouth_level",
                    "units": "m",
                },
                "events": [
                    {"date": "2025-03-14", "time": "10:00:00", "value": "3.0"},
                    {"date": "2025-03-14", "time": "11:00:00", "value": "4.0"},
                ],
            },
        ]
    }

    ds = convert_timeseries_response_to_xarray(response)

    assert isinstance(ds, xr.Dataset)
    assert "H_simulated__Amanzimtoti_River_level" in ds.data_vars
    assert "H_simulated__Amanzimtoti_River_Mouth_level" in ds.data_vars
    assert ds["H_simulated__Amanzimtoti_River_level"].values.tolist() == [1.0, 2.0]
    assert ds["H_simulated__Amanzimtoti_River_Mouth_level"].values.tolist() == [
        3.0,
        4.0,
    ]


def test_convert_netcdf_zip_response_to_xarray(
    netcdf_zip_response: bytes, netcdf_dataset: xr.Dataset
):
    ds = convert_netcdf_zip_response_to_xarray(netcdf_zip_response)

    assert isinstance(ds, xr.Dataset)
    xr.testing.assert_identical(ds, netcdf_dataset)


def test_convert_raw_netcdf_response_to_xarray(
    raw_netcdf_response: bytes, netcdf_dataset: xr.Dataset
):
    ds = convert_netcdf_zip_response_to_xarray(raw_netcdf_response)

    assert isinstance(ds, xr.Dataset)
    xr.testing.assert_identical(ds, netcdf_dataset)


def test_convert_multi_member_netcdf_zip_response_to_xarray(
    multi_member_netcdf_zip_response: bytes,
):
    ds = convert_netcdf_zip_response_to_xarray(multi_member_netcdf_zip_response)

    assert isinstance(ds, xr.Dataset)
    assert "H_simulated__Amanzimtoti_River_level" in ds.data_vars
    assert "H_simulated__Amanzimtoti_River_Mouth_level" in ds.data_vars
    assert ds["H_simulated__Amanzimtoti_River_level"].values.tolist() == [
        1.0,
        2.0,
    ]
    assert ds["H_simulated__Amanzimtoti_River_Mouth_level"].values.tolist() == [
        3.0,
        4.0,
    ]


def test_convert_station_conflict_netcdf_zip_response_to_xarray(
    station_conflict_netcdf_zip_response: bytes,
):
    ds = convert_netcdf_zip_response_to_xarray(station_conflict_netcdf_zip_response)

    assert isinstance(ds, xr.Dataset)
    assert "H_simulated__Amanzimtoti_River_level" in ds.data_vars
    assert "H_simulated__Amanzimtoti_River_Mouth_level" in ds.data_vars
    assert "stations__Amanzimtoti_River_level" in ds.dims
    assert "stations__Amanzimtoti_River_Mouth_level" in ds.dims
    assert ds.sizes["stations__Amanzimtoti_River_level"] == 1
    assert ds.sizes["stations__Amanzimtoti_River_Mouth_level"] == 2


def test_convert_netcdf_zip_response_to_xarray_rejects_invalid_zip():
    with pytest.raises(ValueError, match="Expected FEWS PI_NETCDF content"):
        convert_netcdf_zip_response_to_xarray(b"not-a-zip")


def test_normalize_netcdf_dataset_to_timeseries_xarray_with_station_dimension():
    raw_dataset = xr.Dataset(
        data_vars={
            "time_bnds": (
                ("time", "nbnds"),
                np.array(
                    [
                        [
                            np.datetime64("2025-03-14T09:50:00"),
                            np.datetime64("2025-03-14T10:10:00"),
                        ],
                        [
                            np.datetime64("2025-03-14T10:10:00"),
                            np.datetime64("2025-03-14T10:30:00"),
                        ],
                    ]
                ),
            ),
            "station_names": ("stations", [b"River Level", b"River Mouth"]),
            "H_simulated": (("time", "stations"), np.array([[1.0, 3.0], [2.0, 4.0]])),
        },
        coords={
            "time": np.array(
                ["2025-03-14T10:00:00", "2025-03-14T10:20:00"],
                dtype="datetime64[ns]",
            ),
            "station_id": ("stations", [b"River_level", b"River_mouth"]),
            "x": ("stations", [30.8, 30.9]),
            "y": ("stations", [-30.0, -30.1]),
            "z": ("stations", [1.0, 2.0]),
        },
    )

    normalized_dataset = normalize_netcdf_dataset_to_timeseries_xarray(raw_dataset)

    assert isinstance(normalized_dataset, xr.Dataset)
    assert set(normalized_dataset.data_vars) == {
        "H_simulated__River_level",
        "H_simulated__River_mouth",
    }
    assert normalized_dataset["H_simulated__River_level"].values.tolist() == [1.0, 2.0]
    assert normalized_dataset["H_simulated__River_mouth"].values.tolist() == [3.0, 4.0]
    assert normalized_dataset["H_simulated__River_level"].attrs == {
        "location_id": "River_level",
        "parameter_id": "H_simulated",
        "station_name": "River Level",
        "latitude": -30.0,
        "longitude": 30.8,
        "elevation": 1.0,
        "time_step_unit": "second",
        "time_step_multiplier": 1200,
    }


def test_normalize_netcdf_dataset_to_timeseries_xarray_is_noop_for_canonical_dataset(
    netcdf_dataset: xr.Dataset,
):
    normalized_dataset = normalize_netcdf_dataset_to_timeseries_xarray(netcdf_dataset)

    xr.testing.assert_identical(normalized_dataset, netcdf_dataset)
