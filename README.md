![Tests](https://github.com/Deltares-research/fews-py-wrapper/workflows/Tests/badge.svg)

### fews-py-wrapper
User-friendly Python wrapper for the Delft-FEWS WebServices

### Documentation
The published documentation is available at [deltares-research.github.io/fews-py-wrapper](https://deltares-research.github.io/fews-py-wrapper/).

### How-to
See the [example notebook](example_notebook.ipynb) on how to use the FEWS py wrapper for interacting with the FEWS PI REST API.

### Quick example: get task runs

`get_taskruns()` queries the FEWS `/taskruns` endpoint. The `workflow_id`
argument is required by that endpoint; all other filters are optional.

```python
from datetime import datetime, timezone

from fews_py_wrapper import FewsWebServiceClient


client = FewsWebServiceClient(base_url="https://example.com/FewsWebServices/rest")

all_taskruns_for_workflow = client.get_taskruns(
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

### Contributing
For contributing to this project please see the [CONTRIBUTING](CONTRIBUTING.md).
