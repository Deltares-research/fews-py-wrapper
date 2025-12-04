from datetime import datetime

from fews_openapi_py_client.api.timeseries.timeseries import sync_detailed

from fews_py_wrapper.utils import format_time_args, update_api_call_kwargs


def retrieve_timeseries(
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    start_creation_time: datetime | None = None,
    end_creation_time: datetime | None = None,
    start_forecast_time: datetime | None = None,
    end_forecast_time: datetime | None = None,
    **kwargs,
) -> dict:
    # Format datetime arguments to strings
    format_time_args(
        start_time,
        end_time,
        start_creation_time,
        end_creation_time,
        start_forecast_time,
        end_forecast_time,
    )
    kwargs = update_api_call_kwargs(kwargs, sync_detailed)
    response = sync_detailed(
        start_time=start_time,
        end_time=end_time,
        start_creation_time=start_creation_time,
        end_creation_time=end_creation_time,
        start_forecast_time=start_forecast_time,
        end_forecast_time=end_forecast_time,
        **kwargs,
    )
    if response.status_code != 200:
        response.raise_for_status()
    return response.json()
