from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Sequence

from psycheval.harbor.family import scope
from psycheval.metric_contract import BUILTIN_IDS, validate_metric_id_syntax

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class CatalogQuery:
    state: str = "active"
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE
    search: str = ""
    sort: str = "last_turn_end"
    direction: str = "desc"
    categories: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    agents: tuple[str, ...] = ()
    models: tuple[str, ...] = ()
    results: tuple[str, ...] = ()
    tasks: tuple[str, ...] = ()
    jobs: tuple[str, ...] = ()
    providers: tuple[str, ...] = ()
    datasets: tuple[str, ...] = ()
    review_comments: tuple[str, ...] = ()
    include_unreadable: bool = False
    metric_scope: str = "family"

    def normalized(self) -> CatalogQuery:
        scope(self.metric_scope)
        state = str(self.state or "active").strip().lower()
        if state not in {"active", "archived", "all"}:
            raise ValueError("state must be active, archived, or all")
        direction = str(self.direction or "desc").strip().lower()
        if direction not in {"asc", "desc"}:
            raise ValueError("direction must be asc or desc")
        review_comments = tuple(
            dict.fromkeys(
                value.strip().lower()
                for value in self.review_comments
                if str(value or "").strip()
            )
        )
        if any(value not in {"commented", "uncommented"} for value in review_comments):
            raise ValueError(
                "review_comments must contain only commented or uncommented"
            )
        page = max(1, int(self.page))
        page_size = min(MAX_PAGE_SIZE, max(1, int(self.page_size)))
        return CatalogQuery(
            state=state,
            page=page,
            page_size=page_size,
            search=str(self.search or "").strip(),
            sort=str(self.sort or "last_turn_end").strip(),
            direction=direction,
            categories=_normalized_values(self.categories),
            tags=_normalized_values(self.tags),
            agents=_normalized_values(self.agents),
            models=_normalized_values(self.models),
            results=_normalized_values(self.results),
            tasks=_normalized_values(self.tasks),
            jobs=_normalized_values(self.jobs),
            providers=_normalized_values(self.providers),
            datasets=_normalized_values(self.datasets),
            review_comments=review_comments,
            include_unreadable=bool(self.include_unreadable),
            metric_scope=self.metric_scope,
        )


@dataclass(frozen=True)
class CatalogRow:
    source_key: str
    artifact_revision: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            **{
                key: value
                for key, value in self.payload.items()
                if key != "_reference_location"
            },
            "source_key": self.source_key,
            "artifact_revision": self.artifact_revision,
        }


@dataclass(frozen=True)
class CatalogPage:
    generation: int
    checking: bool
    stale: bool
    total: int
    page: int
    page_size: int
    items: tuple[CatalogRow, ...]
    facets: dict[str, list[dict[str, Any]]]
    column_presence: dict[str, int]
    metric_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "checking": self.checking,
            "stale": self.stale,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "items": [item.to_dict() for item in self.items],
            "facets": self.facets,
            "column_presence": self.column_presence,
            **self.metric_metadata,
        }


@dataclass(frozen=True)
class DetailEnvelope:
    generation: int
    artifact_revision: str
    source_key: str
    report: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "artifact_revision": self.artifact_revision,
            "source_key": self.source_key,
            "report": self.report,
        }


@dataclass
class OperationStatus:
    operation_id: str
    operation_type: str
    state: str
    completed: int
    total: int
    successes: list[dict[str, Any]] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type,
            "state": self.state,
            "completed": self.completed,
            "total": self.total,
            "successes": list(self.successes),
            "failures": list(self.failures),
        }


def query_where(query: CatalogQuery) -> tuple[str, list[Any]]:
    scope_where, parameters = facet_scope_where(query)
    clauses = [] if scope_where == "1" else [scope_where]
    if query.search:
        if len(query.search) < 3:
            clauses.append("search_doc LIKE ? ESCAPE '\\' COLLATE NOCASE")
            parameters.append(f"%{_escape_like(query.search)}%")
        else:
            clauses.append(
                "cells.source_key IN (SELECT source_key FROM cell_search WHERE cell_search MATCH ?)"
            )
            parameters.append(_fts_literal(query.search))
    if query.tags:
        clauses.append(
            "EXISTS (SELECT 1 FROM json_each(tags_json) WHERE value IN (SELECT value FROM json_each(?)))"
        )
        parameters.append(json.dumps(query.tags))
    for column, values in (
        ("category", query.categories),
        ("agent", query.agents),
        ("model", query.models),
        ("result", query.results),
        ("task", query.tasks),
        ("job", query.jobs),
        ("provider", query.providers),
        ("dataset", query.datasets),
    ):
        if not values:
            continue
        clauses.append(f"{column} IN (SELECT value FROM json_each(?))")
        parameters.append(json.dumps(values))
    if query.review_comments:
        want_commented = "commented" in query.review_comments
        want_uncommented = "uncommented" in query.review_comments
        if want_commented and not want_uncommented:
            clauses.append("json_extract(row_json, '$.review_comments_present') = 1")
        elif want_uncommented and not want_commented:
            clauses.append(
                "COALESCE(json_extract(row_json, '$.review_comments_present'), 0) != 1"
            )
    return " AND ".join(clauses) if clauses else "1", parameters


