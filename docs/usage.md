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

## Post time series

Use `post_timeseries()` to write PI time series data back to FEWS. The wrapper
accepts PI XML content and/or PI JSON content. The FEWS response is returned as
PI diagnostic XML.

```python
from pathlib import Path

from fews_py_wrapper import FewsWebServiceClient


client = FewsWebServiceClient(base_url="https://example.com/FewsWebServices/rest")

xml_payload = Path("tests/test_data/post_timeseries.xml").read_text(encoding="utf-8")

diag_xml = client.post_timeseries(
    pi_time_series_xml_content=xml_payload,
    filter_id="MEAS",
)

print(diag_xml)
```

The repository includes small reusable sample payloads in
`tests/test_data/post_timeseries.xml` and `tests/test_data/post_timeseries.json`.

## Get filters

Use `get_filters()` to retrieve the available FEWS filters. Optionally pass a
`filter_id` to retrieve only the subfilters of that filter.

```python
filters = client.get_filters()

subfilters = client.get_filters(filter_id="MEAS")
```

## Get task runs

Use `get_taskruns()` to inspect task runs for a FEWS workflow. The
`workflow_id` argument is required by the FEWS `/taskruns` endpoint; all other
filters are optional.

```python
taskruns = client.get_taskruns(
    workflow_id="RunParticleTracking",
)

specific_taskruns = client.get_taskruns(
    workflow_id="RunParticleTracking",
    task_run_ids=["SA5_1", "SA5_2"],
)

filtered_taskruns = client.get_taskruns(
    workflow_id="RunParticleTracking",
    start_forecast_time=datetime(2025, 3, 14, 0, 0, tzinfo=timezone.utc),
    end_forecast_time=datetime(2025, 3, 15, 0, 0, tzinfo=timezone.utc),
    task_run_status_ids=["Completed fully successful"],
    only_forecasts=True,
)
```

## Get what-if scenarios

Use `get_whatifscenarios()` to retrieve FEWS what-if scenarios, optionally
filtered by template, scenario, or workflow.

```python
whatif_scenarios = client.get_whatifscenarios(
    what_if_template_id="mywhatIfTemplateId",
)

specific_whatif_scenario = client.get_whatifscenarios(
    what_if_scenario_id="myWhatIfScenarioId",
)
```

## Post what-if scenario

Use `post_whatifscenarios()` to create or trigger a FEWS what-if scenario.

```python
created_scenario = client.post_whatifscenarios(
    what_if_template_id="mywhatIfTemplateId",
    single_run_what_if=True,
    name="Scenario created from Python",
)

print(created_scenario)
```
