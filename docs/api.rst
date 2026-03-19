API Reference
=============

Client
------

.. autoclass:: fews_py_wrapper.fews_webservices.FewsWebServiceClient
   :members:
   :show-inheritance:

Models
------

.. autoclass:: fews_py_wrapper.models.PiBaseModel
   :members:
   :show-inheritance:

.. autoclass:: fews_py_wrapper.models.PiLocationAttribute
   :members:
   :show-inheritance:

.. autoclass:: fews_py_wrapper.models.PiLocationRelation
   :members:
   :show-inheritance:

.. autoclass:: fews_py_wrapper.models.PiLocation
   :members:
   :show-inheritance:

.. autoclass:: fews_py_wrapper.models.PiLocationsResponse
   :members:
   :show-inheritance:

.. autoclass:: fews_py_wrapper.models.PiParameter
   :members:
   :show-inheritance:

.. autoclass:: fews_py_wrapper.models.PiParametersResponse
   :members:
   :show-inheritance:

Utilities
---------

.. autofunction:: fews_py_wrapper.utils.format_datetime

.. autofunction:: fews_py_wrapper.utils.convert_timeseries_response_to_xarray

.. autofunction:: fews_py_wrapper.utils.format_time_args

.. autofunction:: fews_py_wrapper.utils.get_function_arg_names

.. autofunction:: fews_py_wrapper.utils.replace_dots_attrs_values

API Endpoint Wrappers
---------------------

.. autoclass:: fews_py_wrapper._api.base.ApiEndpoint
   :members:
   :exclude-members: endpoint_function
   :show-inheritance:

.. autoclass:: fews_py_wrapper._api.endpoints.Taskruns
   :members:
   :exclude-members: endpoint_function
   :show-inheritance:

.. autoclass:: fews_py_wrapper._api.endpoints.Parameters
   :members:
   :exclude-members: endpoint_function
   :show-inheritance:

.. autoclass:: fews_py_wrapper._api.endpoints.Locations
   :members:
   :exclude-members: endpoint_function
   :show-inheritance:

.. autoclass:: fews_py_wrapper._api.endpoints.TimeSeries
   :members:
   :exclude-members: endpoint_function
   :show-inheritance:

.. autoclass:: fews_py_wrapper._api.endpoints.WhatIfScenarios
   :members:
   :exclude-members: endpoint_function
   :show-inheritance:

.. autoclass:: fews_py_wrapper._api.endpoints.Workflows
   :members:
   :exclude-members: endpoint_function
   :show-inheritance:
