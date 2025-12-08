import json
from enum import Enum
from unittest.mock import Mock

import httpx
import pytest
import requests
from fews_openapi_py_client.types import Unset

from fews_py_wrapper._api.base import ApiEndpoint


class TestEnum(str, Enum):
    FALSE = "false"
    TRUE = "true"

    def __str__(self) -> str:
        return str(self.value)


def mock_endpoint_function(
    client,
    test_enum: TestEnum | Unset = TestEnum.FALSE,
    status_code: int = 200,
    **kwargs,
):
    mock_response = httpx.Response(
        status_code=status_code,
        content=json.dumps({"taskruns": []}).encode(),
        headers={"content-type": "application/json"},
    )
    mock_response.raise_for_status = Mock(side_effect=requests.HTTPError)
    return mock_response


@pytest.fixture
def mock_api_endpoint():
    endpoint = ApiEndpoint()
    endpoint.endpoint_function = mock_endpoint_function
    return endpoint


def test_execute_method(mock_api_endpoint):
    client = Mock()  # Mock client
    response = mock_api_endpoint.execute(client, workflow_id="test", task_ids=["task1"])
    assert response == {"taskruns": []}

    with pytest.raises(requests.HTTPError):
        mock_api_endpoint.execute(
            client, workflow_id="test", task_ids=["task1"], status_code=404
        )


def test_input_args(mock_api_endpoint):
    arg_names = mock_api_endpoint.input_args()
    assert "client" in arg_names
    assert "test_enum" in arg_names
    assert "status_code" in arg_names


def test_update_input_kwargs(mock_api_endpoint):
    kwargs = {"test_enum": True, "extra_param": 123}
    updated_kwargs = mock_api_endpoint.update_input_kwargs(kwargs)
    assert updated_kwargs["test_enum"] == TestEnum.TRUE
    assert updated_kwargs["extra_param"] == 123


def test_update_api_input_kwargs_invalid_enum(mock_api_endpoint):
    kwargs = {"test_enum": "invalid_value"}
    with pytest.raises(
        ValueError,
        match="Invalid argument value: Expected boolean value, got invalid_value",
    ):
        mock_api_endpoint.update_input_kwargs(kwargs)


def test_contains_types(mock_api_endpoint):
    assert mock_api_endpoint._contains_types((int, str, float), (str, float)) is True
    assert mock_api_endpoint._contains_types((int, bool), (str, float)) is False
    assert mock_api_endpoint._contains_types((list[str, float]), (str, float)) is True


def test_convert_bools(mock_api_endpoint):
    assert mock_api_endpoint._convert_bools(True) == "true"
    assert mock_api_endpoint._convert_bools(False) == "false"
    with pytest.raises(ValueError, match="Expected boolean value, got 123"):
        mock_api_endpoint._convert_bools(123)
