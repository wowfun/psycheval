"""Dataset Task previews, manual counts, custom metadata, and exports."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Annotated, Any, Literal

import xlsxwriter
from fastapi import Depends, FastAPI, Header, Request, Response
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

from psycheval.config import ManualRuleCount
from psycheval.harbor.task_metadata import (
    custom_metadata_group_keys,
    is_custom_column_id,
    parse_custom_column_id,
    validate_custom_metadata_key,
    validate_custom_metadata_value,
)
from psycheval.harbor.task_resources import task_totals
from psycheval.i18n import messages_for
from psycheval.serve.api_access import (
    ADMIN_ACCESS,
    GUEST_ACCESS,
    access,
    mutation_guard,
    require_admin,
    role_for,
)
from psycheval.serve.api_http import (
    etag,
    expect_revision,
    if_match_value,
    json_response,
    operation_payload,
    operation_response,
)
from psycheval.serve.api_support import harbor_workspace, writable_runtime
from psycheval.serve.harbor_workspace import HarborWorkspaceError, config_revision
from psycheval.serve.summary_xlsx import EXCEL_CONTENT_TYPE
from psycheval.serve.visibility import (
    project_harbor_inventory,
    project_harbor_text_file,
)

BUILTIN_SUMMARY_GROUPINGS = frozenset(
    ("overall", "dataset", "category", "difficulty", "tags")
)


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class TaskRuleCount(_Request):
    count: ManualRuleCount | None


CustomMetadataKey = Annotated[str, AfterValidator(validate_custom_metadata_key)]
CustomMetadataValue = Annotated[Any, AfterValidator(validate_custom_metadata_value)]


class TaskMetadataPatch(_Request):
    key: CustomMetadataKey
    value: CustomMetadataValue = None


class TaskMetadataBatchItem(_Request):
    dataset_id: str
    task: str
    etag: str


class TaskMetadataBatchOperation(_Request):
    key: CustomMetadataKey
    value: CustomMetadataValue = None
    overwrite: bool = False
    items: list[TaskMetadataBatchItem] = Field(min_length=1, max_length=100_000)


class TaskPreview(_Request):
    path: str
    content: str = Field(max_length=2 * 1024 * 1024)


class TaskRowRef(_Request):
    dataset_id: str
    task: str
    item_key: str | None = None


class TaskExport(_Request):
    kind: Literal["xlsx", "json"]
    mode: Literal["tasks", "items", "summary"]
    rows: list[TaskRowRef] = Field(max_length=100_000)
    columns: list[str] = Field(default_factory=list, max_length=128)
    group_by: str = "overall"
    comparison_groups: list[str | None] | None = Field(default=None, max_length=100_000)

    @field_validator("group_by")
    @classmethod
    def _validate_group_by(cls, value: str) -> str:
        if value in BUILTIN_SUMMARY_GROUPINGS or is_custom_column_id(value):
            return value
        raise ValueError(f"Invalid Task summary grouping: {value}")


TASK_COLUMNS = {
    "dataset": ("harbor_dataset", "Dataset"),
    "task": ("task", "Task"),
    "tags": ("tags", "Tags"),
    "instruction": ("task_instruction", "Instruction"),
    "skill_count": ("task_skills", "Skills"),
    "input_file_count": ("task_files", "Files"),
    "has_prepare": ("task_prepare", "Prepare"),
    "rule_count": ("task_rules", "Rules"),
    "rubric_count": ("task_rubrics", "Rubrics"),
    "scoring_item_count": ("task_scoring_items", "Scoring items"),
    "scoring_comment_count": ("scoring_comments", "Scoring comments"),
}
ITEM_COLUMNS = {
    key: value
    for key, value in TASK_COLUMNS.items()
    if key
    not in {"rule_count", "rubric_count", "scoring_item_count", "scoring_comment_count"}
} | {
    "step": ("task_scoring_step", "Step"),
    "id": ("task_scoring_id", "ID"),
    "type": ("task_scoring_type", "Type"),
    "question": ("task_scoring_question", "Question"),
    "pass_criteria": ("task_scoring_pass", "Pass criteria"),
    "fail_criteria": ("task_scoring_fail", "Fail criteria"),
    "scope_limits": ("task_scoring_scope", "Scope limits"),
    "artifact_refs": ("task_scoring_artifacts", "Artifact refs"),
    "scoring_comments": ("comments", "Comments"),
}
SUMMARY_COLUMNS = {
    "group": ("summary_group_by", "Group by"),
    "task_count": ("tasks", "Tasks"),
    **{
        key: TASK_COLUMNS[key]
        for key in ("rule_count", "rubric_count", "scoring_item_count")
    },
    "missing_rule_count": ("task_missing_rules", "Tasks without a rule count"),
    "missing_rubric_count": ("task_missing_rubrics", "Tasks without a rubric count"),
    "missing_scoring_item_count": (
        "task_missing_items",
        "Tasks without a scoring item count",
    ),
}


def task_summary(rows: list[dict[str, Any]], group_by: str) -> list[dict[str, Any]]:
    groups: dict[str | None, list[dict[str, Any]]] = {}
    custom_key = (
        parse_custom_column_id(group_by) if is_custom_column_id(group_by) else None
    )
    for row in rows:
        if custom_key is not None:
            metadata = row.get("custom_metadata")
            raw_value = metadata.get(custom_key) if isinstance(metadata, dict) else None
            keys = custom_metadata_group_keys(raw_value)
        elif group_by == "tags":
            keys = list(dict.fromkeys(tag for tag in row.get("tags", []) if tag)) or [
                None
            ]
        else:
            keys = ["overall" if group_by == "overall" else row.get(group_by)]
        for key in keys:
            groups.setdefault(key, []).append(row)
    result = []
    for group, tasks in groups.items():
        result.append({"group": group, **task_totals(tasks)})
    return result


def task_export_rows(library, request: TaskExport, role: str) -> list[dict[str, Any]]:
    from psycheval.state.comments import (
        ScoringCommentStore,
        attach_task_scoring_comments,
        resolve_dataset_comment_key,
    )

    config_path = getattr(library, "config_path", None)
    comment_store = (
        ScoringCommentStore(config_path.parent) if config_path is not None else None
    )
    harbor_datasets = getattr(getattr(library, "config", None), "harbor_datasets", ())
    datasets = {}
    for ref in request.rows:
        if ref.dataset_id not in datasets:
            projected = project_harbor_inventory(
                library.task_inventory(ref.dataset_id), role
            )
            dataset_cfg = next(
                (item for item in harbor_datasets if item.id == ref.dataset_id),
                None,
            )
            dataset_comments = (
                comment_store.read_dataset(
                    resolve_dataset_comment_key(
                        Path(dataset_cfg.path),
                        dataset_id=dataset_cfg.id,
                        dataset_format=dataset_cfg.format,
                    )
                )
                if comment_store is not None and dataset_cfg is not None
                else {}
            )
            datasets[ref.dataset_id] = {
                task["directory"]: attach_task_scoring_comments(
                    task, dataset_comments.get(str(task.get("directory") or ""), {})
                )
                for task in projected["datasets"][0]["tasks"]
            }
    custom_columns = [
        (key, parse_custom_column_id(key))
        for key in request.columns
        if is_custom_column_id(key)
    ]
    result, seen, item_indexes = [], set(), {}
    for ref in request.rows:
        task = datasets[ref.dataset_id].get(ref.task)
        if task is None:
            raise HarborWorkspaceError("Task changed; refresh before exporting")
        identity = (
            ref.dataset_id,
            ref.task,
            ref.item_key if request.mode == "items" else None,
        )
        if identity in seen:
            continue
        seen.add(identity)
        custom_metadata = (
            task.get("custom_metadata")
            if isinstance(task.get("custom_metadata"), dict)
            else {}
        )
        row: dict[str, Any] = {
            "dataset": ref.dataset_id,
            "task": ref.task,
            **{
                key: task.get(key)
                for key in TASK_COLUMNS
                if key not in {"dataset", "task"}
            },
            **{
                column_id: custom_metadata.get(raw_key)
                for column_id, raw_key in custom_columns
            },
        }
        if request.mode == "summary":
            row.update(
                category=task.get("category"),
                difficulty=task.get("difficulty"),
                custom_metadata=custom_metadata,
            )
        if request.mode == "items":
            task_key = (ref.dataset_id, ref.task)
            if task_key not in item_indexes:
                item_indexes[task_key] = {
                    item["key"]: item for item in task["scoring_items"]
                }
            items = item_indexes[task_key]
            item = items.get(ref.item_key)
            if item is None and (ref.item_key is not None or items):
                raise HarborWorkspaceError(
                    "Scoring items changed; refresh before exporting"
                )
            row = {
                **row,
                **{
                    key: (
                        (item or {}).get("comments", [])
                        if key == "scoring_comments"
                        else (item or {}).get(key)
                    )
                    for key in ITEM_COLUMNS
                    if key not in TASK_COLUMNS
                },
            }
        result.append(row)
    if request.mode != "summary":
        return result
    summary = task_summary(result, request.group_by)
    if request.comparison_groups is None or request.group_by == "overall":
        return summary
    selected = set(request.comparison_groups)
    return [group for group in summary if group["group"] in selected]


def _valid_export_column(
    key: str, mode: str, definitions: dict[str, tuple[str, str]]
) -> bool:
    if key in definitions:
        return True
    return mode in {"tasks", "items"} and is_custom_column_id(key)


def _json_export_key(key: str) -> str:
    if is_custom_column_id(key):
        return f"meta:{parse_custom_column_id(key)}"
    return key


def build_task_export(
    rows: list[dict[str, Any]], request: TaskExport, locale: str
) -> tuple[bytes, str, str]:
    definitions = (
        SUMMARY_COLUMNS
        if request.mode == "summary"
        else ITEM_COLUMNS
        if request.mode == "items"
        else TASK_COLUMNS
    )
    columns = request.columns or list(definitions)
    if len(set(columns)) != len(columns) or any(
        not _valid_export_column(key, request.mode, definitions) for key in columns
    ):
        raise HarborWorkspaceError("Invalid Task export columns")
    filename = f"peval-task-{request.mode}"
    if request.kind == "json":
        projected = [
            {_json_export_key(key): row.get(key) for key in columns} for row in rows
        ]
        return (
            (json.dumps(projected, ensure_ascii=False, indent=2) + "\n").encode(),
            "application/json; charset=utf-8",
            filename + ".json",
        )
    projected = [{key: row.get(key) for key in columns} for row in rows]
    messages = messages_for(locale)
    output = io.BytesIO()
    with xlsxwriter.Workbook(
        output,
        {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False},
    ) as workbook:
        sheet = workbook.add_worksheet(
            "Task Summary" if request.mode == "summary" else "Tasks"
        )
        header = workbook.add_format(
            {"bold": True, "bg_color": "#ECE7DD", "text_wrap": True}
        )
        body = workbook.add_format({"valign": "top", "text_wrap": True})
        for index, key in enumerate(columns):
            if is_custom_column_id(key):
                title = parse_custom_column_id(key)
            else:
                label_key, fallback = definitions[key]
                title = messages.get(label_key, fallback)
            sheet.write(0, index, title, header)
            sheet.set_column(
                index,
                index,
                55
                if key
                in {
                    "instruction",
                    "question",
                    "pass_criteria",
                    "fail_criteria",
                    "scope_limits",
                    "scoring_comments",
                }
                else 24,
            )
        for index, row in enumerate(projected, 1):
            for column, key in enumerate(columns):
                value = row[key]
                if key == "group":
                    if request.group_by == "overall":
                        value = messages["summary_overall"]
                    elif value is None:
                        value = messages["task_group_unset"]
                if key == "scoring_comments" and isinstance(value, list):
                    from psycheval.state.comments import format_comments_for_export

                    value = format_comments_for_export(value)
                elif isinstance(value, list):
                    value = "\n".join(
                        item
                        if isinstance(item, str)
                        else json.dumps(item, ensure_ascii=False)
                        for item in value
                    )
                elif isinstance(value, dict):
                    value = json.dumps(value, ensure_ascii=False)
                if isinstance(value, str) and len(value) > 32767:
                    raise HarborWorkspaceError(
                        "Excel cells are limited to 32767 characters; export JSON for complete text"
                    )
                sheet.write(index, column, value, body)
        sheet.freeze_panes(1, 0)
        if projected:
            sheet.autofilter(0, 0, len(projected), len(columns) - 1)
    return output.getvalue(), EXCEL_CONTENT_TYPE, filename + ".xlsx"


def register_task_table_routes(app: FastAPI) -> None:
    base = "/api/harbor/datasets/{dataset_id}/tasks/{task}"

    @app.put(
        base + "/rule-count",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def put_rule_count(
        request: Request,
        dataset_id: str,
        task: str,
        body: TaskRuleCount,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ):
        runtime = writable_runtime(request)
        expected = expect_revision(
            if_match, config_revision(runtime.store.paths.config_path)
        )

        def update():
            library = harbor_workspace(runtime.store, runtime)
            config = library.set_task_rule_count(
                dataset_id, task, body.count, expected_revision=expected
            )
            runtime.set_config(config)
            return harbor_workspace(runtime.store, runtime).task_scoring(
                dataset_id, task
            )

        result = runtime.mutate_with_background_reconcile(
            "harbor-task-rule-count", update
        )
        operation = runtime.operation(result["operation"]["operation_id"])
        return json_response(
            {**operation_payload(operation), "task": result["result"]},
            status=202,
            headers={
                "Location": f"/api/operations/{operation.operation_id}",
                "Retry-After": "1",
                "ETag": etag(config_revision(runtime.store.paths.config_path)),
                "X-Peval-Invalidations": "tasks,dataset-registry",
            },
        )

    @app.patch(
        base + "/metadata",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def patch_task_metadata(
        request: Request,
        dataset_id: str,
        task: str,
        body: TaskMetadataPatch,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ):
        runtime = writable_runtime(request)
        current_revision = harbor_workspace(runtime.store, runtime).task_revision(
            dataset_id, task
        )
        expected = expect_revision(if_match, current_revision)

        def update():
            return harbor_workspace(runtime.store, runtime).set_task_metadata(
                dataset_id,
                task,
                body.key,
                body.value,
                expected_revision=expected,
                overwrite=True,
            )

        result = runtime.mutate_with_background_reconcile(
            "harbor-task-metadata", update
        )
        operation = runtime.operation(result["operation"]["operation_id"])
        updated_task = result["result"]
        return json_response(
            {**operation_payload(operation), "task": updated_task},
            status=202,
            headers={
                "Location": f"/api/operations/{operation.operation_id}",
                "Retry-After": "1",
                "ETag": etag(str(updated_task["revision"])),
                "X-Peval-Invalidations": "tasks,dataset-registry",
            },
        )

    @app.post(
        "/api/harbor/task-metadata-operations",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def batch_task_metadata(request: Request, body: TaskMetadataBatchOperation):
        runtime = writable_runtime(request)
        items = [
            {
                "dataset_id": item.dataset_id,
                "task": item.task,
                "expected_revision": if_match_value(item.etag),
            }
            for item in body.items
        ]

        def action(item: dict[str, str]) -> dict[str, Any]:
            updated = harbor_workspace(runtime.store, runtime).set_task_metadata(
                item["dataset_id"],
                item["task"],
                body.key,
                body.value,
                expected_revision=item["expected_revision"],
                overwrite=body.overwrite,
            )
            return {
                "dataset_id": item["dataset_id"],
                "task": item["task"],
                "revision": updated["revision"],
            }

        operation = runtime.start_operation("harbor-task-metadata", items, action)
        return operation_response(
            operation,
            headers={"X-Peval-Invalidations": "tasks,dataset-registry"},
        )

    @app.post(base + "/preview", dependencies=[Depends(mutation_guard)])
    @access(GUEST_ACCESS)
    def preview(request: Request, dataset_id: str, task: str, body: TaskPreview):
        runtime = request.app.state.runtime
        payload = harbor_workspace(runtime.store, runtime).preview_file(
            dataset_id, task, body.path, body.content
        )
        return json_response(
            project_harbor_text_file(payload, role_for(request)),
            headers={"X-Peval-Invalidations": ""},
        )

    @app.post("/api/harbor/task-exports", dependencies=[Depends(mutation_guard)])
    @access(GUEST_ACCESS)
    def export(request: Request, body: TaskExport):
        runtime = request.app.state.runtime
        library = harbor_workspace(runtime.store, runtime)
        rows = task_export_rows(library, body, role_for(request))
        content, media_type, filename = build_task_export(
            rows, body, runtime.config.locale
        )
        return Response(
            content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store",
            },
        )
