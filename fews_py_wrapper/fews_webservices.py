from datetime import datetime
from typing import Any

import xarray as xr
from fews_openapi_py_client import AuthenticatedClient, Client

from fews_py_wrapper._api import (
    Filters,
    Locations,
    Parameters,
    Taskruns,
    TimeSeries,
    WhatIfScenarios,
    Workflows,
)
from fews_py_wrapper.models import PiLocationsResponse, PiParametersResponse
from fews_py_wrapper.utils import (
    convert_netcdf_zip_response_to_xarray,
    convert_timeseries_response_to_xarray,
    normalize_netcdf_response_to_timeseries_xarray,
)

__all__ = ["FewsWebServiceClient"]

PI_TIMESERIES_DOCUMENT_FORMATS = frozenset({"PI_JSON", "PI_XML", "PI_CSV", "PI_NETCDF"})
PI_NETCDF_XARRAY_TYPES = frozenset({"grid", "flat"})


class FewsWebServiceClient:
    """Client for interacting with FEWS web services."""

    client: Client | AuthenticatedClient

    def __init__(
        self,
        base_url: str,
        authenticate: bool = False,
        token: str | None = None,
        verify_ssl: bool = True,
    ) -> None:
        self.base_url = base_url
        if authenticate:
            if not token:
                raise ValueError("Token must be provided for authentication.")
            self.authenticate(token, verify_ssl)
        else:
            self.client = Client(base_url=base_url, verify_ssl=verify_ssl)

    def authenticate(self, token: str, verify_ssl: bool) -> None:
        """Authenticate with the FEWS web services."""
        self.client = AuthenticatedClient(
            base_url=self.base_url, token=token, verify_ssl=verify_ssl
        )

    def get_locations(self) -> PiLocationsResponse:
        """Get locations from the FEWS web services as a typed PI model.

        Returns:
            A validated PI locations response containing location identifiers,
            coordinates, names, and optional relations or attributes.

        Example:
            ::

                client = FewsWebServiceClient(
                    base_url="https://example.com/FewsWebServices/rest"
                )

                locations = client.get_locations()
                first_location = locations.locations[0]

                print(first_location.location_id)
                print(first_location.lat, first_location.lon)
        """
        content = Locations().execute(client=self.client, document_format="PI_JSON")
        return PiLocationsResponse.model_validate(content)

    def get_parameters(self) -> PiParametersResponse:
        """Get parameters from the FEWS web services as a typed PI model.

        Returns:
            A validated PI parameters response containing parameter metadata such
            as parameter IDs, units, parameter type, and optional attributes.

        Example:
            ::

                client = FewsWebServiceClient(
                    base_url="https://example.com/FewsWebServices/rest"
                )

                parameters = client.get_parameters()
                first_parameter = parameters.parameters[0]

                print(first_parameter.id)
                print(first_parameter.unit)
        """
        content = Parameters().execute(client=self.client, document_format="PI_JSON")
        return PiParametersResponse.model_validate(content)

    def get_timeseries(
        self,
        *,
        location_ids: list[str] | None = None,
        parameter_ids: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        to_xarray: bool | None = None,
        document_format: str | None = "PI_NETCDF",
        xarray_type: str = "flat",
        **kwargs: Any,
    ) -> xr.Dataset | dict[str, Any] | str | bytes:
        """Get time series data from the FEWS web services.

        Args:
            location_ids: One or more FEWS location identifiers.
            parameter_ids: One or more FEWS parameter identifiers.
            start_time: Inclusive start timestamp. Must be timezone-aware.
            end_time: Inclusive end timestamp. Must be timezone-aware.
            to_xarray: Optional conversion flag for ``PI_JSON`` responses.
                ``PI_NETCDF`` responses are always returned as an
                ``xarray.Dataset``.
            document_format: FEWS PI response format. Supported values are
                ``PI_JSON``, ``PI_XML``, ``PI_CSV`` and ``PI_NETCDF``.
                Defaults to ``PI_NETCDF``.
            xarray_type: NetCDF-specific xarray representation. Supported values
                are ``"flat"`` and ``"grid"``.
                ``"flat"`` normalizes NetCDF to the same
                one-series-per-variable structure used by PI_JSON conversion.
                ``"grid"`` preserves the original NetCDF/xarray
                layout as closely as possible. Ignored for non-NetCDF formats.
            **kwargs: Additional endpoint arguments accepted by the underlying
                FEWS time series endpoint.

        Returns:
            An ``xarray.Dataset`` for ``PI_NETCDF`` responses, using the
            requested NetCDF representation; an ``xarray.Dataset`` for
            ``PI_JSON`` when ``to_xarray=True`` is requested; a dictionary for
            ``PI_JSON``; or a string for ``PI_XML`` and ``PI_CSV``.

        Example:
            Request time series as normalized NetCDF time series xarray. The ZIP
            payload returned by FEWS is unpacked automatically and returned as
            an ``xarray.Dataset``.

            ::

                from datetime import datetime, timezone

                client = FewsWebServiceClient(
                    base_url="https://example.com/FewsWebServices/rest"
                )

                dataset = client.get_timeseries(
                    location_ids=["Amanzimtoti_River_level"],
                    parameter_ids=["H.obs"],
                    start_time=datetime(2025, 3, 14, 10, 0, tzinfo=timezone.utc),
                    end_time=datetime(2025, 3, 15, 0, 0, tzinfo=timezone.utc),
                    xarray_type="flat",
                )

                print(dataset)

            Request NetCDF while preserving the original gridded or native
            NetCDF structure.

            ::

                gridded_dataset = client.get_timeseries(
                    location_ids=["Amanzimtoti_River_level"],
                    parameter_ids=["H.obs"],
                    start_time=datetime(2025, 3, 14, 10, 0, tzinfo=timezone.utc),
                    end_time=datetime(2025, 3, 15, 0, 0, tzinfo=timezone.utc),
                    xarray_type="grid",
                )

                print(gridded_dataset)

            Request raw PI JSON explicitly.

            ::

                response = client.get_timeseries(
                    location_ids=["Amanzimtoti_River_level"],
                    parameter_ids=["H.obs"],
                    start_time=datetime(2025, 3, 14, 10, 0, tzinfo=timezone.utc),
                    end_time=datetime(2025, 3, 15, 0, 0, tzinfo=timezone.utc),
                    document_format="PI_JSON",
                )

                print(response["timeSeries"][0]["header"]["parameterId"])
        """
        document_format_value = getattr(document_format, "value", document_format)
        if document_format_value is None:
            document_format_value = "PI_NETCDF"

        if document_format_value not in PI_TIMESERIES_DOCUMENT_FORMATS:
            supported_formats = ", ".join(sorted(PI_TIMESERIES_DOCUMENT_FORMATS))
            raise ValueError(
                "Unsupported timeseries document_format for this PI-focused wrapper: "
                f"{document_format_value}. Supported formats are: {supported_formats}."
            )

        if document_format_value == "PI_NETCDF":
            if xarray_type not in PI_NETCDF_XARRAY_TYPES:
                supported_xarray_types = ", ".join(sorted(PI_NETCDF_XARRAY_TYPES))
                raise ValueError(
                    "Unsupported NetCDF xarray_type for get_timeseries: "
                    f"{xarray_type}. Supported values are: {supported_xarray_types}."
                )

        # Collect only non-None keyword arguments
        non_none_kwargs = self._collect_non_none_kwargs(
            local_kwargs=locals().copy(),
            pop_kwargs=["to_xarray", "document_format_value", "xarray_type"],
        )
        content = TimeSeries().execute(client=self.client, **non_none_kwargs)

        if document_format_value == "PI_NETCDF":
            if not isinstance(content, bytes):
                raise ValueError("Expected PI_NETCDF response content as bytes.")
            if xarray_type == "grid":
                return convert_netcdf_zip_response_to_xarray(content)
            return normalize_netcdf_response_to_timeseries_xarray(content)
        if to_xarray:
            if document_format_value != "PI_JSON":
                raise ValueError("to_xarray=True is only supported with PI_JSON.")
            if not isinstance(content, dict):
                raise ValueError("Expected PI_JSON response content as a dictionary.")
            return convert_timeseries_response_to_xarray(content)
        return content

    def get_filters(
        self,
        filter_id: str | None = None,
        *,
        document_format: str | None = "PI_JSON",
        document_version: str | None = None,
    ) -> dict[str, Any] | str:
        """Get filters from the FEWS web services.

        Retrieves filters that are subfilters of the default filter. An
        existing subfilter ID can be specified to narrow the results.

        Args:
            filter_id: Optional FEWS filter identifier. When provided, only
                subfilters of this filter are returned.
            document_format: Response format supported by the FEWS filters
                endpoint. Defaults to ``PI_JSON``.
            document_version: Optional PI document version.

        Returns:
            A parsed PI JSON response dictionary by default, or a string when a
            text-based format such as ``PI_XML`` is requested.

        Example:
            Retrieve all available filters.

            ::

                client = FewsWebServiceClient(
                    base_url="https://example.com/FewsWebServices/rest"
                )

                filters = client.get_filters()
                print(filters)

            Retrieve subfilters of a specific filter.

            ::

                filters = client.get_filters(filter_id="MEAS")
                print(filters)
        """
        endpoint_kwargs = self._collect_non_none_kwargs(
            {
                "filter_id": filter_id,
                "document_format": document_format,
                "document_version": document_version,
            }
        )
        return Filters().execute(client=self.client, **endpoint_kwargs)

    def get_taskruns(
        self,
        workflow_id: str,
        task_run_ids: list[str] | str | None = None,
        *,
        topology_node_id: str | None = None,
        forecast_count: str | None = None,
        scenario_id: str | None = None,
        mc_id: str | None = None,
        start_forecast_time: datetime | None = None,
        end_forecast_time: datetime | None = None,
        start_dispatch_time: datetime | None = None,
        end_dispatch_time: datetime | None = None,
        task_run_status_ids: list[str] | str | None = None,
        only_forecasts: bool | None = None,
        task_run_count: str | None = None,
        only_current: bool | None = None,
        document_format: str | None = "PI_JSON",
        document_version: str | None = None,
    ) -> dict[str, Any] | str:
        """Get task runs for a FEWS workflow with optional filters.

        Args:
            workflow_id: FEWS workflow identifier to query task runs for.
                This parameter is required by the FEWS ``/taskruns`` endpoint.
            task_run_ids: Optional task run IDs to filter on. A single string is
                normalized to a one-item list.
            topology_node_id: Optional topology node filter.
            forecast_count: Optional number of forecast task runs to return.
            scenario_id: Optional scenario filter.
            mc_id: Optional Monte Carlo identifier filter.
            start_forecast_time: Optional inclusive forecast start filter.
            end_forecast_time: Optional inclusive forecast end filter.
            start_dispatch_time: Optional inclusive dispatch start filter.
            end_dispatch_time: Optional inclusive dispatch end filter.
            task_run_status_ids: Optional task run status filters. A single string
                is normalized to a one-item list.
            only_forecasts: Optional FEWS forecast-only flag.
            task_run_count: Optional maximum number of task runs to return.
            only_current: Optional FEWS current-taskrun-only flag.
            document_format: Response format supported by the FEWS taskruns
                endpoint. Defaults to ``PI_JSON``.
            document_version: Optional PI document version.

        Returns:
            A parsed PI JSON response dictionary by default, or a string when a
            text-based format such as ``PI_XML`` is requested.

        Example:
            Query all task runs for a workflow. ``workflow_id`` is required by
            the FEWS ``/taskruns`` endpoint, but all other filters are optional.

            ::

                client = FewsWebServiceClient(
                    base_url="https://example.com/FewsWebServices/rest"
                )

                taskruns = client.get_taskruns(
                    workflow_id="RunParticleTracking",
                )

                print(taskruns["taskRuns"][0]["id"])

            Query one or more specific task runs within a workflow.

            ::

                taskruns = client.get_taskruns(
                    workflow_id="RunParticleTracking",
                    task_run_ids=["SA5_1", "SA5_2"],
                )

                print(len(taskruns["taskRuns"]))

            Filter task runs further by forecast and status-related options.

            ::

                from datetime import datetime, timezone

                filtered_taskruns = client.get_taskruns(
                    workflow_id="RunParticleTracking",
                    start_forecast_time=datetime(
                        2025, 3, 14, 0, 0, tzinfo=timezone.utc
                    ),
                    end_forecast_time=datetime(
                        2025, 3, 15, 0, 0, tzinfo=timezone.utc
                    ),
                    task_run_status_ids=["Completed fully successful"],
                    only_forecasts=True,
                )

                print(filtered_taskruns["taskRuns"])
        """
        if isinstance(task_run_ids, str):
            task_run_ids = [task_run_ids]

        if isinstance(task_run_status_ids, str):
            task_run_status_ids = [task_run_status_ids]

        endpoint_kwargs = self._collect_non_none_kwargs(
            {
                "workflow_id": workflow_id,
                "task_run_ids": task_run_ids,
                "topology_node_id": topology_node_id,
                "forecast_count": forecast_count,
                "scenario_id": scenario_id,
                "mc_id": mc_id,
                "start_forecast_time": start_forecast_time,
                "end_forecast_time": end_forecast_time,
                "start_dispatch_time": start_dispatch_time,
                "end_dispatch_time": end_dispatch_time,
                "task_run_status_ids": task_run_status_ids,
                "only_forecasts": only_forecasts,
                "task_run_count": task_run_count,
                "only_current": only_current,
                "document_format": document_format,
                "document_version": document_version,
            }
        )
        return Taskruns().execute(client=self.client, **endpoint_kwargs)

    def execute_workflow(self, *args: Any, **kwargs: Any) -> None:
        """Execute a workflow in the FEWS web services."""
        pass

    def execute_whatif_scenario(
        self,
        what_if_template_id: str | None = None,
        single_run_what_if: str | None = None,
        name: str | None = None,
        document_format: str | None = None,
        document_version: str | None = None,
    ) -> dict[str, Any]:
        """Execute a what-if scenario in the FEWS web services."""
        return WhatIfScenarios().execute(
            client=self.client,
            what_if_template_id=what_if_template_id,
            single_run_what_if=single_run_what_if,
            name=name,
            document_format=document_format,
            document_version=document_version,
        )

    def get_workflows(self) -> dict[str, Any]:
        return Workflows().execute(client=self.client, document_format="PI_JSON")

    def endpoint_arguments(self, endpoint: str) -> list[str]:
        """Get the arguments for a specific FEWS web service endpoint.

        Args:
            endpoint: The name of the endpoint, options: "timeseries", "taskruns",
             "whatif_scenarios", "workflows".

        Returns:
            The argument names for the specified endpoint.
        """
        if endpoint == "timeseries":
            return TimeSeries().input_args()
        elif endpoint == "taskruns":
            return Taskruns().input_args()
        elif endpoint == "whatif_scenarios":
            return WhatIfScenarios().input_args()
        elif endpoint == "workflows":
            return Workflows().input_args()
        else:
            raise ValueError(f"Unknown endpoint: {endpoint}")

    def _collect_non_none_kwargs(
        self, local_kwargs: dict[str, Any], pop_kwargs: list[str] | None = None
    ) -> dict[str, Any]:
        """Collect only non-None keyword arguments."""
        local_kwargs.pop("self", None)
        for key in pop_kwargs or []:
            local_kwargs.pop(key, None)
        if "kwargs" in local_kwargs:
            extra_kwargs = local_kwargs.pop("kwargs")
            if isinstance(extra_kwargs, dict):
                local_kwargs.update(extra_kwargs)
        return {k: v for k, v in local_kwargs.items() if v is not None}
