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

timeseries_datasets = client.get_timeseries(
    location_ids=["Amanzimtoti_River_level"],
    parameter_ids=["H.obs"],
    start_time=datetime(2025, 3, 14, 10, 0, tzinfo=timezone.utc),
    end_time=datetime(2025, 3, 15, 0, 0, tzinfo=timezone.utc),
)

first_dataset = timeseries_datasets[0]
```

## Get parameters

Use `get_parameters()` when you need the available FEWS parameter metadata before
requesting observations or forecasts.

```python
from fews_py_wrapper import FewsWebServiceClient


client = FewsWebServiceClient(base_url="https://example.com/FewsWebServices/rest")
parameters = client.get_parameters()

for parameter in parameters.parameters[:3]:
    print(parameter.id, parameter.name, parameter.unit)
```

## Get locations

Use `get_locations()` when you need the available FEWS locations before requesting
time series for a specific site.

```python
from fews_py_wrapper import FewsWebServiceClient


client = FewsWebServiceClient(base_url="https://example.com/FewsWebServices/rest")
locations = client.get_locations()

for location in locations.locations[:3]:
    print(location.location_id, location.description, location.lat, location.lon)
```

## Get time series

`get_timeseries()` requests `PI_NETCDF` by default when `document_format` is
omitted. The FEWS response is retrieved as a ZIP file containing one or more
NetCDF files. The wrapper returns these as a `list[xarray.Dataset]`, preserving
the original NetCDF layout of each member and the ZIP member order.

```python
from datetime import datetime, timezone

import xarray as xr

from fews_py_wrapper import FewsWebServiceClient


client = FewsWebServiceClient(base_url="https://example.com/FewsWebServices/rest")

datasets = client.get_timeseries(
    location_ids=["Amanzimtoti_River_level"],
    parameter_ids=["H.obs"],
    start_time=datetime(2025, 3, 14, 10, 0, tzinfo=timezone.utc),
    end_time=datetime(2025, 3, 15, 0, 0, tzinfo=timezone.utc),
)

first_dataset = datasets[0]
print(first_dataset)

merged = xr.merge(datasets, combine_attrs="override")
print(merged)

raw_timeseries = client.get_timeseries(
    location_ids=["Amanzimtoti_River_level"],
    parameter_ids=["H.obs"],
    start_time=datetime(2025, 3, 14, 10, 0, tzinfo=timezone.utc),
    end_time=datetime(2025, 3, 15, 0, 0, tzinfo=timezone.utc),
    document_format="PI_JSON",
)
```

When `document_format="PI_JSON"`, `get_timeseries()` always returns the raw
PI JSON dictionary. If you need xarray objects, request
`document_format="PI_NETCDF"` instead.

See the repository notebook in [example_notebook.ipynb](../example_notebook.ipynb)
for a fuller walkthrough.
