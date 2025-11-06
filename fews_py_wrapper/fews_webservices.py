import json
from datetime import datetime

import xarray as xr
from fews_openapi_py_client import AuthenticatedClient, Client
from fews_openapi_py_client.api.tasks import taskruns
from fews_openapi_py_client.api.timeseries import timeseries
from fews_openapi_py_client.api.whatif import post_what_if_scenarios

from fews_py_wrapper.utils import (
    convert_timeseries_response_to_dataframe,
    format_datetime,
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
        locationd_ids: list[str] | None = None,
        parameter_ids: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        as_dataframe: bool = False,
    ) -> xr.Dataset:
        """Get time series data from the FEWS web services."""
        if start_time:
            start_time = format_datetime(start_time)
        if end_time:
            end_time = format_datetime(end_time)
        response = timeseries.sync_detailed(
            client=self.client,
            locationd_ids=locationd_ids,
            parameter_ids=parameter_ids,
            start_time=start_time,
            end_time=end_time,
        )

        if as_dataframe:
            return convert_timeseries_response_to_dataframe(response.content)

    def get_taskrun(
        self, workflow_id: str, task_ids: list[str] | str
    ) -> dict:
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
