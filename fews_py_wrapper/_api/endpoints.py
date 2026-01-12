from datetime import datetime

from fews_openapi_py_client import AuthenticatedClient, Client
from fews_openapi_py_client.api.tasks import taskruns
from fews_openapi_py_client.api.timeseries import timeseries
from fews_openapi_py_client.api.whatif import post_what_if_scenarios

from fews_py_wrapper._api.base import ApiEndpoint
from fews_py_wrapper.utils import format_datetime


class Taskruns(ApiEndpoint):
    endpoint_function = staticmethod(taskruns.sync_detailed)

    def execute(
        self,
        client: AuthenticatedClient | Client,
        **kwargs,
    ) -> dict:
        kwargs = self.update_input_kwargs(kwargs)
        return super().execute(client, **kwargs)


class TimeSeries(ApiEndpoint):
    endpoint_function = staticmethod(timeseries.sync_detailed)

    def execute(self, *, client: AuthenticatedClient | Client, **kwargs) -> dict:
        kwargs = self.update_input_kwargs(kwargs)
        kwargs = self._format_time_args(kwargs)
        return super().execute(client=client, **kwargs)

    def _format_time_args(self, kwargs: dict[datetime]) -> dict:
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
                if not isinstance(kwargs[arg], datetime):
                    arg_type = type(kwargs[arg])
                    raise ValueError(
                        f"Invalid argument value for {arg}: Expected datetime,"
                        f" got {arg_type}"
                    )
                kwargs[arg] = format_datetime(kwargs[arg])
        return kwargs


class WhatIfScenarios(ApiEndpoint):
    endpoint_function = staticmethod(post_what_if_scenarios.sync_detailed)

    def execute(self, client: AuthenticatedClient | Client, **kwargs) -> dict:
        kwargs = self.update_input_kwargs(kwargs)
        return super().execute(client, **kwargs)
