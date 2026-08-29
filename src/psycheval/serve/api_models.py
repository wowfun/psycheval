from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictRequest(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=True,
        validate_default=True,
        hide_input_in_errors=True,
    )

    def payload(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class LoginRequest(StrictRequest):
    password: str = Field(min_length=1)


class CatalogQueryRequest(StrictRequest):
    state: str
    page: int
    page_size: int
    search: str
    sort: str
    direction: str
    categories: list[str]
    tags: list[str]
    agents: list[str]
    models: list[str]
    results: list[str]
    views: list[str]
    browser_views: list[dict[str, Any]]
    tasks: list[str] = Field(default_factory=list)
    jobs: list[str] = Field(default_factory=list)
    providers: list[str] = Field(default_factory=list)


class CatalogSummaryRequest(StrictRequest):
    state: str
    search: str
    categories: list[str]
    tags: list[str]
    agents: list[str]
    models: list[str]
    tasks: list[str]
    jobs: list[str]
    providers: list[str]
    results: list[str]
    views: list[str]
    browser_views: list[dict[str, Any]]
    group_by: str


class SourceKeysRequest(StrictRequest):
    source_keys: list[str] = Field(min_length=1)


class SourceStateOperationRequest(SourceKeysRequest):
    active: bool


class SourceImportRequest(StrictRequest):
    path: str | None = None
    db: str | None = None
    session_id: str | None = None
    session_ids: list[str] | None = None
    adapter: str | None = None
    alias: str | None = None

    @model_validator(mode="after")
    def reject_ambiguous_batch_axes(self) -> SourceImportRequest:
        path_count = len(
            [line for line in (self.path or "").splitlines() if line.strip()]
        )
        if path_count > 1 and self.session_ids and len(self.session_ids) > 1:
            raise ValueError(
                "multiple paths cannot be combined with multiple session_ids"
            )
        return self


class SourcePatchRequest(StrictRequest):
    alias: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    notes: str | None = None
    active: bool | None = None

    @model_validator(mode="after")
    def require_change(self) -> SourcePatchRequest:
        if not self.model_fields_set:
            raise ValueError("at least one source field is required")
        return self


class ExportRequest(StrictRequest):
    kind: str
    query: dict[str, Any] | None = None
    source_keys: list[str] | None = None
    summary: dict[str, Any] | None = None


class AcpAgentInput(StrictRequest):
    id: str
    title: str
    command: str
    args: list[str] = Field(default_factory=list)


class ConfigPatchRequest(StrictRequest):
    locale: str | None = None
    adapter_defaults: dict[str, str | None] | None = None
    acp_agents: list[AcpAgentInput] | None = None

    @model_validator(mode="after")
    def require_change(self) -> ConfigPatchRequest:
        if not self.model_fields_set:
            raise ValueError("at least one configuration field is required")
        return self


class PromptPutRequest(StrictRequest):
    content: str


class BrowserViewsRequest(StrictRequest):
    browser_views: list[dict[str, Any]]


class ViewPutRequest(StrictRequest):
    filters: dict[str, Any]
    group_by: str
    notes: str = ""
    overwrite: bool = False


class ViewPatchRequest(StrictRequest):
    field: Literal["name", "configuration", "notes"]
    value: str


class ViewDeletionRequest(StrictRequest):
    names: list[str] = Field(min_length=1)


class ReportImportRequest(StrictRequest):
    path: str
    source_keys: list[str] = Field(default_factory=list)


class ReportBindingsRequest(StrictRequest):
    source_keys: list[str]


class DatabaseInspectionRequest(StrictRequest):
    db: str
    adapter: str | None = None


class PathSelectionRequest(StrictRequest):
    multiple: bool = True


class DatasetCreateRequest(StrictRequest):
    source: Literal["new", "existing"]
    id: str | None = None
    path: str
    package_name: str | None = None
    description: str = ""


class DatasetPatchRequest(StrictRequest):
    new_id: str
    path: str
    mount_ids: list[str] = Field(default_factory=list)


class DatasetUnregisterRequest(StrictRequest):
    dataset_ids: list[str] = Field(min_length=1)


class TaskCreateRequest(StrictRequest):
    directory: str
    package_name: str
    steps: int = 0


class TaskPatchRequest(StrictRequest):
    new_directory: str


class ManifestPutRequest(StrictRequest):
    pass


class TaskOperationItem(StrictRequest):
    dataset_id: str
    task: str | None = None
    entry_id: str | None = None
    etag: str
    directory: str | None = None

    @model_validator(mode="after")
    def require_one_identity(self) -> TaskOperationItem:
        if bool(self.task) == bool(self.entry_id):
            raise ValueError("each item must identify either task or entry_id")
        return self


class TaskStateOperationRequest(StrictRequest):
    archived: bool
    items: list[TaskOperationItem] = Field(min_length=1)


class TaskDeletionRequest(StrictRequest):
    items: list[TaskOperationItem] = Field(min_length=1)


class FilePutRequest(StrictRequest):
    content: str


class FilePatchRequest(StrictRequest):
    new_path: str


class FileCreateRequest(StrictRequest):
    kind: Literal["file", "directory", "upload"]
    path: str
    content: str | None = None


class MountCreateRequest(StrictRequest):
    path: str


class MountPatchRequest(StrictRequest):
    new_id: str
    path: str
    dataset_ids: list[str] = Field(default_factory=list)


class MountDeletionRequest(StrictRequest):
    mount_ids: list[str] = Field(min_length=1)


class AcpContextRequest(StrictRequest):
    context: dict[str, Any]
    embedded_context: bool
