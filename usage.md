# Usage

## Overview

`fews-py-wrapper` provides a small typed wrapper around the Delft-FEWS
WebServices API. The main entry point is `FewsWebServiceClient`.

## Basic example

```python
from datetime import datetime, timezone

from fews_py_wrapper import FewsWebServiceClient


client = FewsWebServiceClient(base_url="https://example.com/FewsWebServices/rest")

parameters = client.get_parameters()
locations = client.get_locations()

timeseries = client.get_timeseries(
    location_ids=["Amanzimtoti_River_level"],
    parameter_ids=["H.obs"],
    start_time=datetime(2025, 3, 14, 10, 0, tzinfo=timezone.utc),
    end_time=datetime(2025, 3, 15, 0, 0, tzinfo=timezone.utc),
)
```

## Get parameters

Use `get_parameters()` when you need the available FEWS parameter metadata before
requesting observations or forecasts.

```python
parameters = client.get_parameters()

for parameter in parameters.parameters[:3]:
    print(parameter.id, parameter.name, parameter.unit)
```

## Get locations

Use `get_locations()` when you need the available FEWS locations before requesting
time series for a specific site.

```python
locations = client.get_locations()

for location in locations.locations[:3]:
    print(location.location_id, location.description, location.lat, location.lon)
```

## Get time series

`get_timeseries()` can return either the raw PI JSON payload or an `xarray`
dataset.

```python
raw_timeseries = client.get_timeseries(
    location_ids=["Amanzimtoti_River_level"],
    parameter_ids=["H.obs"],
    start_time=datetime(2025, 3, 14, 10, 0, tzinfo=timezone.utc),
    end_time=datetime(2025, 3, 15, 0, 0, tzinfo=timezone.utc),
)

dataset = client.get_timeseries(
    location_ids=["Amanzimtoti_River_level"],
    parameter_ids=["H.obs"],
    start_time=datetime(2025, 3, 14, 10, 0, tzinfo=timezone.utc),
    end_time=datetime(2025, 3, 15, 0, 0, tzinfo=timezone.utc),
    to_xarray=True,
)
```

See the repository notebook in [example_notebook.ipynb](../example_notebook.ipynb)
for a fuller walkthrough.
