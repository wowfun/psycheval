from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import uuid
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Sequence

from psycheval._state.annotations import optional_int, optional_str
from psycheval.config import ToolConfig
from psycheval.report.inference import inference_row_metrics
from psycheval.report.metrics import final_metric, token_total
from psycheval.state.store import ServeStateStore
from psycheval.state.workspace_sources import (
    HARBOR_SOURCE_KIND,
    SourceDocument,
    WorkspaceSources,
)

CATALOG_SCHEMA_VERSION = 15
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 100
SUMMARY_CACHE_ENTRY_LIMIT = 128
SUMMARY_CACHE_BYTE_LIMIT = 16 * 1024 * 1024
SUMMARY_GROUP_LIMIT = 1_000
CATALOG_RELATIVE_PATH = Path(".cache/peval/serve-catalog.sqlite3")
TASK_DIRECTORY_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$")


class CatalogBusyError(RuntimeError):
    pass


class CatalogSummaryCapacityError(ValueError):
    pass


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
    include_unreadable: bool = False

    def normalized(self) -> CatalogQuery:
        state = str(self.state or "active").strip().lower()
        if state not in {"active", "archived", "all"}:
            raise ValueError("state must be active, archived, or all")
        direction = str(self.direction or "desc").strip().lower()
        if direction not in {"asc", "desc"}:
            raise ValueError("direction must be asc or desc")
        page = max(1, int(self.page))
        page_size = min(MAX_PAGE_SIZE, max(1, int(self.page_size)))
        return CatalogQuery(
            state=state,
            page=page,
            page_size=page_size,
            search=str(self.search or "").strip(),
            sort=str(self.sort or "last_turn_end").strip().lower(),
            direction=direction,
            categories=_normalized_values(self.categories),
            tags=_normalized_values(self.tags),
            agents=_normalized_values(self.agents),
            models=_normalized_values(self.models),
            results=_normalized_values(self.results),
            tasks=_normalized_values(self.tasks),
            jobs=_normalized_values(self.jobs),
            providers=_normalized_values(self.providers),
            include_unreadable=bool(self.include_unreadable),
        )


@dataclass(frozen=True)
class CatalogRow:
    source_key: str
    artifact_revision: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.payload,
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


