from datetime import datetime, timezone

import numpy as np
import pytest
import xarray as xr
from fews_openapi_py_client.api.timeseries.timeseries import sync_detailed

from fews_py_wrapper.utils import (
    convert_timeseries_response_to_xarray,
    format_datetime,
    format_time_args,
    get_function_arg_names,
    get_parameter_models,
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


def test_get_paramter_models():
    get_parameter_models(sync_detailed)
