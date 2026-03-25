import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import dotenv
import pytest
import xarray as xr
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

    def test_get_timeseries_json_to_xarray(
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
            to_xarray=True,
            module_instance_ids=["HydraulicPCSWMMFC_South_Toti_Simplified"],
        )
        assert isinstance(timeseries_json, xr.Dataset)

    def test_get_timeseries_json_and_netcdf(
        self, fews_webservice_client: FewsWebServiceClient
    ):
        start_time = datetime(2025, 3, 14, 10, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 3, 14, 12, 0, 0, tzinfo=timezone.utc)
        parameter_ids = ["H_simulated"]
        location_ids = ["Amanzimtoti_River_level", "Amanzimtoti_River_Mouth_level"]
        timeseries_json = fews_webservice_client.get_timeseries(
            start_time=start_time,
            end_time=end_time,
            parameter_ids=parameter_ids,
            location_ids=location_ids,
            document_format="PI_JSON",
            to_xarray=True,
        )
        timeseries_netcdf = fews_webservice_client.get_timeseries(
            start_time=start_time,
            end_time=end_time,
            parameter_ids=parameter_ids,
            location_ids=location_ids,
        )
        assert isinstance(timeseries_json, xr.Dataset)
        assert isinstance(timeseries_netcdf, xr.Dataset)
        xr.testing.assert_identical(timeseries_json, timeseries_netcdf)

    # TODO: Failing test, to be fixed later (GitHub issue #7)
    # def test_get_taskruns(self, fews_webservice_client: FewsWebServiceClient):
    #     task_id = "SA5_1"
    #     task = fews_webservice_client.get_taskruns(
    #         workflow_id="RunParticleTracking",
    #         task_ids=task_id,
    #     )
    #     assert isinstance(task, dict)

    def test_endpoint_arguments(self, fews_webservice_client: FewsWebServiceClient):
        # This test checks that invalid arguments raise a ValueError
        input_args = fews_webservice_client.endpoint_arguments("timeseries")
        assert "location_ids" in input_args
        with pytest.raises(ValueError, match="Unknown endpoint: invalid_endpoint"):
            fews_webservice_client.endpoint_arguments("invalid_endpoint")

    def test_get_workflows(self, fews_webservice_client: FewsWebServiceClient):
        all_workflows = fews_webservice_client.get_workflows()
        assert isinstance(all_workflows, dict)
        assert len(all_workflows["workflows"]) > 1


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

    def test_get_timeseries_defaults_to_netcdf_xarray(
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

        assert isinstance(result, xr.Dataset)
        assert list(result.data_vars) == ["H_obs"]
        assert result["H_obs"].values.tolist() == [1.1, 1.2, 1.3]
        assert result["H_obs"].attrs == {
            "location_id": "timeseries",
            "parameter_id": "H_obs",
            "time_step_unit": "second",
            "time_step_multiplier": 3600,
        }

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

    def test_get_timeseries_rejects_to_xarray_for_non_pi_json(
        self,
        fews_webservice_client_with_mock: FewsWebServiceClient,
    ):
        with patch(
            "fews_py_wrapper._api.endpoints.TimeSeries.execute",
            return_value='<TimeSeries version="1.34" />',
        ):
            with pytest.raises(
                ValueError, match="to_xarray=True is only supported with PI_JSON"
            ):
                fews_webservice_client_with_mock.get_timeseries(
                    document_format="PI_XML",
                    to_xarray=True,
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
                workflow_id="RunParticleTracking", task_ids="SA5_1"
            )

            # Assert
            assert isinstance(result, dict)
            assert result["taskRuns"][0]["id"] == "SA5_1"
            assert result["taskRuns"][0]["status"] == "pending"
