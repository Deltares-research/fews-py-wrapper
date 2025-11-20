import json
from pathlib import Path

import pytest


@pytest.fixture()
def timeseries_response():
    file_path = Path(__file__).parent / "test_data" / "timeseries_response.json"
    with open(file_path, "r") as f:
        content = json.load(f)
    return content