def combined_query_where(
    refinement: CatalogQuery,
    any_queries: Sequence[CatalogQuery],
) -> tuple[str, list[Any]]:
    if not any_queries:
        return query_where(refinement)
    any_clauses: list[str] = []
    parameters: list[Any] = []
    for query in any_queries:
        where, query_parameters = query_where(query)
        any_clauses.append(f"({where})")
        parameters.extend(query_parameters)
    refinement_where, refinement_parameters = query_where(refinement)
    parameters.extend(refinement_parameters)
    return (
        f"({' OR '.join(any_clauses)}) AND ({refinement_where})",
        parameters,
    )


def facet_scope_where(query: CatalogQuery) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    if not query.include_unreadable:
        clauses.append("readable = 1")
    if query.state == "active":
        clauses.append("active = 1")
    elif query.state == "archived":
        clauses.append("active = 0")
    return " AND ".join(clauses) if clauses else "1", []


def query_facets(
    connection: sqlite3.Connection, where: str, parameters: list[Any]
) -> dict[str, list[dict[str, Any]]]:
    facets: dict[str, list[dict[str, Any]]] = {}
    facets["tags"] = [
        {"value": str(row[0]), "count": int(row[1])}
        for row in connection.execute(
            f"""
            SELECT tags.value, count(*)
            FROM cells, json_each(cells.tags_json) AS tags
            WHERE {where} AND tags.value <> ''
            GROUP BY tags.value ORDER BY count(*) DESC, tags.value COLLATE NOCASE
            """,
            parameters,
        )
    ]
    for name, column in (
        ("categories", "category"),
        ("agents", "agent"),
        ("models", "model"),
        ("results", "result"),
        ("tasks", "task"),
        ("jobs", "job"),
        ("providers", "provider"),
        ("datasets", "dataset"),
    ):
        facets[name] = [
            {"value": str(row[0]), "count": int(row[1])}
            for row in connection.execute(
                f"""
                SELECT {column}, count(*) FROM cells
                WHERE {where} AND {column} <> ''
                GROUP BY {column} ORDER BY count(*) DESC, {column} COLLATE NOCASE
                """,
                parameters,
            )
        ]
    comment_expr = (
        "CASE WHEN json_extract(row_json, '$.review_comments_present') = 1 "
        "THEN 'commented' ELSE 'uncommented' END"
    )
    facets["review_comments"] = [
        {"value": str(row[0]), "count": int(row[1])}
        for row in connection.execute(
            f"""
            SELECT {comment_expr} AS comment_status, count(*) FROM cells
            WHERE {where}
            GROUP BY comment_status
            ORDER BY CASE comment_status WHEN 'commented' THEN 0 ELSE 1 END
            """,
            parameters,
        )
    ]
    return facets


def search_document(row: dict[str, Any], trajectory: dict[str, Any]) -> str:
    values: list[str] = []
    for value in (
        row.get("session_id"),
        row.get("trial_session_id"),
        row.get("source_alias"),
        row.get("display_alias"),
        row.get("source_category"),
        row.get("source_tags"),
        row.get("display_tags"),
        row.get("task_name"),
        row.get("job_name"),
        row.get("trial_name"),
        row.get("task_keywords"),
        row.get("model_provider"),
        row.get("harbor_provenance"),
        row.get("task_metadata"),
        row.get("rewards"),
        row.get("agent_name"),
        row.get("adapter"),
        row.get("model"),
        row.get("status"),
        row.get("last_status"),
        row.get("last_error"),
    ):
        _append_search_value(values, value)
    for comment in row.get("review_comments") or ():
        if isinstance(comment, dict):
            _append_search_value(values, comment.get("author_id"))
            _append_search_value(values, comment.get("body"))
    steps = trajectory.get("steps")
    if isinstance(steps, list):
        for step in steps:
            if not isinstance(step, dict):
                continue
            for key in ("message", "reasoning_content", "tool_calls", "observation"):
                _append_search_value(values, step.get(key))
    return "\n".join(values).casefold()


def _append_search_value(values: list[str], value: Any) -> None:
    if value is None:
        return
    if isinstance(value, str):
        text = value.strip()
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if text:
        values.append(text)


def _normalized_values(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(str(value).strip() for value in values if str(value).strip())
    )


def _escape_like(value: str) -> str:
    return (
        value.casefold().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )


def _fts_literal(value: str) -> str:
    return '"' + value.casefold().replace('"', '""') + '"'


def catalog_sort(
    connection: sqlite3.Connection, sort: str, metric_scope: str = "family"
) -> tuple[str, str, list[Any], str]:
    if not sort.startswith("metric:"):
        return "", _sort_expression(sort), [], sort
    key = sort.removeprefix("metric:")
    validate_metric_id_syntax(key)
    if (
        connection.execute(
            "SELECT 1 FROM metric_registry WHERE metric_id = ?", (key,)
        ).fetchone()
        is None
    ):
        return "", "last_turn_end", [], "last_turn_end"
    join = "LEFT JOIN (SELECT source_key AS metric_source, value AS metric_sort_value FROM metric_values WHERE metric_id = ? AND metric_scope = ?) AS metric_sort ON metric_sort.metric_source = cells.source_key"
    return join, "metric_sort_value", [key, metric_scope], sort


