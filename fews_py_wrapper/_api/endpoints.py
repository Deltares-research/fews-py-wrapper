from fews_openapi_py_client import AuthenticatedClient, Client
from fews_openapi_py_client.api.tasks import taskruns
from fews_openapi_py_client.api.timeseries import timeseries

from fews_py_wrapper._api.base import ApiEndpoint
from fews_py_wrapper.utils import format_datetime


class Taskruns(ApiEndpoint):
    api_call_function = taskruns.sync_detailed

    def get(self, client: AuthenticatedClient | Client, **kwargs) -> dict:
        kwargs = self.update_api_call_kwargs(kwargs)
        return super().get(client, **kwargs)


class TimeSeries(ApiEndpoint):
    api_call_function = timeseries.sync_detailed

    def get(self, client: AuthenticatedClient | Client, **kwargs) -> dict:
        kwargs = self.update_api_call_kwargs(kwargs)
        kwargs = self._format_time_args(kwargs)
        return super().get(client, **kwargs)

    def _format_time_args(self, kwargs: dict) -> dict:
        time_args = [
            "start_time",
            "end_time",
            "start_creation_time",
            "end_creation_time",
            "start_forecast_time",
            "end_forecast_time",
        ]
        for arg in time_args:
            if arg in kwargs and kwargs[arg] is not None:
                kwargs[arg] = format_datetime(kwargs[arg])
        return kwargs
