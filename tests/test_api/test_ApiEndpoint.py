import json
from enum import Enum
from typing import Any
from unittest.mock import Mock

import httpx
import pytest
import requests
from fews_openapi_py_client.client import AuthenticatedClient, Client
from fews_openapi_py_client.types import UNSET, Unset

from fews_py_wrapper._api.base import ApiEndpoint


class TestEnum(str, Enum):
    FALSE = "false"
    TRUE = "true"

    def __str__(self) -> str:
        return str(self.value)


def mock_endpoint_function(
    *,
    client: Client | AuthenticatedClient,
    test_enum: TestEnum | Unset = UNSET,
    status_code: int | None = None,
    response_content: Any = None,
    content_type: str = "application/json",
    **kwargs,
):
    if isinstance(response_content, bytes):
        content = response_content
    elif response_content is None:
        content = json.dumps({"taskruns": []}).encode()
    elif content_type.endswith("json"):
        content = json.dumps(response_content).encode()
    else:
        content = str(response_content).encode()

    mock_response = httpx.Response(
        status_code=status_code,
        content=content,
        headers={"content-type": content_type},
    )
    mock_response.raise_for_status = Mock(side_effect=requests.HTTPError)
    return mock_response


class MockEndpoint(ApiEndpoint):
    endpoint_function = staticmethod(mock_endpoint_function)


@pytest.fixture
def mock_api_endpoint() -> MockEndpoint:
    return MockEndpoint()


def test_execute_method(mock_api_endpoint):
    client = Mock()  # Mock client
    response = mock_api_endpoint.execute(
        client=client, workflow_id="test", task_ids=["task1"], status_code=200
    )
    assert response == {"taskruns": []}

    with pytest.raises(requests.HTTPError):
        mock_api_endpoint.execute(
            client=client, workflow_id="test", task_ids=["task1"], status_code=404
        )

    binary_response = mock_api_endpoint.execute(
        client=client,
        workflow_id="test",
        task_ids=["task1"],
        status_code=200,
        response_content=b"netcdf-bytes",
        content_type="application/octet-stream",
    )
    assert isinstance(binary_response, bytes)
    assert binary_response == b"netcdf-bytes"

    xml_response = mock_api_endpoint.execute(
        client=client,
        workflow_id="test",
        task_ids=["task1"],
        status_code=200,
        response_content="<TimeSeries />",
        content_type="application/xml",
    )
    assert xml_response == "<TimeSeries />"


class MockPartialContentEndpoint(MockEndpoint):
    success_status_codes = frozenset({200, 206})


def test_execute_allows_partial_content_for_configured_endpoints():
    client = Mock()
    endpoint = MockPartialContentEndpoint()

    response = endpoint.execute(
        client=client,
        status_code=206,
        response_content={"timeSeries": []},
        content_type="application/json",
    )

    assert response == {"timeSeries": []}


def test_input_args(mock_api_endpoint):
    arg_names = mock_api_endpoint.input_args()
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
