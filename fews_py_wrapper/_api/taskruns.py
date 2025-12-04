from fews_openapi_py_client import AuthenticatedClient, Client
from fews_openapi_py_client.api.tasks import taskruns

from fews_py_wrapper._api.base import ApiCaller


class Taskruns(ApiCaller):
    api_call_function = taskruns.sync_detailed

    def get(self, client: AuthenticatedClient | Client, **kwargs) -> dict:
        kwargs = self.update_api_call_kwargs(kwargs)
        return super().get(**kwargs)
