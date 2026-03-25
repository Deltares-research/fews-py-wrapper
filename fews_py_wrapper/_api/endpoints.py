from datetime import datetime
from typing import Any

from fews_openapi_py_client import AuthenticatedClient, Client
from fews_openapi_py_client.api.locations import locations
from fews_openapi_py_client.api.parameters import parameters
from fews_openapi_py_client.api.tasks import taskruns
from fews_openapi_py_client.api.timeseries import timeseries
from fews_openapi_py_client.api.whatif import post_what_if_scenarios
from fews_openapi_py_client.api.workflows import workflows

from fews_py_wrapper._api.base import ApiEndpoint
from fews_py_wrapper.utils import format_datetime

__all__ = [
    "Taskruns",
    "Parameters",
    "Locations",
    "TimeSeries",
    "WhatIfScenarios",
    "Workflows",
]


class Taskruns(ApiEndpoint):
    endpoint_function = staticmethod(taskruns.sync_detailed)

    def execute(
        self,
        *,
        client: AuthenticatedClient | Client,
        **kwargs: Any,
    ) -> dict[str, Any]:
        kwargs = self.update_input_kwargs(kwargs)
        return super().execute(client=client, **kwargs)


class Parameters(ApiEndpoint):
    endpoint_function = staticmethod(parameters.sync_detailed)

    def execute(
        self, *, client: AuthenticatedClient | Client, **kwargs: Any
    ) -> dict[str, Any]:
        kwargs = self.update_input_kwargs(kwargs)
        return super().execute(client=client, **kwargs)


class Locations(ApiEndpoint):
    endpoint_function = staticmethod(locations.sync_detailed)

    def execute(
        self, *, client: AuthenticatedClient | Client, **kwargs: Any
    ) -> dict[str, Any]:
        kwargs = self.update_input_kwargs(kwargs)
        return super().execute(client=client, **kwargs)


class TimeSeries(ApiEndpoint):
    endpoint_function = staticmethod(timeseries.sync_detailed)
    success_status_codes = frozenset({200, 206})

    def execute(
        self, *, client: AuthenticatedClient | Client, **kwargs: Any
    ) -> dict[str, Any] | bytes | str:
        kwargs = self.update_input_kwargs(kwargs)
        kwargs = self._format_time_args(kwargs)
        return super().execute(client=client, **kwargs)

    def _format_time_args(self, kwargs: dict[str, Any]) -> dict[str, Any]:
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

        if (
            "external_forecast_times" in kwargs
            and kwargs["external_forecast_times"] is not None
        ):
            external_forecast_times = kwargs["external_forecast_times"]
            if not isinstance(external_forecast_times, list):
                arg_type = type(external_forecast_times)
                raise ValueError(
                    "Invalid argument value for external_forecast_times: Expected list,"
                    f" got {arg_type}"
                )

            formatted_external_forecast_times: list[str] = []
            for external_forecast_time in external_forecast_times:
                if isinstance(external_forecast_time, datetime):
                    formatted_external_forecast_times.append(
                        format_datetime(external_forecast_time)
                    )
                    continue
                if isinstance(external_forecast_time, str):
                    formatted_external_forecast_times.append(external_forecast_time)
                    continue

                arg_type = type(external_forecast_time)
                raise ValueError(
                    "Invalid argument value for external_forecast_times: Expected"
                    f" datetime or str items, got {arg_type}"
                )

            kwargs["external_forecast_times"] = formatted_external_forecast_times
        return kwargs


class WhatIfScenarios(ApiEndpoint):
    endpoint_function = staticmethod(post_what_if_scenarios.sync_detailed)

    def execute(
        self, *, client: AuthenticatedClient | Client, **kwargs: Any
    ) -> dict[str, Any]:
        kwargs = self.update_input_kwargs(kwargs)
        return super().execute(client=client, **kwargs)


class Workflows(ApiEndpoint):
    endpoint_function = staticmethod(workflows.sync_detailed)

    def execute(
        self,
        *,
        client: AuthenticatedClient | Client,
        **kwargs: Any,
    ) -> dict[str, Any]:
        kwargs = self.update_input_kwargs(kwargs)
        return super().execute(client=client, **kwargs)
