import json
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pytest
import xarray as xr


@pytest.fixture()
def timeseries_response():
    file_path = Path(__file__).parent / "test_data" / "timeseries_response.json"
    with open(file_path, "r") as f:
        content = json.load(f)
    return content


@pytest.fixture()
def netcdf_dataset() -> xr.Dataset:
    return xr.Dataset(
        data_vars={"H_obs": ("time", [1.1, 1.2, 1.3])},
        coords={
            "time": np.array(
                [
                    "2025-03-14T10:00:00",
                    "2025-03-14T11:00:00",
                    "2025-03-14T12:00:00",
                ],
                dtype="datetime64[ns]",
            )
        },
        attrs={"source": "test"},
    )


@pytest.fixture()
def netcdf_zip_response(netcdf_dataset: xr.Dataset) -> bytes:
    with TemporaryDirectory() as temp_dir:
        netcdf_path = Path(temp_dir) / "timeseries.nc"
        netcdf_dataset.to_netcdf(netcdf_path, engine="netcdf4")

        zip_buffer_path = Path(temp_dir) / "timeseries.zip"
        with zipfile.ZipFile(zip_buffer_path, mode="w") as zip_file:
            zip_file.write(netcdf_path, arcname="timeseries.nc")

        return zip_buffer_path.read_bytes()


@pytest.fixture()
def raw_netcdf_response(netcdf_dataset: xr.Dataset) -> bytes:
    with TemporaryDirectory() as temp_dir:
        netcdf_path = Path(temp_dir) / "timeseries.nc"
        netcdf_dataset.to_netcdf(netcdf_path, engine="netcdf4")
        return netcdf_path.read_bytes()


@pytest.fixture()
def multi_member_netcdf_zip_response() -> bytes:
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        time_coord = np.array(
            ["2025-03-14T10:00:00", "2025-03-14T11:00:00"],
            dtype="datetime64[ns]",
        )
        dataset_upstream = xr.Dataset(
            data_vars={"H_simulated": ("time", [1.0, 2.0])},
            coords={"time": time_coord},
            attrs={"locationId": "Amanzimtoti_River_level"},
        )
        dataset_mouth = xr.Dataset(
            data_vars={"H_simulated": ("time", [3.0, 4.0])},
            coords={"time": time_coord},
            attrs={"locationId": "Amanzimtoti_River_Mouth_level"},
        )

        first_path = temp_path / "upstream.nc"
        second_path = temp_path / "mouth.nc"
        dataset_upstream.to_netcdf(first_path, engine="netcdf4")
        dataset_mouth.to_netcdf(second_path, engine="netcdf4")

        zip_path = temp_path / "timeseries_multi.zip"
        with zipfile.ZipFile(zip_path, mode="w") as zip_file:
            zip_file.write(first_path, arcname="upstream.nc")
            zip_file.write(second_path, arcname="mouth.nc")

        return zip_path.read_bytes()


@pytest.fixture()
def station_conflict_netcdf_zip_response() -> bytes:
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        time_coord = np.array(
            ["2025-03-14T10:00:00", "2025-03-14T11:00:00"],
            dtype="datetime64[ns]",
        )
        dataset_single_station = xr.Dataset(
            data_vars={
                "H_simulated": (
                    ("time", "stations"),
                    np.array([[1.0], [2.0]]),
                )
            },
            coords={"time": time_coord},
            attrs={"locationId": "Amanzimtoti_River_level"},
        )
        dataset_two_stations = xr.Dataset(
            data_vars={
                "H_simulated": (
                    ("time", "stations"),
                    np.array([[3.0, 4.0], [5.0, 6.0]]),
                )
            },
            coords={"time": time_coord},
            attrs={"locationId": "Amanzimtoti_River_Mouth_level"},
        )

        first_path = temp_path / "single_station.nc"
        second_path = temp_path / "two_stations.nc"
        dataset_single_station.to_netcdf(first_path, engine="netcdf4")
        dataset_two_stations.to_netcdf(second_path, engine="netcdf4")

        zip_path = temp_path / "station_conflict.zip"
        with zipfile.ZipFile(zip_path, mode="w") as zip_file:
            zip_file.write(first_path, arcname="single_station.nc")
            zip_file.write(second_path, arcname="two_stations.nc")

        return zip_path.read_bytes()
