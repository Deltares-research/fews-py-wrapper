from datetime import datetime
from typing import Any

import xarray as xr
from fews_openapi_py_client import AuthenticatedClient, Client

from fews_py_wrapper._api import (
    Locations,
    Parameters,
    Taskruns,
    TimeSeries,
    WhatIfScenarios,
    Workflows,
)
from fews_py_wrapper.models import PiLocationsResponse, PiParametersResponse
from fews_py_wrapper.utils import (
    convert_timeseries_response_to_xarray,
)


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
        to_xarray: bool = False,
        document_format: str | None = "PI_JSON",
        **kwargs: Any,
    ) -> xr.Dataset | dict[str, Any]:
        """Get time series data from the FEWS web services.

        Args:
            location_ids: One or more FEWS location identifiers.
            parameter_ids: One or more FEWS parameter identifiers.
            start_time: Inclusive start timestamp. Must be timezone-aware.
            end_time: Inclusive end timestamp. Must be timezone-aware.
            to_xarray: If ``True``, convert the PI JSON response into an
                ``xarray.Dataset``.
            document_format: FEWS response format. ``PI_JSON`` is currently the
                supported option.
            **kwargs: Additional endpoint arguments accepted by the underlying
                FEWS time series endpoint.

        Returns:
            Either the raw PI JSON response as a dictionary, or an
            ``xarray.Dataset`` when ``to_xarray=True``.

        Example:
            Request raw PI JSON for a single parameter and location.

            ::

                from datetime import datetime, timezone

                client = FewsWebServiceClient(
                    base_url="https://example.com/FewsWebServices/rest"
                )

                response = client.get_timeseries(
                    location_ids=["Amanzimtoti_River_level"],
                    parameter_ids=["H.obs"],
                    start_time=datetime(2025, 3, 14, 10, 0, tzinfo=timezone.utc),
                    end_time=datetime(2025, 3, 15, 0, 0, tzinfo=timezone.utc),
                )

                print(response["timeSeries"][0]["header"]["parameterId"])

            Request the same data and convert it to ``xarray`` for analysis.

            ::

                dataset = client.get_timeseries(
                    location_ids=["Amanzimtoti_River_level"],
                    parameter_ids=["H.obs"],
                    start_time=datetime(2025, 3, 14, 10, 0, tzinfo=timezone.utc),
                    end_time=datetime(2025, 3, 15, 0, 0, tzinfo=timezone.utc),
                    to_xarray=True,
                )

                print(dataset)
        """
        # Collect only non-None keyword arguments
        non_none_kwargs = self._collect_non_none_kwargs(
            local_kwargs=locals().copy(), pop_kwargs=["to_xarray"]
        )
        content = TimeSeries().execute(client=self.client, **non_none_kwargs)
        if to_xarray:
            return convert_timeseries_response_to_xarray(content)
        return content

    def get_taskruns(
        self, workflow_id: str, task_ids: list[str] | str | None = None
    ) -> dict[str, Any]:
        """Get the status of a task run in the FEWS web services."""
        if isinstance(task_ids, str):
            task_ids = [task_ids]

        # Collect only non-None keyword arguments
        non_none_kwargs = self._collect_non_none_kwargs(local_kwargs=locals().copy())
        return Taskruns().execute(
            client=self.client, document_format="PI_JSON", **non_none_kwargs
        )

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
