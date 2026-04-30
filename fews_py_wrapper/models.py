from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

__all__ = [
    "PiBaseModel",
    "PiFilterBoundingBox",
    "PiFilter",
    "PiFiltersResponse",
    "PiLocationAttribute",
    "PiLocationRelation",
    "PiLocation",
    "PiLocationsResponse",
    "PiParameter",
    "PiParametersResponse",
    "PiTaskRun",
    "PiTaskRunStatusResponse",
    "PiTaskRunsResponse",
    "PiWhatIfScenarioDescriptor",
    "PiWhatIfScenariosResponse",
    "PiWhatIfTemplateCardinalTimeStep",
    "PiWhatIfTemplateProperty",
    "PiWhatIfTemplateRelativeViewPeriod",
    "PiWhatIfTemplate",
    "PiWhatIfTemplatesResponse",
    "PiWorkflow",
    "PiWorkflowsResponse",
]


class PiBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class PiFilterBoundingBox(PiBaseModel):
    """Typed FEWS PI filter bounding box."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    crs: str | None = None
    minx: float | None = None
    maxx: float | None = None
    miny: float | None = None
    maxy: float | None = None


class PiFilter(PiBaseModel):
    """Typed FEWS PI filter entry."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str
    name: str | None = None
    description: str | None = None
    bounding_box: PiFilterBoundingBox | None = Field(default=None, alias="boundingBox")
    children: list["PiFilter"] = Field(
        default_factory=list,
        validation_alias=AliasChoices("children", "child"),
    )


class PiFiltersResponse(PiBaseModel):
    """Collection model for the FEWS PI filters response."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    version: str | None = None
    filters: list[PiFilter] = Field(
        default_factory=list,
        validation_alias=AliasChoices("filters", "filter"),
    )


class PiLocationAttribute(PiBaseModel):
    """Typed FEWS PI location attribute."""

    id: str | None = None
    name: str | None = None
    description: str | None = None
    start_date_time: str | None = Field(default=None, alias="startDateTime")
    end_date_time: str | None = Field(default=None, alias="endDateTime")
    text: str | None = None
    number: float | None = None
    boolean: bool | None = None
    date_time: str | None = Field(default=None, alias="dateTime")

    @model_validator(mode="after")
    def validate_value_choice(self) -> "PiLocationAttribute":
        value_fields = [self.text, self.number, self.boolean, self.date_time]
        populated_fields = sum(value is not None for value in value_fields)
        if populated_fields != 1:
            raise ValueError(
                "A PI location attribute must define exactly one of text, number, "
                "boolean, or dateTime."
            )
        return self


class PiLocationRelation(PiBaseModel):
    """Typed FEWS PI location relation."""

    related_location_id: str = Field(alias="relatedLocationId")
    start_date_time: str | None = Field(default=None, alias="startDateTime")
    end_date_time: str | None = Field(default=None, alias="endDateTime")
    id: str | None = None


class PiLocation(PiBaseModel):
    """Typed representation of a FEWS PI location entry."""

    location_id: str = Field(alias="locationId")
    description: str | None = None
    short_name: str | None = Field(default=None, alias="shortName")
    start_date_time: str | None = Field(default=None, alias="startDateTime")
    end_date_time: str | None = Field(default=None, alias="endDateTime")
    lat: float | None = None
    lon: float | None = None
    x: float | None = None
    y: float | None = None
    z: float | None = None
    parent_location_id: str | None = Field(default=None, alias="parentLocationId")
    relations: list[PiLocationRelation] = Field(
        default_factory=list,
        validation_alias=AliasChoices("relations", "relation"),
    )
    attributes: list[PiLocationAttribute] = Field(
        default_factory=list,
        validation_alias=AliasChoices("attributes", "attribute"),
    )


class PiLocationsResponse(PiBaseModel):
    """Collection model for the FEWS PI locations response."""

    version: str | None = None
    geo_datum: str | None = Field(default=None, alias="geoDatum")
    locations: list[PiLocation] = Field(
        default_factory=list,
        validation_alias=AliasChoices("locations", "location"),
    )


class PiParameter(PiBaseModel):
    """Typed FEWS PI time-series parameter entry."""

    id: str
    name: str | None = None
    short_name: str | None = Field(default=None, alias="shortName")
    parameter_type: str = Field(alias="parameterType")
    unit: str
    display_unit: str | None = Field(default=None, alias="displayUnit")
    uses_datum: bool = Field(default=False, alias="usesDatum")
    parameter_group: str | None = Field(default=None, alias="parameterGroup")
    parameter_group_name: str | None = Field(default=None, alias="parameterGroupName")
    attributes: list[PiLocationAttribute] = Field(
        default_factory=list,
        validation_alias=AliasChoices("attributes", "attribute"),
    )

    @model_validator(mode="after")
    def validate_parameter_type(self) -> "PiParameter":
        if self.parameter_type not in {"instantaneous", "accumulative", "mean"}:
            raise ValueError(
                "parameterType must be one of instantaneous, accumulative, or mean."
            )
        return self


class PiParametersResponse(PiBaseModel):
    """Collection model for the FEWS PI time-series parameters response."""

    version: str | None = None
    parameters: list[PiParameter] = Field(
        default_factory=list,
        validation_alias=AliasChoices("parameters", "param", "timeSeriesParameters"),
    )


class PiTaskRun(PiBaseModel):
    """Typed FEWS task-run descriptor."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str
    forecast: bool | None = None
    current: bool | None = None
    status: str | None = None
    workflow_id: str | None = Field(default=None, alias="workflowId")
    topology_node_id: str | None = Field(default=None, alias="topologyNodeId")
    scenario_id: str | None = Field(default=None, alias="scenarioId")
    mc_id: str | None = Field(default=None, alias="mcId")
    dispatch_time: str | None = Field(default=None, alias="dispatchTime")
    time_zero: str | None = Field(default=None, alias="time0")
    cold_state_id: str | None = Field(default=None, alias="coldStateId")
    user: str | None = None
    description: str | None = None


