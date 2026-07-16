from __future__ import annotations

from argparse import Namespace
from threading import Event, Lock, Thread
from typing import Any, Callable, Sequence

from peval_py.config import ToolConfig
from peval_py.inputs import AdapterAssignments
from peval_py.report import empty_report
from peval_py.serve.sources import load_serve_inputs
from peval_py.state import (
    CatalogBusyError,
    CatalogPage,
    CatalogQuery,
    DetailEnvelope,
    OperationStatus,
    ServeStateStore,
    WorkspaceCatalog,
)
from peval_py.workspace_reports import WorkspaceReportLibrary
from peval_py.workspace_views import WorkspaceViewLibrary


class ServeRuntime:
    def __init__(
        self,
        store: ServeStateStore,
        config: ToolConfig,
        *,
        initialize_snapshot: bool = True,
    ) -> None:
        self.store = store
        self.config = config
        self.catalog = WorkspaceCatalog(store, config)
        self.workspace_reports = WorkspaceReportLibrary(
            store.paths.root,
            self._all_catalog_rows,
        )
        self.workspace_views = WorkspaceViewLibrary(store.paths.root)
        self._lock = Lock()
        self._ready = Event()
        self._ready.set()
        self._thread: Thread | None = None
        self._loading = False
        self._load_error: str | None = None
        if initialize_snapshot:
            self._loading = True
            self._ready.clear()
            try:
                self.catalog.reconcile()
            finally:
                self._loading = False
                self._ready.set()

    def start_initial_load(
        self,
        args: Namespace,
        adapter_assignments: AdapterAssignments,
    ) -> None:
        with self._lock:
            if self._thread is not None:
                return
            self._loading = True
            self._load_error = None
            self._ready.clear()
            self._thread = Thread(
                target=self._run_initial_load,
                args=(args, adapter_assignments),
                daemon=True,
            )
            self._thread.start()

    def _run_initial_load(
        self,
        args: Namespace,
        adapter_assignments: AdapterAssignments,
    ) -> None:
        error: str | None = None
        try:
            loaded_inputs = load_serve_inputs(args, adapter_assignments, self.config)
            self.store.import_loaded_sources(loaded_inputs, self.config)
            self.catalog.reconcile()
        except Exception as exc:  # noqa: BLE001 - background startup boundary.
            error = str(exc)
            if not self.catalog.has_generation:
                try:
                    self.catalog.reconcile()
                except Exception:  # noqa: BLE001 - preserve the primary startup error.
                    pass
        with self._lock:
            self._loading = False
            self._load_error = error
            self._ready.set()

    def wait_until_ready(self, timeout: float | None = None) -> bool:
        return self._ready.wait(timeout)

    def ensure_ready(self) -> None:
        if not self.catalog.has_generation:
            self._ready.wait()
        with self._lock:
            error = self._load_error
        if error and not self.catalog.has_generation:
            raise ValueError(error)

    def is_loading(self) -> bool:
        with self._lock:
            return self._loading or self.catalog.checking

    def load_error(self) -> str | None:
        with self._lock:
            return self._load_error

    def set_config(self, config: ToolConfig) -> None:
        with self._lock:
            self.config = config
            self.catalog.config = config

    def catalog_page(self, query: CatalogQuery) -> CatalogPage:
        return self.catalog.query(query)

    def workspace_view_catalog(self) -> list[dict[str, Any]]:
        return [view.to_dict() for view in self.workspace_views.list()]

    def workspace_view_summaries(self) -> dict[str, Any]:
        views = self.workspace_views.list()
        payload = self.catalog.summarize_saved_views(
            [(view.name, view.filters, view.group_by) for view in views]
        )
        summaries = {item["name"]: item for item in payload["views"]}
        return {
            **payload,
            "views": [
                {**view.to_dict(), **summaries.get(view.name, {})}
                for view in views
            ],
        }

    def detail(self, source_key: str) -> DetailEnvelope:
        self.ensure_ready()
        return self.catalog.load_detail(source_key)

    def resolve_keys(self, keys: list[str]) -> list[str]:
        return self.catalog.resolve_keys(keys)

    def report(
        self,
        *,
        source_keys: list[str] | None = None,
        source_state: str = "active",
    ) -> dict[str, Any]:
        del source_state
        if not source_keys or len(source_keys) != 1:
            raise ValueError("source_key is required for serve detail reports")
        return self.detail(source_keys[0]).report

    def source_envelope(self, *, refresh: bool = False) -> dict[str, Any]:
        del refresh
        page = self.catalog.query(
            CatalogQuery(state="all", include_unreadable=True, page_size=100)
        )
        return {
            "generation": page.generation,
            "checking": page.checking,
            "stale": page.stale,
            "sources": [item.to_dict() for item in page.items],
            "total": page.total,
            "loading": not self.catalog.has_generation or self.is_loading(),
            "error": self.load_error(),
        }

    def mutate(
        self,
        change_type: str,
        source_keys: list[str],
        action: Callable[[], Any],
    ) -> dict[str, Any]:
        generation, result = self.catalog.mutate(action)
        payload: dict[str, Any] = {
            "generation": generation,
            "change": change_type,
            "source_keys": source_keys,
        }
        if result is not None:
            payload["result"] = result
        return payload

    def start_operation(
        self,
        operation_type: str,
        items: Sequence[Any],
        action: Callable[[Any], Any],
    ) -> OperationStatus:
        return self.catalog.start_operation(operation_type, items, action)

    def operation(self, operation_id: str) -> OperationStatus:
        return self.catalog.operation(operation_id)

    def workspace_report_catalog(self) -> list[dict[str, Any]]:
        return self.workspace_reports.catalog()

    def shell_report(self) -> dict[str, Any]:
        return empty_report("serve")

    def empty_envelope(
        self,
        *,
        loading: bool,
        error: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "generation": self.catalog.generation,
            "checking": loading,
            "stale": loading and self.catalog.has_generation,
            "sources": [],
            "loading": loading,
        }
        if error:
            payload["error"] = error
        return payload

    def _all_catalog_rows(self) -> list[dict[str, Any]]:
        return self.catalog.binding_rows()


__all__ = ["CatalogBusyError", "ServeRuntime"]
