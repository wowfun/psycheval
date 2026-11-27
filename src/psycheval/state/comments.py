"""Workspace-owned plain-text comment threads for scoring items and Trial results."""

from __future__ import annotations

import hashlib
import json
import re
import time
import tomllib
import unicodedata
import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from psycheval.file_access import blocking_file_lease
from psycheval.jobs.storage import read_bytes, safe_path, write_json
from psycheval.state.workspace_source_models import HARBOR_OVERLAY_ROOT

COMMENT_SCHEMA_VERSION = 1
COMMENT_BODY_MAX_BYTES = 8 * 1024
MAX_COMMENTS_PER_TARGET = 200
COMMENTS_FILE_MAX_BYTES = 4 * 1024 * 1024
DATASET_MANIFEST_MAX_BYTES = 256 * 1024
DATASET_KEY_MAX_LEN = 128
SCORING_COMMENTS_FILENAME = "scoring_comments.json"
SOURCE_COMMENTS_FILENAME = "review_comments.json"
SCORING_COMMENTS_LOCK = "scoring-comments.lock"
SOURCE_COMMENTS_LOCK = "source-comments.lock"
_DATASET_KEY_UNSAFE_RE = re.compile(r"[^a-z0-9._-]+")
_DATASET_KEY_DASHES_RE = re.compile(r"-{2,}")
_WINDOWS_RESERVED_NAMES = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{i}" for i in range(1, 10)}
    | {f"lpt{i}" for i in range(1, 10)}
)


