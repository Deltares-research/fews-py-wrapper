from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from fews_openapi_py_client.models.posttimeseries_body import PosttimeseriesBody
from pytz import timezone

from fews_py_wrapper._api import Filters, PostTimeSeries, Taskruns, TimeSeries
from fews_py_wrapper._api.base import ApiEndpoint


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


def test_filters_execute_returns_json_as_dict():
    response = Mock(
        status_code=200,
        content=b'{"filters": [{"id": "MEAS"}]}',
        headers={"content-type": "application/json"},
    )

    def mock_endpoint_function(*, client, **kwargs):
        return response

    with patch.object(
        Filters, "endpoint_function", staticmethod(mock_endpoint_function)
    ):
        result = Filters().execute(client=Mock(), document_format="PI_JSON")

    assert isinstance(result, dict)
    assert result["filters"][0]["id"] == "MEAS"


def test_filters_execute_returns_xml_as_text():
    response = Mock(
        status_code=200,
        content=b"<Filters />",
        headers={"content-type": "application/xml"},
    )

    def mock_endpoint_function(*, client, **kwargs):
        return response

    with patch.object(
        Filters, "endpoint_function", staticmethod(mock_endpoint_function)
    ):
        result = Filters().execute(client=Mock(), document_format="PI_XML")

    assert isinstance(result, str)
    assert result == "<Filters />"


def test_post_timeseries_execute_returns_xml_as_text_and_prepares_body():
    response = Mock(
        status_code=200,
        content=b"<Diag />",
        headers={"content-type": "application/xml"},
    )
    captured_kwargs: dict[str, object] = {}

    def mock_endpoint_function(*, client, **kwargs):
        captured_kwargs.update(kwargs)
        return response

    with patch.object(
        PostTimeSeries,
        "endpoint_function",
        staticmethod(mock_endpoint_function),
    ):
        result = PostTimeSeries().execute(
            client=Mock(),
            body={"piTimeSeriesXmlContent": "<TimeSeries />"},
            filter_id="MEAS",
            convert_datum=True,
        )

    assert isinstance(result, str)
    assert result == "<Diag />"
    assert isinstance(captured_kwargs["body"], PosttimeseriesBody)
    prepared_body = captured_kwargs["body"]
    assert isinstance(prepared_body, PosttimeseriesBody)
    assert prepared_body.pi_time_series_xml_content == "<TimeSeries />"
    assert captured_kwargs["convert_datum"] is True


def test_post_timeseries_execute_handles_generated_body_model_without_enum_error():
    with patch.object(ApiEndpoint, "execute", return_value="<Diag />") as execute_mock:
        result = PostTimeSeries().execute(
            client=Mock(),
            body={"piTimeSeriesXmlContent": "<TimeSeries />"},
            filter_id="MEAS",
            convert_datum=True,
        )

    assert result == "<Diag />"
    called_kwargs = execute_mock.call_args.kwargs
    assert isinstance(called_kwargs["body"], PosttimeseriesBody)
    assert called_kwargs["body"].pi_time_series_xml_content == "<TimeSeries />"
    assert getattr(called_kwargs["convert_datum"], "value", None) == "true"
