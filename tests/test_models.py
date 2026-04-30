import pytest
from pydantic import ValidationError

from fews_py_wrapper.models import (
    PiFiltersResponse,
    PiParametersResponse,
    PiWorkflowsResponse,
)


def test_pi_parameters_response_validates_timeseries_parameters():
    payload = {
        "version": "1.34",
        "timeSeriesParameters": [
            {
                "id": "alpha",
                "name": "Alpha",
                "shortName": "A",
                "parameterType": "instantaneous",
                "unit": "m/s",
                "displayUnit": "knots",
                "usesDatum": "false",
                "parameterGroup": "Current Speed",
                "parameterGroupName": "Current Speed",
            },
            {
                "id": "enabled",
                "name": "Enabled",
                "parameterType": "mean",
                "unit": "-",
                "usesDatum": True,
                "attributes": [{"name": "category", "text": "derived"}],
            },
        ],
    }

    result = PiParametersResponse.model_validate(payload)

    assert len(result.parameters) == 2
    assert result.parameters[0].short_name == "A"
    assert result.parameters[0].display_unit == "knots"
    assert result.parameters[0].uses_datum is False
    assert result.parameters[1].uses_datum is True
    assert result.parameters[1].attributes[0].text == "derived"


def test_pi_parameter_requires_valid_parameter_type():
    with pytest.raises(ValidationError):
        PiParametersResponse.model_validate(
            {
                "timeSeriesParameters": [
                    {
                        "id": "alpha",
                        "name": "Alpha",
                        "parameterType": "invalid",
                        "unit": "m/s",
                    }
                ]
            }
        )


def test_pi_filters_response_validates_nested_children_and_bounding_boxes():
    payload = {
        "version": "1.34",
        "filters": [
            {
                "id": "Viewer",
                "name": "Viewer",
                "child": [
                    {
                        "id": "Rain Gauges",
                        "name": "Rain Gauges",
                        "boundingBox": {
                            "crs": "EPSG:3857",
                            "minx": "3411942.35",
                            "maxx": "3467602.1",
                            "miny": "-3516410.45",
                            "maxy": "-3445836.6",
                        },
                    }
                ],
            }
        ],
    }

    result = PiFiltersResponse.model_validate(payload)

    assert result.version == "1.34"
    assert len(result.filters) == 1
    assert result.filters[0].id == "Viewer"
    assert result.filters[0].children[0].id == "Rain Gauges"
    assert result.filters[0].children[0].bounding_box is not None
    assert result.filters[0].children[0].bounding_box.minx == pytest.approx(3411942.35)


def test_pi_workflows_response_validates_workflow_descriptors():
    payload = {
        "workflows": [
            {
                "id": "ImportObscape",
                "name": "Import Obscape",
                "description": "Imports time series from Obscape API",
            }
        ]
    }

    result = PiWorkflowsResponse.model_validate(payload)

    assert len(result.workflows) == 1
    assert result.workflows[0].id == "ImportObscape"
    assert result.workflows[0].description == "Imports time series from Obscape API"