class WorkspaceCatalog:
    """Serve-only derived index over canonical Trial-cell artifacts."""

    def __init__(self, store: ServeStateStore, config: ToolConfig) -> None:
        self.store = store
        self.config = config
        self.sources = WorkspaceSources(store, config)
        self.path = store.paths.root / CATALOG_RELATIVE_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._state_lock = threading.RLock()
        self._writer_lock = threading.Lock()
        self._checking = False
        self._current_operation: OperationStatus | None = None
        self._recent_operation: OperationStatus | None = None
        self._query_summary_cache: OrderedDict[
            tuple[Any, ...], tuple[dict[str, Any], int]
        ] = OrderedDict()
        self._query_summary_cache_bytes = 0
        self._prepare_database()

    @property
    def checking(self) -> bool:
        with self._state_lock:
            return self._checking

    @property
    def generation(self) -> int:
        with self._connect(readonly=True) as connection:
            return self._meta_int(connection, "generation", 0)

    @property
    def has_generation(self) -> bool:
        with self._connect(readonly=True) as connection:
            return self._meta_int(connection, "valid_generation", 0) == 1

    def reconcile(self) -> int:
        if not self._writer_lock.acquire(blocking=False):
            raise CatalogBusyError(
                "serve catalog is busy with another writer operation"
            )
        with self._state_lock:
            self._checking = True
        try:
            with self._workspace_writer_lease():
                return self._reconcile_locked()
        finally:
            with self._state_lock:
                self._checking = False
            self._writer_lock.release()

    def query(
        self,
        query: CatalogQuery,
        *,
        include_facets: bool = True,
        any_queries: Sequence[CatalogQuery] = (),
        workspace_report_source_refs: Sequence[str] = (),
    ) -> CatalogPage:
        query = query.normalized()
        normalized_any_queries = tuple(item.normalized() for item in any_queries)
        with self._connect(readonly=True) as connection:
            generation = self._meta_int(connection, "generation", 0)
            valid = self._meta_int(connection, "valid_generation", 0) == 1
            if not valid:
                return CatalogPage(
                    generation=0,
                    checking=self.checking,
                    stale=self.checking,
                    total=0,
                    page=query.page,
                    page_size=query.page_size,
                    items=(),
                    facets=_empty_facets(),
                    column_presence=_empty_column_presence(),
                )
            where, parameters = self._combined_query_where(
                query, normalized_any_queries
            )
            total, column_presence = _catalog_query_presence(
                connection,
                where,
                parameters,
            )
            column_presence["workspace_reports"] = _count_matching_source_refs(
                connection,
                where,
                parameters,
                workspace_report_source_refs,
            )
            sort_expression = _sort_expression(query.sort)
            direction = "ASC" if query.direction == "asc" else "DESC"
            offset = (query.page - 1) * query.page_size
            records = connection.execute(
                f"""
                SELECT source_key, artifact_revision, row_json
                FROM cells
                WHERE {where}
                ORDER BY ({sort_expression} IS NULL) ASC,
                         {sort_expression} {direction}, source_key ASC
                LIMIT ? OFFSET ?
                """,
                [*parameters, query.page_size, offset],
            ).fetchall()
            items = tuple(
                CatalogRow(
                    source_key=str(record["source_key"]),
                    artifact_revision=str(record["artifact_revision"]),
                    payload=json.loads(str(record["row_json"])),
                )
                for record in records
            )
            facets = (
                self._facets(
                    connection,
                    *self._combined_facet_where(query, normalized_any_queries),
                )
                if include_facets
                else _empty_facets()
            )
        return CatalogPage(
            generation=generation,
            checking=self.checking,
            stale=self.checking,
            total=total,
            page=query.page,
            page_size=query.page_size,
            items=items,
            facets=facets,
            column_presence=column_presence,
        )

    @contextmanager
    def read_snapshot_rows(
        self,
        query: CatalogQuery,
        *,
        any_queries: Sequence[CatalogQuery] | Callable[[], Sequence[CatalogQuery]] = (),
        selected_source_keys: Sequence[str] = (),
    ) -> Iterator[tuple[int, list[dict[str, Any]]]]:
        """Hold one catalog generation while a read-only export is assembled."""
        if not self._writer_lock.acquire(blocking=False):
            raise CatalogBusyError(
                "serve catalog is busy with another writer operation"
            )
        try:
            if self.checking:
                raise CatalogBusyError("serve catalog is checking runs")
            normalized = query.normalized()
            resolved_any_queries = (
                any_queries() if callable(any_queries) else any_queries
            )
            normalized_any = tuple(item.normalized() for item in resolved_any_queries)
            selected = list(
                dict.fromkeys(str(key) for key in selected_source_keys if str(key))
            )
            with self._connect(readonly=True) as connection:
                generation = self._meta_int(connection, "generation", 0)
                if self._meta_int(connection, "valid_generation", 0) != 1:
                    raise ValueError("serve catalog has no valid generation")
                if selected:
                    found: set[str] = set()
                    for chunk in _chunks(selected, 500):
                        placeholders = ",".join("?" for _ in chunk)
                        found.update(
                            str(record[0])
                            for record in connection.execute(
                                f"SELECT source_key FROM cells WHERE source_key IN ({placeholders})",
                                chunk,
                            )
                        )
                    missing = next((key for key in selected if key not in found), None)
                    if missing is not None:
                        raise ValueError(f"unknown source: {missing}")
                where, parameters = self._combined_query_where(
                    normalized, normalized_any
                )
                sort_expression = _sort_expression(normalized.sort)
                direction = "ASC" if normalized.direction == "asc" else "DESC"
                records = connection.execute(
                    f"""
                    SELECT source_key, row_json FROM cells
                    WHERE {where}
                    ORDER BY ({sort_expression} IS NULL) ASC,
                             {sort_expression} {direction}, source_key ASC
                    """,
                    parameters,
                ).fetchall()
                selected_set = set(selected)
                rows = [
                    json.loads(str(record["row_json"]))
                    for record in records
                    if not selected or str(record["source_key"]) in selected_set
                ]
            yield generation, rows
        finally:
            self._writer_lock.release()

    @contextmanager
    def workspace_write_guard(self) -> Iterator[None]:
        """Serialize file-backed workspace writes with catalog snapshots."""
        if not self._writer_lock.acquire(blocking=False):
            raise CatalogBusyError(
                "serve catalog is busy with another writer operation"
            )
        try:
            if self.checking:
                raise CatalogBusyError("serve catalog is checking runs")
            yield
        finally:
            self._writer_lock.release()

    def summarize_saved_views(
        self,
        views: Sequence[tuple[str, CatalogQuery, str]],
    ) -> dict[str, Any]:
        """Return compact full-query metrics for saved view definitions.

        This deliberately bypasses `CatalogQuery` pagination while retaining its
        filtering semantics. All summaries read one committed SQLite generation.
        """
        normalized = [
            (str(name), query.normalized(), str(group_by))
            for name, query, group_by in views
        ]
        with self._connect(readonly=True) as connection:
            generation = self._meta_int(connection, "generation", 0)
            valid = self._meta_int(connection, "valid_generation", 0) == 1
            if not valid:
                return {
                    "generation": 0,
                    "checking": self.checking,
                    "stale": self.checking,
                    "views": [
                        _saved_view_summary(name, group_by, [])
                        for name, _query, group_by in normalized
                    ],
                }
            summaries: list[dict[str, Any]] = []
            for name, query, group_by in normalized:
                where, parameters = self._query_where(query)
                rows = _summary_rows(connection, where, parameters)
                summaries.append(_saved_view_summary(name, group_by, rows))
        return {
            "generation": generation,
            "checking": self.checking,
            "stale": self.checking,
            "views": summaries,
        }

    def summarize_query(
        self,
        query: CatalogQuery,
        *,
        any_queries: Sequence[CatalogQuery] = (),
        name: str,
        group_by: str,
    ) -> dict[str, Any]:
        """Summarize one complete query from a committed catalog generation."""
        normalized = query.normalized()
        normalized_any = tuple(item.normalized() for item in any_queries)
        with self._connect(readonly=True) as connection:
            generation = self._meta_int(connection, "generation", 0)
            valid = self._meta_int(connection, "valid_generation", 0) == 1
            if not valid:
                return {
                    "generation": 0,
                    "checking": self.checking,
                    "stale": self.checking,
                    "summary": _saved_view_summary(name, group_by, []),
                }
            cache_key = (
                generation,
                _summary_query_scope(normalized),
                tuple(sorted(_summary_query_scope(item) for item in normalized_any)),
                str(name),
                str(group_by),
            )
            with self._state_lock:
                cached_entry = self._query_summary_cache.get(cache_key)
                if cached_entry is not None:
                    self._query_summary_cache.move_to_end(cache_key)
            if cached_entry is not None:
                return {
                    "generation": generation,
                    "checking": self.checking,
                    "stale": self.checking,
                    "summary": cached_entry[0],
                }
            where, parameters = self._combined_query_where(normalized, normalized_any)
            rows = _summary_rows(connection, where, parameters)
            summary = _saved_view_summary(name, group_by, rows)
        self._cache_query_summary(cache_key, summary)
        return {
            "generation": generation,
            "checking": self.checking,
            "stale": self.checking,
            "summary": summary,
        }

    def _cache_query_summary(
        self,
        cache_key: tuple[Any, ...],
        summary: dict[str, Any],
    ) -> None:
        byte_size = len(
            json.dumps(summary, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
        )
        if byte_size > SUMMARY_CACHE_BYTE_LIMIT:
            return
        with self._state_lock:
            previous = self._query_summary_cache.pop(cache_key, None)
            if previous is not None:
                self._query_summary_cache_bytes -= previous[1]
            while self._query_summary_cache and (
                len(self._query_summary_cache) >= SUMMARY_CACHE_ENTRY_LIMIT
                or self._query_summary_cache_bytes + byte_size
                > SUMMARY_CACHE_BYTE_LIMIT
            ):
                _old_key, (_old_summary, old_size) = self._query_summary_cache.popitem(
                    last=False
                )
                self._query_summary_cache_bytes -= old_size
            self._query_summary_cache[cache_key] = (summary, byte_size)
            self._query_summary_cache_bytes += byte_size

    def load_detail(self, source_key: str) -> DetailEnvelope:
        with self._connect(readonly=True) as connection:
            generation = self._meta_int(connection, "generation", 0)
            record = connection.execute(
                "SELECT artifact_revision, readable, row_json FROM cells WHERE source_key = ?",
                (source_key,),
            ).fetchone()
        if record is None:
            raise ValueError(f"unknown source: {source_key}")
        if not bool(record["readable"]):
            raise ValueError(f"source is not readable: {source_key}")
        row = json.loads(str(record["row_json"]))
        report = _report_with_live_task_ref(
            self.store.report_for_rows([row], self.config), self.config
        )
        return DetailEnvelope(
            generation=generation,
            artifact_revision=str(record["artifact_revision"]),
            source_key=source_key,
            report=report,
        )

    def resolve_keys(self, keys: Iterable[str]) -> list[str]:
        ordered = list(dict.fromkeys(str(key) for key in keys if str(key)))
        if not ordered:
            return []
        found: set[str] = set()
        with self._connect(readonly=True) as connection:
            for chunk in _chunks(ordered, 500):
                placeholders = ",".join("?" for _ in chunk)
                found.update(
                    str(row[0])
                    for row in connection.execute(
                        f"SELECT source_key FROM cells WHERE source_key IN ({placeholders})",
                        chunk,
                    )
                )
        return [key for key in ordered if key in found]

    def row_for_key(self, source_key: str) -> dict[str, Any]:
        with self._connect(readonly=True) as connection:
            record = connection.execute(
                "SELECT row_json FROM cells WHERE source_key = ?", (source_key,)
            ).fetchone()
        if record is None:
            raise ValueError(f"unknown source: {source_key}")
        return json.loads(str(record[0]))

    def binding_rows(self) -> list[dict[str, Any]]:
        with self._connect(readonly=True) as connection:
            return [
                json.loads(str(record[0]))
                for record in connection.execute(
                    "SELECT row_json FROM cells ORDER BY source_key"
                )
            ]

    def start_operation(
        self,
        operation_type: str,
        items: Sequence[Any],
        action: Callable[[Any], Any],
    ) -> OperationStatus:
        with self._state_lock:
            if self._checking or (
                self._current_operation is not None
                and self._current_operation.state in {"queued", "running"}
            ):
                raise CatalogBusyError(
                    "serve catalog is busy with another writer operation"
                )
            status = OperationStatus(
                operation_id=uuid.uuid4().hex,
                operation_type=str(operation_type),
                state="queued",
                completed=0,
                total=len(items),
            )
            self._current_operation = status
            self._checking = True
        threading.Thread(
            target=self._run_operation,
            args=(status, list(items), action),
            daemon=True,
        ).start()
        return status

    def mutate(self, action: Callable[[], Any]) -> tuple[int, Any]:
        if not self._writer_lock.acquire(blocking=False):
            raise CatalogBusyError(
                "serve catalog is busy with another writer operation"
            )
        with self._state_lock:
            if self._checking:
                self._writer_lock.release()
                raise CatalogBusyError("serve catalog is checking runs")
            self._checking = True
        try:
            with self._workspace_writer_lease():
                result = action()
                generation = self._reconcile_locked()
                return generation, result
        finally:
            with self._state_lock:
                self._checking = False
            self._writer_lock.release()

    def mutate_with_background_reconcile(
        self,
        operation_type: str,
        action: Callable[[], Any],
    ) -> tuple[Any, OperationStatus]:
        """Commit one workspace mutation, then reconcile it in the background."""
        if not self._writer_lock.acquire(blocking=False):
            raise CatalogBusyError(
                "serve catalog is busy with another writer operation"
            )
        status: OperationStatus | None = None
        try:
            with self._state_lock:
                if self._checking:
                    raise CatalogBusyError("serve catalog is checking runs")
            with self._workspace_writer_lease():
                result = action()
            status = OperationStatus(
                operation_id=uuid.uuid4().hex,
                operation_type=operation_type,
                state="queued",
                completed=0,
                total=1,
            )
            with self._state_lock:
                self._current_operation = status
                self._checking = True
        finally:
            self._writer_lock.release()
        assert status is not None
        threading.Thread(
            target=self._run_reconcile_operation,
            args=(status,),
            daemon=True,
        ).start()
        return result, OperationStatus(**status.to_dict())

    def _run_reconcile_operation(self, status: OperationStatus) -> None:
        try:
            if not self._writer_lock.acquire(blocking=False):
                raise CatalogBusyError(
                    "serve catalog is busy with another writer operation"
                )
            try:
                with self._workspace_writer_lease():
                    with self._state_lock:
                        status.state = "running"
                    self._reconcile_locked()
                    with self._state_lock:
                        status.completed = 1
                        status.successes.append({"index": 0, "status": "ok"})
            finally:
                self._writer_lock.release()
            with self._state_lock:
                status.state = "completed"
        except Exception as exc:  # noqa: BLE001 - operation thread boundary.
            with self._state_lock:
                status.state = "failed"
                status.failures.append(
                    {"index": 0, "status": "error", "error": str(exc)}
                )
        finally:
            with self._state_lock:
                self._checking = False
                self._recent_operation = status
                self._current_operation = status

    def operation(self, operation_id: str) -> OperationStatus:
        with self._state_lock:
            for status in (self._current_operation, self._recent_operation):
                if status is not None and status.operation_id == operation_id:
                    return OperationStatus(**status.to_dict())
        raise ValueError(f"unknown operation: {operation_id}")

    def close(self) -> None:
        return None

    def _run_operation(
        self,
        status: OperationStatus,
        items: list[Any],
        action: Callable[[Any], Any],
    ) -> None:
        try:
            if not self._writer_lock.acquire(blocking=False):
                raise CatalogBusyError(
                    "serve catalog is busy with another writer operation"
                )
            try:
                with self._workspace_writer_lease():
                    with self._state_lock:
                        status.state = "running"
                    for index, item in enumerate(items):
                        try:
                            value = action(item)
                            result = {"index": index, "status": "ok"}
                            if isinstance(value, dict):
                                result.update(value)
                            elif value is not None:
                                result["result"] = value
                            with self._state_lock:
                                status.successes.append(result)
                        except Exception as exc:  # noqa: BLE001 - per-item operation isolation.
                            with self._state_lock:
                                failure = {
                                    "index": index,
                                    "status": "error",
                                    "error": str(exc),
                                }
                                if (
                                    isinstance(
                                        item, (str, int, float, bool, dict, list)
                                    )
                                    or item is None
                                ):
                                    failure["item"] = item
                                status.failures.append(failure)
                        with self._state_lock:
                            status.completed = index + 1
                    self._reconcile_locked()
            finally:
                self._writer_lock.release()
            with self._state_lock:
                status.state = "completed"
        except Exception as exc:  # noqa: BLE001 - operation thread boundary.
            with self._state_lock:
                status.state = "failed"
                status.failures.append(
                    {"index": None, "status": "error", "error": str(exc)}
                )
        finally:
            with self._state_lock:
                self._checking = False
                self._recent_operation = status
                self._current_operation = status

    def _reconcile_locked(self) -> int:
        candidates = self.sources.discover()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = {
                str(row["source_ref"]): (
                    str(row["fingerprint"]),
                    str(row["source_key"]),
                )
                for row in connection.execute(
                    "SELECT source_ref, fingerprint, source_key FROM cells"
                )
            }
            seen: set[str] = set()
            for candidate in candidates:
                source_ref = candidate.source_ref
                seen.add(source_ref)
                prior = existing.get(source_ref)
                if prior is not None and prior[0] == candidate.fingerprint:
                    continue
                document = self.sources.load(candidate)
                row, readable, search_doc = self._row_for_document(document)
                source_key = str(row["source_key"])
                connection.execute(
                    "DELETE FROM cells WHERE source_ref = ? OR source_key = ?",
                    (source_ref, source_key),
                )
                if prior is not None and prior[1] != source_key:
                    connection.execute(
                        "DELETE FROM cell_search WHERE source_key = ?", (prior[1],)
                    )
                connection.execute(
                    "DELETE FROM cell_search WHERE source_key = ?", (source_key,)
                )
                connection.execute(
                    """
                    INSERT INTO cells (
                        source_key, source_ref, fingerprint, artifact_revision,
                        readable, active, last_status, search_doc, category, tags_json,
                        agent, model, result, task, job, provider, reward,
                        session_id, last_turn_end, duration_ms, turns, tool_calls,
                        tool_errors, tokens, cost_usd, ttft_ms, tps, cache_hit_rate,
                        created_at_ms, updated_at_ms, row_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source_key,
                        source_ref,
                        document.fingerprint,
                        document.fingerprint,
                        int(readable),
                        int(bool(row.get("active", True))),
                        str(row.get("last_status") or ""),
                        search_doc,
                        str(row.get("source_category") or ""),
                        json.dumps(
                            row.get("display_tags") or row.get("source_tags") or [],
                            ensure_ascii=False,
                        ),
                        str(row.get("agent_name") or row.get("adapter") or ""),
                        str(row.get("model") or ""),
                        str(row.get("status") or row.get("last_status") or ""),
                        str(row.get("task_name") or ""),
                        str(row.get("job_name") or ""),
                        str(row.get("model_provider") or ""),
                        row.get("score"),
                        str(row.get("session_id") or row.get("trial_session_id") or ""),
                        optional_int(row.get("last_turn_finished_at_ms")),
                        row.get("duration_ms"),
                        row.get("turns"),
                        row.get("total_tool_calls"),
                        row.get("total_tool_errors"),
                        row.get("tokens"),
                        row.get("cost_usd"),
                        row.get("ttft_ms"),
                        row.get("tps"),
                        row.get("cache_hit_rate"),
                        int(row.get("created_at_ms") or 0),
                        int(row.get("updated_at_ms") or 0),
                        json.dumps(row, ensure_ascii=False, separators=(",", ":")),
                    ),
                )
                connection.execute(
                    "INSERT INTO cell_search(source_key, search_doc) VALUES (?, ?)",
                    (source_key, search_doc),
                )
            removed = [
                (source_ref, source_key)
                for source_ref, (_, source_key) in existing.items()
                if source_ref not in seen
            ]
            for source_ref, source_key in removed:
                connection.execute(
                    "DELETE FROM cells WHERE source_ref = ?", (source_ref,)
                )
                if (
                    connection.execute(
                        "SELECT 1 FROM cells WHERE source_key = ?", (source_key,)
                    ).fetchone()
                    is None
                ):
                    connection.execute(
                        "DELETE FROM cell_search WHERE source_key = ?", (source_key,)
                    )
            generation = self._meta_int(connection, "generation", 0) + 1
            self._set_meta(connection, "generation", str(generation))
            self._set_meta(connection, "valid_generation", "1")
            connection.commit()
            return generation

    def _row_for_document(
        self, document: SourceDocument
    ) -> tuple[dict[str, Any], bool, str]:
        trajectory = document.trajectory or {}
        meta = document.meta or {}
        if document.readable or document.meta is not None:
            summary = _catalog_summary(
                trajectory,
                meta,
                self._analysis_count(document),
            )
            if not document.readable:
                summary.pop("step_outline", None)
                summary["last_turn_finished_at_ms"] = None
            if summary.get("model") is None:
                summary["model"] = document.source.get("model")
        else:
            summary = {
                "trial_key": document.source.get("trial_key"),
                "trial_session_id": document.source.get("session_id"),
                "last_turn_finished_at_ms": None,
            }
        row = {
            "source_key": document.source_key,
            "source_ref": document.source_ref,
            **document.source,
            "artifact_updated_at_ms": document.updated_at_ms,
            **summary,
            "artifact_revision": document.fingerprint,
            "refreshable": document.refreshable,
            "active": document.active,
            "snapshot": document.snapshot,
            "readable": document.readable,
            "created_at_ms": document.updated_at_ms,
            "updated_at_ms": document.updated_at_ms,
            "last_status": document.last_status,
            "last_error": document.last_error,
            "last_refreshed_at_ms": None,
            "input_bytes": document.input_bytes,
            "notes_present": self._notes_present(document.source_ref, document.source),
        }
        if document.source_ref.startswith("runs/"):
            row["artifact_dir"] = document.source_ref
        if document.evidence_revision is not None:
            row["evidence_revision"] = document.evidence_revision
        if document.analysis_revision is not None:
            row["analysis_revision"] = document.analysis_revision
        return row, document.readable, _search_document(row, trajectory)

    def _analysis_count(self, document: SourceDocument) -> int:
        if document.source.get("kind") == HARBOR_SOURCE_KIND:
            return int(bool(document.harbor_analysis_markdown))
        cell_dir = self.store.resolve_artifact_dir(document.source_ref)
        return int(
            any(
                (cell_dir / filename).is_file()
                for filename in ("analysis.json", "analysis.md")
            )
        )

    def _notes_present(self, source_ref: str, source: dict[str, Any]) -> bool:
        if source.get("kind") == HARBOR_SOURCE_KIND:
            return self.sources.annotation_path(source_ref, "notes.md").is_file()
        return (self.store.resolve_artifact_dir(source_ref) / "notes.md").is_file()

    def _query_where(self, query: CatalogQuery) -> tuple[str, list[Any]]:
        scope_where, parameters = self._facet_scope_where(query)
        clauses = [] if scope_where == "1" else [scope_where]
        if query.search:
            if len(query.search) < 3:
                clauses.append("search_doc LIKE ? ESCAPE '\\' COLLATE NOCASE")
                parameters.append(f"%{_escape_like(query.search)}%")
            else:
                clauses.append(
                    "source_key IN (SELECT source_key FROM cell_search WHERE cell_search MATCH ?)"
                )
                parameters.append(_fts_literal(query.search))
        if query.tags:
            placeholders = ",".join("?" for _ in query.tags)
            clauses.append(
                f"EXISTS (SELECT 1 FROM json_each(tags_json) WHERE value IN ({placeholders}))"
            )
            parameters.extend(query.tags)
        for column, values in (
            ("category", query.categories),
            ("agent", query.agents),
            ("model", query.models),
            ("result", query.results),
            ("task", query.tasks),
            ("job", query.jobs),
            ("provider", query.providers),
        ):
            if not values:
                continue
            placeholders = ",".join("?" for _ in values)
            clauses.append(f"{column} IN ({placeholders})")
            parameters.extend(values)
        return " AND ".join(clauses) if clauses else "1", parameters

    def _combined_query_where(
        self,
        refinement: CatalogQuery,
        any_queries: Sequence[CatalogQuery],
    ) -> tuple[str, list[Any]]:
        if not any_queries:
            return self._query_where(refinement)
        any_clauses: list[str] = []
        parameters: list[Any] = []
        for query in any_queries:
            where, query_parameters = self._query_where(query)
            any_clauses.append(f"({where})")
            parameters.extend(query_parameters)
        refinement_where, refinement_parameters = self._query_where(refinement)
        parameters.extend(refinement_parameters)
        return (
            f"({' OR '.join(any_clauses)}) AND ({refinement_where})",
            parameters,
        )

    def _combined_facet_where(
        self,
        refinement: CatalogQuery,
        any_queries: Sequence[CatalogQuery],
    ) -> tuple[str, list[Any]]:
        if not any_queries:
            return self._facet_scope_where(refinement)
        any_clauses: list[str] = []
        parameters: list[Any] = []
        for query in any_queries:
            where, query_parameters = self._query_where(query)
            any_clauses.append(f"({where})")
            parameters.extend(query_parameters)
        scope_where, scope_parameters = self._facet_scope_where(refinement)
        parameters.extend(scope_parameters)
        return f"({' OR '.join(any_clauses)}) AND ({scope_where})", parameters

    def _facet_scope_where(self, query: CatalogQuery) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        if not query.include_unreadable:
            clauses.append("readable = 1")
        if query.state == "active":
            clauses.append("active = 1")
        elif query.state == "archived":
            clauses.append("active = 0")
        return " AND ".join(clauses) if clauses else "1", []

    def _facets(
        self, connection: sqlite3.Connection, where: str, parameters: list[Any]
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
        return facets

    def _prepare_database(self) -> None:
        rebuild = False
        try:
            with self._connect() as connection:
                self._probe_fts5(connection)
                tables = {
                    str(row[0])
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
                    )
                }
                if tables and "catalog_meta" in tables:
                    version = self._meta_int(connection, "schema_version", -1)
                    if version != CATALOG_SCHEMA_VERSION:
                        rebuild = True
                    elif connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                        rebuild = True
                elif tables:
                    rebuild = True
        except sqlite3.Error:
            rebuild = True
        if rebuild:
            self._delete_database_files()
        try:
            with self._connect() as connection:
                self._create_schema(connection)
        except sqlite3.Error as exc:
            raise RuntimeError(
                f"SQLite FTS5 with trigram support is required: {exc}"
            ) from exc

    def _create_schema(self, connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS catalog_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cells (
                source_key TEXT PRIMARY KEY,
                source_ref TEXT NOT NULL UNIQUE,
                fingerprint TEXT NOT NULL,
                artifact_revision TEXT NOT NULL,
                readable INTEGER NOT NULL,
                active INTEGER NOT NULL,
                last_status TEXT NOT NULL,
                search_doc TEXT NOT NULL,
                category TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                agent TEXT NOT NULL,
                model TEXT NOT NULL,
                result TEXT NOT NULL,
                task TEXT NOT NULL,
                job TEXT NOT NULL,
                provider TEXT NOT NULL,
                reward REAL,
                session_id TEXT NOT NULL,
                last_turn_end INTEGER,
                duration_ms REAL,
                turns REAL,
                tool_calls REAL,
                tool_errors REAL,
                tokens REAL,
                cost_usd REAL,
                ttft_ms REAL,
                tps REAL,
                cache_hit_rate REAL,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL,
                row_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS cells_state_end_key
                ON cells(active, readable, last_turn_end DESC, source_key);
            CREATE INDEX IF NOT EXISTS cells_category ON cells(category);
            CREATE INDEX IF NOT EXISTS cells_agent ON cells(agent);
            CREATE INDEX IF NOT EXISTS cells_model ON cells(model);
            CREATE INDEX IF NOT EXISTS cells_result ON cells(result);
            CREATE INDEX IF NOT EXISTS cells_task ON cells(task);
            CREATE INDEX IF NOT EXISTS cells_job ON cells(job);
            CREATE INDEX IF NOT EXISTS cells_provider ON cells(provider);
            """
        )
        connection.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS cell_search USING fts5("
            "source_key UNINDEXED, search_doc, tokenize='trigram case_sensitive 0')"
        )
        self._set_meta(connection, "schema_version", str(CATALOG_SCHEMA_VERSION))
        if self._meta(connection, "generation") is None:
            self._set_meta(connection, "generation", "0")
        if self._meta(connection, "valid_generation") is None:
            self._set_meta(connection, "valid_generation", "0")
        connection.commit()

    def _probe_fts5(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS temp.peval_fts_probe "
            "USING fts5(value, tokenize='trigram case_sensitive 0')"
        )
        connection.execute("DROP TABLE temp.peval_fts_probe")

    @contextmanager
    def _connect(self, *, readonly: bool = False) -> Iterator[sqlite3.Connection]:
        if readonly:
            connection = sqlite3.connect(
                f"{self.path.resolve().as_uri()}?mode=ro", uri=True, timeout=1.0
            )
        else:
            connection = sqlite3.connect(self.path, timeout=1.0)
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
        connection.row_factory = sqlite3.Row
        try:
            if readonly:
                connection.execute("BEGIN")
            yield connection
        finally:
            connection.close()

    @contextmanager
    def _workspace_writer_lease(self) -> Iterator[None]:
        lease_path = self.path.with_suffix(self.path.suffix + ".writer.lock")
        lease_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lease_path.open("a+")
        lock_kind = "fcntl"
        try:
            try:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except ImportError:
                import msvcrt

                lock_kind = "msvcrt"
                handle.seek(0)
                if not handle.read(1):
                    handle.write("0")
                    handle.flush()
                handle.seek(0)
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError as exc:
                    raise CatalogBusyError(
                        "serve catalog is busy in another process"
                    ) from exc
            except BlockingIOError as exc:
                raise CatalogBusyError(
                    "serve catalog is busy in another process"
                ) from exc
            yield
        finally:
            try:
                if lock_kind == "msvcrt":
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except (ImportError, OSError, ValueError):
                pass
            handle.close()

    def _delete_database_files(self) -> None:
        for path in (
            self.path,
            self.path.with_name(self.path.name + "-wal"),
            self.path.with_name(self.path.name + "-shm"),
        ):
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def _meta(self, connection: sqlite3.Connection, key: str) -> str | None:
        try:
            row = connection.execute(
                "SELECT value FROM catalog_meta WHERE key = ?", (key,)
            ).fetchone()
        except sqlite3.OperationalError:
            return None
        return str(row[0]) if row is not None else None

    def _meta_int(self, connection: sqlite3.Connection, key: str, default: int) -> int:
        value = self._meta(connection, key)
        try:
            return int(value) if value is not None else default
        except ValueError:
            return default

    def _set_meta(self, connection: sqlite3.Connection, key: str, value: str) -> None:
        connection.execute(
            "INSERT INTO catalog_meta(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


_SAVED_VIEW_SUMMARY_METRICS = (
    ("duration_ms", "duration"),
    ("ttft_ms", "duration"),
    ("tps", "number"),
    ("tokens", "number"),
    ("cache_hit_rate", "percent"),
    ("turns", "number"),
    ("model_duration_ms", "duration"),
    ("total_tool_calls", "number"),
    ("tool_error_rate", "percent"),
    ("score", "number"),
)


def _summary_query_scope(query: CatalogQuery) -> tuple[Any, ...]:
    return (
        query.state,
        query.search,
        tuple(sorted(query.categories)),
        tuple(sorted(query.tags)),
        tuple(sorted(query.agents)),
        tuple(sorted(query.models)),
        tuple(sorted(query.results)),
        tuple(sorted(query.tasks)),
        tuple(sorted(query.jobs)),
        tuple(sorted(query.providers)),
        query.include_unreadable,
    )


def _summary_rows(
    connection: sqlite3.Connection,
    where: str,
    parameters: Sequence[Any],
) -> Iterator[dict[str, Any]]:
    records = connection.execute(
        f"""
        SELECT category AS source_category,
               agent AS agent_name,
               model,
               task AS task_name,
               job AS job_name,
               provider AS model_provider,
               reward AS score,
               duration_ms,
               ttft_ms,
               tps,
               tokens,
               cache_hit_rate,
               turns,
               json_extract(row_json, '$.model_duration_ms') AS model_duration_ms,
               tool_calls AS total_tool_calls,
               tool_errors AS total_tool_errors
        FROM cells
        WHERE {where}
        """,
        parameters,
    )
    for record in records:
        yield dict(record)


@dataclass
class _SummaryGroupValues:
    count: int = 0
    metrics: list[list[float]] = field(
        default_factory=lambda: [[] for _item in _SAVED_VIEW_SUMMARY_METRICS]
    )


def _saved_view_summary(
    name: str,
    group_by: str,
    rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    grouped: dict[str | None, _SummaryGroupValues] = {}
    if group_by == "overall":
        grouped["overall"] = _SummaryGroupValues()
    matched_count = 0
    for row in rows:
        matched_count += 1
        key = _saved_view_group_key(row, group_by)
        values = grouped.get(key)
        if values is None:
            if len(grouped) >= SUMMARY_GROUP_LIMIT:
                raise CatalogSummaryCapacityError(
                    f"grouped summaries support at most {SUMMARY_GROUP_LIMIT} groups; "
                    "refine the query or use an overall summary"
                )
            values = _SummaryGroupValues()
            grouped[key] = values
        values.count += 1
        for index, (metric_key, _value_type) in enumerate(_SAVED_VIEW_SUMMARY_METRICS):
            metric_value = _saved_view_metric_value(row, metric_key)
            if metric_value is not None:
                values.metrics[index].append(metric_value)
    groups = [
        {
            "key": key,
            "label": "-" if key is None else key,
            "count": group_values.count,
            "metrics": _saved_view_metric_rows(group_values.metrics),
        }
        for key, group_values in sorted(
            grouped.items(),
            key=lambda item: (
                ("-" if item[0] is None else item[0]).casefold(),
                item[0] is not None,
            ),
        )
    ]
    return {
        "name": name,
        "group_by": group_by,
        "matched_count": matched_count,
        "groups": groups,
    }


def _saved_view_group_key(row: dict[str, Any], group_by: str) -> str | None:
    if group_by == "overall":
        return "overall"
    if group_by == "model":
        return str(row.get("model") or "-")
    if group_by == "category":
        category = str(row.get("source_category") or "").strip()
        return category or None
    if group_by == "task":
        return str(row.get("task_name") or "-")
    if group_by == "job":
        return str(row.get("job_name") or "-")
    if group_by == "provider":
        return str(row.get("model_provider") or "-")
    return str(row.get("agent_name") or row.get("adapter") or "-")


def _saved_view_metric_rows(
    metric_values: list[list[float]],
) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    for (key, value_type), values in zip(_SAVED_VIEW_SUMMARY_METRICS, metric_values):
        metrics.append(
            {
                "key": key,
                "type": value_type,
                "count": len(values),
                "mean": sum(values) / len(values) if values else None,
                "distribution": _saved_view_distribution(values),
            }
        )
    return metrics


def _saved_view_metric_value(row: dict[str, Any], key: str) -> float | None:
    if key != "tool_error_rate":
        return _optional_number(row.get(key))
    calls = _optional_number(row.get("total_tool_calls"))
    if calls is None or calls == 0:
        return None
    errors = _optional_number(row.get("total_tool_errors"))
    return (errors or 0) / calls


def _saved_view_distribution(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    ordered = sorted(values)
    return {
        "min": ordered[0],
        "q1": _saved_view_percentile(ordered, 25),
        "p50": _saved_view_percentile(ordered, 50),
        "q3": _saved_view_percentile(ordered, 75),
        "p95": _saved_view_percentile(ordered, 95),
        "max": ordered[-1],
    }


def _saved_view_percentile(ordered: list[float], percentile: int) -> float:
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * (percentile / 100)
    lower = int(position)
    upper = min(len(ordered) - 1, lower + 1)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _report_with_live_task_ref(
    report: dict[str, Any], config: ToolConfig
) -> dict[str, Any]:
    metas = report.get("trajectory_meta")
    if not isinstance(metas, list):
        return report
    projected = list(metas)
    changed = False
    for index, original in enumerate(metas):
        if not isinstance(original, dict) or original.get("adapter") != "harbor":
            continue
        task_ref = _live_task_ref(original, config)
        if task_ref is None:
            continue
        metadata = original.get("task_metadata")
        if not isinstance(metadata, dict):
            continue
        copy = dict(original)
        copy["task_metadata"] = {**metadata, "task_ref": task_ref}
        projected[index] = copy
        changed = True
    if not changed:
        return report
    return {**report, "trajectory_meta": projected}


def _live_task_ref(meta: dict[str, Any], config: ToolConfig) -> dict[str, str] | None:
    metadata = meta.get("task_metadata")
    provenance = meta.get("harbor_provenance")
    if not isinstance(metadata, dict) or not isinstance(provenance, dict):
        return None
    if metadata.get("status") not in {"resolved", "digest_mismatch"}:
        return None
    task_path_value = metadata.get("path")
    mount_id = provenance.get("mount_id")
    if not isinstance(task_path_value, str) or not isinstance(mount_id, str):
        return None
    mount = next((item for item in config.harbor_mounts if item.id == mount_id), None)
    if mount is None:
        return None
    task_path = Path(os.path.abspath(Path(task_path_value).expanduser()))
    task_name = task_path.name
    if not TASK_DIRECTORY_RE.fullmatch(task_name):
        return None
    datasets = {item.id: item for item in config.harbor_datasets}
    matches = []
    for dataset_id in mount.dataset_ids:
        dataset = datasets.get(dataset_id)
        if dataset is None:
            continue
        root = Path(os.path.abspath(Path(dataset.path).expanduser()))
        if task_path.parent == root:
            matches.append(dataset_id)
    if len(matches) != 1:
        return None
    return {"dataset_id": matches[0], "task": task_name}


def _catalog_summary(
    trajectory: dict[str, Any], meta: dict[str, Any], analysis_count: int
) -> dict[str, Any]:
    metrics = _summary_metrics(trajectory, meta)
    agent = trajectory.get("agent")
    if not isinstance(agent, dict):
        agent = {}
    warnings = meta.get("warnings")
    return {
        "trial_key": optional_str(
            meta.get("trial_key") or trajectory.get("trajectory_id")
        ),
        "trial_session_id": optional_str(trajectory.get("session_id")),
        "step_outline": _step_outline(trajectory, meta),
        "last_turn_finished_at_ms": optional_int(meta.get("finished_at_ms")),
        "status": optional_str(meta.get("status")) or "unknown",
        "score": _optional_number(meta.get("score")),
        "score_message": optional_str(meta.get("score_message")),
        "duration_ms": optional_int(meta.get("duration_ms")),
        "wall_duration_ms": _wall_duration_ms(meta),
        "model_duration_ms": _model_duration_ms(trajectory, meta),
        "turns": _optional_number(final_metric(metrics, "total_turns")),
        "total_tool_calls": _optional_number(final_metric(metrics, "total_tool_calls")),
        "total_tool_errors": _optional_number(
            final_metric(metrics, "total_tool_errors")
        ),
        "tokens": token_total(metrics),
        "cost_usd": _optional_number(metrics.get("total_cost_usd")),
        "warnings": len(warnings) if isinstance(warnings, list) else 0,
        "analysis_count": max(0, min(2, int(analysis_count))),
        "model": optional_str(agent.get("model_name")),
        "task_name": optional_str(meta.get("task_name")),
        "job_name": optional_str(meta.get("job_name")),
        "trial_name": optional_str(meta.get("trial_name")),
        "model_provider": optional_str(meta.get("model_provider")),
        "task_keywords": meta.get("task_keywords") or [],
        "rewards": meta.get("rewards") or {},
        "harbor_provenance": meta.get("harbor_provenance") or {},
        "task_metadata": _catalog_task_metadata(meta.get("task_metadata")),
        **inference_row_metrics(metrics),
    }


def _catalog_task_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    fields = {
        "description",
        "diagnostic",
        "digest_comparison",
        "digest_matches",
        "keywords",
        "live",
        "live_digest",
        "name",
        "path",
        "requested_name",
        "status",
        "version",
    }
    return {key: item for key, item in value.items() if key in fields}


def _summary_metrics(
    trajectory: dict[str, Any], meta: dict[str, Any]
) -> dict[str, Any]:
    source = meta.get("source_metrics")
    fallback = source if isinstance(source, dict) else {}
    trajectory_metrics = trajectory.get("final_metrics")
    explicit = trajectory_metrics if isinstance(trajectory_metrics, dict) else {}
    metrics = {**fallback, **explicit}
    fallback_extra = (
        fallback.get("extra") if isinstance(fallback.get("extra"), dict) else {}
    )
    explicit_extra = (
        explicit.get("extra") if isinstance(explicit.get("extra"), dict) else {}
    )
    if fallback_extra or explicit_extra:
        metrics["extra"] = {**fallback_extra, **explicit_extra}
    return metrics


def _step_outline(
    trajectory: dict[str, Any], meta: dict[str, Any]
) -> list[dict[str, Any]]:
    metadata_by_step_id = {
        str(step.get("step_id")): step
        for step in meta.get("steps", [])
        if isinstance(step, dict) and step.get("step_id") is not None
    }
    outline: list[dict[str, Any]] = []
    for step in trajectory.get("steps", []):
        if not isinstance(step, dict) or step.get("step_id") is None:
            continue
        step_id = step["step_id"]
        source = str(step.get("source") or "").strip().lower()
        normalized_source = "agent" if source == "assistant" else source
        if normalized_source not in {"system", "user", "agent"}:
            normalized_source = "unknown"
        item: dict[str, Any] = {"step_id": step_id, "source": normalized_source}
        duration = _optional_number(
            metadata_by_step_id.get(str(step_id), {}).get("duration_ms")
        )
        if duration is not None:
            item["duration_ms"] = duration
        outline.append(item)
    return outline


def _model_duration_ms(
    trajectory: dict[str, Any], meta: dict[str, Any]
) -> int | float | None:
    trajectory_steps = trajectory.get("steps")
    meta_steps = meta.get("steps")
    if not isinstance(trajectory_steps, list) or not isinstance(meta_steps, list):
        return None
    total: int | float = 0
    count = 0
    for index, step_meta in enumerate(meta_steps):
        if not isinstance(step_meta, dict) or index >= len(trajectory_steps):
            continue
        step = trajectory_steps[index]
        if not isinstance(step, dict):
            continue
        if str(step.get("source") or "").lower() not in {"agent", "assistant"}:
            continue
        duration = _optional_number(step_meta.get("duration_ms"))
        if duration is None:
            continue
        total += duration
        count += 1
    return total if count else None


def _wall_duration_ms(meta: dict[str, Any]) -> int | None:
    explicit = optional_int(meta.get("wall_duration_ms"))
    if explicit is not None:
        return explicit
    started = optional_int(meta.get("started_at_ms"))
    finished = optional_int(meta.get("finished_at_ms"))
    if started is None or finished is None:
        return None
    return max(0, finished - started)


def _optional_number(value: Any) -> int | float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _search_document(row: dict[str, Any], trajectory: dict[str, Any]) -> str:
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
        "reward": "reward",
        "duration_ms": "duration_ms",
        "turns": "turns",
        "total_tool_calls": "tool_calls",
        "tool_error_rate": "CASE WHEN tool_calls > 0 THEN coalesce(tool_errors, 0) / tool_calls END",
        "tokens": "tokens",
        "cost_usd": "cost_usd",
        "ttft_ms": "ttft_ms",
        "tps": "tps",
        "cache_hit_rate": "cache_hit_rate",
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
    "source_category": "trim(category) <> ''",
    "source_tags": "json_array_length(tags_json) > 0",
    "session_id": "trim(session_id) <> ''",
    "task_name": f"({_json_value_present('$.source_alias')}) OR trim(task) <> ''",
    "agent": "trim(agent) <> ''",
    "model": "trim(model) <> ''",
    "job_name": "trim(job) <> ''",
    "model_provider": "trim(provider) <> ''",
    "reward": f"reward IS NOT NULL OR ({_json_value_present('$.rewards')})",
    "status": "trim(last_status) <> ''",
    "finished_at_ms": "last_turn_end IS NOT NULL",
    "duration_ms": "duration_ms IS NOT NULL",
    "ttft_ms": "ttft_ms IS NOT NULL",
    "tps": "tps IS NOT NULL",
    "turns": "turns IS NOT NULL",
    "total_tool_calls": "tool_calls IS NOT NULL",
    "tool_error_rate": "tool_calls > 0 AND tool_errors IS NOT NULL",
    "tokens": "tokens IS NOT NULL",
    "cache_hit_rate": "cache_hit_rate IS NOT NULL",
    "cost_usd": "cost_usd IS NOT NULL",
    "analysis_count": _json_value_present("$.analysis_count"),
    "notes": "json_extract(row_json, '$.notes_present') = 1",
}


def _empty_column_presence() -> dict[str, int]:
    return {**dict.fromkeys(_CATALOG_COLUMN_PRESENCE_SQL, 0), "workspace_reports": 0}


def _catalog_query_presence(
    connection: sqlite3.Connection,
    where: str,
    parameters: Sequence[Any],
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
    return matched, presence


def _count_matching_source_refs(
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


def _empty_facets() -> dict[str, list[dict[str, Any]]]:
    return {
        "categories": [],
        "tags": [],
        "agents": [],
        "models": [],
        "results": [],
        "tasks": [],
        "jobs": [],
        "providers": [],
    }


def _chunks(values: list[str], size: int) -> Iterator[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]
