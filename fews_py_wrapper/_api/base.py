import inspect
import json
from datetime import datetime
from enum import Enum
from typing import get_args, get_origin

from fews_openapi_py_client import AuthenticatedClient, Client
from fews_openapi_py_client.types import Unset


class ApiEndpoint:
    """Wraps a single API endpoint with parameter handling and validation."""

    endpoint_function: callable

    def execute(
        self,
        *,
        client: AuthenticatedClient | Client,
        document_format: Enum,
        **kwargs,
    ) -> dict:
        """
        Execute the API endpoint call.

        Args:
            client: AuthenticatedClient or Client instance for API calls.
            document_format: Format of the returned document.
            **kwargs: Keyword arguments for the API call.

        Returns:
            dict: Parsed JSON response from the API.

        """
        if document_format.value == "PI_JSON":
            kwargs.update(document_format=document_format)
            return self._handle_json_call(client=client, **kwargs)
        else:
            raise NotImplementedError(
                f"Document format {document_format} not implemented."
            )

    def input_args(self) -> list:
        """
        Get the list of input argument names for the API endpoint.

        Returns:
            list: Parameter names accepted by the API endpoint function.
        """
        return list(inspect.signature(self.endpoint_function).parameters)

    def update_input_kwargs(self, kwargs: dict) -> dict:
        """
        Convert and validate kwargs to match API endpoint parameter models.

        Converts values to their appropriate enum types and handles boolean
        conversions as needed.

        Args:
            kwargs: Dictionary of keyword arguments to update.

        Returns:
            dict: Updated kwargs with values converted to correct types.

        Raises:
            ValueError: If an argument value is invalid or cannot be converted.
        """
        param_models = self._get_parameter_models()
        updated_kwargs = {}
        try:
            for key, value in kwargs.items():
                if key in param_models:
                    if param_models[key]["is_bool"]:
                        updated_kwargs[key] = param_models[key]["model"](
                            self._convert_bools(value)
                        )
                    else:
                        updated_kwargs[key] = param_models[key]["model"](value)
                else:
                    updated_kwargs[key] = value
            return updated_kwargs
        except ValueError as e:
            raise ValueError(f"Invalid argument value: {e}") from e

    def _get_parameter_models(self) -> dict:
        """
        Extract parameter models from the API endpoint function signature.

        Identifies enum types and boolean flags from function parameter
        annotations, excluding standard types and the 'client' parameter.

        Returns:
            dict: Mapping of parameter names to model information containing:
                - 'is_bool': bool indicating if the parameter is a boolean enum
                - 'model': The enum class for the parameter

        Raises:
            ValueError: If a parameter has unexpected annotation structure.
        """
        function_params = inspect.signature(self.endpoint_function).parameters
        standard_types = (str, int, float, bool, list, dict, tuple, set, datetime)
        parameter_models = {}
        for param_name, param in function_params.items():
            if param_name == "client":
                continue
            annotation = param.annotation
            args = get_args(annotation)

            # Check if argument annotation contains standard types
            if self._contains_types(args, standard_types) or not args:
                continue

            arg_list = list(args)
            if Unset in arg_list:
                arg_list.remove(Unset)

            if not len(arg_list) == 1:
                raise ValueError(
                    f"Expected two annotation arguments, but got"
                    f" {len(arg_list)} for {param_name}"
                )

            m_dict = {}
            if "TRUE" in arg_list[0].__members__.keys():
                m_dict["is_bool"] = True
            else:
                m_dict["is_bool"] = False
            m_dict["model"] = arg_list[0]
            parameter_models[param_name] = m_dict
        return parameter_models

    def _contains_types(self, args: tuple | list, check_types: tuple | list) -> bool:
        """
        Recursively check if any type in args is contained in check_types.

        Handles nested generic types like list[str] or dict[str, int].

        Args:
            args: Tuple of type arguments to check.
            check_types: Tuple of types to check against.

        Returns:
            bool: True if any arg matches a type in check_types, False otherwise.
        """
        for arg in args:
            if arg in check_types:
                return True
            if isinstance(get_origin(arg), (type(list), type(tuple))):
                return self._contains_types(get_args(arg), check_types)
        return False

    def _convert_bools(self, arg):
        """
        Convert a boolean value to the string representation expected by the API.

        Args:
            arg: Boolean value to convert.

        Returns:
            str: "true" if arg is truthy, "false" otherwise.
        """
        if arg is True:
            return "true"
        if arg is False:
            return "false"
        raise ValueError(f"Expected boolean value, got {arg}")

    def _handle_json_call(self, client, **kwargs):
        """Internal method to call the API endpoint with specified HTTP method."""
        response = self.endpoint_function(client=client, **kwargs)
        if response.status_code != 200:
            response.raise_for_status()
        return json.loads(response.content.decode("utf-8"))
