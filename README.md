![Tests](https://github.com/Deltares-research/fews-py-wrapper/workflows/Tests/badge.svg)

### fews-py-wrapper
User-friendly Python wrapper for the Delft-FEWS WebServices

### Documentation
The published documentation is available at [deltares-research.github.io/fews-py-wrapper](https://deltares-research.github.io/fews-py-wrapper/).

### How-to
See the [usage document](docs/usage.md) on how to use the FEWS-py-wrapper for interacting with the FEWS PI REST API.


By default, `get_timeseries()` requests `PI_NETCDF` and returns a
`list[xarray.Dataset]`, preserving the original NetCDF member layout returned by
FEWS.

### Contributing
For contributing to this project please see the [CONTRIBUTING](CONTRIBUTING.md).
