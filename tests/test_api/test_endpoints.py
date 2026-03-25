from datetime import datetime

import pytest
from pytz import timezone

from fews_py_wrapper._api import TimeSeries


def test_format_time_args():
    endpoint = TimeSeries()
    kwargs = {
        "start_time": "2023-01-01T12:00:00Z",  # Invalid, should be datetime
    }
    with pytest.raises(
        ValueError,
        match=(
            "Invalid argument value for start_time: Expected datetime,"
            " got <class 'str'>"
        ),
    ):
        endpoint._format_time_args(kwargs)

    kwargs = {
        "start_time": datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone("UTC")),
    }
    formatted_kwargs = endpoint._format_time_args(kwargs)
    assert formatted_kwargs["start_time"] == "2023-01-01T12:00:00Z"


def test_format_external_forecast_times():
    endpoint = TimeSeries()
    kwargs = {
        "external_forecast_times": [
            datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone("UTC")),
            "2023-01-01T13:00:00Z",
        ]
    }

    formatted_kwargs = endpoint._format_time_args(kwargs)

    assert formatted_kwargs["external_forecast_times"] == [
        "2023-01-01T12:00:00Z",
        "2023-01-01T13:00:00Z",
    ]
