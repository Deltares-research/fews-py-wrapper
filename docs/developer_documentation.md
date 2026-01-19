# Developer Documentation

## Setting Up a Developer Environment

This guide will help you set up a development environment for the fews-py-wrapper project.

### Prerequisites

- **Python**: 3.9 or higher (check with `python --version`)
- **uv**: A fast Python package installer and resolver (recommended)
- **Git**: For cloning and version control

### Option 1: Using uv (Recommended)

#### Installing uv

`uv` is a fast, reliable Python package installer written in Rust. Install it using:

**On macOS or Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**On Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy BypassUser -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Using pip:**
```bash
pip install uv
```

For more information, visit the [uv documentation](https://docs.astral.sh/uv/).

#### Setting Up the Development Environment with uv

1. Clone the repository:
```bash
git clone https://github.com/Deltares-research/fews-py-wrapper.git
cd fews-py-wrapper
```

2. Create a virtual environment and install dependencies:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install the project in development mode with all dependencies:
```bash
uv pip install -e ".[dev]"
```

Or, if you prefer using uv's dependency groups:
```bash
uv sync --group dev
```

#### Using uv Commands

**Running tests:**
```bash
uv run pytest
```

**Running tests with coverage:**
```bash
uv run pytest --cov=fews_py_wrapper
```

**Installing additional packages:**
```bash
uv pip install package-name
```

**Updating dependencies:**
```bash
uv sync
```

### Option 2: Using pip and venv (Traditional)

If you prefer not to use `uv`, you can use Python's built-in tools:

1. Clone the repository:
```bash
git clone https://github.com/Deltares-research/fews-py-wrapper.git
cd fews-py-wrapper
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install the project in development mode:
```bash
pip install -e ".[dev]"
```

## Development Workflow

### Running Tests

Execute the test suite:
```bash
uv run pytest
```

Run tests with coverage report:
```bash
uv run pytest --cov=fews_py_wrapper
```

Run tests for a specific module:
```bash
uv run pytest tests/test_utils.py
```

### Code Quality

The project uses **ruff** for linting and formatting. Configuration is in `pyproject.toml`.

Format your code:
```bash
uv run ruff format .
```

Check for linting issues:
```bash
uv run ruff check .
```

Fix linting issues automatically:
```bash
uv run ruff check . --fix
```

### Pre-commit Hooks

The project uses `pre-commit` to run checks before each commit:

```bash
uv run pre-commit install
```

This will automatically run linting and other checks before you commit code.

## Adding Endpoints to the FEWS WebService Client

This section explains how to add new API endpoints to the `FewsWebServiceClient` class.

### Architecture Overview

The endpoint system uses a wrapper pattern with three main components:

1. **`ApiEndpoint`** ([_api/base.py](_api/base.py)): Base class for all endpoints that wraps OpenAPI client functions
2. **Endpoint implementations** ([_api/endpoints.py](_api/endpoints.py)): Specific endpoint classes inheriting from `ApiEndpoint`
3. **Client methods** ([fews_webservices.py](fews_webservices.py)): Public methods in `FewsWebServiceClient` that use endpoints

### Step-by-Step Guide

#### 1. Create an Endpoint Class

In [_api/endpoints.py](_api/endpoints.py), create a new class inheriting from `ApiEndpoint`:

```python
from fews_openapi_py_client import AuthenticatedClient, Client
from fews_openapi_py_client.api.your_module import your_endpoint_function

from fews_py_wrapper._api.base import ApiEndpoint


class YourEndpoint(ApiEndpoint):
    endpoint_function = staticmethod(your_endpoint_function.sync_detailed)

    def execute(self, client: AuthenticatedClient | Client, **kwargs) -> dict:
        # Optional: Add custom parameter validation or transformation
        kwargs = self.update_input_kwargs(kwargs)
        return super().execute(client=client, **kwargs)
```

**Key points:**
- Set `endpoint_function` to the `sync_detailed` version from the OpenAPI client
- Override `execute()` to add custom logic (parameter validation, formatting, etc.)
- Call `self.update_input_kwargs()` to automatically convert parameters to correct enum types
- Call `super().execute()` to handle the actual API call

#### 2. Add a Client Method

In [fews_webservices.py](fews_webservices.py), add a public method to `FewsWebServiceClient`:

```python
def your_method_name(
    self,
    *,
    param1: str,
    param2: int | None = None,
    document_format: str | None = "PI_JSON",
    **kwargs,
) -> dict:
    """Brief description of what the method does.

    Args:
        param1: Description of param1.
        param2: Description of param2.
        document_format: Format of the returned document (default: "PI_JSON").
        **kwargs: Additional keyword arguments.

    Returns:
        dict: Parsed JSON response from the API.
    """
    non_none_kwargs = self._collect_non_none_kwargs(
        local_kwargs=locals().copy(), pop_kwargs=[]
    )
    return YourEndpoint().execute(client=self.client, **non_none_kwargs)
```

**Key points:**
- Use keyword-only arguments (after `*`) for clarity
- Use `_collect_non_none_kwargs()` to filter out `None` values
- Always include `document_format` parameter (default: "PI_JSON")
- Call the endpoint's `execute()` method with the client and filtered kwargs

#### 3. Add Custom Parameter Handling (Optional)

If your endpoint needs special parameter handling (like datetime formatting), add methods to your endpoint class:

```python
class YourEndpoint(ApiEndpoint):
    endpoint_function = staticmethod(your_endpoint_function.sync_detailed)

    def execute(self, client: AuthenticatedClient | Client, **kwargs) -> dict:
        kwargs = self.update_input_kwargs(kwargs)
        kwargs = self._format_custom_params(kwargs)  # Custom processing
        return super().execute(client=client, **kwargs)

    def _format_custom_params(self, kwargs: dict) -> dict:
        """Transform parameters to the format expected by the API."""
        # Example: format datetime objects
        if "timestamp" in kwargs and kwargs["timestamp"] is not None:
            kwargs["timestamp"] = format_datetime(kwargs["timestamp"])
        return kwargs
```

#### 4. Write Tests

Add tests for your new endpoint in [tests/test_api/](tests/test_api/):

```python
# tests/test_api/test_your_endpoint.py
from unittest.mock import Mock
import pytest
from fews_py_wrapper._api.endpoints import YourEndpoint


def test_your_endpoint_execute(mock_client):
    """Test that YourEndpoint executes correctly."""
    endpoint = YourEndpoint()
    response = endpoint.execute(client=mock_client, param1="test")
    assert response is not None


def test_your_endpoint_input_args():
    """Test that input_args returns expected parameters."""
    endpoint = YourEndpoint()
    args = endpoint.input_args()
    assert "param1" in args
    assert "param2" in args
```

Also add integration tests in [tests/test_fews_webservices.py](tests/test_fews_webservices.py):

```python
def test_your_method(fews_client):
    """Test the client method."""
    result = fews_client.your_method_name(param1="test")
    assert isinstance(result, dict)
```

#### 5. Update the `endpoint_arguments()` Method

If you want to expose endpoint arguments, add a case in the `endpoint_arguments()` method:

```python
def endpoint_arguments(self, endpoint: str) -> list[str]:
    """Get the arguments for a specific FEWS web service endpoint."""
    if endpoint == "timeseries":
        return TimeSeries().input_args()
    elif endpoint == "your_endpoint":
        return YourEndpoint().input_args()
    else:
        raise ValueError(f"Unknown endpoint: {endpoint}")
```



## Project Structure

```
fews-py-wrapper/
├── fews_py_wrapper/          # Main package
│   ├── __init__.py
│   ├── fews_webservices.py   # Main module
│   ├── utils.py              # Utility functions
│   └── _api/                 # API implementation
│       ├── __init__.py
│       ├── base.py
│       └── endpoints.py
├── tests/                    # Test suite
│   ├── conftest.py          # Test configuration
│   ├── test_fews_webservices.py
│   ├── test_utils.py
│   └── test_api/
├── docs/                     # Documentation
├── pyproject.toml           # Project configuration
├── README.md                # Project overview
└── example_notebook.ipynb   # Example usage notebook
```

## Dependencies

### Core Dependencies
- `fews-openapi-py-client`: OpenAPI client for FEWS
- `pandas`: Data manipulation and analysis
- `xarray`: Working with multi-dimensional arrays
- `requests`: HTTP requests
- `python-dotenv`: Environment variable management
- `ipykernel`: Jupyter kernel support

### Development Dependencies
- `pytest`: Testing framework
- `pytest-cov`: Coverage reporting
- `pytest-mock`: Mocking support
- `ruff`: Linting and formatting
- `pre-commit`: Git hooks management

## Troubleshooting

### Virtual environment not activated
Make sure to activate the virtual environment:
```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Import errors when running tests
Ensure all dependencies are installed:
```bash
uv sync --group dev
```

## Contributing

When contributing to this project:
1. Create a new branch for your changes
2. Make your changes following the code style
3. Run tests to ensure everything passes
4. Run `ruff format` to format your code
5. Commit and push your changes
6. Submit a pull request
