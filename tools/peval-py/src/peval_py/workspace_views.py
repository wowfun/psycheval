from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from peval_py.state.catalog import CatalogQuery


VIEW_SCHEMA_VERSION = 1
VIEW_MAX_NOTE_BYTES = 1024 * 1024
VIEW_SUFFIX = ".md"
VIEW_NAME_MAX_CHARS = 120
VIEW_GROUP_BY_VALUES = frozenset({"overall", "agent", "model"})
_FRONTMATTER_RE = re.compile(
    r"\A---\r?\n(?P<header>[\s\S]*?)\r?\n---(?:\r?\n|\Z)(?P<notes>[\s\S]*)\Z"
)


class WorkspaceViewConflict(ValueError):
    pass


class WorkspaceViewNotFound(ValueError):
    pass


@dataclass(frozen=True)
class WorkspaceView:
    name: str
    filters: CatalogQuery
    group_by: str
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "filters": view_filters_dict(self.filters),
            "group_by": self.group_by,
            "notes": self.notes,
        }


class WorkspaceViewLibrary:
    """Own safe, human-editable saved Leaderboard view files."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser().resolve()
        self.views_root = self.workspace_root / "views"

    def list(self) -> list[WorkspaceView]:
        if not self._views_root_is_safe():
            return []
        views: list[WorkspaceView] = []
        for path in self.views_root.iterdir():
            if path.is_symlink() or not path.is_file() or path.suffix.lower() != VIEW_SUFFIX:
                continue
            try:
                views.append(self._read(path))
            except (OSError, UnicodeError, ValueError, yaml.YAMLError):
                continue
        return sorted(views, key=lambda view: view.name.casefold())

    def save(
        self,
        *,
        name: str,
        filters: Any,
        group_by: Any,
        notes: Any,
        overwrite: bool = False,
    ) -> WorkspaceView:
        view = view_from_values(name=name, filters=filters, group_by=group_by, notes=notes)
        self._ensure_views_root()
        target = self._path_for_name(view.name)
        if target.exists():
            if target.is_symlink() or not target.is_file():
                raise ValueError(f"saved view path is not a regular file: {view.name}")
            if not overwrite:
                raise WorkspaceViewConflict(f"saved view already exists: {view.name}")
        temp_path = self.views_root / f".{target.name}.tmp-{uuid4().hex}"
        try:
            temp_path.write_text(render_view_markdown(view), encoding="utf-8")
            temp_path.replace(target)
        finally:
            if temp_path.exists() and not temp_path.is_symlink():
                temp_path.unlink()
        return view

    def get(self, name: Any) -> WorkspaceView:
        if not self._views_root_is_safe():
            raise WorkspaceViewNotFound(f"saved view does not exist: {name}")
        path = self._path_for_name(validate_view_name(name))
        if path.is_symlink() or not path.is_file():
            raise WorkspaceViewNotFound(f"saved view does not exist: {name}")
        try:
            return self._read(path)
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise ValueError(f"saved view is not readable: {name}") from exc

    def update(self, *, name: Any, field: Any, value: Any) -> WorkspaceView:
        view = self.get(name)
        field_name = str(field or "").strip().lower()
        if field_name == "name":
            return self._rename(view, value)
        if not isinstance(value, str):
            raise ValueError(f"saved view {field_name or 'value'} must be a string")
        if field_name == "notes":
            return self.save(
                name=view.name,
                filters=view_filters_dict(view.filters),
                group_by=view.group_by,
                notes=value,
                overwrite=True,
            )
        if field_name == "configuration":
            filters, group_by = editable_view_configuration(value)
            return self.save(
                name=view.name,
                filters=filters,
                group_by=group_by,
                notes=view.notes,
                overwrite=True,
            )
        raise ValueError("saved view field must be name, configuration, or notes")

    def delete(self, names: Any) -> list[str]:
        if not isinstance(names, list) or not names:
            raise ValueError("names must include at least one saved view")
        validated = [validate_view_name(name) for name in names]
        if len(set(validated)) != len(validated):
            raise ValueError("names must not contain duplicate saved views")
        if not self._views_root_is_safe():
            raise WorkspaceViewNotFound(f"saved view does not exist: {validated[0]}")
        paths: list[Path] = []
        for name in validated:
            path = self._path_for_name(name)
            if path.is_symlink() or not path.is_file():
                raise WorkspaceViewNotFound(f"saved view does not exist: {name}")
            self._read(path)
            paths.append(path)
        for path in paths:
            path.unlink()
        return validated

    def _rename(self, view: WorkspaceView, value: Any) -> WorkspaceView:
        new_name = validate_view_name(value)
        if new_name == view.name:
            return view
        source = self._path_for_name(view.name)
        target = self._path_for_name(new_name)
        if target.exists() or target.is_symlink():
            raise WorkspaceViewConflict(f"saved view already exists: {new_name}")
        source.replace(target)
        return WorkspaceView(
            name=new_name,
            filters=view.filters,
            group_by=view.group_by,
            notes=view.notes,
        )

    def _read(self, path: Path) -> WorkspaceView:
        if path.resolve().parent != self.views_root.resolve():
            raise ValueError("saved view escapes workspace views directory")
        name = validate_view_name(path.stem)
        text = path.read_text(encoding="utf-8")
        match = _FRONTMATTER_RE.fullmatch(text)
        if match is None:
            raise ValueError(f"saved view has invalid frontmatter: {path.name}")
        payload = yaml.safe_load(match.group("header"))
        required_fields = {"schema_version", "group_by"}
        allowed_fields = required_fields | {"filters"}
        if (
            not isinstance(payload, dict)
            or not required_fields.issubset(payload)
            or not set(payload).issubset(allowed_fields)
        ):
            raise ValueError(f"saved view has invalid frontmatter fields: {path.name}")
        if payload.get("schema_version") != VIEW_SCHEMA_VERSION:
            raise ValueError(f"saved view has unsupported schema: {path.name}")
        return view_from_values(
            name=name,
            filters=payload.get("filters"),
            group_by=payload["group_by"],
            notes=match.group("notes"),
        )

    def _path_for_name(self, name: str) -> Path:
        target = self.views_root / f"{validate_view_name(name)}{VIEW_SUFFIX}"
        if target.parent != self.views_root:
            raise ValueError("saved view path escapes workspace views directory")
        return target

    def _ensure_views_root(self) -> None:
        if self.views_root.is_symlink():
            raise ValueError("workspace views directory must not be a symlink")
        if self.views_root.exists() and not self.views_root.is_dir():
            raise ValueError("workspace views path must be a directory")
        self.views_root.mkdir(parents=True, exist_ok=True)

    def _views_root_is_safe(self) -> bool:
        return (
            self.views_root.exists()
            and not self.views_root.is_symlink()
            and self.views_root.is_dir()
            and self.views_root.resolve().parent == self.workspace_root
        )


def validate_view_name(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("view name must be a string")
    name = value.strip()
    if not name:
        raise ValueError("view name is required")
    if len(name) > VIEW_NAME_MAX_CHARS:
        raise ValueError(f"view name exceeds {VIEW_NAME_MAX_CHARS} characters")
    if name in {".", ".."} or "/" in name or "\\" in name:
        raise ValueError("view name must be one filename stem")
    if any(ord(character) < 32 or ord(character) == 127 for character in name):
        raise ValueError("view name must not contain control characters")
    return name


def view_from_values(
    *, name: Any, filters: Any, group_by: Any, notes: Any
) -> WorkspaceView:
    if not isinstance(notes, str):
        raise ValueError("view notes must be a string")
    if len(notes.encode("utf-8")) > VIEW_MAX_NOTE_BYTES:
        raise ValueError(f"view notes exceed {VIEW_MAX_NOTE_BYTES} byte limit")
    group = str(group_by or "").strip().lower()
    if group not in VIEW_GROUP_BY_VALUES:
        raise ValueError("group_by must be overall, agent, or model")
    return WorkspaceView(
        name=validate_view_name(name),
        filters=view_filters_from_dict(filters),
        group_by=group,
        notes=notes,
    )


def view_filters_dict(query: CatalogQuery) -> dict[str, Any]:
    normalized = query.normalized()
    filters: dict[str, Any] = {}
    if normalized.state != "active":
        filters["state"] = normalized.state
    if normalized.search:
        filters["search"] = normalized.search
    for key, values in (
        ("tags", normalized.tags),
        ("agents", normalized.agents),
        ("models", normalized.models),
        ("results", normalized.results),
    ):
        if values:
            filters[key] = list(values)
    return filters


def view_filters_from_dict(value: Any) -> CatalogQuery:
    if value is None:
        value = {}
    allowed_fields = {"state", "search", "tags", "agents", "models", "results"}
    if not isinstance(value, dict) or not set(value).issubset(allowed_fields):
        raise ValueError("view filters contain unsupported fields")

    def values(key: str) -> tuple[str, ...]:
        raw = value.get(key, [])
        if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
            raise ValueError(f"view filters {key} must be a string array")
        return tuple(raw)

    state = value.get("state", "active")
    search = value.get("search", "")
    if not isinstance(state, str) or not isinstance(search, str):
        raise ValueError("view filters state and search must be strings")
    return CatalogQuery(
        state=state,
        page=1,
        page_size=100,
        search=search,
        sort="last_turn_end",
        direction="desc",
        tags=values("tags"),
        agents=values("agents"),
        models=values("models"),
        results=values("results"),
    ).normalized()


def editable_view_configuration(value: Any) -> tuple[dict[str, Any], str]:
    if not isinstance(value, str):
        raise ValueError("saved view configuration must be YAML text")
    payload = yaml.safe_load(value)
    required_fields = {"group_by"}
    allowed_fields = required_fields | {"filters"}
    if (
        not isinstance(payload, dict)
        or not required_fields.issubset(payload)
        or not set(payload).issubset(allowed_fields)
    ):
        raise ValueError(
            "saved view configuration must contain group_by and optional filters"
        )
    filters = payload.get("filters")
    view_filters_from_dict(filters)
    group_by = str(payload["group_by"] or "").strip().lower()
    if group_by not in VIEW_GROUP_BY_VALUES:
        raise ValueError("group_by must be overall, agent, or model")
    return filters or {}, group_by


def render_view_markdown(view: WorkspaceView) -> str:
    payload = {"schema_version": VIEW_SCHEMA_VERSION}
    filters = view_filters_dict(view.filters)
    if filters:
        payload["filters"] = filters
    payload["group_by"] = view.group_by
    header = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{header}\n---\n{view.notes}"


def render_editable_view_configuration(view: WorkspaceView) -> str:
    payload: dict[str, Any] = {}
    filters = view_filters_dict(view.filters)
    if filters:
        payload["filters"] = filters
    payload["group_by"] = view.group_by
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False).strip()
