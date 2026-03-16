import pytest
from pydantic import ValidationError

from fews_py_wrapper.models import PiParametersResponse


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
