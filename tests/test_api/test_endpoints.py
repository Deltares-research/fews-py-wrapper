from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from fews_openapi_py_client.models.postruntask_body import PostruntaskBody
from fews_openapi_py_client.models.posttimeseries_body import PosttimeseriesBody
from pytz import timezone

from fews_py_wrapper._api import (
    Filters,
    PostRunTask,
    PostTimeSeries,
    PostWhatIfScenarios,
    Taskruns,
    Taskrunstatus,
    TimeSeries,
    WhatIfScenarios,
    WhatIfTemplates,
    Workflows,
)
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


def test_taskruns_format_time_args_rejects_non_datetime_values():
    with pytest.raises(
        ValueError,
        match=(
            "Invalid argument value for start_forecast_time: Expected datetime,"
            " got <class 'str'>"
        ),
    ):
        Taskruns()._format_time_args({"start_forecast_time": "2025-03-18T15:00:00Z"})


def test_taskruns_execute_returns_json_as_dict_and_formats_times():
    response = Mock(
        status_code=200,
        content=b'{"taskRuns": [{"id": "SA107_14", "workflowId": "ImportObscape"}]}',
        headers={"content-type": "application/json"},
    )
    captured_kwargs: dict[str, object] = {}

    def mock_endpoint_function(*, client, **kwargs):
        captured_kwargs.update(kwargs)
        return response

    with patch.object(
        Taskruns,
        "endpoint_function",
        staticmethod(mock_endpoint_function),
    ):
        result = Taskruns().execute(
            client=Mock(),
            workflow_id="ImportObscape",
            start_forecast_time=datetime(2025, 3, 18, 15, 0, 0, tzinfo=timezone("UTC")),
            end_dispatch_time=datetime(2025, 3, 18, 16, 0, 0, tzinfo=timezone("UTC")),
            only_forecasts=True,
            only_current=False,
            document_format="PI_JSON",
        )

    assert isinstance(result, dict)
    assert result["taskRuns"][0]["id"] == "SA107_14"
    assert captured_kwargs["start_forecast_time"] == "2025-03-18T15:00:00Z"
    assert captured_kwargs["end_dispatch_time"] == "2025-03-18T16:00:00Z"
    assert callable(getattr(captured_kwargs["start_forecast_time"], "isoformat", None))
    assert getattr(captured_kwargs["start_forecast_time"], "isoformat")() == (
        "2025-03-18T15:00:00Z"
    )


def test_taskruns_execute_handles_generated_enums_without_signature_loss():
    with patch.object(
        ApiEndpoint, "execute", return_value={"taskRuns": []}
    ) as execute_mock:
        result = Taskruns().execute(
            client=Mock(),
            workflow_id="ImportObscape",
            only_forecasts=True,
            only_current=False,
            document_format="PI_JSON",
        )

    assert result == {"taskRuns": []}
    called_kwargs = execute_mock.call_args.kwargs
    assert getattr(called_kwargs["only_forecasts"], "value", None) == "true"
    assert getattr(called_kwargs["only_current"], "value", None) == "false"
    assert getattr(called_kwargs["document_format"], "value", None) == "PI_JSON"


def test_taskruns_execute_returns_xml_as_text():
    response = Mock(
        status_code=200,
        content=b"<TaskRuns />",
        headers={"content-type": "application/xml"},
    )

    def mock_endpoint_function(*, client, **kwargs):
        return response

    with patch.object(
        Taskruns,
        "endpoint_function",
        staticmethod(mock_endpoint_function),
    ):
        result = Taskruns().execute(client=Mock(), workflow_id="ImportObscape")

    assert isinstance(result, str)
    assert result == "<TaskRuns />"


def test_taskrunstatus_execute_returns_json_as_dict():
    response = Mock(
        status_code=200,
        content=b'{"version": "1.34", "code": "P", "description": "Pending", '
        b'"taskRunId": "SA107_32"}',
        headers={"content-type": "application/json"},
    )

    def mock_endpoint_function(*, client, **kwargs):
        return response

    with patch.object(
        Taskrunstatus,
        "endpoint_function",
        staticmethod(mock_endpoint_function),
    ):
        result = Taskrunstatus().execute(
            client=Mock(),
            task_id="SA107_0000032",
            document_format="PI_JSON",
        )

    assert isinstance(result, dict)
    assert result["code"] == "P"
    assert result["taskRunId"] == "SA107_32"