class CommentConflict(ValueError):
    """The comment changed since the editor loaded it."""

    def __init__(
        self,
        message: str,
        *,
        current_revision: str | None = None,
        current_comment: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.current_revision = current_revision
        self.current_comment = current_comment


class CommentNotFound(LookupError):
    """The requested comment does not exist."""


class CommentForbidden(PermissionError):
    """The authenticated user cannot modify or delete this comment."""


def validate_comment_body(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("Comment body must be text")
    normalized = value.strip()
    if not normalized:
        raise ValueError("Comment body must not be empty")
    if len(normalized.encode("utf-8")) > COMMENT_BODY_MAX_BYTES:
        raise ValueError(
            f"Comment body must be at most {COMMENT_BODY_MAX_BYTES} UTF-8 bytes"
        )
    if any(
        ch not in {"\n", "\r", "\t"} and unicodedata.category(ch) == "Cc"
        for ch in normalized
    ):
        raise ValueError("Comment body contains invalid control characters")
    return normalized


def comment_revision(comment: dict[str, Any]) -> str:
    payload = json.dumps(
        [
            comment.get("id"),
            comment.get("updated_at_ms"),
            comment.get("body"),
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:24]


def _strip_revision(comment: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": str(comment["id"]).strip(),
        "body": str(comment["body"]),
    }
    author_id = comment.get("author_id")
    if isinstance(author_id, str) and author_id.strip():
        result["author_id"] = author_id.strip()
    updated = comment.get("updated_at_ms")
    if type(updated) is int:
        result["updated_at_ms"] = updated
    return result


def _with_revision(comment: dict[str, Any]) -> dict[str, Any]:
    normalized = _strip_revision(comment)
    normalized["revision"] = comment_revision(normalized)
    return normalized


def can_mutate_comment(
    comment: dict[str, Any], *, role: str, user_id: str | None
) -> bool:
    if role == "admin":
        return True
    if role == "annotator" and user_id and user_id.casefold() != "admin":
        return comment.get("author_id") == user_id
    return False


def format_comments_for_export(comments: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for item in comments:
        if not isinstance(item, dict):
            continue
        author = str(item.get("author_id") or "").strip()
        body = str(item.get("body") or "").strip()
        if not body:
            continue
        timestamp = item.get("updated_at_ms")
        stamp = ""
        if isinstance(timestamp, int) and not isinstance(timestamp, bool):
            stamp = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC"
            )
        prefix = (
            f"[{author} @ {stamp}]"
            if author and stamp
            else f"[{author}]"
            if author
            else f"[{stamp}]"
            if stamp
            else ""
        )
        lines.append(f"{prefix} {body}".strip())
    return "\n\n".join(lines)


def _valid_stored_comment(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    cid = value.get("id")
    body = value.get("body")
    if (
        not isinstance(cid, str)
        or not cid.strip()
        or not isinstance(body, str)
        or not body.strip()
    ):
        return None
    author_id = value.get("author_id")
    if author_id is not None and not isinstance(author_id, str):
        return None
    updated = value.get("updated_at_ms")
    if updated is not None and type(updated) is not int:
        return None
    return _with_revision(value)


def _parse_comment_list(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    result: list[dict[str, Any]] = []
    for item in raw[:MAX_COMMENTS_PER_TARGET]:
        normalized = _valid_stored_comment(item)
        if normalized is not None:
            result.append(normalized)
    return result


def _new_comment(body: str, *, author_id: str) -> dict[str, Any]:
    now_ms = int(time.time() * 1000)
    return _with_revision(
        {
            "id": f"c_{uuid.uuid4().hex[:16]}",
            "body": body,
            "author_id": author_id,
            "updated_at_ms": now_ms,
        }
    )


def _append_comment(
    comments: list[dict[str, Any]],
    body: str,
    *,
    author_id: str,
    target_label: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if len(comments) >= MAX_COMMENTS_PER_TARGET:
        raise ValueError(
            f"At most {MAX_COMMENTS_PER_TARGET} comments are allowed per {target_label}"
        )
    created = _new_comment(body, author_id=author_id)
    updated_list = [*comments, created]
    return created, updated_list


def _edit_comment(
    comments: list[dict[str, Any]],
    comment_id: str,
    body: str,
    *,
    role: str,
    user_id: str | None,
    expected_revision: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    index = next(
        (i for i, item in enumerate(comments) if item["id"] == comment_id),
        None,
    )
    if index is None:
        raise CommentNotFound("Comment not found")
    current = comments[index]
    if not can_mutate_comment(current, role=role, user_id=user_id):
        raise CommentForbidden("You can only edit your own comments")
    if current["revision"] != expected_revision:
        raise CommentConflict(
            "Comment changed elsewhere; refresh before saving",
            current_revision=current["revision"],
            current_comment=current,
        )
    prev_updated = current.get("updated_at_ms")
    now_ms = max(
        int(time.time() * 1000),
        (prev_updated + 1) if type(prev_updated) is int else 0,
    )
    updated = _with_revision({**current, "body": body, "updated_at_ms": now_ms})
    updated_list = list(comments)
    updated_list[index] = updated
    return updated, updated_list


def _remove_comment(
    comments: list[dict[str, Any]],
    comment_id: str,
    *,
    role: str,
    user_id: str | None,
    expected_revision: str,
) -> list[dict[str, Any]]:
    index = next(
        (i for i, item in enumerate(comments) if item["id"] == comment_id),
        None,
    )
    if index is None:
        raise CommentNotFound("Comment not found")
    current = comments[index]
    if not can_mutate_comment(current, role=role, user_id=user_id):
        raise CommentForbidden("You can only delete your own comments")
    if current["revision"] != expected_revision:
        raise CommentConflict(
            "Comment changed elsewhere; refresh before deleting",
            current_revision=current["revision"],
            current_comment=current,
        )
    return [item for i, item in enumerate(comments) if i != index]


def _check_file_size(payload: dict[str, Any]) -> None:
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if len(encoded) > COMMENTS_FILE_MAX_BYTES:
        raise ValueError(
            f"Comments overlay exceeds the {COMMENTS_FILE_MAX_BYTES // (1024 * 1024)} MiB limit"
        )


def attach_task_scoring_comments(
    task_summary: dict[str, Any],
    task_comments: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Return a shallow copy of task_summary with scoring-item comments merged."""
    raw_items = task_summary.get("scoring_items")
    items = raw_items if isinstance(raw_items, list) else []
    attached_items = []
    total = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "")
        comments = list(task_comments.get(key, ()))
        total += len(comments)
        attached_items.append({**item, "comments": comments})
    return {
        **task_summary,
        "scoring_items": attached_items,
        "scoring_comments": {
            key: list(value) for key, value in task_comments.items() if value
        },
        "scoring_comment_count": total,
    }


def normalize_dataset_comment_key(value: str) -> str:
    """Normalize a Dataset ID or manifest name into a cross-platform path segment."""
    if not isinstance(value, str):
        raise ValueError("Dataset comment key must be a string")
    normalized = value.strip().lower()
    normalized = _DATASET_KEY_UNSAFE_RE.sub("-", normalized)
    normalized = _DATASET_KEY_DASHES_RE.sub("-", normalized)
    normalized = normalized.strip(".-")
    if len(normalized) > DATASET_KEY_MAX_LEN:
        normalized = normalized[:DATASET_KEY_MAX_LEN].rstrip(".-")
    if not normalized or normalized in {".", ".."}:
        raise ValueError(f"Invalid dataset comment key: {value!r}")
    if normalized.split(".", 1)[0] in _WINDOWS_RESERVED_NAMES:
        normalized = f"dataset-{normalized}"
    return normalized


def _manifest_dataset_name(data: Mapping[str, Any]) -> str | None:
    dataset = data.get("dataset")
    if not isinstance(dataset, Mapping):
        return None
    for field in ("id", "name"):
        raw_value = dataset.get(field)
        if isinstance(raw_value, str) and raw_value.strip():
            return raw_value.strip()
    return None


def _read_dataset_manifest_name(
    dataset_root: Path, *, dataset_format: str | None = None
) -> str | None:
    candidates: list[tuple[Path, bool]] = [(dataset_root / "dataset.toml", False)]
    if dataset_format in {None, "workbuddy.v1"}:
        candidates.extend(
            (parent / "dataset.toml", True) for parent in dataset_root.parents
        )
    for manifest_path, require_workbuddy in candidates:
        try:
            raw = read_bytes(manifest_path, DATASET_MANIFEST_MAX_BYTES)
        except (FileNotFoundError, OSError, ValueError):
            continue
        try:
            data = tomllib.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError):
            return None
        dataset = data.get("dataset")
        if not isinstance(dataset, dict):
            if require_workbuddy:
                continue
            return None
        if require_workbuddy and dataset.get("schema") != "workbuddy.dataset.v1":
            continue
        name = _manifest_dataset_name(data)
        if name:
            return name
        if not require_workbuddy:
            return None
    return None


def resolve_dataset_comment_key(
    dataset_path: Path,
    *,
    dataset_id: str | None = None,
    dataset_format: str | None = None,
    manifest: Mapping[str, Any] | None = None,
) -> str:
    """Resolve the portable <dataset> key for .peval/datasets/<dataset>/<task>/."""
    resolved = Path(dataset_path).expanduser().resolve()
    manifest_name = _manifest_dataset_name(manifest) if manifest else None
    if manifest_name is None:
        manifest_name = _read_dataset_manifest_name(
            resolved, dataset_format=dataset_format
        )
    if manifest_name:
        try:
            return normalize_dataset_comment_key(manifest_name)
        except ValueError:
            pass
    if resolved.name:
        try:
            return normalize_dataset_comment_key(resolved.name)
        except ValueError:
            pass
    if dataset_id:
        return normalize_dataset_comment_key(dataset_id)
    raise ValueError(f"Cannot derive dataset comment key from {dataset_path}")


def _validate_task_segment(task_directory: str) -> str:
    if not isinstance(task_directory, str):
        raise ValueError("Task directory must be a string")
    name = task_directory.strip()
    if not name or name in {".", ".."} or "/" in name or "\\" in name or "\x00" in name:
        raise ValueError(f"Invalid task directory for comments: {task_directory!r}")
    return name


def _extract_scoring_items(data: Any) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    if "schema_version" in data:
        if data.get("schema_version") != COMMENT_SCHEMA_VERSION or not isinstance(
            data.get("items"), dict
        ):
            return None
        return data["items"]
    if (
        set(data) == {"items"}
        and isinstance(data["items"], dict)
        and all(isinstance(value, list) for value in data["items"].values())
    ):
        return data["items"]
    if all(isinstance(value, list) for value in data.values()):
        return data
    return None


def _store_lock_path(workspace: Path, filename: str) -> Path:
    lock_root = safe_path(workspace, ".peval", "locks")
    lock_root.mkdir(parents=True, exist_ok=True)
    return safe_path(lock_root, filename)


class ScoringCommentStore:
    """Per-Task comment store at .peval/datasets/<dataset>/<task>/scoring_comments.json."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.expanduser().resolve()

    def _datasets_root(self) -> Path:
        return safe_path(self.workspace, ".peval", "datasets")

    def _dataset_dir(self, dataset_key: str) -> Path:
        normalized = normalize_dataset_comment_key(dataset_key)
        return safe_path(self._datasets_root(), normalized)

    def _task_file_path(self, dataset_key: str, task_directory: str) -> Path:
        task_segment = _validate_task_segment(task_directory)
        return safe_path(
            self._dataset_dir(dataset_key),
            task_segment,
            SCORING_COMMENTS_FILENAME,
        )

    def _lock_path(self) -> Path:
        return _store_lock_path(self.workspace, SCORING_COMMENTS_LOCK)

    def lease(self, label: str = "Scoring comment update"):
        return blocking_file_lease(self._lock_path(), label=label)

    def _remove_empty_dataset_dirs(self, leaf: Path) -> None:
        peval_root = safe_path(self.workspace, ".peval")
        current = leaf
        while current != peval_root and peval_root in current.parents:
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent

    def _read_target(
        self, target: Path, *, strict: bool = False
    ) -> dict[str, list[dict[str, Any]]]:
        try:
            raw = read_bytes(target, COMMENTS_FILE_MAX_BYTES)
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as exc:
            if strict:
                raise ValueError(f"Invalid scoring comments overlay: {exc}") from exc
            return {}
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            if strict:
                raise ValueError("Scoring comments overlay is not valid JSON") from exc
            return {}
        raw_items = _extract_scoring_items(data)
        if raw_items is None:
            if strict:
                raise ValueError("Invalid scoring comments overlay structure")
            return {}
        result: dict[str, list[dict[str, Any]]] = {}
        for item_key, raw_comments in raw_items.items():
            if not isinstance(item_key, str):
                continue
            parsed = _parse_comment_list(raw_comments)
            if parsed:
                result[item_key] = parsed
        return result

    def _read_task_raw(
        self, dataset_key: str, task_directory: str, *, strict: bool = False
    ) -> dict[str, list[dict[str, Any]]]:
        return self._read_target(
            self._task_file_path(dataset_key, task_directory), strict=strict
        )

    def _write_target(
        self,
        target: Path,
        items: dict[str, list[dict[str, Any]]],
    ) -> None:
        cleaned = {
            item_key: [_strip_revision(comment) for comment in comments]
            for item_key, comments in items.items()
            if comments
        }
        if not cleaned:
            target.unlink(missing_ok=True)
            self._remove_empty_dataset_dirs(target.parent)
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": COMMENT_SCHEMA_VERSION, "items": cleaned}
        _check_file_size(payload)
        write_json(target, payload)

    def read_dataset(
        self, dataset_key: str
    ) -> dict[str, dict[str, list[dict[str, Any]]]]:
        dataset_dir = self._dataset_dir(dataset_key)
        try:
            entries = sorted(dataset_dir.iterdir(), key=lambda item: item.name)
        except (FileNotFoundError, OSError):
            return {}
        result: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for entry in entries:
            if entry.is_symlink() or not entry.is_dir():
                continue
            try:
                task_file = safe_path(entry, SCORING_COMMENTS_FILENAME)
                task_comments = self._read_target(task_file, strict=False)
            except ValueError:
                continue
            if task_comments:
                result[entry.name] = task_comments
        return result

    def read_task(
        self, dataset_key: str, task_directory: str
    ) -> dict[str, list[dict[str, Any]]]:
        return self._read_task_raw(dataset_key, task_directory, strict=False)

    def move_task_comments_locked(
        self, dataset_key: str, old_task: str, new_task: str
    ) -> None:
        old_name = _validate_task_segment(old_task)
        new_name = _validate_task_segment(new_task)
        if old_name == new_name:
            return
        old_file = self._task_file_path(dataset_key, old_name)
        if not old_file.exists():
            return
        new_file = self._task_file_path(dataset_key, new_name)
        old_items = self._read_target(old_file, strict=False)
        if not old_items:
            old_file.unlink(missing_ok=True)
            self._remove_empty_dataset_dirs(old_file.parent)
            return
        merged = self._read_target(new_file, strict=False)
        for item_key, comments in old_items.items():
            existing = merged.setdefault(item_key, [])
            seen_ids = {item["id"] for item in existing}
            for comment in comments:
                if comment["id"] not in seen_ids:
                    existing.append(comment)
                    seen_ids.add(comment["id"])
        self._write_target(new_file, merged)
        old_file.unlink(missing_ok=True)
        self._remove_empty_dataset_dirs(old_file.parent)

    def move_task_comments(
        self, dataset_key: str, old_task: str, new_task: str
    ) -> None:
        old_name = _validate_task_segment(old_task)
        new_name = _validate_task_segment(new_task)
        if old_name == new_name:
            return
        with self.lease("Scoring comment move"):
            self.move_task_comments_locked(dataset_key, old_name, new_name)

    def delete_task_comments(self, dataset_key: str, task_directory: str) -> None:
        target = self._task_file_path(dataset_key, task_directory)
        with self.lease("Scoring comment delete"):
            if not target.exists():
                return
            target.unlink(missing_ok=True)
            self._remove_empty_dataset_dirs(target.parent)

    def add_comment(
        self,
        dataset_key: str,
        task_directory: str,
        item_key: str,
        body: str,
        *,
        author_id: str,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        validated = validate_comment_body(body)
        target = self._task_file_path(dataset_key, task_directory)
        with self.lease("Scoring comment update"):
            item_map = self._read_target(target, strict=True)
            created, updated_list = _append_comment(
                item_map.get(item_key, []),
                validated,
                author_id=author_id,
                target_label="scoring item",
            )
            item_map[item_key] = updated_list
            self._write_target(target, item_map)
            return created, list(updated_list)

    def update_comment(
        self,
        dataset_key: str,
        task_directory: str,
        item_key: str,
        comment_id: str,
        body: str,
        *,
        role: str,
        user_id: str | None,
        expected_revision: str,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        validated = validate_comment_body(body)
        target = self._task_file_path(dataset_key, task_directory)
        with self.lease("Scoring comment update"):
            item_map = self._read_target(target, strict=True)
            updated, updated_list = _edit_comment(
                item_map.get(item_key, []),
                comment_id,
                validated,
                role=role,
                user_id=user_id,
                expected_revision=expected_revision,
            )
            item_map[item_key] = updated_list
            self._write_target(target, item_map)
            return updated, list(updated_list)

    def delete_comment(
        self,
        dataset_key: str,
        task_directory: str,
        item_key: str,
        comment_id: str,
        *,
        role: str,
        user_id: str | None,
        expected_revision: str,
    ) -> list[dict[str, Any]]:
        target = self._task_file_path(dataset_key, task_directory)
        with self.lease("Scoring comment update"):
            item_map = self._read_target(target, strict=True)
            remaining = _remove_comment(
                item_map.get(item_key, []),
                comment_id,
                role=role,
                user_id=user_id,
                expected_revision=expected_revision,
            )
            item_map[item_key] = remaining
            self._write_target(target, item_map)
            return remaining


def _resolve_source_overlay_dir(workspace: Path, source_ref: str) -> Path:
    text = str(source_ref or "")
    if not text or "\\" in text:
        raise ValueError(f"Invalid source reference: {source_ref}")
    parts = Path(text).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"Invalid source reference: {source_ref}")
    if parts[0] == HARBOR_OVERLAY_ROOT:
        if len(parts) not in {4, 6} or (len(parts) == 6 and parts[4] != "steps"):
            raise ValueError(f"Invalid Harbor source reference: {source_ref}")
        return safe_path(workspace, *parts)
    if parts[0] == "runs" and len(parts) == 5:
        return safe_path(workspace, *parts)
    raise ValueError(f"Unsupported source reference for comments: {source_ref}")


class SourceCommentStore:
    """Per-source overlay comment store for Trial scoring-result comments."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.expanduser().resolve()

    def _file_path(self, source_ref: str) -> Path:
        return safe_path(
            _resolve_source_overlay_dir(self.workspace, source_ref),
            SOURCE_COMMENTS_FILENAME,
        )

    def _lock_path(self) -> Path:
        return _store_lock_path(self.workspace, SOURCE_COMMENTS_LOCK)

    def _remove_empty_harbor_dirs(self, leaf: Path) -> None:
        harbor_root = self.workspace / HARBOR_OVERLAY_ROOT
        current = leaf
        while current != harbor_root and harbor_root in current.parents:
            try:
                current.rmdir()
            except OSError:
                return
            current = current.parent
        if current == harbor_root:
            try:
                harbor_root.rmdir()
            except OSError:
                pass

    def _read_target(
        self, target: Path, *, strict: bool = False
    ) -> list[dict[str, Any]]:
        try:
            raw = read_bytes(target, COMMENTS_FILE_MAX_BYTES)
        except FileNotFoundError:
            return []
        except (OSError, ValueError) as exc:
            if strict:
                raise ValueError(f"Invalid review comments overlay: {exc}") from exc
            return []
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            if strict:
                raise ValueError("Review comments overlay is not valid JSON") from exc
            return []
        if isinstance(data, list):
            raw_comments = data
        elif (
            isinstance(data, dict)
            and (
                "schema_version" not in data
                or data.get("schema_version") == COMMENT_SCHEMA_VERSION
            )
            and isinstance(data.get("comments"), list)
        ):
            raw_comments = data["comments"]
        else:
            if strict:
                raise ValueError("Invalid review comments overlay structure")
            return []
        return _parse_comment_list(raw_comments)

    def read_comments(
        self, source_ref: str, *, strict: bool = False
    ) -> list[dict[str, Any]]:
        try:
            target = self._file_path(source_ref)
        except ValueError:
            if strict:
                raise
            return []
        return self._read_target(target, strict=strict)

    def _write_target(
        self, source_ref: str, target: Path, comments: list[dict[str, Any]]
    ) -> None:
        if not comments:
            target.unlink(missing_ok=True)
            if str(source_ref).startswith(f"{HARBOR_OVERLAY_ROOT}/"):
                self._remove_empty_harbor_dirs(target.parent)
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": COMMENT_SCHEMA_VERSION,
            "comments": [_strip_revision(comment) for comment in comments],
        }
        _check_file_size(payload)
        write_json(target, payload)

    def add_comment(
        self,
        source_ref: str,
        body: str,
        *,
        author_id: str,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        validated = validate_comment_body(body)
        target = self._file_path(source_ref)
        with blocking_file_lease(self._lock_path(), label="Review comment update"):
            comments = self._read_target(target, strict=True)
            created, updated_list = _append_comment(
                comments,
                validated,
                author_id=author_id,
                target_label="Trial",
            )
            self._write_target(source_ref, target, updated_list)
            return created, list(updated_list)

    def update_comment(
        self,
        source_ref: str,
        comment_id: str,
        body: str,
        *,
        role: str,
        user_id: str | None,
        expected_revision: str,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        validated = validate_comment_body(body)
        target = self._file_path(source_ref)
        with blocking_file_lease(self._lock_path(), label="Review comment update"):
            comments = self._read_target(target, strict=True)
            updated, updated_list = _edit_comment(
                comments,
                comment_id,
                validated,
                role=role,
                user_id=user_id,
                expected_revision=expected_revision,
            )
            self._write_target(source_ref, target, updated_list)
            return updated, list(updated_list)

    def delete_comment(
        self,
        source_ref: str,
        comment_id: str,
        *,
        role: str,
        user_id: str | None,
        expected_revision: str,
    ) -> list[dict[str, Any]]:
        target = self._file_path(source_ref)
        with blocking_file_lease(self._lock_path(), label="Review comment update"):
            comments = self._read_target(target, strict=True)
            remaining = _remove_comment(
                comments,
                comment_id,
                role=role,
                user_id=user_id,
                expected_revision=expected_revision,
            )
            self._write_target(source_ref, target, remaining)
            return remaining


def read_source_comments(workspace: Path, source_ref: str) -> list[dict[str, Any]]:
    return SourceCommentStore(workspace).read_comments(source_ref, strict=False)
