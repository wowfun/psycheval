"""Dataset Task previews, manual counts, and current-view exports."""

from __future__ import annotations

import io
import json
from typing import Annotated, Any, Literal

import xlsxwriter
from fastapi import Depends, FastAPI, Header, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from psycheval.config import ManualRuleCount
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
    json_response,
    operation_payload,
)
from psycheval.serve.api_support import harbor_workspace, writable_runtime
from psycheval.serve.harbor_workspace import HarborWorkspaceError, config_revision
from psycheval.serve.summary_xlsx import EXCEL_CONTENT_TYPE
from psycheval.serve.visibility import (
    project_harbor_inventory,
    project_harbor_text_file,
)


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class TaskRuleCount(_Request):
    count: ManualRuleCount | None


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
    columns: list[str] = Field(default_factory=list, max_length=20)
    group_by: Literal["overall", "dataset", "category", "difficulty", "tags"] = (
        "overall"
    )
    comparison_groups: list[str | None] | None = Field(default=None, max_length=100_000)


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
}
ITEM_COLUMNS = {
    key: value
    for key, value in TASK_COLUMNS.items()
    if key not in {"rule_count", "rubric_count", "scoring_item_count"}
} | {
    "step": ("task_scoring_step", "Step"),
    "id": ("task_scoring_id", "ID"),
    "type": ("task_scoring_type", "Type"),
    "question": ("task_scoring_question", "Question"),
    "pass_criteria": ("task_scoring_pass", "Pass criteria"),
    "fail_criteria": ("task_scoring_fail", "Fail criteria"),
    "scope_limits": ("task_scoring_scope", "Scope limits"),
    "artifact_refs": ("task_scoring_artifacts", "Artifact refs"),
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
    for row in rows:
        if group_by == "tags":
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
    datasets = {}
    for ref in request.rows:
        if ref.dataset_id not in datasets:
            projected = project_harbor_inventory(
                library.task_inventory(ref.dataset_id), role
            )
            datasets[ref.dataset_id] = {
                task["directory"]: task for task in projected["datasets"][0]["tasks"]
            }
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
        row = {
            "dataset": ref.dataset_id,
            "task": ref.task,
            **{
                key: task.get(key)
                for key in TASK_COLUMNS
                if key not in {"dataset", "task"}
            },
        }
        if request.mode == "summary":
            row.update(category=task.get("category"), difficulty=task.get("difficulty"))
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
                    key: (item or {}).get(key)
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
        key not in definitions for key in columns
    ):
        raise HarborWorkspaceError("Invalid Task export columns")
    projected = [{key: row.get(key) for key in columns} for row in rows]
    filename = f"peval-task-{request.mode}"
    if request.kind == "json":
        return (
            (json.dumps(projected, ensure_ascii=False, indent=2) + "\n").encode(),
            "application/json; charset=utf-8",
            filename + ".json",
        )
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
            label_key, fallback = definitions[key]
            sheet.write(0, index, messages.get(label_key, fallback), header)
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
                if isinstance(value, list):
                    value = "\n".join(
                        item
                        if isinstance(item, str)
                        else json.dumps(item, ensure_ascii=False)
                        for item in value
                    )
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
