import inspect
import io
import json
import zipfile
from datetime import datetime, timezone
from urllib.parse import parse_qs

import httpx
import numpy as np
import pytest
import xarray as xr
from fews_openapi_py_client.models.posttimeseries_json_body import (
    PosttimeseriesJsonBody,
)

from fews_py_wrapper import FewsWebServiceClient
from fews_py_wrapper._api import PostTimeSeries
from fews_py_wrapper.utils import convert_netcdf_zip_response_to_xarray


@pytest.fixture()
def metadata_netcdf(tmp_path):
    """Generate a small FEWS-style member without a stored binary fixture."""
    dataset = xr.Dataset(
        data_vars={
            "double": (
                ("time", "stations", "realization"),
                np.array([[[1.0, np.nan], [2.0, 3.0]]]),
                {
                    "long_name": "double",
                    "units": "m",
                    "module_instance_id": "ts_value_property",
                    "FEWS_internal_parameter_id": "double",
                    "FEWS_time_series_type": "simulated forecasting",
                    "FEWS_time_series_value_type": "scalar",
                    "time_step_id": "SETS10",
                    "ensemble_id": "main",
                    "qualifier_id": "['15']",
                    "task_run_id": "SA105_20",
                    "workflow_id": "Test_WhatIfProperties2",
                    "mc_id": "none",
                    "user_id": "Test user",
                },
            )
        },
        coords={
            "time": [np.datetime64("2026-10-13T00:00:00", "ns")],
            "station_id": ("stations", ["site-1", "site-2"]),
            "realization": [0, 1],
            "double_location_id": ("stations", ["site-1", "site-2"]),
            "double_module_instance_id": (
                "stations",
                ["ts_value_property", "other_module"],
            ),
            "double_qualifier_id": ("stations", ["15", "16"]),
            "double_ensemble_member": ("realization", ["member-a", "member-b"]),
        },
        attrs={"Conventions": "CF-1.6"},
    )
    path = tmp_path / "metadata.nc"
    dataset.to_netcdf(
        path, engine="netcdf4", encoding={"double": {"_FillValue": -999.0}}
    )
    return path.read_bytes(), dataset


@pytest.mark.parametrize("zipped", [True, False])
def test_native_netcdf_metadata_is_preserved(metadata_netcdf, zipped):
    content, expected = metadata_netcdf
    if zipped:
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as members:
            members.writestr("first.nc", content)
            members.writestr("nested/second.nc", content)
        content = archive.getvalue()

    datasets = convert_netcdf_zip_response_to_xarray(content)
    assert len(datasets) == (2 if zipped else 1)
    for index, dataset in enumerate(datasets):
        reference = expected.copy(deep=True)
        if zipped:
            reference.attrs["fews_zip_member_filename"] = ["first", "nested/second"][
                index
            ]
        xr.testing.assert_identical(dataset, reference)
        assert dataset["double"].encoding["_FillValue"] == -999.0
        assert "_FillValue" not in dataset["double"].attrs
        assert "module_instance_id" not in dataset.attrs


@pytest.mark.parametrize("flag", ["omitted", None, True, False])
def test_get_timeseries_metadata_query_and_native_output(metadata_netcdf, flag):
    content, expected = metadata_netcdf
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200, content=content, headers={"content-type": "application/x-netcdf"}
        )

    client = FewsWebServiceClient(base_url="https://example.test")
    with httpx.Client(
        base_url=client.base_url, transport=httpx.MockTransport(respond)
    ) as http_client:
        client.client.set_httpx_client(http_client)
        arguments = (
            {} if flag == "omitted" else {"show_fews_time_series_metadata": flag}
        )
        datasets = client.get_timeseries(**arguments)

    assert isinstance(datasets, list)
    xr.testing.assert_identical(datasets[0], expected)
    assert len(requests) == 1
    assert requests[0].url.path == "/timeseries"
    assert requests[0].url.params["documentFormat"] == "PI_NETCDF"
    assert requests[0].url.params.get("showFewsTimeSeriesMetadata") == (
        "true" if flag is True else "false" if flag is False else None
    )
    parameter = inspect.signature(client.get_timeseries).parameters[
        "show_fews_time_series_metadata"
    ]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is None


