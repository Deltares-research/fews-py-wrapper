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
    "PiTaskRunsResponse",
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


class PiTaskRunsResponse(PiBaseModel):
    """Collection model for the FEWS task-runs response."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    task_runs: list[PiTaskRun] = Field(
        default_factory=list,
        validation_alias=AliasChoices("taskRuns", "taskruns", "taskRun", "taskrun"),
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
