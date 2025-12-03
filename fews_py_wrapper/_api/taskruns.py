from fews_openapi_py_client import AuthenticatedClient, Client
from fews_openapi_py_client.api.tasks import taskruns
from fews_openapi_py_client.models.taskruns_document_format import (
    TaskrunsDocumentFormat,
)
from fews_openapi_py_client.models.taskruns_only_current import TaskrunsOnlyCurrent
from fews_openapi_py_client.models.taskruns_only_forecasts import TaskrunsOnlyForecasts


def retrieve_taskruns(
    client: AuthenticatedClient | Client,
    workflow_id: str,
    task_ids: list[str],
    **kwargs,
) -> dict:
    """Retrieve task runs from the FEWS web services."""
    kwargs = retrieve_argument_models(kwargs)
    response = taskruns.sync_detailed(
        client=client, workflow_id=workflow_id, task_ids=task_ids, **kwargs
    )
    response.raise_for_status()
    return response.parsed


def retrieve_argument_models(kwargs: dict) -> dict:
    """Retrieve argument models for the taskruns endpoint."""
    try:
        if "document_format" in kwargs:
            kwargs["document_format"] = TaskrunsDocumentFormat(
                kwargs["document_format"]
            )
        if "only_current" in kwargs:
            kwargs["only_current"] = TaskrunsOnlyCurrent(kwargs["only_current"])
        if "only_forecasts" in kwargs:
            kwargs["only_forecasts"] = TaskrunsOnlyForecasts(kwargs["only_forecasts"])
        return kwargs
    except ValueError as e:
        raise ValueError(f"Invalid argument value: {e}") from e
