import inspect
from datetime import datetime
from typing import Any

import xarray as xr
from fews_openapi_py_client import AuthenticatedClient, Client

from fews_py_wrapper._api import (
    Filters,
    Locations,
    Parameters,
    PostRunTask,
    PostTimeSeries,
    Taskruns,
    TimeSeries,
    Workflows,
)
from fews_py_wrapper.models import (
    PiFiltersResponse,
    PiLocationsResponse,
    PiParametersResponse,
    PiTaskRunsResponse,
    PiWorkflowsResponse,
)
from fews_py_wrapper.utils import convert_netcdf_zip_response_to_xarray

__all__ = ["FewsWebServiceClient"]

PI_TIMESERIES_DOCUMENT_FORMATS = frozenset({"PI_JSON", "PI_XML", "PI_CSV", "PI_NETCDF"})


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
        document_format: str = "PI_NETCDF",
        **kwargs: Any,
    ) -> list[xr.Dataset] | dict[str, Any] | str:
        """Get time series data from the FEWS web services.

        Args:
            location_ids: One or more FEWS location identifiers.
            parameter_ids: One or more FEWS parameter identifiers.
            start_time: Inclusive start timestamp. Must be timezone-aware.
            end_time: Inclusive end timestamp. Must be timezone-aware.
            document_format: FEWS PI response format. Supported values are
                ``PI_JSON``, ``PI_XML``, ``PI_CSV`` and ``PI_NETCDF``.
                Defaults to ``PI_NETCDF`` when omitted.
            **kwargs: Additional endpoint arguments accepted by the underlying
                FEWS time series endpoint.

        Returns:
            A list of ``xarray.Dataset`` objects for ``PI_NETCDF`` responses,
            preserving the original NetCDF member layout and ZIP member order;
            a dictionary for ``PI_JSON``; or a string for ``PI_XML`` and
            ``PI_CSV``.

        Example:
            Request time series as NetCDF. The ZIP payload returned by FEWS is
            unpacked automatically and returned as a list of
            ``xarray.Dataset`` objects.

            ::

                from datetime import datetime, timezone

                client = FewsWebServiceClient(
                    base_url="https://example.com/FewsWebServices/rest"
                )

                datasets = client.get_timeseries(
                    location_ids=["Amanzimtoti_River_level"],
                    parameter_ids=["H.obs"],
                    start_time=datetime(2025, 3, 14, 10, 0, tzinfo=timezone.utc),
                    end_time=datetime(2025, 3, 15, 0, 0, tzinfo=timezone.utc),
                )

                first_dataset = datasets[0]
                print(first_dataset)

            When FEWS writes multiple NetCDF files for a single request, each
            member is returned as a separate dataset so you can choose your own
            merge strategy.

            ::

                datasets = client.get_timeseries(
                    location_ids=["Amanzimtoti_River_level"],
                    parameter_ids=["H.obs"],
                    start_time=datetime(2025, 3, 14, 10, 0, tzinfo=timezone.utc),
                    end_time=datetime(2025, 3, 15, 0, 0, tzinfo=timezone.utc),
                )

                merged = xr.merge(datasets, combine_attrs="override")
                print(merged)

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

            PI JSON responses are returned as raw dictionaries. Use
            ``PI_NETCDF`` when you want the wrapper to return one or more
            ``xarray.Dataset`` objects.
        """
        document_format_value = getattr(document_format, "value", document_format)

        if document_format_value not in PI_TIMESERIES_DOCUMENT_FORMATS:
            supported_formats = ", ".join(sorted(PI_TIMESERIES_DOCUMENT_FORMATS))
            raise ValueError(
                "Unsupported timeseries document_format for this PI-focused wrapper: "
                f"{document_format_value}. Supported formats are: {supported_formats}."
            )

        # Collect only non-None keyword arguments
        non_none_kwargs = self._collect_non_none_kwargs(
            local_kwargs=locals().copy(),
            pop_kwargs=["document_format_value"],
        )
        content = TimeSeries().execute(client=self.client, **non_none_kwargs)

        if document_format_value == "PI_NETCDF":
            if not isinstance(content, bytes):
                raise ValueError("Expected PI_NETCDF response content as bytes.")
            return convert_netcdf_zip_response_to_xarray(content)
        if document_format_value == "PI_JSON":
            if not isinstance(content, dict):
                raise ValueError("Expected PI_JSON response content as a dictionary.")
            return content
        if not isinstance(content, str):
            raise ValueError(
                f"Expected {document_format_value} response content as a string."
            )
        return content

    def post_timeseries(
        self,
        *,
        pi_time_series_xml_content: str | None = None,
        pi_time_series_json_content: str | None = None,
        filter_id: str | None = None,
        convert_datum: bool | None = None,
    ) -> str:
        """Write PI time series data to the FEWS web services using POST.

        The FEWS ``POST /timeseries`` endpoint writes PI time series that belong
        to time series sets configured in the default filter or in the filter
        identified by ``filter_id``. Provide the PI XML or PI JSON content to be
        written through the dedicated content arguments.

        Args:
            pi_time_series_xml_content: Optional PI XML payload to write.
            pi_time_series_json_content: Optional PI JSON payload to write.
            filter_id: Optional FEWS filter identifier restricting which time
                series sets may be written.
            convert_datum: Optional FEWS convert-datum flag.

        Returns:
            A PI diagnostic XML string describing the import result.

        Example:
            Post PI XML content.

            ::

                from pathlib import Path

                client = FewsWebServiceClient(
                    base_url="https://example.com/FewsWebServices/rest"
                )

                xml_payload = Path("tests/test_data/post_timeseries.xml").read_text(
                    encoding="utf-8"
                )

                diag_xml = client.post_timeseries(
                    pi_time_series_xml_content=xml_payload,
                    filter_id="MEAS",
                )

                print(diag_xml)

            Post PI JSON content.

            ::

                from pathlib import Path

                json_payload = Path("tests/test_data/post_timeseries.json").read_text(
                    encoding="utf-8"
                )

                diag_xml = client.post_timeseries(
                    pi_time_series_json_content=json_payload,
                )

                print(diag_xml)
        """
        if pi_time_series_xml_content is None and pi_time_series_json_content is None:
            raise ValueError(
                "One of pi_time_series_xml_content or "
                "pi_time_series_json_content must be provided."
            )

        request_body = self._collect_non_none_kwargs(
            {
                "piTimeSeriesXmlContent": pi_time_series_xml_content,
                "piTimeSeriesJsonContent": pi_time_series_json_content,
            }
        )

        endpoint_kwargs = self._collect_non_none_kwargs(
            {
                "body": request_body,
                "filter_id": filter_id,
                "convert_datum": convert_datum,
            }
        )
        content = PostTimeSeries().execute(client=self.client, **endpoint_kwargs)
        if not isinstance(content, str):
            raise ValueError("Expected POST timeseries response content as a string.")
        return content

    def get_filters(
        self,
        filter_id: str | None = None,
        *,
        document_format: str | None = "PI_JSON",
        document_version: str | None = None,
    ) -> PiFiltersResponse | str:
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
            A validated PI filters response for ``PI_JSON`` by default, or a
            string when a text-based format such as ``PI_XML`` is requested.

        Example:
            Retrieve all available filters.

            ::

                client = FewsWebServiceClient(
                    base_url="https://example.com/FewsWebServices/rest"
                )

                filters = client.get_filters()
                print(filters.filters[0].id)

            Retrieve subfilters of a specific filter.

            ::

                filters = client.get_filters(filter_id="MEAS")
                print(filters.filters)
        """
        endpoint_kwargs = self._collect_non_none_kwargs(
            {
                "filter_id": filter_id,
                "document_format": document_format,
                "document_version": document_version,
            }
        )
        content = Filters().execute(client=self.client, **endpoint_kwargs)
        if isinstance(content, dict):
            return PiFiltersResponse.model_validate(content)
        if not isinstance(content, str):
            raise ValueError("Expected filters response content as a string.")
        return content

    def post_runtask(
        self,
        *,
        workflow_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        time_zero: datetime | None = None,
        cold_state_id: str | None = None,
        scenario_id: str | None = None,
        user_id: str | None = None,
        description: str | None = None,
        run_option: str | None = None,
        run_locally_and_promote_to_server: bool | None = None,
        pi_parameters_xml_content: str | None = None,
    ) -> str:
        """Run a one-off FEWS task for a workflow and return the task ID.

        This wraps FEWS ``POST /runtask`` using
        ``application/x-www-form-urlencoded`` request encoding. FEWS returns a
        plain-text ``taskId`` that can be used to track the task status.

        Args:
            workflow_id: Required FEWS workflow identifier.
            start_time: Optional workflow start time. Must be timezone-aware.
            end_time: Optional workflow end time. Must be timezone-aware.
            time_zero: Optional forecast time zero. Must be timezone-aware.
            cold_state_id: Optional FEWS cold-state identifier.
            scenario_id: Optional FEWS scenario identifier.
            user_id: Optional FEWS user identifier.
            description: Optional task description stored by FEWS.
            run_option: Optional FEWS run option. Supported values are ``all``,
                ``allmostrecentonly``, and ``alloneatatime``.
            run_locally_and_promote_to_server: Optional FEWS execution flag.
            pi_parameters_xml_content: Optional PI model parameters XML content.

        Returns:
            The FEWS task identifier returned by ``POST /runtask``.

        Example:
            ::

                from datetime import datetime, timezone

                client = FewsWebServiceClient(
                    base_url="https://example.com/FewsWebServices/rest"
                )

                task_id = client.post_runtask(
                    workflow_id="ImportObscape",
                    start_time=datetime(2025, 3, 18, 15, 0, tzinfo=timezone.utc),
                    end_time=datetime(2025, 3, 18, 16, 0, tzinfo=timezone.utc),
                    description="Run ImportObscape once from the wrapper",
                    run_option="all",
                )

                print(task_id)
        """
        request_body = self._collect_non_none_kwargs(
            {
                "piParametersXmlContent": pi_parameters_xml_content,
            }
        )
        endpoint_kwargs = self._collect_non_none_kwargs(
            {
                "workflow_id": workflow_id,
                "start_time": start_time,
                "end_time": end_time,
                "time_zero": time_zero,
                "cold_state_id": cold_state_id,
                "scenario_id": scenario_id,
                "user_id": user_id,
                "description": description,
                "run_option": run_option,
                "run_locally_and_promote_to_server": run_locally_and_promote_to_server,
                "body": request_body or None,
            }
        )
        content = PostRunTask().execute(client=self.client, **endpoint_kwargs)
        if not isinstance(content, str):
            raise ValueError("Expected POST runtask response content as a string.")
        return content

    def get_taskruns(
        self,
        *,
        workflow_id: str,
        topology_node_id: str | None = None,
        forecast_count: int | str | None = None,
        task_run_ids: list[str] | None = None,
        scenario_id: str | None = None,
        mc_id: str | None = None,
        start_forecast_time: datetime | None = None,
        end_forecast_time: datetime | None = None,
        start_dispatch_time: datetime | None = None,
        end_dispatch_time: datetime | None = None,
        task_run_status_ids: list[str] | None = None,
        only_forecasts: bool | None = None,
        task_run_count: int | str | None = None,
        only_current: bool | None = None,
        document_format: str | None = "PI_JSON",
        document_version: str | None = None,
    ) -> PiTaskRunsResponse | str:
        """Get task runs for a FEWS workflow.

        Retrieves task runs from FEWS ``GET /taskruns`` for the specified
        ``workflow_id``, optionally filtered by identifiers, status, forecast
        time, or dispatch time.

        FEWS returns only forecast task runs by default. As a result,
        non-forecast workflows can legitimately produce an empty
        ``task_runs`` list unless you pass ``only_forecasts=False``.

        Args:
            workflow_id: Required FEWS workflow identifier.
            topology_node_id: Optional FEWS topology-node identifier.
            forecast_count: Optional forecast-count filter accepted by FEWS.
            task_run_ids: Optional FEWS task-run IDs to filter by.
            scenario_id: Optional FEWS scenario identifier.
            mc_id: Optional FEWS MC identifier.
            start_forecast_time: Optional inclusive forecast-time lower bound.
                Must be timezone-aware.
            end_forecast_time: Optional inclusive forecast-time upper bound.
                Must be timezone-aware.
            start_dispatch_time: Optional inclusive dispatch-time lower bound.
                Must be timezone-aware.
            end_dispatch_time: Optional inclusive dispatch-time upper bound.
                Must be timezone-aware.
            task_run_status_ids: Optional FEWS task-run status identifiers.
            only_forecasts: Optional FEWS forecast-only filter. When omitted,
                FEWS may default to returning only forecast task runs.
            task_run_count: Optional maximum number of returned task runs.
            only_current: Optional FEWS current-only filter.
            document_format: Response format. Defaults to ``PI_JSON``.
            document_version: Optional PI document version.

        Returns:
            A validated task-runs response for ``PI_JSON`` by default, or a
            string when a text-based format such as ``PI_XML`` is requested.

        Example:
            Retrieve the latest forecast task runs for a workflow.

            ::

                taskruns = client.get_taskruns(
                    workflow_id="ImportObscape",
                    task_run_count=10,
                )

                for task_run in taskruns.task_runs:
                    print(task_run.id, task_run.status, task_run.dispatch_time)

            Retrieve task runs for a non-forecast workflow.

            ::

                taskruns = client.get_taskruns(
                    workflow_id="ftpClientConfig",
                    only_forecasts=False,
                    task_run_count=10,
                )

                print(taskruns.task_runs)

            Retrieve the raw PI XML response.

            ::

                taskruns_xml = client.get_taskruns(
                    workflow_id="ImportObscape",
                    document_format="PI_XML",
                )
                print(taskruns_xml)
        """
        endpoint_kwargs = self._collect_non_none_kwargs(
            {
                "workflow_id": workflow_id,
                "topology_node_id": topology_node_id,
                "forecast_count": forecast_count,
                "task_run_ids": task_run_ids,
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
        content = Taskruns().execute(client=self.client, **endpoint_kwargs)
        if isinstance(content, dict):
            return PiTaskRunsResponse.model_validate(content)
        if not isinstance(content, str):
            raise ValueError("Expected taskruns response content as a string.")
        return content

    def execute_workflow(self, *args: Any, **kwargs: Any) -> str:
        """Backward-compatible alias for :meth:`post_runtask`."""
        return self.post_runtask(*args, **kwargs)

    def get_workflows(
        self,
        *,
        document_format: str | None = "PI_JSON",
        document_version: str | None = None,
    ) -> PiWorkflowsResponse | str:
        """Get available FEWS workflows.

        Retrieves the default workflow XML files exposed by the FEWS
        ``/workflows`` endpoint.

        Args:
            document_format: Response format supported by the FEWS workflows
                endpoint. Defaults to ``PI_JSON``.
            document_version: Optional PI document version.

        Returns:
            A validated workflows response for ``PI_JSON`` by default, or a
            string when a text-based format such as ``PI_XML`` is requested.

        Example:
            Retrieve the available workflows as PI JSON.

            ::

                client = FewsWebServiceClient(
                    base_url="https://example.com/FewsWebServices/rest"
                )

                workflows = client.get_workflows()
                print(workflows.workflows[0].id)

            Retrieve the raw PI XML response.

            ::

                workflows_xml = client.get_workflows(document_format="PI_XML")
                print(workflows_xml)
        """
        endpoint_kwargs = self._collect_non_none_kwargs(
            {
                "document_format": document_format,
                "document_version": document_version,
            }
        )
        content = Workflows().execute(client=self.client, **endpoint_kwargs)
        if isinstance(content, dict):
            return PiWorkflowsResponse.model_validate(content)
        if not isinstance(content, str):
            raise ValueError("Expected workflows response content as a string.")
        return content

    def endpoint_arguments(self, endpoint: str) -> list[str]:
        """Get the arguments for a specific FEWS web service endpoint.

        Args:
            endpoint: The name of the endpoint, options: ``timeseries``,
                ``post_timeseries``, ``post_runtask``, ``taskruns``,
                ``filters``, and ``workflows``.

        Returns:
            The argument names for the specified endpoint.
        """
        if endpoint == "timeseries":
            return TimeSeries().input_args()
        elif endpoint == "post_timeseries":
            return list(inspect.signature(self.post_timeseries).parameters)
        elif endpoint == "post_runtask":
            return list(inspect.signature(self.post_runtask).parameters)
        elif endpoint == "taskruns":
            return list(inspect.signature(self.get_taskruns).parameters)
        elif endpoint == "filters":
            return list(inspect.signature(self.get_filters).parameters)
        elif endpoint == "workflows":
            return list(inspect.signature(self.get_workflows).parameters)
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
