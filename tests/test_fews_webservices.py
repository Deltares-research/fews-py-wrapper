import os
from datetime import datetime, timezone

import dotenv
import pytest

from fews_py_wrapper.fews_webservices import FewsWebServiceClient

dotenv.load_dotenv()


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

    def test_get_taskrun(self, fews_webservice_client: FewsWebServiceClient):
        task_id = "SA5_1"
        task = fews_webservice_client.get_taskrun(
            workflow_id="RunParticleTracking", task_ids=task_id
        )
        assert isinstance(task, dict)
        assert task["taskRuns"][0]["id"] == task_id
        assert task["taskRuns"][0]["status"] == "pending"

    def test_endpoint_arguments(self, fews_webservice_client: FewsWebServiceClient):
        # This test checks that invalid arguments raise a ValueError
        input_args = fews_webservice_client.endpoint_arguments("timeseries")
        assert "location_ids" in input_args
        with pytest.raises(ValueError, match="Unknown endpoint: invalid_endpoint"):
            fews_webservice_client.endpoint_arguments("invalid_endpoint")

    def test__validate_input_kwargs(self, fews_webservice_client: FewsWebServiceClient):
        # This test checks that invalid kwargs raise a ValueError
        with pytest.raises(ValueError, match="Invalid argument: invalid_arg"):
            fews_webservice_client.get_timeseries(invalid_arg="invalid_value")