def test_taskrunstatus_execute_handles_generated_document_format_enum():
    with patch.object(
        ApiEndpoint,
        "execute",
        return_value={"code": "P", "taskRunId": "SA107_32"},
    ) as execute_mock:
        result = Taskrunstatus().execute(
            client=Mock(),
            task_id="SA107_0000032",
            document_format="PI_JSON",
        )

    assert result == {"code": "P", "taskRunId": "SA107_32"}
    called_kwargs = execute_mock.call_args.kwargs
    assert getattr(called_kwargs["document_format"], "value", None) == "PI_JSON"


def test_whatiftemplates_execute_returns_json_as_dict():
    response = Mock(
        status_code=200,
        content=b'{"whatIfTemplates": [{"id": "template-1", "name": "Template 1"}]}',
        headers={"content-type": "application/json"},
    )

    def mock_endpoint_function(*, client, **kwargs):
        return response

    with patch.object(
        WhatIfTemplates,
        "endpoint_function",
        staticmethod(mock_endpoint_function),
    ):
        result = WhatIfTemplates().execute(client=Mock(), document_format="PI_JSON")

    assert isinstance(result, dict)
    assert result["whatIfTemplates"][0]["id"] == "template-1"


def test_whatiftemplates_execute_handles_generated_document_format_enum():
    with patch.object(
        ApiEndpoint,
        "execute",
        return_value={"whatIfTemplates": []},
    ) as execute_mock:
        result = WhatIfTemplates().execute(client=Mock(), document_format="PI_JSON")

    assert result == {"whatIfTemplates": []}
    called_kwargs = execute_mock.call_args.kwargs
    assert getattr(called_kwargs["document_format"], "value", None) == "PI_JSON"


def test_whatifscenarios_execute_returns_json_as_dict():
    response = Mock(
        status_code=200,
        content=(
            b'{"whatIfScenarioDescriptors": [{"id": "SA107:2", '
            b'"whatIfTemplateId": "template-1", "singleRunWhatIf": false, '
            b'"properties": []}]}'
        ),
        headers={"content-type": "application/json"},
    )

    def mock_endpoint_function(*, client, **kwargs):
        return response

    with patch.object(
        WhatIfScenarios,
        "endpoint_function",
        staticmethod(mock_endpoint_function),
    ):
        result = WhatIfScenarios().execute(
            client=Mock(),
            what_if_template_id="template-1",
            what_if_scenario_id="SA107:2",
            workflow_id="ImportObscape",
            document_format="PI_JSON",
        )

    assert isinstance(result, dict)
    assert result["whatIfScenarioDescriptors"][0]["id"] == "SA107:2"
    assert result["whatIfScenarioDescriptors"][0]["whatIfTemplateId"] == "template-1"


def test_whatifscenarios_execute_handles_generated_document_format_enum():
    with patch.object(
        ApiEndpoint,
        "execute",
        return_value={"whatIfScenarioDescriptors": []},
    ) as execute_mock:
        result = WhatIfScenarios().execute(client=Mock(), document_format="PI_JSON")

    assert result == {"whatIfScenarioDescriptors": []}
    called_kwargs = execute_mock.call_args.kwargs
    assert getattr(called_kwargs["document_format"], "value", None) == "PI_JSON"


def test_post_whatifscenarios_execute_returns_json_as_dict():
    response = Mock(
        status_code=200,
        content=(
            b'{"id": "SA107:2", "name": "Wrapper what-if scenario", '
            b'"whatIfTemplateId": "template-1", "singleRunWhatIf": false, '
            b'"properties": []}'
        ),
        headers={"content-type": "application/json"},
    )

    def mock_endpoint_function(*, client, **kwargs):
        return response

    with patch.object(
        PostWhatIfScenarios,
        "endpoint_function",
        staticmethod(mock_endpoint_function),
    ):
        result = PostWhatIfScenarios().execute(
            client=Mock(),
            what_if_template_id="template-1",
            single_run_what_if=False,
            name="Wrapper what-if scenario",
            document_format="PI_JSON",
        )

    assert isinstance(result, dict)
    assert result["id"] == "SA107:2"
    assert result["whatIfTemplateId"] == "template-1"
    assert result["singleRunWhatIf"] is False


