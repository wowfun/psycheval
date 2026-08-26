from __future__ import annotations

import hashlib
from threading import Event, Lock, Thread
from typing import Any, Callable, Sequence

from psycheval.config import ToolConfig
from psycheval.inputs import AdapterAssignments
from psycheval.serve.acp import AcpManager
from psycheval.serve.prompt_assets import PromptAssetLibrary
from psycheval.serve.sources import load_serve_inputs
from psycheval.serve.summary_xlsx import SummaryWorksheet
from psycheval.state import (
    CatalogBusyError,
    CatalogPage,
    CatalogQuery,
    DetailEnvelope,
    OperationStatus,
    ServeStateStore,
    WorkspaceCatalog,
)
from psycheval.state.workspace_sources import WorkspaceSources
from psycheval.workspace_reports import WorkspaceReportLibrary
from psycheval.workspace_views import (
    WorkspaceView,
    WorkspaceViewConflict,
    WorkspaceViewLibrary,
    browser_views_from_payload,
    render_editable_view_configuration,
)


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
        self.workspace_id = hashlib.sha256(
            str(store.paths.root.resolve()).encode("utf-8")
        ).hexdigest()[:20]
        self.acp = AcpManager(config.acp_agents, store.paths.root)
        self.prompt_assets = PromptAssetLibrary(store.paths.root)
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
        args: Any,
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
        args: Any,
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
            self.acp.reconfigure(config.acp_agents)
            self.config = config
            self.catalog.config = config
            self.catalog.sources = WorkspaceSources(self.store, config)

    def config_with_acp_status(self) -> tuple[ToolConfig, dict[str, Any]]:
        with self._lock:
            return self.config, self.acp.agents()

    def close(self) -> None:
        self.acp.close()

    def catalog_page(
        self,
        query: CatalogQuery,
        *,
        view_names: Sequence[str] = (),
        browser_views: Sequence[WorkspaceView] = (),
    ) -> CatalogPage:
        bound_refs = self.workspace_reports.bound_source_refs()
        return self.catalog.query(
            query,
            any_queries=self.workspace_view_queries(view_names, browser_views),
            workspace_report_source_refs=tuple(bound_refs),
        )

    def workspace_view_queries(
        self,
        names: Sequence[str],
        browser_views: Sequence[WorkspaceView] = (),
    ) -> list[CatalogQuery]:
        ordered = list(dict.fromkeys(str(name) for name in names if str(name)))
        return [self.workspace_views.get(name).filters for name in ordered] + [
            view.filters for view in browser_views
        ]

    def validated_browser_views(self, value: Any) -> list[WorkspaceView]:
        views = (
            list(value)
            if isinstance(value, (list, tuple))
            and all(isinstance(item, WorkspaceView) for item in value)
            else browser_views_from_payload(value)
        )
        self.ensure_browser_view_names_available(views)
        return views

    def ensure_browser_view_names_available(
        self, views: Sequence[WorkspaceView]
    ) -> None:
        server_names = {view.name for view in self.workspace_views.list()}
        conflict = next(
            (view.name for view in views if view.name in server_names), None
        )
        if conflict is not None:
            raise WorkspaceViewConflict(
                f"workspace saved view already exists: {conflict}"
            )

    def browser_view_summaries(self, views: Sequence[WorkspaceView]) -> dict[str, Any]:
        payload = self.catalog.summarize_saved_views(
            [(view.name, view.filters, view.group_by) for view in views]
        )
        summaries = {item["name"]: item for item in payload["views"]}
        return {
            **payload,
            "views": [
                {**view.to_dict(), **summaries.get(view.name, {})} for view in views
            ],
        }

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
                {**view.to_dict(), **summaries.get(view.name, {})} for view in views
            ],
        }

    def leaderboard_summary_worksheet(
        self,
        source_keys: Sequence[str],
        *,
        query: CatalogQuery,
        view_names: Sequence[str] = (),
        browser_views: Sequence[WorkspaceView] = (),
        group_by: str,
        statistic: str,
    ) -> SummaryWorksheet:
        payload = self.catalog.summarize_source_keys(
            source_keys,
            name="Leaderboard Summary",
            group_by=group_by,
            inference_query=query,
            inference_any_queries=self.workspace_view_queries(
                view_names, browser_views
            ),
        )
        summary = payload["summary"]
        return SummaryWorksheet(
            name="Leaderboard Summary",
            group_by=group_by,
            matched_count=int(summary["matched_count"]),
            groups=summary["groups"],
            statistic=statistic,
            inference_summary=payload["inference_summary"],
            metadata=(
                ("Scope", "Current visible Leaderboard page"),
                ("Group", group_by),
                ("Match count", int(summary["matched_count"])),
                ("Chart statistic", statistic),
            ),
        )

    def workspace_view_summary_worksheets(
        self,
        names: Sequence[str],
        browser_views: Sequence[WorkspaceView] = (),
    ) -> list[SummaryWorksheet]:
        views = [self.workspace_views.get(name) for name in names] + list(browser_views)
        payload = self.catalog.summarize_saved_views(
            [(view.name, view.filters, view.group_by) for view in views]
        )
        return [
            SummaryWorksheet(
                name=view.name,
                group_by=view.group_by,
                matched_count=int(summary["matched_count"]),
                groups=summary["groups"],
                statistic="mean",
                metadata=(
                    ("Name", view.name),
                    ("Configuration", render_editable_view_configuration(view)),
                    ("Notes", view.notes),
                    ("Group", view.group_by),
                    ("Match count", int(summary["matched_count"])),
                    ("Chart statistic", "mean"),
                ),
            )
            for view, summary in zip(views, payload["views"])
        ]

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

    def mutate_with_background_reconcile(
        self,
        change_type: str,
        action: Callable[[], Any],
    ) -> dict[str, Any]:
        result, operation = self.catalog.mutate_with_background_reconcile(
            change_type,
            action,
        )
        return {
            "change": change_type,
            "result": result,
            "operation": operation.to_dict(),
        }

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
