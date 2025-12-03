from fews_openapi_py_client.models.taskruns_document_format import (
    TaskrunsDocumentFormat,
)
from fews_openapi_py_client.models.taskruns_only_current import TaskrunsOnlyCurrent
from fews_openapi_py_client.models.taskruns_only_forecasts import TaskrunsOnlyForecasts

from fews_py_wrapper._api.taskruns import retrieve_argument_models


def test_retrieve_argument_models() -> None:
    """Test the retrieve_argument_models function."""
    kwargs = {
        "document_format": "PI_JSON",
        "only_current": True,
        "only_forecasts": False,
    }
    converted_kwargs = retrieve_argument_models(kwargs)

    assert isinstance(converted_kwargs["document_format"], TaskrunsDocumentFormat)
    assert converted_kwargs["document_format"] == TaskrunsDocumentFormat.PI_JSON

    assert isinstance(converted_kwargs["only_current"], TaskrunsOnlyCurrent)
    assert converted_kwargs["only_current"] == TaskrunsOnlyCurrent.TRUE

    assert isinstance(converted_kwargs["only_forecasts"], TaskrunsOnlyForecasts)
    assert converted_kwargs["only_forecasts"] == TaskrunsOnlyForecasts.FALSE
