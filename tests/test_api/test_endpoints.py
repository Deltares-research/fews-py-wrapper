# from fews_py_wrapper._api.taskruns import retrieve_parameter_models, retrieve_taskruns


# def test_retrieve_taskruns(mocker):
#     workflow_id = "test_workflow_id"
#     task_ids = ["test_task_id"]
#     document_format = "PI_JSON"
#     mock_response = httpx.Response(
#         status_code=200,
#         content=json.dumps({"taskruns": []}).encode(),
#         headers={"content-type": "application/json"},
#     )
#     mocker.patch(
#         "fews_py_wrapper._api.taskruns.taskruns.sync_detailed",
#         return_value=mock_response,
#     )
#     response = retrieve_taskruns(
#         client=Mock(),
#         workflow_id=workflow_id,
#         task_ids=task_ids,
#         document_format=document_format,
#     )
#     assert response == {"taskruns": []}
#     mock_response.status_code = 404
#     mock_response.raise_for_status = Mock(side_effect=requests.HTTPError)
#     with pytest.raises(requests.HTTPError):
#         retrieve_taskruns(
#             client=Mock(),
#             workflow_id=workflow_id,
#             task_ids=task_ids,
#             document_format=document_format,
#         )


# def test_retrieve_parameter_models() -> None:
#     """Test the retrieve_argument_models function."""
#     kwargs = {
#         "document_format": "PI_JSON",
#         "only_current": True,
#         "only_forecasts": False,
#     }
#     converted_kwargs = retrieve_parameter_models(kwargs)

#     assert isinstance(converted_kwargs["document_format"], TaskrunsDocumentFormat)
#     assert converted_kwargs["document_format"] == TaskrunsDocumentFormat.PI_JSON

#     assert isinstance(converted_kwargs["only_current"], TaskrunsOnlyCurrent)
#     assert converted_kwargs["only_current"] == TaskrunsOnlyCurrent.TRUE

#     assert isinstance(converted_kwargs["only_forecasts"], TaskrunsOnlyForecasts)
#     assert converted_kwargs["only_forecasts"] == TaskrunsOnlyForecasts.FALSE

#     with pytest.raises(ValueError, match="Invalid argument value: "):
#         kwargs = {"document_format": "INVALID_FORMAT"}
#         retrieve_parameter_models(kwargs)