def test_post_whatifscenarios_execute_handles_generated_enums_without_signature_loss():
    with patch.object(
        ApiEndpoint,
        "execute",
        return_value={"id": "SA107:2", "properties": []},
    ) as execute_mock:
        result = PostWhatIfScenarios().execute(
            client=Mock(),
            what_if_template_id="template-1",
            single_run_what_if=True,
            document_format="PI_JSON",
        )

    assert result == {"id": "SA107:2", "properties": []}
    called_kwargs = execute_mock.call_args.kwargs
    assert getattr(called_kwargs["single_run_what_if"], "value", None) == "true"
    assert getattr(called_kwargs["document_format"], "value", None) == "PI_JSON"


def test_post_runtask_execute_returns_text_and_prepares_body():
    response = Mock(
        status_code=200,
        content=b"SA107_00000000",
        headers={"content-type": "text/plain"},
    )
    captured_kwargs: dict[str, object] = {}

    def mock_endpoint_function(*, client, **kwargs):
        captured_kwargs.update(kwargs)
        return response

    with patch.object(
        PostRunTask,
        "endpoint_function",
        staticmethod(mock_endpoint_function),
    ):
        result = PostRunTask().execute(
            client=Mock(),
            workflow_id="ImportObscape",
            start_time=datetime(2025, 3, 18, 15, 0, 0, tzinfo=timezone("UTC")),
            end_time=datetime(2025, 3, 18, 16, 0, 0, tzinfo=timezone("UTC")),
            run_option="all",
            run_locally_and_promote_to_server=True,
            body={"piParametersXmlContent": "<ModelParameters />"},
        )

    assert result == "SA107_00000000"
    assert isinstance(captured_kwargs["body"], PostruntaskBody)
    prepared_body = captured_kwargs["body"]
    assert isinstance(prepared_body, PostruntaskBody)
    assert prepared_body.pi_parameters_xml_content == "<ModelParameters />"
    assert captured_kwargs["start_time"] == "2025-03-18T15:00:00Z"
    assert captured_kwargs["end_time"] == "2025-03-18T16:00:00Z"
    assert captured_kwargs["start_time"].isoformat() == "2025-03-18T15:00:00Z"
    assert captured_kwargs["run_option"] == "all"
    assert captured_kwargs["run_locally_and_promote_to_server"] is True


def test_post_runtask_execute_handles_generated_body_model_without_enum_error():
    with patch.object(
        ApiEndpoint, "execute", return_value="SA107_00000000"
    ) as execute_mock:
        result = PostRunTask().execute(
            client=Mock(),
            workflow_id="ImportObscape",
            time_zero=datetime(2025, 3, 18, 15, 0, 0, tzinfo=timezone("UTC")),
            run_option="allmostrecentonly",
            run_locally_and_promote_to_server=False,
            body={"piParametersXmlContent": "<ModelParameters />"},
        )

    assert result == "SA107_00000000"
    called_kwargs = execute_mock.call_args.kwargs
    assert isinstance(called_kwargs["body"], PostruntaskBody)
    assert called_kwargs["body"].pi_parameters_xml_content == "<ModelParameters />"
    assert called_kwargs["time_zero"] == "2025-03-18T15:00:00Z"
    assert getattr(called_kwargs["run_option"], "value", None) == "allmostrecentonly"
    assert (
        getattr(called_kwargs["run_locally_and_promote_to_server"], "value", None)
        == "false"
    )


def test_workflows_execute_returns_json_as_dict():
    response = Mock(
        status_code=200,
        content=b'{"workflows": [{"id": "workflow-1"}]}',
        headers={"content-type": "application/json"},
    )

    def mock_endpoint_function(*, client, **kwargs):
        return response

    with patch.object(
        Workflows,
        "endpoint_function",
        staticmethod(mock_endpoint_function),
    ):
        result = Workflows().execute(client=Mock(), document_format="PI_JSON")

    assert isinstance(result, dict)
    assert result["workflows"][0]["id"] == "workflow-1"


def test_workflows_execute_returns_xml_as_text():
    response = Mock(
        status_code=200,
        content=b"<Workflows />",
        headers={"content-type": "application/xml"},
    )

    def mock_endpoint_function(*, client, **kwargs):
        return response

    with patch.object(
        Workflows,
        "endpoint_function",
        staticmethod(mock_endpoint_function),
    ):
        result = Workflows().execute(client=Mock(), document_format="PI_XML")

    assert isinstance(result, str)
    assert result == "<Workflows />"
