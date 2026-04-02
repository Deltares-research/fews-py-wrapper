from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from pytz import timezone

from fews_py_wrapper._api import Taskruns, TimeSeries


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


def test_taskruns_execute_returns_xml_as_text():
    response = Mock(
        status_code=200,
        content=b"<TaskRuns />",
        headers={"content-type": "application/xml"},
    )

    def mock_endpoint_function(*, client, **kwargs):
        return response

    with patch.object(
        Taskruns, "endpoint_function", staticmethod(mock_endpoint_function)
    ):
        result = Taskruns().execute(client=Mock(), document_format="PI_XML")

    assert isinstance(result, str)
    assert result == "<TaskRuns />"