def _sort_expression(sort: str) -> str:
    mapping = {
        "last_turn_end": "last_turn_end",
        "session": "session_id COLLATE NOCASE",
        "agent": "agent COLLATE NOCASE",
        "model": "model COLLATE NOCASE",
        "result": "result COLLATE NOCASE",
        "task": "task COLLATE NOCASE",
        "job": "job COLLATE NOCASE",
        "provider": "provider COLLATE NOCASE",
        "dataset": "dataset COLLATE NOCASE",
        "created": "created_at_ms",
        "updated": "updated_at_ms",
        "source_key": "source_key",
    }
    if sort not in mapping:
        raise ValueError(f"unsupported catalog sort: {sort}")
    return mapping[sort]


def _json_value_present(path: str) -> str:
    value_type = f"json_type(row_json, '{path}')"
    value = f"json_extract(row_json, '{path}')"
    return (
        f"CASE {value_type} "
        f"WHEN 'text' THEN trim({value}) <> '' "
        f"WHEN 'array' THEN json_array_length({value}) > 0 "
        f"WHEN 'object' THEN {value} <> '{{}}' "
        f"WHEN 'null' THEN 0 "
        f"ELSE {value_type} IS NOT NULL END"
    )


_CATALOG_COLUMN_PRESENCE_SQL = {
    "score": f"reward IS NOT NULL OR ({_json_value_present('$.rewards')})",
    "dataset_id": "dataset IS NOT NULL AND trim(dataset) <> ''",
    "source_category": "trim(category) <> ''",
    "source_tags": "json_array_length(tags_json) > 0",
    "session_id": "trim(session_id) <> ''",
    "task_name": f"({_json_value_present('$.source_alias')}) OR trim(task) <> ''",
    "agent": "trim(agent) <> ''",
    "model": "trim(model) <> ''",
    "job_name": "trim(job) <> ''",
    "model_provider": "trim(provider) <> ''",
    "status": "trim(last_status) <> ''",
    "finished_at_ms": "last_turn_end IS NOT NULL",
    "analysis_count": _json_value_present("$.analysis_count"),
    "notes": "json_extract(row_json, '$.notes_present') = 1",
    "review_comments": "json_extract(row_json, '$.review_comments_present') = 1",
}


def empty_column_presence() -> dict[str, int]:
    return {
        **dict.fromkeys(_CATALOG_COLUMN_PRESENCE_SQL, 0),
        **dict.fromkeys(BUILTIN_IDS, 0),
        "workspace_reports": 0,
    }


def catalog_query_presence(
    connection: sqlite3.Connection,
    where: str,
    parameters: Sequence[Any],
    metric_scope: str = "family",
) -> tuple[int, dict[str, int]]:
    select_items = [
        "count(*) AS matched_trials",
        *(
            f"sum(CASE WHEN {expression} THEN 1 ELSE 0 END) AS presence_{key}"
            for key, expression in _CATALOG_COLUMN_PRESENCE_SQL.items()
        ),
    ]
    record = connection.execute(
        f"SELECT {', '.join(select_items)} FROM cells WHERE {where}",
        parameters,
    ).fetchone()
    assert record is not None
    matched = int(record["matched_trials"])
    presence = {
        key: int(record[f"presence_{key}"] or 0) for key in _CATALOG_COLUMN_PRESENCE_SQL
    }
    ids = [
        *BUILTIN_IDS,
        *(
            record[0]
            for record in connection.execute("SELECT metric_id FROM metric_registry")
            if record[0] not in BUILTIN_IDS
        ),
    ]
    counts = dict(
        connection.execute(
            f"SELECT metric_id, count(*) FROM metric_values WHERE metric_scope = ? AND source_key IN (SELECT source_key FROM cells WHERE {where}) GROUP BY metric_id",
            [metric_scope, *parameters],
        )
    )
    for key in ids:
        if key != "score":
            presence[key] = counts.get(key, 0)
    return matched, presence


def count_matching_source_refs(
    connection: sqlite3.Connection,
    where: str,
    parameters: Sequence[Any],
    source_refs: Sequence[str],
) -> int:
    ordered = list(dict.fromkeys(str(value) for value in source_refs if str(value)))
    if not ordered:
        return 0
    return int(
        connection.execute(
            f"SELECT count(*) FROM cells WHERE ({where}) "
            "AND source_ref IN (SELECT value FROM json_each(?))",
            [*parameters, json.dumps(ordered, ensure_ascii=False)],
        ).fetchone()[0]
    )


def empty_facets() -> dict[str, list[dict[str, Any]]]:
    return {
        "categories": [],
        "tags": [],
        "agents": [],
        "models": [],
        "results": [],
        "tasks": [],
        "jobs": [],
        "providers": [],
        "datasets": [],
        "review_comments": [],
    }


def chunks(values: list[str], size: int) -> Iterator[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]
