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

    def test_get_timeseries(
        self, fews_webservice_client: FewsWebServiceClient
    ):
        start_time = datetime(2025, 3, 13, 19, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 3, 15, 0, 0, 0, tzinfo=timezone.utc)
        pass

    def test_get_taskrun(
        self, fews_webservice_client: FewsWebServiceClient
    ):
        task_id = "SA5_1"
        task = fews_webservice_client.get_taskrun(
            workflow_id="RunParticleTracking", task_ids=task_id
        )
        assert isinstance(task, dict)
        assert task["taskRuns"][0]["id"] == task_id
        assert task["taskRuns"][0]["status"] == "pending"
