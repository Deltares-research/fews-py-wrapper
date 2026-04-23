import json
from pathlib import Path

import pytest

TEST_DATA_DIR = Path(__file__).parent / "test_data"


def _read_test_data_bytes(file_name: str) -> bytes:
    return (TEST_DATA_DIR / file_name).read_bytes()


def _read_test_data_text(file_name: str) -> str:
    return (TEST_DATA_DIR / file_name).read_text(encoding="utf-8")


@pytest.fixture()
def timeseries_response():
    file_path = TEST_DATA_DIR / "timeseries_response.json"
    with open(file_path, "r") as f:
        content = json.load(f)
    return content


@pytest.fixture()
def post_timeseries_xml_content() -> str:
    return _read_test_data_text("post_timeseries.xml")


@pytest.fixture()
def post_timeseries_json_content() -> str:
    return _read_test_data_text("post_timeseries.json")


@pytest.fixture()
def netcdf_zip_response() -> bytes:
    return _read_test_data_bytes("timeseries_single_member.zip")


@pytest.fixture()
def multi_member_netcdf_zip_response() -> bytes:
    return _read_test_data_bytes("timeseries_multi_member.zip")


@pytest.fixture()
def varying_station_sizes_netcdf_zip_response() -> bytes:
    return _read_test_data_bytes("timeseries_multi_member.zip")
