from datetime import datetime
import xarray as xr

from fews_openapi_py_client import Client, AuthenticatedClient
from fews_openapi_py_client.api.timeseries import timeseries
from fews_openapi_py_client.api.tasks import taskrunstatus
from fews_py_wrapper.utils import (
    format_datetime,
    convert_timeseries_response_to_dataframe,
)


class FewsWebServiceClient:
    """Client for interacting with FEWS web services."""

    def __init__(
        self,
        base_url: str,
        authenticate: bool = False,
        token: str | None = None,
    ) -> None:
        self.base_url = base_url
        if authenticate:
            self.authenticate(token)
        else:
            self.client = Client(base_url=base_url)

    def authenticate(self, token: str) -> None:
        """Authenticate with the FEWS web services."""
        self.client = AuthenticatedClient(base_url=self.base_url, token=token)

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

    def get_taskrun_status(self, task_id: str) -> dict:
        """Get the status of a task run in the FEWS web services."""
        response = taskrunstatus.sync_detailed(
            client=self.client,
            task_id=task_id,
        )
        return response.content

    def execute_workflow(self, *args, **kwargs):
        """Execute a workflow in the FEWS web services."""
        pass

    def execute_whatif_scenario(self, *args, **kwargs):
        """Execute a what-if scenario in the FEWS web services."""
        pass
