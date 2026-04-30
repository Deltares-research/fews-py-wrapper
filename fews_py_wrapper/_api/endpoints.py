from datetime import datetime
from typing import Any, cast

from fews_openapi_py_client import AuthenticatedClient, Client
from fews_openapi_py_client.api.filters import filters
from fews_openapi_py_client.api.locations import locations
from fews_openapi_py_client.api.parameters import parameters
from fews_openapi_py_client.api.timeseries import posttimeseries, timeseries
from fews_openapi_py_client.api.workflows import workflows
from fews_openapi_py_client.models.posttimeseries_body import PosttimeseriesBody

from fews_py_wrapper._api.base import ApiEndpoint
from fews_py_wrapper.utils import format_datetime

__all__ = [
    "Filters",
    "Parameters",
    "Locations",
    "TimeSeries",
    "PostTimeSeries",
    "Workflows",
]


class Filters(ApiEndpoint):
    endpoint_function = staticmethod(filters.sync_detailed)

    def execute(
        self,
        *,
        client: AuthenticatedClient | Client,
        **kwargs: Any,
    ) -> dict[str, Any] | str:
        kwargs = self.update_input_kwargs(kwargs)
        return cast(dict[str, Any] | str, super().execute(client=client, **kwargs))


class Parameters(ApiEndpoint):
    endpoint_function = staticmethod(parameters.sync_detailed)

    def execute(
        self, *, client: AuthenticatedClient | Client, **kwargs: Any
    ) -> dict[str, Any]:
        kwargs = self.update_input_kwargs(kwargs)
        return cast(dict[str, Any], super().execute(client=client, **kwargs))


class Locations(ApiEndpoint):
    endpoint_function = staticmethod(locations.sync_detailed)

    def execute(
        self, *, client: AuthenticatedClient | Client, **kwargs: Any
    ) -> dict[str, Any]:
        kwargs = self.update_input_kwargs(kwargs)
        return cast(dict[str, Any], super().execute(client=client, **kwargs))


class TimeSeries(ApiEndpoint):
    endpoint_function = staticmethod(timeseries.sync_detailed)
    success_status_codes = frozenset({200, 206})

    def execute(
        self, *, client: AuthenticatedClient | Client, **kwargs: Any
    ) -> dict[str, Any] | bytes | str:
        kwargs = self.update_input_kwargs(kwargs)
        kwargs = self._format_time_args(kwargs)
        return cast(
            dict[str, Any] | bytes | str, super().execute(client=client, **kwargs)
        )

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


class PostTimeSeries(ApiEndpoint):
    endpoint_function = staticmethod(posttimeseries.sync_detailed)

    def execute(
        self, *, client: AuthenticatedClient | Client, **kwargs: Any
    ) -> dict[str, Any] | bytes | str:
        kwargs = self._prepare_body(kwargs)
        body = kwargs.pop("body", None)
        kwargs = self.update_input_kwargs(kwargs)
        if body is not None:
            kwargs["body"] = body
        return cast(
            dict[str, Any] | bytes | str,
            super().execute(client=client, **kwargs),
        )

    def _prepare_body(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        body = kwargs.get("body")
        if body is None:
            return kwargs
        if isinstance(body, dict):
            kwargs["body"] = PosttimeseriesBody.from_dict(body)
            return kwargs
        if isinstance(body, PosttimeseriesBody):
            return kwargs
        raise ValueError(
            "Invalid argument value for body: Expected PosttimeseriesBody or dict, "
            f"got {type(body)}"
        )


class Workflows(ApiEndpoint):
    endpoint_function = staticmethod(workflows.sync_detailed)

    def execute(
        self,
        *,
        client: AuthenticatedClient | Client,
        **kwargs: Any,
    ) -> dict[str, Any] | str:
        kwargs = self.update_input_kwargs(kwargs)
        return cast(dict[str, Any] | str, super().execute(client=client, **kwargs))
