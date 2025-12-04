import inspect
import json
from datetime import datetime
from typing import get_args, get_origin

from fews_openapi_py_client import AuthenticatedClient, Client
from fews_openapi_py_client.types import Unset


class ApiCaller:
    api_call_function: callable

    def get(self, client: AuthenticatedClient | Client, **kwargs) -> dict:
        response = self.api_call_function(client=client, **kwargs)
        if response.status_code != 200:
            response.raise_for_status()
        return json.loads(response.content.decode("utf-8"))

    def post(self, client: AuthenticatedClient | Client, **kwargs) -> dict: ...

    def input_args(self) -> list:
        return list(inspect.signature(self.api_call_function).parameters)

    def update_api_call_kwargs(self, kwargs: dict) -> dict:
        param_models = self._get_parameter_models(self.api_call_function)
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
        function_params = inspect.signature(self.api_call_function).parameters
        standard_types = (str, int, float, bool, list, dict, tuple, set, datetime)
        parameter_models = {}
        for param_name, param in function_params.items():
            if param_name == "client":
                continue
            annotation = param.annotation
            args = get_args(annotation)

            # Check if argument annotation contains standard types
            if self._contains_types(args, standard_types):
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

    def _contains_types(self, args, check_types):
        for arg in args:
            if arg in check_types:
                return True
            if isinstance(get_origin(arg), (type(list), type(tuple))):
                return self._contains_types(get_args(arg), check_types)
        return False

    def _convert_bools(self, arg):
        if arg:
            return "true"
        return "false"
