import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

import dotenv
import pytest
import xarray as xr
from fews_openapi_py_client.api.whatif import whatiftemplates
from fews_openapi_py_client.models.whatiftemplates_document_format import (
    WhatiftemplatesDocumentFormat,
)
from pydantic import ValidationError

from fews_py_wrapper.fews_webservices import FewsWebServiceClient
from fews_py_wrapper.models import (
    PiLocation,
    PiLocationAttribute,
    PiLocationsResponse,
    PiParameter,
    PiParametersResponse,
)

dotenv.load_dotenv()

PI_XML_NS = {"pi": "http://www.wldelft.nl/fews/PI"}


def _parse_pi_xml_payload(
    xml_content: str,
) -> tuple[str, str, datetime, datetime, list[dict[str, str]]]:
    root = ET.fromstring(xml_content)
    series = root.find("pi:series", PI_XML_NS)
    assert series is not None

    header = series.find("pi:header", PI_XML_NS)
    assert header is not None

    location_id = header.findtext("pi:locationId", namespaces=PI_XML_NS)
    parameter_id = header.findtext("pi:parameterId", namespaces=PI_XML_NS)
    assert location_id is not None
    assert parameter_id is not None

    start_date = header.find("pi:startDate", PI_XML_NS)
    end_date = header.find("pi:endDate", PI_XML_NS)
    assert start_date is not None
    assert end_date is not None

    start_time = datetime.fromisoformat(
        f"{start_date.attrib['date']}T{start_date.attrib['time']}+00:00"
    )
    end_time = datetime.fromisoformat(
        f"{end_date.attrib['date']}T{end_date.attrib['time']}+00:00"
    )

    events = [
        {
            "date": event.attrib["date"],
            "time": event.attrib["time"],
            "value": event.attrib["value"],
        }
        for event in series.findall("pi:event", PI_XML_NS)
    ]
    return location_id, parameter_id, start_time, end_time, events


def _parse_pi_json_datetime(value: str | dict[str, str]) -> datetime:
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.fromisoformat(f"{value['date']}T{value['time']}+00:00")


def _parse_pi_json_payload(
    json_content: str,
) -> tuple[str, str, datetime, datetime, list[dict[str, str]]]:
    payload = json.loads(json_content)
    series = payload["timeSeries"][0]
    header = series["header"]

    events = []
    for event in series["events"]:
        if "time" in event:
            event_date = event["date"]
            event_time = event["time"]
        else:
            event_datetime = datetime.fromisoformat(
                event["date"].replace("Z", "+00:00")
            )
            event_date = event_datetime.strftime("%Y-%m-%d")
            event_time = event_datetime.strftime("%H:%M:%S")
        events.append(
            {
                "date": event_date,
                "time": event_time,
                "value": str(event["value"]),
            }
        )

    return (
        header["locationId"],
        header["parameterId"],
        _parse_pi_json_datetime(header["startDate"]),
        _parse_pi_json_datetime(header["endDate"]),
        events,
    )