@pytest.mark.parametrize("flag", ["true", 1])
def test_metadata_flag_rejects_non_booleans(flag):
    client = FewsWebServiceClient(base_url="https://example.test")
    with pytest.raises(ValueError, match="Expected boolean value"):
        client.get_timeseries(show_fews_time_series_metadata=flag)


def test_pi_json_only_header_fields_remain_available():
    payload = {
        "timeSeries": [
            {
                "header": {
                    "type": "instantaneous",
                    "timeSeriesId": "opaque-id",
                    "creationDate": "2026-10-13",
                    "creationTime": "00:00:00",
                    "timeStep": {"unit": "second", "multiplier": "600"},
                    "customField": "preserved",
                }
            }
        ]
    }
    client = FewsWebServiceClient(base_url="https://example.test")
    with httpx.Client(
        base_url=client.base_url,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=payload)
        ),
    ) as http_client:
        client.client.set_httpx_client(http_client)
        result = client.get_timeseries(document_format="PI_JSON")
    assert result == payload


@pytest.mark.parametrize("content_format", ["xml", "json"])
def test_post_timeseries_uses_generated_form_body(content_format):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200, text="<Diag />", headers={"content-type": "application/xml"}
        )

    content = "<TimeSeries />" if content_format == "xml" else '{"timeSeries": []}'
    client = FewsWebServiceClient(base_url="https://example.test")
    with httpx.Client(
        base_url=client.base_url, transport=httpx.MockTransport(respond)
    ) as http_client:
        client.client.set_httpx_client(http_client)
        result = client.post_timeseries(
            **{f"pi_time_series_{content_format}_content": content}, convert_datum=False
        )
    assert result == "<Diag />"
    assert requests[0].headers["content-type"] == "application/x-www-form-urlencoded"
    field = (
        "piTimeSeriesXmlContent"
        if content_format == "xml"
        else "piTimeSeriesJsonContent"
    )
    assert parse_qs(requests[0].content.decode())[field] == [content]
    assert requests[0].url.params["convertDatum"] == "false"


def test_post_timeseries_accepts_generated_json_body():
    payload = {"timeSeries": []}
    client = FewsWebServiceClient(base_url="https://example.test")

    def respond(request):
        assert request.headers["content-type"] == "application/json"
        assert json.loads(request.content) == payload
        return httpx.Response(
            200, text="<Diag />", headers={"content-type": "application/xml"}
        )

    with httpx.Client(
        base_url=client.base_url, transport=httpx.MockTransport(respond)
    ) as http_client:
        client.client.set_httpx_client(http_client)
        assert (
            PostTimeSeries().execute(
                client=client.client, body=PosttimeseriesJsonBody.from_dict(payload)
            )
            == "<Diag />"
        )


@pytest.mark.parametrize("xml_content", [None, "<ModelParameters />"])
def test_post_runtask_uses_generated_form_encoding(xml_content):
    client = FewsWebServiceClient(base_url="https://example.test")

    def respond(request):
        assert request.headers["content-type"] == "application/x-www-form-urlencoded"
        assert request.url.params["workflowId"] == "TestWorkflow"
        assert request.url.params["timeZero"] == "2026-10-13T00:00:00Z"
        assert request.url.params["runLocallyAndPromoteToServer"] == "false"
        if xml_content is None:
            assert request.content == b""
        else:
            assert parse_qs(request.content.decode()) == {
                "piParametersXmlContent": [xml_content]
            }
        return httpx.Response(200, text="SA105_20")

    with httpx.Client(
        base_url=client.base_url, transport=httpx.MockTransport(respond)
    ) as http_client:
        client.client.set_httpx_client(http_client)
        assert (
            client.post_runtask(
                workflow_id="TestWorkflow",
                time_zero=datetime(2026, 10, 13, tzinfo=timezone.utc),
                run_locally_and_promote_to_server=False,
                pi_parameters_xml_content=xml_content,
            )
            == "SA105_20"
        )
