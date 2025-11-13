import json
from datetime import datetime

import xarray as xr
from fews_openapi_py_client import AuthenticatedClient, Client
from fews_openapi_py_client.api.tasks import taskruns
from fews_openapi_py_client.api.timeseries import timeseries
from fews_openapi_py_client.api.whatif import post_what_if_scenarios

from fews_py_wrapper.utils import (
    convert_timeseries_response_to_dataframe,
    format_time_args,
    get_function_arg_names,
)


class FewsWebServiceClient:
    """Client for interacting with FEWS web services."""

    def __init__(
        self,
        base_url: str,
        authenticate: bool = False,
        token: str | None = None,
        verify_ssl: bool = True,
    ) -> None:
        self.base_url = base_url
        if authenticate:
            self.authenticate(token, verify_ssl)
        else:
            self.client = Client(base_url=base_url, verify_ssl=verify_ssl)

    def authenticate(self, token: str, verify_ssl: bool) -> None:
        """Authenticate with the FEWS web services."""
        self.client = AuthenticatedClient(
            base_url=self.base_url, token=token, verify_ssl=verify_ssl
        )

    def get_timeseries(
        self,
        *,
        location_ids: list[str] | None = None,
        parameter_ids: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        as_dataframe: bool = False,
        start_creation_time: datetime | None = None,
        end_creation_time: datetime | None = None,
        start_forecast_time: datetime | None = None,
        end_forecast_time: datetime | None = None,
        document_format: str | None = None,
        **kwargs,
    ) -> xr.Dataset:
        """Get time series data from the FEWS web services."""
        # Validate passed kwargs if they match function signature
        self._validate_input_kwargs(timeseries.sync_detailed, kwargs)

        # Format datetime arguments to strings
        (
            start_time,
            end_time,
            start_creation_time,
            end_creation_time,
            start_forecast_time,
            end_forecast_time,
        ) = format_time_args(
            start_time,
            end_time,
            start_creation_time,
            end_creation_time,
            start_forecast_time,
            end_forecast_time,
        )

        # Collect only non-None keyword arguments
        non_none_kwargs = self._collect_non_none_kwargs(
            local_kwargs=locals().copy(), pop_kwargs=["as_dataframe"]
        )
        response = timeseries.sync_detailed(
            client=self.client,
            **non_none_kwargs,
        )

        if response.status_code != 200:
            response.raise_for_status()
        content = json.loads(response.content.decode("utf-8"))
        if as_dataframe:
            return convert_timeseries_response_to_dataframe(content)
        return content

    def get_taskrun(self, workflow_id: str, task_ids: list[str] | str) -> dict:
        """Get the status of a task run in the FEWS web services."""
        if isinstance(task_ids, str):
            task_ids = [task_ids]
        response = taskruns.sync_detailed(
            client=self.client,
            workflow_id=workflow_id,
            task_run_ids=task_ids,
            document_format="PI_JSON",
        )
        if response.status_code == 200:
            return json.loads(response.content.decode("utf-8"))
        else:
            response.raise_for_status()

    def execute_workflow(self, *args, **kwargs):
        """Execute a workflow in the FEWS web services."""
        pass

    def execute_whatif_scenario(
        self,
        what_if_template_id: str | None = None,
        single_run_what_if: str | None = None,
        name: str | None = None,
        document_format: str | None = None,
        document_version: str | None = None,
    ):
        """Execute a what-if scenario in the FEWS web services."""
        response = post_what_if_scenarios.sync_detailed(
            client=self.client,
            what_if_template_id=what_if_template_id,
            single_run_what_if=single_run_what_if,
            name=name,
            document_format=document_format,
            document_version=document_version,
        )
        return response.content

    def endpoint_arguments(self, endpoint: str) -> dict:
        """Get the arguments for a specific FEWS web service endpoint."""
        if endpoint == "timeseries":
            return get_function_arg_names(timeseries.sync_detailed)
        elif endpoint == "taskruns":
            return get_function_arg_names(taskruns.sync_detailed)
        elif endpoint == "whatif_scenarios":
            return get_function_arg_names(post_what_if_scenarios.sync_detailed)
        else:
            raise ValueError(f"Unknown endpoint: {endpoint}")

    def _validate_input_kwargs(self, func, kwargs: dict) -> None:
        """Validate input kwargs against function signature."""
        valid_arg_names = get_function_arg_names(func)
        for key in list(kwargs.keys()):
            if key not in valid_arg_names:
                raise ValueError(
                    f"Invalid argument: {key}, valid arguments are: {valid_arg_names}"
                )

    def _collect_non_none_kwargs(
        self, local_kwargs: dict, pop_kwargs: list[str]
    ) -> dict:
        """Collect only non-None keyword arguments."""
        local_kwargs.pop("self", None)
        for key in pop_kwargs:
            local_kwargs.pop(key, None)
        if "kwargs" in local_kwargs:
            local_kwargs.update(local_kwargs.pop("kwargs"))
        return {k: v for k, v in local_kwargs.items() if v is not None}
