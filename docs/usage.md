# Usage

## Overview

`fews-py-wrapper` provides a small typed wrapper around the Delft-FEWS
WebServices API. The main entry point is `FewsWebServiceClient`.

## Contents

- [Basic example](#basic-example)
- [Get parameters](#get-parameters)
- [Get locations](#get-locations)
- [Get time series](#get-time-series)
- [Post time series](#post-time-series)
- [Get filters](#get-filters)
- [Get workflows](#get-workflows)
- [Post run task](#post-run-task)
- [Get task runs](#get-task-runs)
- [Get task run status](#get-task-run-status)
- [Run and track a workflow end-to-end](#run-and-track-a-workflow-end-to-end)

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
from fews_py_wrapper import FewsWebServiceClient


client = FewsWebServiceClient(base_url="https://example.com/FewsWebServices/rest")

filters = client.get_filters()

for filter_ in filters.filters:
    print(filter_.id, filter_.name)

subfilters = client.get_filters(filter_id="MEAS")

for child in subfilters.filters[0].children:
    print(child.id, child.name)
```

## Get workflows

Use `get_workflows()` to retrieve the FEWS workflows exposed by the
`/workflows` endpoint. By default the wrapper requests `PI_JSON`, but you can
also request the raw `PI_XML` response.

```python
from fews_py_wrapper import FewsWebServiceClient


client = FewsWebServiceClient(base_url="https://example.com/FewsWebServices/rest")

workflows = client.get_workflows()

for workflow in workflows.workflows[:3]:
    print(workflow.id, workflow.name)

workflows_xml = client.get_workflows(document_format="PI_XML")
print(workflows_xml)
```

## Post run task

Use `post_runtask()` to trigger a one-off FEWS workflow execution through
`POST /runtask`. The wrapper returns the plain-text FEWS task ID, which you can
use with other FEWS task-run endpoints.

```python
from datetime import datetime, timezone

from fews_py_wrapper import FewsWebServiceClient


client = FewsWebServiceClient(base_url="https://example.com/FewsWebServices/rest")


task_id = client.post_runtask(
    workflow_id="ImportObscape",
    start_time=datetime(2025, 3, 18, 15, 0, tzinfo=timezone.utc),
    end_time=datetime(2025, 3, 18, 16, 0, tzinfo=timezone.utc),
    description="Run ImportObscape once from the wrapper",
    run_option="all",
)

print(task_id)
```

When needed, you can also provide `pi_parameters_xml_content` with PI model
parameters XML content encoded as text.

## Get task runs

Use `get_taskruns()` to inspect FEWS task runs for a specific workflow. By
default the wrapper requests `PI_JSON` and returns a typed
`PiTaskRunsResponse`. You can also request the raw `PI_XML` response.

FEWS itself returns only forecast task runs by default. This means that a
non-forecast workflow can legitimately return `task_runs=[]` unless you pass
`only_forecasts=False`.

```python
from fews_py_wrapper import FewsWebServiceClient


client = FewsWebServiceClient(base_url="https://example.com/FewsWebServices/rest")

taskruns = client.get_taskruns(
    workflow_id="ImportObscape",
    task_run_count=10,
)

for task_run in taskruns.task_runs:
    print(task_run.id, task_run.status, task_run.dispatch_time)

non_forecast_taskruns = client.get_taskruns(
    workflow_id="ftpClientConfig",
    only_forecasts=False,
    task_run_count=10,
)

print(non_forecast_taskruns.task_runs)

taskruns_xml = client.get_taskruns(
    workflow_id="ImportObscape",
    document_format="PI_XML",
)
print(taskruns_xml)
```

If you call `post_runtask()` and then immediately query `get_taskruns()` for a
non-forecast workflow without setting `only_forecasts=False`, an empty typed
response does not necessarily indicate an error in the wrapper or in FEWS.

## Get task run status

Use `get_taskrunstatus()` to inspect the current status of a task ID returned by
`post_runtask()`. The current FEWS OpenAPI specification exposes `PI_JSON` for
this endpoint, and the wrapper returns a typed `PiTaskRunStatusResponse`.

```python
from fews_py_wrapper import FewsWebServiceClient


client = FewsWebServiceClient(base_url="https://example.com/FewsWebServices/rest")

task_id = client.post_runtask(workflow_id="ImportObscape")

status = client.get_taskrunstatus(
    task_id=task_id,
    max_wait_millis=1000,
)

print(status.code, status.description, status.task_run_id)
```

Possible FEWS status codes are:
- ``I``: invalid
- ``P``:pending
- ``T``: terminated
- ``R``: running
- ``F``: failed
- ``C``: completed fully successful
- ``D``: completed partly successful
- ``A``: approved
- ``B``: approved partly successful.

## Run and track a workflow end-to-end

The workflow and task-run APIs can be combined in one script to:

1. retrieve the available workflows,
2. choose a workflow,
3. post a new task run,
4. look up the corresponding task run entry, and
5. inspect its current status.

The example below uses a unique description so the newly created task run can be
found reliably in the `get_taskruns()` response. It also uses
`only_forecasts=False` because some workflows are not forecast workflows, and in
that case FEWS may otherwise return `task_runs=[]` by default.

```python
import os
import time
from uuid import uuid4

from fews_py_wrapper import FewsWebServiceClient


base_url = os.getenv("FEWS_API_URL")
if not base_url:
    raise RuntimeError("Set FEWS_API_URL before running this example.")

fews_client = FewsWebServiceClient(base_url=base_url, verify_ssl=False)

# Step 1: retrieve workflows
workflows = fews_client.get_workflows()
if not workflows.workflows:
    raise RuntimeError("No workflows were returned by FEWS.")

# Prefer a known workflow when available; otherwise fall back to the first one.
preferred_workflow_ids = ["ImportObscape"]
workflow = next(
    (
        workflow
        for workflow in workflows.workflows
        if workflow.id in preferred_workflow_ids
    ),
    workflows.workflows[0],
)

print("Selected workflow:", workflow)
print()

# Step 2: post a new task run with a unique description.
task_description = f"fews-py-wrapper demo task run {uuid4()}"
task_id = fews_client.post_runtask(
    workflow_id=workflow.id,
    description=task_description,
)

print("Task run posted.")
print("Returned task ID:", task_id)
print()

# Step 3: poll task runs until the newly created task becomes visible.
matched_taskrun = None
for _ in range(5):
    taskruns = fews_client.get_taskruns(
        workflow_id=workflow.id,
        only_forecasts=False,
        task_run_count=25,
    )

    matched_taskrun = next(
        (
            taskrun
            for taskrun in taskruns.task_runs
            if taskrun.workflow_id == workflow.id
            and taskrun.description == task_description
        ),
        None,
    )
    if matched_taskrun is not None:
        break

    time.sleep(1)

if matched_taskrun is None:
    print("The new task run is not visible yet in get_taskruns().")
else:
    print("Matching task run entry returned by get_taskruns():")
    print(matched_taskrun)
print()

# Step 4: query the current task-run status.
status = fews_client.get_taskrunstatus(task_id=task_id, max_wait_millis=1000)

print("Task run status:", status.code, f"({status.description})")
print("taskRunId returned by FEWS:", status.task_run_id)
```

Notes:

- `post_runtask()` returns the FEWS task identifier immediately, but the task
  run may appear in `get_taskruns()` slightly later.
- `get_taskruns()` may need `only_forecasts=False` when you query a
  non-forecast workflow.
- `get_taskrunstatus()` currently uses the `PI_JSON` response defined by the
  FEWS OpenAPI specification.