class PiTaskRunStatusResponse(PiBaseModel):
    """Typed FEWS task-run status response."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    version: str | None = None
    code: str | None = None
    description: str | None = None
    task_run_id: str | None = Field(default=None, alias="taskRunId")

    @model_validator(mode="after")
    def validate_code(self) -> "PiTaskRunStatusResponse":
        valid_codes = {"I", "P", "T", "R", "F", "C", "D", "A", "B"}
        if self.code is not None and self.code not in valid_codes:
            raise ValueError(
                "taskrunstatus code must be one of I, P, T, R, F, C, D, A, or B."
            )
        return self


class PiTaskRunsResponse(PiBaseModel):
    """Collection model for the FEWS task-runs response."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    task_runs: list[PiTaskRun] = Field(
        default_factory=list,
        validation_alias=AliasChoices("taskRuns", "taskruns", "taskRun", "taskrun"),
    )


class PiWhatIfScenarioDescriptor(PiBaseModel):
    """Typed FEWS what-if scenario descriptor."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str
    name: str | None = None
    what_if_template_id: str | None = Field(default=None, alias="whatIfTemplateId")
    single_run_what_if: bool | None = Field(default=None, alias="singleRunWhatIf")
    properties: list[dict[str, Any]] = Field(default_factory=list)


class PiWhatIfScenariosResponse(PiBaseModel):
    """Collection model for the FEWS what-if scenarios response."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    scenario_descriptors: list[PiWhatIfScenarioDescriptor] = Field(
        default_factory=list,
        validation_alias=AliasChoices(
            "whatIfScenarioDescriptors", "whatifscenariodescriptors"
        ),
    )


class PiWhatIfTemplateRelativeViewPeriod(PiBaseModel):
    """Typed FEWS what-if template relative-view-period metadata."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    unit: str | None = None
    start: str | None = None
    end: str | None = None


class PiWhatIfTemplateCardinalTimeStep(PiBaseModel):
    """Typed FEWS what-if template cardinal-time-step metadata."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    time_zone: str | None = Field(default=None, alias="timeZone")
    unit: str | None = None
    multiplier: int | None = None


class PiWhatIfTemplateProperty(PiBaseModel):
    """Typed FEWS what-if template property descriptor."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str
    name: str | None = None
    type: str | None = None
    description: str | None = None
    default_value: Any | None = Field(default=None, alias="defaultValue")
    max_value: Any | None = Field(default=None, alias="maxValue")
    min_value: Any | None = Field(default=None, alias="minValue")
    enum_values: list[Any] = Field(default_factory=list, alias="enumValues")
    relative_view_period: PiWhatIfTemplateRelativeViewPeriod | None = Field(
        default=None, alias="relativeViewPeriod"
    )
    cardinal_time_step: PiWhatIfTemplateCardinalTimeStep | None = Field(
        default=None, alias="cardinalTimeStep"
    )


class PiWhatIfTemplate(PiBaseModel):
    """Typed FEWS what-if template descriptor."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str
    name: str | None = None
    properties: list[PiWhatIfTemplateProperty] = Field(default_factory=list)
    default_single_run_what_if_setting: bool | None = Field(
        default=None, alias="defaultSingleRunWhatIfSetting"
    )
    overrulable_single_run_what_if: bool | None = Field(
        default=None, alias="overrulableSingleRunWhatIf"
    )


class PiWhatIfTemplatesResponse(PiBaseModel):
    """Collection model for the FEWS what-if templates response."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    templates: list[PiWhatIfTemplate] = Field(
        default_factory=list,
        validation_alias=AliasChoices("whatIfTemplates", "whatiftemplates"),
    )


class PiWorkflow(PiBaseModel):
    """Typed FEWS workflow descriptor."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str
    name: str | None = None
    description: str | None = None


class PiWorkflowsResponse(PiBaseModel):
    """Collection model for the FEWS workflows response."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    workflows: list[PiWorkflow] = Field(default_factory=list)


PiFilter.model_rebuild()
