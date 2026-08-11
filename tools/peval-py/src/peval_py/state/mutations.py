from __future__ import annotations

from typing import Any

from peval_py._state.artifacts import remove_artifact_dir
from peval_py.analysis import write_note_file
from peval_py.config import ToolConfig
from peval_py.state.summaries import now_ms, trial_summary
from peval_py.state.workspace_sources import WorkspaceSources, is_harbor_source


class StateMutationMixin:
    def upsert_source_row(
        self,
        source_key: str,
        source: dict[str, Any],
        artifact_dir: str,
        timestamp: int,
        *,
        trajectory: dict[str, Any] | None = None,
        meta: dict[str, Any] | None = None,
        refreshable: bool,
        snapshot: bool,
        status: str,
        error: str | None = None,
    ) -> None:
        cell_dir = self.resolve_artifact_dir(artifact_dir)
        existing = self.read_source_state(cell_dir)
        summary = trial_summary(trajectory, meta)
        source_alias = source.get("source_alias")
        if source_alias is None:
            source_alias = existing.get("source_alias")
        source_category = source.get("source_category")
        if source_category is None:
            source_category = existing.get("source_category")
        source_tags = source.get("source_tags")
        if source_tags is None:
            source_tags = existing.get("source_tags")
        state = {
            "source_key": source_key,
            "kind": source["kind"],
            "adapter": source["adapter"],
            "label": source["label"],
            "input_path": source.get("input_path"),
            "db_path": source.get("db_path"),
            "session_id": source.get("session_id"),
            "source_alias": source_alias,
            "source_category": self.source_category_from_state(
                {"source_category": source_category}
            ),
            "source_tags": self.source_tags_from_state({"source_tags": source_tags}),
            "agent_name": source.get("agent_name"),
            "agent_version": source.get("agent_version"),
            "model": source.get("model"),
            "artifact_dir": artifact_dir,
            "artifact_updated_at_ms": timestamp,
            "trial_key": summary["trial_key"],
            "trial_session_id": summary["trial_session_id"],
            "last_turn_finished_at_ms": summary["last_turn_finished_at_ms"],
            "refreshable": bool(refreshable),
            "active": bool(existing.get("active", True)),
            "snapshot": bool(snapshot),
            "created_at_ms": int(existing.get("created_at_ms") or timestamp),
            "updated_at_ms": timestamp,
            "last_status": status,
            "last_error": error,
            "last_refreshed_at_ms": (
                timestamp if refreshable else existing.get("last_refreshed_at_ms")
            ),
        }
        self.write_source_state(cell_dir, state)

    def set_source_active(self, source_key: str, active: bool) -> None:
        self.set_source_active_row(self.source_by_key(source_key), active)

    def set_source_active_row(self, row: dict[str, Any], active: bool) -> None:
        if is_harbor_source(row):
            state = self._harbor_overlay(row)
            state["active"] = bool(active)
            self._write_harbor_overlay(row, state)
            return
        cell_dir = self.resolve_artifact_dir(str(row["artifact_dir"]))
        state = {**row, **self.read_source_state(cell_dir)}
        state["active"] = bool(active)
        state["updated_at_ms"] = now_ms()
        self.write_source_state(cell_dir, state)

    def set_source_alias(self, source_key: str, alias: str | None) -> None:
        self.set_source_alias_row(self.source_by_key(source_key), alias)

    def set_source_alias_row(self, row: dict[str, Any], alias: str | None) -> None:
        if is_harbor_source(row):
            state = self._harbor_overlay(row)
            state["source_alias"] = alias or None
            self._write_harbor_overlay(row, state)
            return
        cell_dir = self.resolve_artifact_dir(str(row["artifact_dir"]))
        state = {**row, **self.read_source_state(cell_dir)}
        state["source_alias"] = alias or None
        state["updated_at_ms"] = now_ms()
        self.write_source_state(cell_dir, state)

    def set_source_tags(self, source_key: str, tags: list[str]) -> None:
        self.set_source_tags_row(self.source_by_key(source_key), tags)

    def set_source_category(self, source_key: str, category: str | None) -> None:
        self.set_source_category_row(self.source_by_key(source_key), category)

    def set_source_category_row(
        self,
        row: dict[str, Any],
        category: str | None,
    ) -> None:
        if is_harbor_source(row):
            state = self._harbor_overlay(row)
            state["source_category"] = self.source_category_from_state(
                {"source_category": category}
            )
            self._write_harbor_overlay(row, state)
            return
        cell_dir = self.resolve_artifact_dir(str(row["artifact_dir"]))
        state = {**row, **self.read_source_state(cell_dir)}
        state["source_category"] = self.source_category_from_state(
            {"source_category": category}
        )
        state["updated_at_ms"] = now_ms()
        self.write_source_state(cell_dir, state)

    def set_source_tags_row(self, row: dict[str, Any], tags: list[str]) -> None:
        if is_harbor_source(row):
            state = self._harbor_overlay(row)
            state["source_tags"] = self.source_tags_from_state({"source_tags": tags})
            self._write_harbor_overlay(row, state)
            return
        cell_dir = self.resolve_artifact_dir(str(row["artifact_dir"]))
        state = {**row, **self.read_source_state(cell_dir)}
        state["source_tags"] = self.source_tags_from_state({"source_tags": tags})
        state["updated_at_ms"] = now_ms()
        self.write_source_state(cell_dir, state)

    def delete_source(self, source_key: str) -> None:
        self.delete_source_row(self.source_by_key(source_key))

    def delete_source_row(self, row: dict[str, Any]) -> None:
        if is_harbor_source(row):
            raise ValueError(
                "linked Harbor Trials cannot be deleted; archive the source instead"
            )
        artifact_dir = row.get("artifact_dir")
        if artifact_dir:
            remove_artifact_dir(
                self.paths.root,
                self.resolve_artifact_dir(str(artifact_dir)),
            )

    def save_source_notes(
        self,
        source_key: str,
        markdown: str,
        config: ToolConfig,
    ) -> None:
        self.save_source_notes_row(self.source_by_key(source_key), markdown, config)

    def save_source_notes_row(
        self,
        source: dict[str, Any],
        markdown: str,
        config: ToolConfig,
    ) -> None:
        if not source.get("refreshable") or source.get("snapshot"):
            raise ValueError("notes.md can only be saved for refreshable sources")
        if is_harbor_source(source):
            sources = WorkspaceSources(self, config)
            note_path = sources.annotation_path(str(source["source_ref"]), "notes.md")
            if not markdown:
                sources.remove_annotation(str(source["source_ref"]), "notes.md")
                self.refresh_source(source, config)
                return
        elif source.get("artifact_dir"):
            note_path = (
                self.resolve_artifact_dir(str(source["artifact_dir"])) / "notes.md"
            )
        else:
            raise ValueError("notes.md requires a persisted source")
        write_note_file(
            note_path,
            self.paths.root,
            markdown,
        )
        self.refresh_source(source, config)

    def _harbor_overlay(self, row: dict[str, Any]) -> dict[str, Any]:
        return WorkspaceSources(self, ToolConfig()).read_overlay(str(row["source_ref"]))

    def _write_harbor_overlay(self, row: dict[str, Any], state: dict[str, Any]) -> None:
        WorkspaceSources(self, ToolConfig()).write_overlay(
            str(row["source_ref"]), state
        )
