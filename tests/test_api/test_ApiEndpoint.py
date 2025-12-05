import json
from unittest import TestCase
from unittest.mock import Mock

import httpx
import pytest
import requests

from fews_py_wrapper._api.base import ApiEndpoint


class TestApiEndpoint(TestCase):
    def mock_api_call_function(self, client, status_code=200, **kwargs):
        mock_response = httpx.Response(
            status_code=status_code,
            content=json.dumps({"taskruns": []}).encode(),
            headers={"content-type": "application/json"},
        )
        mock_response.raise_for_status = Mock(side_effect=requests.HTTPError)
        return mock_response

    @pytest.fixture
    def mock_api_endpoint(self):
        endpoint = ApiEndpoint()
        endpoint.api_call_function = self.mock_api_call_function
        return endpoint

    def test_get_method(self, mock_api_endpoint):
        client = Mock()  # Mock client
        response = mock_api_endpoint.get(client, workflow_id="test", task_ids=["task1"])
        self.assertEqual(response, {"taskruns": []})

        with pytest.raises(requests.HTTPError):
            mock_api_endpoint.get(
                client, workflow_id="test", task_ids=["task1"], status_code=404
            )