def _build_unique_post_series() -> tuple[datetime, list[datetime], list[str]]:
    seed = int(uuid4().hex[:8], 16)
    start_time = datetime(2099, 1, 1, 10, 0, 0, tzinfo=timezone.utc) + timedelta(
        days=seed % 365,
        minutes=(seed // 365) % (24 * 60),
        seconds=(seed // (365 * 24 * 60)) % 60,
    )
    event_times = [start_time + timedelta(hours=offset) for offset in range(3)]

    value_offset = Decimal(seed % 100) / Decimal("1000")
    base_values = [Decimal("0.214"), Decimal("0.211"), Decimal("0.209")]
    values = [str(value + value_offset) for value in base_values]
    return start_time, event_times, values


def _mutate_pi_xml_payload(xml_content: str) -> str:
    _, event_times, values = _build_unique_post_series()
    root = ET.fromstring(xml_content)
    series = root.find("pi:series", PI_XML_NS)
    assert series is not None

    header = series.find("pi:header", PI_XML_NS)
    assert header is not None

    start_date = header.find("pi:startDate", PI_XML_NS)
    end_date = header.find("pi:endDate", PI_XML_NS)
    assert start_date is not None
    assert end_date is not None
    start_date.attrib.update(
        {
            "date": event_times[0].strftime("%Y-%m-%d"),
            "time": event_times[0].strftime("%H:%M:%S"),
        }
    )
    end_date.attrib.update(
        {
            "date": event_times[-1].strftime("%Y-%m-%d"),
            "time": event_times[-1].strftime("%H:%M:%S"),
        }
    )

    events = series.findall("pi:event", PI_XML_NS)
    assert len(events) == len(event_times) == len(values)
    for event, event_time, value in zip(events, event_times, values, strict=True):
        event.attrib.update(
            {
                "date": event_time.strftime("%Y-%m-%d"),
                "time": event_time.strftime("%H:%M:%S"),
                "value": value,
            }
        )

    return ET.tostring(root, encoding="unicode")


def _mutate_pi_json_payload(json_content: str) -> str:
    _, event_times, values = _build_unique_post_series()
    payload = json.loads(json_content)
    series = payload["timeSeries"][0]
    header = series["header"]

    header["startDate"] = {
        "date": event_times[0].strftime("%Y-%m-%d"),
        "time": event_times[0].strftime("%H:%M:%S"),
    }
    header["endDate"] = {
        "date": event_times[-1].strftime("%Y-%m-%d"),
        "time": event_times[-1].strftime("%H:%M:%S"),
    }

    events = series["events"]
    assert len(events) == len(event_times) == len(values)
    for event, event_time, value in zip(events, event_times, values, strict=True):
        event.update(
            {
                "date": event_time.strftime("%Y-%m-%d"),
                "time": event_time.strftime("%H:%M:%S"),
                "value": value,
            }
        )

    return json.dumps(payload)


def _assert_timeseries_roundtrip(
    timeseries_json: dict[str, object],
    *,
    location_id: str,
    parameter_id: str,
    expected_events: list[dict[str, str]],
) -> None:
    matching_series = [
        series
        for series in timeseries_json["timeSeries"]
        if series["header"].get("locationId") == location_id
        and series["header"].get("parameterId") == parameter_id
    ]
    assert matching_series

    returned_events = matching_series[0]["events"]
    assert len(returned_events) == len(expected_events)

    for returned_event, expected_event in zip(
        returned_events, expected_events, strict=True
    ):
        assert returned_event["date"] == expected_event["date"]
        assert returned_event["time"] == expected_event["time"]
        assert Decimal(returned_event["value"]) == Decimal(expected_event["value"])


def _get_whatif_templates(
    fews_webservice_client: FewsWebServiceClient,
) -> list[dict[str, object]]:
    response = whatiftemplates.sync_detailed(
        client=fews_webservice_client.client,
        document_format=WhatiftemplatesDocumentFormat.PI_JSON,
    )
    assert response.status_code == 200
    payload = json.loads(response.content.decode("utf-8"))
    templates = payload.get("whatIfTemplates", [])
    assert isinstance(templates, list)
    return templates


@pytest.mark.integration
class TestFewsWebServiceClient:
    @pytest.fixture
    def fews_webservice_client(self) -> FewsWebServiceClient:
        fews_api_url = os.getenv("FEWS_API_URL")
        if fews_api_url is None:
            pytest.skip("FEWS_API_URL environment variable not set")
        return FewsWebServiceClient(
            base_url=fews_api_url, verify_ssl=False
        )  # Only for testing!

    def test_get_parameters(self, fews_webservice_client: FewsWebServiceClient):
        parameters = fews_webservice_client.get_parameters()
        assert isinstance(parameters, PiParametersResponse)
        assert isinstance(parameters.parameters, list)

    def test_get_locations(self, fews_webservice_client: FewsWebServiceClient):
        locations = fews_webservice_client.get_locations()
        assert isinstance(locations, PiLocationsResponse)
        assert isinstance(locations.locations, list)

    def test_get_timeseries_pi_json_returns_dict(
        self, fews_webservice_client: FewsWebServiceClient
    ):
        start_time = datetime(2025, 3, 14, 10, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 3, 14, 12, 0, 0, tzinfo=timezone.utc)
        timeseries_json = fews_webservice_client.get_timeseries(
            start_time=start_time,
            end_time=end_time,
            parameter_ids=["H_simulated"],
            location_ids=["Amanzimtoti_River_level", "Amanzimtoti_River_Mouth_level"],
            document_format="PI_JSON",
            module_instance_ids=["HydraulicPCSWMMFC_South_Toti_Simplified"],
        )
        assert isinstance(timeseries_json, dict)
        assert "timeSeries" in timeseries_json

    def test_get_timeseries_pi_netcdf_returns_dataset_list(
        self, fews_webservice_client: FewsWebServiceClient
    ):
        start_time = datetime(2025, 3, 14, 10, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 3, 14, 12, 0, 0, tzinfo=timezone.utc)
        parameter_ids = ["H_simulated"]
        location_ids = ["Amanzimtoti_River_level", "Amanzimtoti_River_Mouth_level"]
        timeseries_netcdf = fews_webservice_client.get_timeseries(
            start_time=start_time,
            end_time=end_time,
            parameter_ids=parameter_ids,
            location_ids=location_ids,
        )
        assert isinstance(timeseries_netcdf, list)
        assert timeseries_netcdf
        assert all(isinstance(dataset, xr.Dataset) for dataset in timeseries_netcdf)
        assert all(dataset.data_vars for dataset in timeseries_netcdf)

    def test_get_taskruns(self, fews_webservice_client: FewsWebServiceClient):
        task_id = "saetprtmc00:000104393"
        task = fews_webservice_client.get_taskruns(
            workflow_id="SFINCSPalmiet",
            task_run_ids=task_id,
        )
        assert isinstance(task, dict)

    def test_get_whatifscenarios(self, fews_webservice_client: FewsWebServiceClient):
        whatif_scenarios = fews_webservice_client.get_whatifscenarios()

        assert isinstance(whatif_scenarios, dict)
        assert "whatIfScenarioDescriptors" in whatif_scenarios
        assert isinstance(whatif_scenarios["whatIfScenarioDescriptors"], list)

    def test_post_whatifscenarios(self, fews_webservice_client: FewsWebServiceClient):
        templates = _get_whatif_templates(fews_webservice_client)
        if not templates:
            pytest.skip("No what-if templates available on the FEWS test server")

        template_id = str(templates[0]["id"])
        scenario_name = f"py-whatif-{uuid4().hex[:8]}"

        created_scenario = fews_webservice_client.post_whatifscenarios(
            what_if_template_id=template_id,
            single_run_what_if=True,
            name=scenario_name,
        )

        assert isinstance(created_scenario, dict)
        assert created_scenario["whatIfTemplateId"] == template_id
        assert created_scenario["name"] == scenario_name
        assert created_scenario["singleRunWhatIf"] is True
        assert created_scenario["id"]

    def test_endpoint_arguments(self, fews_webservice_client: FewsWebServiceClient):
        # This test checks that invalid arguments raise a ValueError
        input_args = fews_webservice_client.endpoint_arguments("timeseries")
        assert "location_ids" in input_args
        post_input_args = fews_webservice_client.endpoint_arguments("post_timeseries")
        assert "pi_time_series_xml_content" in post_input_args
        assert "pi_time_series_json_content" in post_input_args
        assert "body" not in post_input_args
        get_whatif_args = fews_webservice_client.endpoint_arguments(
            "get_whatifscenarios"
        )
        assert "what_if_template_id" in get_whatif_args
        assert "what_if_scenario_id" in get_whatif_args
        post_whatif_args = fews_webservice_client.endpoint_arguments(
            "post_whatifscenarios"
        )
        assert "single_run_what_if" in post_whatif_args
        assert "name" in post_whatif_args
        with pytest.raises(ValueError, match="Unknown endpoint: invalid_endpoint"):
            fews_webservice_client.endpoint_arguments("invalid_endpoint")

    def test_get_workflows(self, fews_webservice_client: FewsWebServiceClient):
        all_workflows = fews_webservice_client.get_workflows()
        assert isinstance(all_workflows, dict)
        assert len(all_workflows["workflows"]) > 1

    def test_post_timeseries_roundtrip_with_pi_xml(
        self,
        fews_webservice_client: FewsWebServiceClient,
        post_timeseries_xml_content: str,
    ):
        xml_payload = _mutate_pi_xml_payload(post_timeseries_xml_content)
        location_id, parameter_id, start_time, end_time, posted_events = (
            _parse_pi_xml_payload(xml_payload)
        )

        diag_xml = fews_webservice_client.post_timeseries(
            pi_time_series_xml_content=xml_payload
        )

        assert "<Diag" in diag_xml
        assert "1 time series imported, 0 time series rejected" in diag_xml
        assert f"{location_id}:{parameter_id}" in diag_xml

        timeseries_json = fews_webservice_client.get_timeseries(
            start_time=start_time,
            end_time=end_time,
            parameter_ids=[parameter_id],
            location_ids=[location_id],
            document_format="PI_JSON",
        )

        _assert_timeseries_roundtrip(
            timeseries_json,
            location_id=location_id,
            parameter_id=parameter_id,
            expected_events=posted_events,
        )

    def test_post_timeseries_roundtrip_with_pi_json(
        self,
        fews_webservice_client: FewsWebServiceClient,
        post_timeseries_json_content: str,
    ):
        json_payload = _mutate_pi_json_payload(post_timeseries_json_content)
        location_id, parameter_id, start_time, end_time, posted_events = (
            _parse_pi_json_payload(json_payload)
        )

        diag_xml = fews_webservice_client.post_timeseries(
            pi_time_series_json_content=json_payload
        )

        assert "<Diag" in diag_xml
        assert "1 time series imported, 0 time series rejected" in diag_xml
        assert f"{location_id}:{parameter_id}" in diag_xml

        timeseries_json = fews_webservice_client.get_timeseries(
            start_time=start_time,
            end_time=end_time,
            parameter_ids=[parameter_id],
            location_ids=[location_id],
            document_format="PI_JSON",
        )

        _assert_timeseries_roundtrip(
            timeseries_json,
            location_id=location_id,
            parameter_id=parameter_id,
            expected_events=posted_events,
        )


class TestFewsWebServiceClientWithMocking:
    @pytest.fixture
    def mock_client(self):
        """Create a mock client."""
        return Mock()

    @pytest.fixture
    def fews_webservice_client_with_mock(self, mock_client):
        """Create FewsWebServiceClient with mocked underlying client."""
        with patch("fews_py_wrapper.fews_webservices.Client", return_value=mock_client):
            client = FewsWebServiceClient(
                base_url="http://mock-url.com", verify_ssl=False
            )
            client.client = mock_client  # Ensure the mock is set
            return client

    @pytest.fixture
    def sample_timeseries_response(self):
        """Load sample response from test data."""
        test_data_path = (
            Path(__file__).parent / "test_data" / "timeseries_response.json"
        )
        with open(test_data_path) as f:
            return json.load(f)

    def test_get_timeseries_with_mock(
        self,
        fews_webservice_client_with_mock: FewsWebServiceClient,
        sample_timeseries_response,
    ):
        """Test get_timeseries with mocked response."""
        # Arrange: Set up the mock to return sample data
        with patch(
            "fews_py_wrapper._api.endpoints.TimeSeries.execute",
            return_value=sample_timeseries_response,
        ):
            # Act
            start_time = datetime(2025, 3, 14, 10, 0, 0, tzinfo=timezone.utc)
            end_time = datetime(2025, 3, 15, 0, 0, 0, tzinfo=timezone.utc)
            result = fews_webservice_client_with_mock.get_timeseries(
                start_time=start_time,
                end_time=end_time,
                parameter_ids=["H.obs"],
                location_ids=["Amanzimtoti_River_level"],
                document_format="PI_JSON",
            )

            # Assert
            assert result is not None
            assert result == sample_timeseries_response

    def test_get_timeseries_defaults_to_dataset_list(
        self,
        fews_webservice_client_with_mock: FewsWebServiceClient,
        netcdf_zip_response: bytes,
    ):
        with patch(
            "fews_py_wrapper._api.endpoints.TimeSeries.execute",
            return_value=netcdf_zip_response,
        ):
            start_time = datetime(2025, 3, 14, 10, 0, 0, tzinfo=timezone.utc)
            end_time = datetime(2025, 3, 15, 0, 0, 0, tzinfo=timezone.utc)
            result = fews_webservice_client_with_mock.get_timeseries(
                start_time=start_time,
                end_time=end_time,
                parameter_ids=["H.obs"],
                location_ids=["Amanzimtoti_River_level"],
            )

        assert isinstance(result, list)
        assert len(result) == 1
        dataset = result[0]
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

    def test_get_timeseries_preserves_multiple_netcdf_members(
        self,
        fews_webservice_client_with_mock: FewsWebServiceClient,
        multi_member_netcdf_zip_response: bytes,
    ):
        with patch(
            "fews_py_wrapper._api.endpoints.TimeSeries.execute",
            return_value=multi_member_netcdf_zip_response,
        ):
            result = fews_webservice_client_with_mock.get_timeseries(
                parameter_ids=["H.obs"],
                location_ids=["Amanzimtoti_River_level"],
            )

        assert isinstance(result, list)
        assert len(result) == 21
        assert all(isinstance(dataset, xr.Dataset) for dataset in result)
        assert dict(result[0].sizes) == {"stations": 2, "time": 46}
        assert list(result[0].data_vars) == ["station_names", "C_obs_dir_depthavg"]
        assert dict(result[-1].sizes) == {
            "time": 26,
            "nbnds": 2,
            "stations": 361,
            "analysis_time": 1,
        }
        assert "warning_index" in result[-1].data_vars

    def test_get_timeseries_supports_pi_xml_response(
        self,
        fews_webservice_client_with_mock: FewsWebServiceClient,
    ):
        xml_response = '<TimeSeries version="1.34" />'

        with patch(
            "fews_py_wrapper._api.endpoints.TimeSeries.execute",
            return_value=xml_response,
        ):
            result = fews_webservice_client_with_mock.get_timeseries(
                document_format="PI_XML",
                parameter_ids=["H.obs"],
                location_ids=["Amanzimtoti_River_level"],
            )

        assert result == xml_response

    def test_get_timeseries_supports_pi_csv_response(
        self,
        fews_webservice_client_with_mock: FewsWebServiceClient,
    ):
        csv_response = "time,H.obs\n2025-03-14T10:00:00Z,1.0\n"

        with patch(
            "fews_py_wrapper._api.endpoints.TimeSeries.execute",
            return_value=csv_response,
        ):
            result = fews_webservice_client_with_mock.get_timeseries(
                document_format="PI_CSV",
                parameter_ids=["H.obs"],
                location_ids=["Amanzimtoti_River_level"],
            )

        assert result == csv_response

    def test_post_timeseries_with_xml_content(
        self,
        fews_webservice_client_with_mock: FewsWebServiceClient,
        post_timeseries_xml_content: str,
    ):
        diag_response = "<Diag />"
        assert "<TimeSeries" in post_timeseries_xml_content
        assert "<event" in post_timeseries_xml_content

        with patch(
            "fews_py_wrapper.fews_webservices.PostTimeSeries.execute",
            return_value=diag_response,
        ) as mock_execute:
            result = fews_webservice_client_with_mock.post_timeseries(
                pi_time_series_xml_content=post_timeseries_xml_content,
                filter_id="MEAS",
                convert_datum=True,
            )

        assert result == diag_response
        mock_execute.assert_called_once_with(
            client=fews_webservice_client_with_mock.client,
            body={"piTimeSeriesXmlContent": post_timeseries_xml_content},
            filter_id="MEAS",
            convert_datum=True,
        )

    def test_post_timeseries_with_json_content(
        self,
        fews_webservice_client_with_mock: FewsWebServiceClient,
        post_timeseries_json_content: str,
    ):
        diag_response = "<Diag />"
        sample_json = json.loads(post_timeseries_json_content)
        assert sample_json["timeSeries"][0]["header"]["parameterId"] == "H.obs"

        with patch(
            "fews_py_wrapper.fews_webservices.PostTimeSeries.execute",
            return_value=diag_response,
        ) as mock_execute:
            result = fews_webservice_client_with_mock.post_timeseries(
                pi_time_series_json_content=post_timeseries_json_content
            )

        assert result == diag_response
        mock_execute.assert_called_once_with(
            client=fews_webservice_client_with_mock.client,
            body={"piTimeSeriesJsonContent": post_timeseries_json_content},
        )

    def test_post_timeseries_requires_body_content(
        self,
        fews_webservice_client_with_mock: FewsWebServiceClient,
    ):
        with pytest.raises(
            ValueError,
            match="One of pi_time_series_xml_content or pi_time_series_json_content",
        ):
            fews_webservice_client_with_mock.post_timeseries()

    @pytest.mark.parametrize("document_format", ["DD_JSON", "BINARY", "NOOS_TEXT"])
    def test_get_timeseries_rejects_non_pi_formats(
        self,
        fews_webservice_client_with_mock: FewsWebServiceClient,
        document_format: str,
    ):
        with pytest.raises(
            ValueError,
            match="Unsupported timeseries document_format for this PI-focused wrapper",
        ):
            fews_webservice_client_with_mock.get_timeseries(
                document_format=document_format,
                parameter_ids=["H.obs"],
                location_ids=["Amanzimtoti_River_level"],
            )

    def test_get_locations_with_mock(
        self, fews_webservice_client_with_mock: FewsWebServiceClient
    ):
        """Test get_locations parses the PI response into a Pydantic model."""
        mock_response = {
            "version": "1.34",
            "geoDatum": "WGS 1984",
            "locations": [
                {
                    "locationId": "Adams_K1_rain",
                    "description": "Adams K1",
                    "shortName": "Adams K1",
                    "lat": "-30.036255",
                    "lon": "30.810044",
                    "x": "30.810044",
                    "y": "-30.036255",
                    "z": "0.0",
                    "attributes": [{"name": "stationOwner", "text": "eThekwini"}],
                }
            ],
        }

        with patch(
            "fews_py_wrapper._api.endpoints.Locations.execute",
            return_value=mock_response,
        ):
            result = fews_webservice_client_with_mock.get_locations()

        assert isinstance(result, PiLocationsResponse)
        assert result.geo_datum == "WGS 1984"
        assert len(result.locations) == 1
        assert isinstance(result.locations[0], PiLocation)
        assert result.locations[0].location_id == "Adams_K1_rain"
        assert result.locations[0].lat == pytest.approx(-30.036255)
        assert result.locations[0].attributes[0].text == "eThekwini"

    def test_get_parameters_with_mock(
        self, fews_webservice_client_with_mock: FewsWebServiceClient
    ):
        """Test get_parameters parses the PI response into a Pydantic model."""
        mock_response = {
            "version": "1.34",
            "timeSeriesParameters": [
                {
                    "id": "P_obs",
                    "name": "Observed Precipitation",
                    "shortName": "Precipitation (obs)",
                    "parameterType": "accumulative",
                    "unit": "mm",
                    "displayUnit": "mm",
                    "usesDatum": "false",
                    "parameterGroup": "Precipitation",
                    "parameterGroupName": "Precipitation",
                    "attributes": [{"name": "source", "text": "gauge"}],
                }
            ],
        }

        with patch(
            "fews_py_wrapper._api.endpoints.Parameters.execute",
            return_value=mock_response,
        ):
            result = fews_webservice_client_with_mock.get_parameters()

        assert isinstance(result, PiParametersResponse)
        assert len(result.parameters) == 1
        assert isinstance(result.parameters[0], PiParameter)
        assert result.parameters[0].id == "P_obs"
        assert result.parameters[0].parameter_type == "accumulative"
        assert result.parameters[0].uses_datum is False
        assert result.parameters[0].attributes[0].text == "gauge"

    def test_get_parameters_with_mock_rejects_invalid_parameter_type(
        self, fews_webservice_client_with_mock: FewsWebServiceClient
    ):
        """Test get_parameters rejects PI payloads with an invalid parameter type."""
        mock_response = {
            "version": "1.34",
            "timeSeriesParameters": [
                {
                    "id": "P_obs",
                    "name": "Observed Precipitation",
                    "parameterType": "invalid",
                    "unit": "mm",
                }
            ],
        }

        with patch(
            "fews_py_wrapper._api.endpoints.Parameters.execute",
            return_value=mock_response,
        ):
            with pytest.raises(ValidationError, match="parameterType"):
                fews_webservice_client_with_mock.get_parameters()

    def test_location_attribute_requires_exactly_one_value_field(self):
        with pytest.raises(ValidationError):
            PiLocationAttribute(name="stationOwner", text="eThekwini", number=1.0)

    def test_get_taskruns_with_mock(
        self, fews_webservice_client_with_mock: FewsWebServiceClient
    ):
        """Test get_taskruns with mocked response."""
        # Arrange: Create mock response
        mock_response = {
            "taskRuns": [
                {
                    "id": "SA5_1",
                    "status": "pending",
                    "workflowId": "RunParticleTracking",
                }
            ]
        }

        with patch(
            "fews_py_wrapper._api.endpoints.Taskruns.execute",
            return_value=mock_response,
        ):
            # Act
            result = fews_webservice_client_with_mock.get_taskruns(
                workflow_id="RunParticleTracking", task_run_ids="SA5_1"
            )

            # Assert
            assert isinstance(result, dict)
            assert result["taskRuns"][0]["id"] == "SA5_1"
            assert result["taskRuns"][0]["status"] == "pending"

    def test_get_whatifscenarios_with_mock(
        self, fews_webservice_client_with_mock: FewsWebServiceClient
    ):
        mock_response = {
            "whatIfScenarioDescriptors": [
                {
                    "id": "scenario-1",
                    "whatIfTemplateId": "template-1",
                    "workflowId": "workflow-1",
                }
            ]
        }

        with patch(
            "fews_py_wrapper.fews_webservices.GetWhatIfScenarios.execute",
            return_value=mock_response,
        ) as execute_mock:
            result = fews_webservice_client_with_mock.get_whatifscenarios(
                what_if_template_id="template-1",
                what_if_scenario_id="scenario-1",
                workflow_id="workflow-1",
            )

        assert result == mock_response
        execute_mock.assert_called_once_with(
            client=fews_webservice_client_with_mock.client,
            what_if_template_id="template-1",
            what_if_scenario_id="scenario-1",
            workflow_id="workflow-1",
            document_format="PI_JSON",
        )

    def test_get_whatifscenarios_omits_none_arguments(
        self, fews_webservice_client_with_mock: FewsWebServiceClient
    ):
        with patch(
            "fews_py_wrapper.fews_webservices.GetWhatIfScenarios.execute",
            return_value={"whatIfScenarioDescriptors": []},
        ) as execute_mock:
            result = fews_webservice_client_with_mock.get_whatifscenarios()

        assert result == {"whatIfScenarioDescriptors": []}
        execute_mock.assert_called_once_with(
            client=fews_webservice_client_with_mock.client,
            document_format="PI_JSON",
        )

    def test_post_whatifscenarios_with_mock(
        self, fews_webservice_client_with_mock: FewsWebServiceClient
    ):
        mock_response = {"id": "scenario-1", "name": "Python scenario"}

        with patch(
            "fews_py_wrapper.fews_webservices.PostWhatIfScenarios.execute",
            return_value=mock_response,
        ) as execute_mock:
            result = fews_webservice_client_with_mock.post_whatifscenarios(
                what_if_template_id="template-1",
                single_run_what_if=True,
                name="Python scenario",
            )

        assert result == mock_response
        execute_mock.assert_called_once_with(
            client=fews_webservice_client_with_mock.client,
            what_if_template_id="template-1",
            single_run_what_if=True,
            name="Python scenario",
            document_format="PI_JSON",
        )

    def test_post_whatifscenarios_omits_none_arguments(
        self, fews_webservice_client_with_mock: FewsWebServiceClient
    ):
        with patch(
            "fews_py_wrapper.fews_webservices.PostWhatIfScenarios.execute",
            return_value={"id": "scenario-1"},
        ) as execute_mock:
            result = fews_webservice_client_with_mock.post_whatifscenarios()

        assert result == {"id": "scenario-1"}
        execute_mock.assert_called_once_with(
            client=fews_webservice_client_with_mock.client,
            document_format="PI_JSON",
        )

    def test_get_filters_with_mock(
        self, fews_webservice_client_with_mock: FewsWebServiceClient
    ):
        """Test get_filters with mocked response."""
        mock_response = {
            "filters": [
                {
                    "id": "MEAS",
                    "name": "Measurements",
                }
            ]
        }

        with patch(
            "fews_py_wrapper._api.endpoints.Filters.execute",
            return_value=mock_response,
        ):
            result = fews_webservice_client_with_mock.get_filters()

        assert isinstance(result, dict)
        assert result["filters"][0]["id"] == "MEAS"
        assert result["filters"][0]["name"] == "Measurements"

    def test_get_filters_forwards_filter_id(
        self, fews_webservice_client_with_mock: FewsWebServiceClient
    ):
        """Test that get_filters forwards filter_id to the endpoint."""
        with patch(
            "fews_py_wrapper._api.endpoints.Filters.execute",
            return_value={"filters": []},
        ) as execute_mock:
            result = fews_webservice_client_with_mock.get_filters(filter_id="MEAS")

        assert result == {"filters": []}
        execute_mock.assert_called_once_with(
            client=fews_webservice_client_with_mock.client,
            filter_id="MEAS",
            document_format="PI_JSON",
        )

    def test_get_filters_forwards_optional_arguments(
        self, fews_webservice_client_with_mock: FewsWebServiceClient
    ):
        """Test that get_filters forwards all optional arguments."""
        with patch(
            "fews_py_wrapper._api.endpoints.Filters.execute",
            return_value={"filters": []},
        ) as execute_mock:
            result = fews_webservice_client_with_mock.get_filters(
                filter_id="MEAS",
                document_format="PI_XML",
                document_version="1.25",
            )

        assert result == {"filters": []}
        execute_mock.assert_called_once_with(
            client=fews_webservice_client_with_mock.client,
            filter_id="MEAS",
            document_format="PI_XML",
            document_version="1.25",
        )

    def test_get_filters_omits_none_arguments(
        self, fews_webservice_client_with_mock: FewsWebServiceClient
    ):
        """Test that get_filters omits None arguments from the endpoint call."""
        with patch(
            "fews_py_wrapper._api.endpoints.Filters.execute",
            return_value={"filters": []},
        ) as execute_mock:
            fews_webservice_client_with_mock.get_filters()

        execute_mock.assert_called_once_with(
            client=fews_webservice_client_with_mock.client,
            document_format="PI_JSON",
        )

    def test_get_taskruns_supports_minimal_workflow_only_call(
        self, fews_webservice_client_with_mock: FewsWebServiceClient
    ):
        with patch(
            "fews_py_wrapper._api.endpoints.Taskruns.execute",
            return_value={"taskRuns": []},
        ) as execute_mock:
            result = fews_webservice_client_with_mock.get_taskruns(
                workflow_id="RunParticleTracking"
            )

        assert result == {"taskRuns": []}
        execute_mock.assert_called_once_with(
            client=fews_webservice_client_with_mock.client,
            workflow_id="RunParticleTracking",
            document_format="PI_JSON",
        )

    def test_get_taskruns_forwards_optional_filters(
        self, fews_webservice_client_with_mock: FewsWebServiceClient
    ):
        with patch(
            "fews_py_wrapper._api.endpoints.Taskruns.execute",
            return_value={"taskRuns": []},
        ) as execute_mock:
            start_forecast_time = datetime(2025, 3, 14, 10, 0, 0, tzinfo=timezone.utc)
            end_forecast_time = datetime(2025, 3, 15, 0, 0, 0, tzinfo=timezone.utc)

            result = fews_webservice_client_with_mock.get_taskruns(
                workflow_id="RunParticleTracking",
                task_run_ids="SA5_1",
                topology_node_id="topology_node",
                forecast_count="5",
                scenario_id="scenario-1",
                mc_id="mc-1",
                start_forecast_time=start_forecast_time,
                end_forecast_time=end_forecast_time,
                task_run_status_ids="completed",
                only_forecasts=True,
                task_run_count="10",
                only_current=False,
                document_format="PI_XML",
                document_version="1.25",
            )

        assert result == {"taskRuns": []}
        execute_mock.assert_called_once_with(
            client=fews_webservice_client_with_mock.client,
            workflow_id="RunParticleTracking",
            task_run_ids=["SA5_1"],
            topology_node_id="topology_node",
            forecast_count="5",
            scenario_id="scenario-1",
            mc_id="mc-1",
            start_forecast_time=start_forecast_time,
            end_forecast_time=end_forecast_time,
            task_run_status_ids=["completed"],
            only_forecasts=True,
            task_run_count="10",
            only_current=False,
            document_format="PI_XML",
            document_version="1.25",
        )
