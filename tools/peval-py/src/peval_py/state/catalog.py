from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Sequence

from peval_py._state.annotations import optional_int, optional_str
from peval_py._state.artifacts import (
    read_json_object,
    relative_to_root,
    source_key_for_trial,
    source_key_for_trial_cell_components,
    trial_artifacts,
)
from peval_py.config import ToolConfig
from peval_py.report.metrics import final_metric, token_total
from peval_py.state.constants import SOURCE_STATUS_MISSING, SOURCE_STATUS_OK
from peval_py.state.store import ServeStateStore


CATALOG_SCHEMA_VERSION = 5
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 100
CATALOG_RELATIVE_PATH = Path(".cache/peval-py/serve-catalog.sqlite3")
FINGERPRINT_FILES = (
    "agent/trajectory.json",
    "agent/trajectory_meta.json",
    ".peval/state.json",
    "notes.md",
    "analysis.json",
    "analysis.md",
)


class CatalogBusyError(RuntimeError):
    pass


@dataclass(frozen=True)
class CatalogQuery:
    state: str = "active"
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE
    search: str = ""
    sort: str = "last_turn_end"
    direction: str = "desc"
    tags: tuple[str, ...] = ()
    agents: tuple[str, ...] = ()
    models: tuple[str, ...] = ()
    results: tuple[str, ...] = ()
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
            tags=_normalized_values(self.tags),
            agents=_normalized_values(self.agents),
            models=_normalized_values(self.models),
            results=_normalized_values(self.results),
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
        self.path = store.paths.root / CATALOG_RELATIVE_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._state_lock = threading.RLock()
        self._writer_lock = threading.Lock()
        self._checking = False
        self._current_operation: OperationStatus | None = None
        self._recent_operation: OperationStatus | None = None
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
            raise CatalogBusyError("serve catalog is busy with another writer operation")
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
    ) -> CatalogPage:
        query = query.normalized()
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
                )
            where, parameters = self._query_where(query)
            total = int(
                connection.execute(
                    f"SELECT count(*) FROM cells WHERE {where}", parameters
                ).fetchone()[0]
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
                self._facets(connection, *self._facet_scope_where(query))
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
        )

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
                rows = [
                    json.loads(str(record[0]))
                    for record in connection.execute(
                        f"SELECT row_json FROM cells WHERE {where}", parameters
                    )
                ]
                summaries.append(_saved_view_summary(name, group_by, rows))
        return {
            "generation": generation,
            "checking": self.checking,
            "stale": self.checking,
            "views": summaries,
        }

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
        report = self.store.report_for_rows([row], self.config)
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
                    "SELECT row_json FROM cells WHERE readable = 1 ORDER BY source_key"
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
                raise CatalogBusyError("serve catalog is busy with another writer operation")
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
            raise CatalogBusyError("serve catalog is busy with another writer operation")
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
                raise CatalogBusyError("serve catalog is busy with another writer operation")
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
                                if isinstance(item, (str, int, float, bool, dict, list)) or item is None:
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
                status.failures.append({"index": None, "status": "error", "error": str(exc)})
        finally:
            with self._state_lock:
                self._checking = False
                self._recent_operation = status
                self._current_operation = status

    def _reconcile_locked(self) -> int:
        candidates = self._discover_cell_dirs()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = {
                str(row["artifact_dir"]): (str(row["fingerprint"]), str(row["source_key"]))
                for row in connection.execute(
                    "SELECT artifact_dir, fingerprint, source_key FROM cells"
                )
            }
            seen: set[str] = set()
            for cell_dir in candidates:
                artifact_dir = relative_to_root(self.store.paths.root, cell_dir)
                seen.add(artifact_dir)
                fingerprint = _artifact_fingerprint(cell_dir)
                prior = existing.get(artifact_dir)
                if prior is not None and prior[0] == fingerprint:
                    continue
                row, readable, search_doc = self._parse_cell(cell_dir, fingerprint)
                source_key = str(row["source_key"])
                connection.execute(
                    "DELETE FROM cells WHERE artifact_dir = ? OR source_key = ?",
                    (artifact_dir, source_key),
                )
                if prior is not None and prior[1] != source_key:
                    connection.execute(
                        "DELETE FROM cell_search WHERE source_key = ?", (prior[1],)
                    )
                connection.execute("DELETE FROM cell_search WHERE source_key = ?", (source_key,))
                connection.execute(
                    """
                    INSERT INTO cells (
                        source_key, artifact_dir, fingerprint, artifact_revision,
                        readable, active, last_status, search_doc, tags_json,
                        agent, model, result, session_id, last_turn_end,
                        duration_ms, turns, tool_calls, tool_errors, tokens, cost_usd,
                        created_at_ms, updated_at_ms, row_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source_key,
                        artifact_dir,
                        fingerprint,
                        fingerprint,
                        int(readable),
                        int(bool(row.get("active", True))),
                        str(row.get("last_status") or ""),
                        search_doc,
                        json.dumps(row.get("source_tags") or [], ensure_ascii=False),
                        str(row.get("agent_name") or row.get("adapter") or ""),
                        str(row.get("model") or ""),
                        str(row.get("status") or row.get("last_status") or ""),
                        str(row.get("session_id") or row.get("trial_session_id") or ""),
                        optional_int(row.get("last_turn_finished_at_ms")),
                        row.get("duration_ms"),
                        row.get("turns"),
                        row.get("total_tool_calls"),
                        row.get("total_tool_errors"),
                        row.get("tokens"),
                        row.get("cost_usd"),
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
                (artifact_dir, source_key)
                for artifact_dir, (_, source_key) in existing.items()
                if artifact_dir not in seen
            ]
            for artifact_dir, source_key in removed:
                connection.execute("DELETE FROM cells WHERE artifact_dir = ?", (artifact_dir,))
                if connection.execute(
                    "SELECT 1 FROM cells WHERE source_key = ?", (source_key,)
                ).fetchone() is None:
                    connection.execute("DELETE FROM cell_search WHERE source_key = ?", (source_key,))
            generation = self._meta_int(connection, "generation", 0) + 1
            self._set_meta(connection, "generation", str(generation))
            self._set_meta(connection, "valid_generation", "1")
            connection.commit()
            return generation

    def _parse_cell(
        self, cell_dir: Path, fingerprint: str
    ) -> tuple[dict[str, Any], bool, str]:
        identity = self.store.cell_path_identity(cell_dir)
        artifact_dir = relative_to_root(self.store.paths.root, cell_dir)
        source_key = self.store.source_key_for_cell_identity(identity)
        if not source_key:
            source_key = source_key_for_trial_cell_components(
                eval_slug=self.config.analysis_eval_slug,
                agent_id=cell_dir.parent.parent.name,
                session_id=cell_dir.parent.name,
                cell_key=cell_dir.name,
            )
        artifacts = trial_artifacts(cell_dir)
        try:
            if not _has_complete_artifacts(cell_dir):
                raise ValueError(f"Trial cell artifacts not found: {artifact_dir}")
            trajectory = read_json_object(artifacts.trajectory_path)
            meta = read_json_object(artifacts.meta_path)
            state = self.store.read_source_state(cell_dir)
            source = self.store.source_row_for_artifact_cell(cell_dir, trajectory, meta)
            source["source_alias"] = optional_str(state.get("source_alias"))
            source["source_tags"] = self.store.source_tags_from_state(state)
            source_key = source_key_for_trial(
                self.config.analysis_eval_slug, source, trajectory, meta
            )
            summary = _catalog_summary(trajectory, meta, cell_dir)
            timestamp = _artifact_updated_at_ms(cell_dir)
            status = optional_str(state.get("last_status")) or SOURCE_STATUS_OK
            row = {
                "source_key": source_key,
                **source,
                "artifact_dir": artifact_dir,
                "artifact_updated_at_ms": timestamp,
                **summary,
                "artifact_revision": fingerprint,
                "refreshable": False,
                "active": bool(state.get("active", True)),
                "snapshot": True,
                "readable": True,
                "created_at_ms": int(state.get("created_at_ms") or timestamp),
                "updated_at_ms": int(state.get("updated_at_ms") or timestamp),
                "last_status": status,
                "last_error": optional_str(state.get("last_error")),
                "last_refreshed_at_ms": None,
                "input_bytes": artifacts.trajectory_path.stat().st_size
                + artifacts.meta_path.stat().st_size,
            }
            return row, True, _search_document(row, trajectory)
        except Exception as exc:  # noqa: BLE001 - one malformed cell must not abort a generation.
            state: dict[str, Any] = {}
            try:
                state = self.store.read_source_state(cell_dir)
            except Exception:  # noqa: BLE001 - retain path identity even with invalid overlay.
                pass
            timestamp = _artifact_updated_at_ms(cell_dir)
            row = {
                "source_key": source_key,
                **self.store.missing_source_row(artifact_dir, identity, state),
                "artifact_dir": artifact_dir,
                "artifact_updated_at_ms": timestamp,
                **self.store.missing_trial_summary(identity),
                "artifact_revision": fingerprint,
                "refreshable": False,
                "active": bool(state.get("active", True)),
                "snapshot": True,
                "readable": False,
                "created_at_ms": int(state.get("created_at_ms") or timestamp),
                "updated_at_ms": int(state.get("updated_at_ms") or timestamp),
                "last_status": (
                    SOURCE_STATUS_MISSING
                    if not _has_complete_artifacts(cell_dir)
                    else "error"
                ),
                "last_error": str(exc),
                "last_refreshed_at_ms": None,
                "input_bytes": sum(
                    path.stat().st_size
                    for path in (artifacts.trajectory_path, artifacts.meta_path)
                    if path.is_file()
                ),
            }
            return row, False, _search_document(row, {})

    def _discover_cell_dirs(self) -> list[Path]:
        run_root = self.store.paths.root / "runs" / self.config.analysis_eval_slug
        if not run_root.is_dir():
            return []
        found: set[Path] = set()
        for agent in _scandir_dirs(run_root):
            for session in _scandir_dirs(agent):
                for cell in _scandir_dirs(session):
                    state_path = self.store.source_state_path(cell)
                    if _has_complete_artifacts(cell) or (
                        state_path.is_file()
                        and not state_path.is_symlink()
                        and not state_path.parent.is_symlink()
                    ):
                        found.add(cell)
        return sorted(found, key=lambda path: path.as_posix())

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
            ("agent", query.agents),
            ("model", query.models),
            ("result", query.results),
        ):
            if not values:
                continue
            placeholders = ",".join("?" for _ in values)
            clauses.append(f"{column} IN ({placeholders})")
            parameters.extend(values)
        return " AND ".join(clauses) if clauses else "1", parameters

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
        for name, column in (("agents", "agent"), ("models", "model"), ("results", "result")):
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
            raise RuntimeError(f"SQLite FTS5 with trigram support is required: {exc}") from exc

    def _create_schema(self, connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS catalog_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cells (
                source_key TEXT PRIMARY KEY,
                artifact_dir TEXT NOT NULL UNIQUE,
                fingerprint TEXT NOT NULL,
                artifact_revision TEXT NOT NULL,
                readable INTEGER NOT NULL,
                active INTEGER NOT NULL,
                last_status TEXT NOT NULL,
                search_doc TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                agent TEXT NOT NULL,
                model TEXT NOT NULL,
                result TEXT NOT NULL,
                session_id TEXT NOT NULL,
                last_turn_end INTEGER,
                duration_ms REAL,
                turns REAL,
                tool_calls REAL,
                tool_errors REAL,
                tokens REAL,
                cost_usd REAL,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL,
                row_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS cells_state_end_key
                ON cells(active, readable, last_turn_end DESC, source_key);
            CREATE INDEX IF NOT EXISTS cells_agent ON cells(agent);
            CREATE INDEX IF NOT EXISTS cells_model ON cells(model);
            CREATE INDEX IF NOT EXISTS cells_result ON cells(result);
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

    def _meta_int(
        self, connection: sqlite3.Connection, key: str, default: int
    ) -> int:
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


def _scandir_dirs(root: Path) -> Iterator[Path]:
    try:
        with os.scandir(root) as entries:
            ordered = sorted(entries, key=lambda entry: entry.name)
    except OSError:
        return
    for entry in ordered:
        try:
            if entry.is_dir(follow_symlinks=False):
                yield Path(entry.path)
        except OSError:
            continue


def _artifact_fingerprint(cell_dir: Path) -> str:
    parts: list[str] = []
    for relative in FINGERPRINT_FILES:
        path = cell_dir / relative
        try:
            stat = path.stat(follow_symlinks=False)
            parts.append(f"{relative}:{stat.st_size}:{stat.st_mtime_ns}:{stat.st_mode}")
        except FileNotFoundError:
            parts.append(f"{relative}:-")
        except OSError as exc:
            parts.append(f"{relative}:error:{exc.errno}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _has_complete_artifacts(cell_dir: Path) -> bool:
    artifacts = trial_artifacts(cell_dir)
    if artifacts.trajectory_path.parent.is_symlink():
        return False
    return all(
        path.is_file() and not path.is_symlink()
        for path in (artifacts.trajectory_path, artifacts.meta_path)
    )


def _artifact_updated_at_ms(cell_dir: Path) -> int:
    values: list[int] = []
    for relative in FINGERPRINT_FILES:
        try:
            values.append((cell_dir / relative).stat(follow_symlinks=False).st_mtime_ns // 1_000_000)
        except OSError:
            continue
    return max(values) if values else 0


_SAVED_VIEW_SUMMARY_METRICS = (
    ("duration_ms", "duration"),
    ("tokens", "number"),
    ("turns", "number"),
    ("model_duration_ms", "duration"),
    ("total_tool_calls", "number"),
    ("tool_error_rate", "percent"),
)


def _saved_view_summary(
    name: str,
    group_by: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    if group_by == "overall":
        grouped["overall"] = rows
    else:
        for row in rows:
            if group_by == "model":
                label = str(row.get("model") or "-")
            else:
                label = str(row.get("agent_name") or row.get("adapter") or "-")
            grouped.setdefault(label, []).append(row)
    groups = [
        {
            "key": key,
            "label": key,
            "count": len(group_rows),
            "metrics": _saved_view_metric_rows(group_rows),
        }
        for key, group_rows in sorted(grouped.items(), key=lambda item: item[0].casefold())
    ]
    return {
        "name": name,
        "group_by": group_by,
        "matched_count": len(rows),
        "groups": groups,
    }


def _saved_view_metric_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    for key, value_type in _SAVED_VIEW_SUMMARY_METRICS:
        values = [
            value
            for value in (_saved_view_metric_value(row, key) for row in rows)
            if value is not None
        ]
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


def _catalog_summary(
    trajectory: dict[str, Any], meta: dict[str, Any], cell_dir: Path
) -> dict[str, Any]:
    metrics = trajectory.get("final_metrics")
    if not isinstance(metrics, dict):
        metrics = {}
    agent = trajectory.get("agent")
    if not isinstance(agent, dict):
        agent = {}
    warnings = meta.get("warnings")
    analysis_present = any((cell_dir / name).is_file() for name in ("analysis.json", "analysis.md"))
    return {
        "trial_key": optional_str(meta.get("trial_key") or trajectory.get("trajectory_id")),
        "trial_session_id": optional_str(trajectory.get("session_id")),
        "step_outline": _step_outline(trajectory, meta),
        "last_turn_finished_at_ms": optional_int(meta.get("finished_at_ms")),
        "status": optional_str(meta.get("status")) or "unknown",
        "duration_ms": optional_int(meta.get("duration_ms")),
        "wall_duration_ms": _wall_duration_ms(meta),
        "model_duration_ms": _measured_model_duration_ms(trajectory, meta),
        "turns": _optional_number(final_metric(metrics, "total_turns")),
        "total_tool_calls": _optional_number(final_metric(metrics, "total_tool_calls")),
        "total_tool_errors": _optional_number(final_metric(metrics, "total_tool_errors")),
        "tokens": token_total(metrics),
        "cost_usd": _optional_number(metrics.get("total_cost_usd")),
        "warnings": len(warnings) if isinstance(warnings, list) else 0,
        "analysised": analysis_present,
        "model": optional_str(agent.get("model_name")),
    }


def _step_outline(trajectory: dict[str, Any], meta: dict[str, Any]) -> list[dict[str, Any]]:
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


def _measured_model_duration_ms(
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
        if "estimate" in str(step_meta.get("duration_source") or "").lower():
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
        row.get("source_tags"),
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
    return tuple(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def _escape_like(value: str) -> str:
    return value.casefold().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _fts_literal(value: str) -> str:
    return '"' + value.casefold().replace('"', '""') + '"'


def _sort_expression(sort: str) -> str:
    mapping = {
        "last_turn_end": "last_turn_end",
        "session": "session_id COLLATE NOCASE",
        "agent": "agent COLLATE NOCASE",
        "model": "model COLLATE NOCASE",
        "result": "result COLLATE NOCASE",
        "duration_ms": "duration_ms",
        "turns": "turns",
        "total_tool_calls": "tool_calls",
        "tool_error_rate": "CASE WHEN tool_calls > 0 THEN coalesce(tool_errors, 0) / tool_calls END",
        "tokens": "tokens",
        "cost_usd": "cost_usd",
        "created": "created_at_ms",
        "updated": "updated_at_ms",
        "source_key": "source_key",
    }
    if sort not in mapping:
        raise ValueError(f"unsupported catalog sort: {sort}")
    return mapping[sort]


def _empty_facets() -> dict[str, list[dict[str, Any]]]:
    return {"tags": [], "agents": [], "models": [], "results": []}


def _chunks(values: list[str], size: int) -> Iterator[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]
