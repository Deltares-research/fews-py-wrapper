import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import dotenv
import pytest

from fews_py_wrapper.fews_webservices import FewsWebServiceClient

dotenv.load_dotenv()


@pytest.mark.integration
class TestFewsWebServiceClient:
    @pytest.fixture
    def fews_webservice_client(self) -> FewsWebServiceClient:
        if os.getenv("FEWS_API_URL") is not None:
            return FewsWebServiceClient(
                base_url=os.getenv("FEWS_API_URL"), verify_ssl=False
            )  # Only for testing!

    def test_get_timeseries(self, fews_webservice_client: FewsWebServiceClient):
        start_time = datetime(2025, 3, 14, 10, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 3, 15, 0, 0, 0, tzinfo=timezone.utc)
        timeseries = fews_webservice_client.get_timeseries(
            start_time=start_time,
            end_time=end_time,
            parameter_ids=["H.obs"],
            location_ids=["Amanzimtoti_River_level", "Amanzimtoti_River_Mouth_level"],
            document_format="PI_JSON",
        )
        assert timeseries

    def test_get_taskruns(self, fews_webservice_client: FewsWebServiceClient):
        task_id = "SA5_1"
        task = fews_webservice_client.get_taskruns(
            workflow_id="RunParticleTracking",
            task_ids=task_id,
        )
        assert isinstance(task, dict)

    def test_endpoint_arguments(self, fews_webservice_client: FewsWebServiceClient):
        # This test checks that invalid arguments raise a ValueError
        input_args = fews_webservice_client.endpoint_arguments("timeseries")
        assert "location_ids" in input_args
        with pytest.raises(ValueError, match="Unknown endpoint: invalid_endpoint"):
            fews_webservice_client.endpoint_arguments("invalid_endpoint")


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
