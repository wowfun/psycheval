from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

from psycheval.config import load_config
from psycheval.state import ServeStateStore, workspace_paths
from psycheval.state.catalog import WorkspaceCatalog
from psycheval.state.workspace_harbor import (
    HARBOR_ANALYSIS_MAX_BYTES,
    _assert_safe_descendant,
    _fingerprint,
    _harbor_candidate_source_files,
    _read_bytes_no_follow,
)
from psycheval.state.workspace_source_models import HARBOR_ANALYSIS_MD_FILE
from psycheval.state.workspace_sources import (
    SourceCandidate,
    SourceDocument,
    WorkspaceSources,
)

SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_TASK_SKILL_FILE_BYTES = 2 * 1024 * 1024
MAX_TASK_SKILL_BYTES = 20 * 1024 * 1024
MAX_TASK_SKILL_FILES = 1_000
TRIAL_ANALYSIS_PREAMBLE = "<!-- peval:trial-analysis:v1 -->"
TRIAL_ANALYSIS_LOCK_FILE = ".peval-analysis.lock"
_TRIAL_ANALYSIS_THREAD_LOCK = threading.Lock()


@dataclass(frozen=True)
class TrialAnalysisTarget:
    requested_ref: str
    trial_ref: str
    phase_refs: tuple[str, ...]
    trial_dir: Path
    candidates: tuple[SourceCandidate, ...]
    evidence_revision: str


@dataclass(frozen=True)
class AnalysisState:
    present: bool
    revision: str | None
    content: str | None

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "present": self.present,
            "revision": self.revision,
        }


@dataclass(frozen=True)
class TaskSkillSnapshot:
    target: TrialAnalysisTarget
    name: str
    revision: str
    files: tuple[str, ...]
    selected_file: str
    content: str
    task: dict[str, Any]
    analysis: AnalysisState

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "trial_ref": self.target.trial_ref,
            "phase_refs": list(self.target.phase_refs),
            "evidence_revision": self.target.evidence_revision,
            "analysis": self.analysis.to_jsonable(),
            "task": self.task,
            "skill": {
                "name": self.name,
                "revision": self.revision,
                "files": list(self.files),
                "selected_file": self.selected_file,
                "content": self.content,
            },
        }


class TrialAnalysisReconcileError(RuntimeError):
    def __init__(self, receipt: dict[str, Any], error: Exception) -> None:
        self.receipt = {
            **receipt,
            "catalog_reconciled": False,
            "catalog_error": str(error),
        }
        super().__init__(
            f"Trial analysis was committed but catalog reconciliation failed: {error}"
        )


class TrialAnalysisService:
    """Resolve Trial criteria and publish one revision-bound parent report."""

    def __init__(self, workspace_root: str | Path) -> None:
        root = Path(workspace_root).expanduser().resolve()
        config_path = root / "peval.toml"
        if not config_path.is_file():
            raise ValueError(
                f"{root} is not an initialized peval workspace; "
                f"run `peval init -r {root}`"
            )
        self.root = root
        self.store = ServeStateStore(workspace_paths(root), initialize=False)
        self.config = load_config(workspace_root=str(root))
        self.sources = WorkspaceSources(self.store, self.config)

    def close(self) -> None:
        self.store.close()

    def resolve(self, source_ref: str) -> TrialAnalysisTarget:
        requested = str(source_ref or "").strip()
        parts = Path(requested).parts
        if (
            len(parts) not in {4, 6}
            or parts[0] != "harbor"
            or (len(parts) == 6 and parts[4] != "steps")
        ):
            raise ValueError(f"invalid Harbor source reference: {requested}")
        trial_ref = "/".join(parts[:4])
        selected = tuple(self.sources.harbor_candidates_for_ref(requested))
        if not selected:
            raise ValueError(f"unknown source reference: {requested}")
        for candidate in selected:
            if candidate.diagnostic is not None:
                raise ValueError(candidate.diagnostic)
            if candidate.harbor_evidence is None:
                raise ValueError(f"Harbor evidence is unavailable: {trial_ref}")
        all_candidates = tuple(self.sources.harbor_candidates_for_ref(trial_ref))
        trial_dir = all_candidates[0].path
        if any(candidate.path != trial_dir for candidate in all_candidates):
            raise ValueError(f"Harbor phases do not share one Trial root: {trial_ref}")
        phase_refs = tuple(candidate.source_ref for candidate in all_candidates)
        evidence_revision = self._evidence_revision(all_candidates)
        return TrialAnalysisTarget(
            requested_ref=requested,
            trial_ref=trial_ref,
            phase_refs=phase_refs,
            trial_dir=trial_dir,
            candidates=selected,
            evidence_revision=evidence_revision,
        )

    def documents(self, source_refs: Iterable[str]) -> list[SourceDocument]:
        documents: list[SourceDocument] = []
        for source_ref in source_refs:
            target = self.resolve(source_ref)
            documents.extend(
                self.sources.load(candidate) for candidate in target.candidates
            )
        return documents

    def task_skill(
        self,
        source_ref: str,
        name: str,
        *,
        relative_file: str | None = None,
    ) -> TaskSkillSnapshot:
        target = self.resolve(source_ref)
        return self._task_skill_for_target(target, name, relative_file=relative_file)

    def publish(
        self,
        *,
        source_ref: str,
        skill_name: str,
        expected_evidence_revision: str,
        expected_skill_revision: str,
        draft_path: str | Path,
        replace_revision: str | None = None,
    ) -> dict[str, Any]:
        draft = _read_text_file(
            Path(draft_path).expanduser(),
            label="Trial analysis draft",
            max_bytes=HARBOR_ANALYSIS_MAX_BYTES,
            require_nonempty=True,
        )
        catalog = WorkspaceCatalog(self.store, self.config)
        committed: dict[str, Any] = {}

        def publish_locked() -> dict[str, Any]:
            target = self.resolve(source_ref)
            snapshot = self._task_skill_for_target(target, skill_name)
            if target.evidence_revision != expected_evidence_revision:
                raise ValueError(
                    "Harbor Trial evidence changed; re-read the Trial and review the draft"
                )
            if snapshot.revision != expected_skill_revision:
                raise ValueError(
                    "Task skill changed; re-read the criterion and review the draft"
                )
            result = target.candidates[0].harbor_evidence.trial_values.get(
                "result.json"
            )
            if not isinstance(result, dict) or not result.get("finished_at"):
                raise ValueError(
                    "Trial analysis can only be published after the Trial finishes"
                )

            current = snapshot.analysis
            if current.present:
                if replace_revision is None:
                    raise ValueError(
                        "Trial analysis already exists; pass its current revision with "
                        "--replace-revision after explicit review"
                    )
                if current.revision != replace_revision:
                    raise ValueError(
                        "Trial analysis changed; re-read it before approving replacement"
                    )
            elif replace_revision is not None:
                raise ValueError(
                    "--replace-revision was provided but no Trial analysis exists"
                )

            content = _published_markdown(snapshot, draft)
            report_path = target.trial_dir / HARBOR_ANALYSIS_MD_FILE
            _atomic_replace_text(target.trial_dir, report_path, content)
            analysis_revision = hashlib.sha256(content.encode("utf-8")).hexdigest()
            committed.update(
                {
                    "trial_ref": target.trial_ref,
                    "report_path": HARBOR_ANALYSIS_MD_FILE,
                    "evidence_revision": target.evidence_revision,
                    "skill_revision": snapshot.revision,
                    "analysis_revision": analysis_revision,
                    "replaced": current.present,
                    "catalog_reconciled": True,
                }
            )
            return dict(committed)

        def action() -> dict[str, Any]:
            target = self.resolve(source_ref)
            with _trial_analysis_lease(target.trial_dir):
                return publish_locked()

        try:
            generation, receipt = catalog.mutate(action)
        except Exception as exc:
            if committed:
                raise TrialAnalysisReconcileError(committed, exc) from exc
            raise
        finally:
            catalog.close()
        return {**receipt, "catalog_generation": generation}

    def _task_skill_for_target(
        self,
        target: TrialAnalysisTarget,
        name: str,
        *,
        relative_file: str | None = None,
    ) -> TaskSkillSnapshot:
        normalized_name = str(name or "").strip()
        if SKILL_NAME_RE.fullmatch(normalized_name) is None:
            raise ValueError("Task skill name must be lowercase kebab-case")
        evidence = target.candidates[0].harbor_evidence
        assert evidence is not None
        task = dict(evidence.task_metadata)
        status = str(task.get("status") or "")
        if status not in {"resolved", "digest_mismatch"}:
            diagnostic = task.get("diagnostic")
            raise ValueError(
                f"live Harbor Task is {status or 'unavailable'}"
                + (f": {diagnostic}" if diagnostic else "")
            )
        task_path = Path(str(task.get("path") or ""))
        if not task_path.is_absolute():
            raise ValueError("resolved Harbor Task path is not absolute")
        skill_dir = task_path / "environment" / "skills" / normalized_name
        _assert_safe_descendant(task_path, skill_dir, label="Task skill")
        if skill_dir.is_symlink() or not skill_dir.is_dir():
            raise ValueError(f"Task skill not found: {normalized_name}")
        values = _skill_files(skill_dir)
        if "SKILL.md" not in values:
            raise ValueError(f"Task skill is missing SKILL.md: {normalized_name}")
        selected_file = _safe_skill_relative_path(relative_file or "SKILL.md")
        if selected_file not in values:
            raise ValueError(f"Task skill file not found: {selected_file}")
        try:
            content = values[selected_file].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Task skill file must be UTF-8: {selected_file}") from exc
        revision = _bytes_revision(values)
        task_payload = {
            key: value
            for key, value in {
                "name": task.get("name"),
                "version": task.get("version"),
                "status": status,
                "recorded_digest": evidence.provenance.get("task_digest"),
                "recorded_digest_source": evidence.provenance.get("task_digest_source"),
                "live_digest": task.get("live_digest"),
                "digest_matches": task.get("digest_matches"),
                "digest_comparison": task.get("digest_comparison"),
            }.items()
            if value is not None
        }
        return TaskSkillSnapshot(
            target=target,
            name=normalized_name,
            revision=revision,
            files=tuple(values),
            selected_file=selected_file,
            content=content,
            task=task_payload,
            analysis=_analysis_state(target.trial_dir),
        )

    @staticmethod
    def _evidence_revision(candidates: tuple[SourceCandidate, ...]) -> str:
        evidence = candidates[0].harbor_evidence
        assert evidence is not None
        relative_files: set[str] = set()
        for candidate in candidates:
            relative_files.update(_harbor_candidate_source_files(candidate))
        file_revision = _fingerprint(candidates[0].path, sorted(relative_files))
        digest = hashlib.sha256()
        for value in (evidence.source_revision, file_revision):
            digest.update(value.encode("utf-8") + b"\0")
        return digest.hexdigest()


def _skill_files(skill_dir: Path) -> dict[str, bytes]:
    values: dict[str, bytes] = {}
    file_count = 0
    total = 0

    def fail_unreadable(error: OSError) -> None:
        path = error.filename or skill_dir
        raise ValueError(f"Task skill is unreadable: {path}") from error

    for root, directory_names, filenames in os.walk(
        skill_dir,
        followlinks=False,
        onerror=fail_unreadable,
    ):
        directory = Path(root)
        directory_names.sort()
        filenames.sort()
        for name in directory_names:
            path = directory / name
            if path.is_symlink():
                raise ValueError(f"Task skill must not contain symlinks: {path}")
        directory_names[:] = [name for name in directory_names if name != "__pycache__"]
        for name in filenames:
            path = directory / name
            relative = path.relative_to(skill_dir).as_posix()
            file_count += 1
            if file_count > MAX_TASK_SKILL_FILES:
                raise ValueError(f"Task skill exceeds {MAX_TASK_SKILL_FILES} files")
            file_stat = path.stat(follow_symlinks=False)
            if not stat.S_ISREG(file_stat.st_mode):
                raise ValueError(f"Task skill must contain regular files only: {path}")
            if file_stat.st_size > MAX_TASK_SKILL_FILE_BYTES:
                raise ValueError(
                    f"Task skill file exceeds {MAX_TASK_SKILL_FILE_BYTES} bytes: {relative}"
                )
            content = _read_bytes_no_follow(
                skill_dir, path, max_bytes=MAX_TASK_SKILL_FILE_BYTES
            )
            total += len(content)
            if total > MAX_TASK_SKILL_BYTES:
                raise ValueError(
                    f"Task skill exceeds {MAX_TASK_SKILL_BYTES} total bytes"
                )
            values[relative] = content
    return values


def _safe_skill_relative_path(value: str) -> str:
    text = str(value or "").strip().replace("\\", "/")
    path = Path(text)
    if (
        not text
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != text
    ):
        raise ValueError(f"invalid Task skill relative file: {value}")
    return text


def _bytes_revision(values: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for relative, content in sorted(values.items()):
        digest.update(relative.encode("utf-8") + b"\0" + content + b"\0")
    return digest.hexdigest()


def _analysis_state(trial_dir: Path) -> AnalysisState:
    path = trial_dir / HARBOR_ANALYSIS_MD_FILE
    if not path.exists() and not path.is_symlink():
        return AnalysisState(False, None, None)
    content = _read_text_file(
        path,
        label="Trial analysis",
        max_bytes=HARBOR_ANALYSIS_MAX_BYTES,
        require_nonempty=True,
        containment_root=trial_dir,
    )
    return AnalysisState(
        True,
        hashlib.sha256(content.encode("utf-8")).hexdigest(),
        content,
    )


def _read_text_file(
    path: Path,
    *,
    label: str,
    max_bytes: int,
    require_nonempty: bool,
    containment_root: Path | None = None,
) -> str:
    lexical = Path(os.path.abspath(path))
    root = containment_root or lexical.parent
    try:
        content = _read_bytes_no_follow(root, lexical, max_bytes=max_bytes)
    except FileNotFoundError as exc:
        raise ValueError(f"{label} not found: {path}") from exc
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} must be UTF-8: {path}") from exc
    if require_nonempty and not text.strip():
        raise ValueError(f"{label} must not be empty: {path}")
    return text


def _published_markdown(snapshot: TaskSkillSnapshot, draft: str) -> str:
    task = snapshot.task
    lines = [
        TRIAL_ANALYSIS_PREAMBLE,
        "# Trial evaluation report",
        "",
        "## Evaluation basis",
        "",
        f"- Trial: `{_code(snapshot.target.trial_ref)}`",
        f"- Phases: {', '.join(f'`{_code(ref)}`' for ref in snapshot.target.phase_refs)}",
        f"- Evidence revision: `{snapshot.target.evidence_revision}`",
        f"- Criterion skill: `{_code(snapshot.name)}`",
        f"- Skill revision: `{snapshot.revision}`",
    ]
    for label, key in (
        ("Recorded Task digest", "recorded_digest"),
        ("Live Task digest", "live_digest"),
    ):
        if task.get(key) is not None:
            lines.append(f"- {label}: `{_code(str(task[key]))}`")
    warning = _task_digest_warning(task)
    if warning:
        lines.extend(["", "> [!WARNING]", f"> {warning}"])
    lines.extend(["", "---", "", draft.strip(), ""])
    return "\n".join(lines)


def _task_digest_warning(task: dict[str, Any]) -> str | None:
    if task.get("digest_matches") is False:
        return (
            "The recorded Task digest differs from the current live Task. This "
            "report uses the live skill as its criterion and is not a byte-identical "
            "reconstruction of the Trial-time Task."
        )
    if task.get("digest_comparison") == "not_comparable":
        return (
            "The recorded Task package reference is not comparable to the current "
            "local Task digest. This report uses the live skill as its criterion."
        )
    return None


def _code(value: str) -> str:
    return re.sub(r"[\s\x00-\x1f\x7f]+", " ", value).strip().replace("`", "'")


@contextmanager
def _trial_analysis_lease(trial_dir: Path) -> Iterator[None]:
    lock_path = trial_dir / TRIAL_ANALYSIS_LOCK_FILE
    _assert_safe_descendant(trial_dir, lock_path, label="Trial analysis lock")
    with _TRIAL_ANALYSIS_THREAD_LOCK:
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(lock_path, flags, 0o600)
        except OSError as exc:
            raise ValueError(
                f"Trial analysis lock must be a regular file: {lock_path}"
            ) from exc
        handle = os.fdopen(descriptor, "r+b")
        lock_kind: str | None = None
        try:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise ValueError(
                    f"Trial analysis lock must be a regular file: {lock_path}"
                )
            try:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                lock_kind = "fcntl"
            except ImportError:
                import msvcrt

                if os.fstat(handle.fileno()).st_size == 0:
                    handle.write(b"0")
                    handle.flush()
                    os.fsync(handle.fileno())
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                lock_kind = "msvcrt"
            yield
        finally:
            try:
                if lock_kind == "msvcrt":
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                elif lock_kind == "fcntl":
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except (ImportError, OSError, ValueError):
                pass
            finally:
                handle.close()


def _atomic_replace_text(root: Path, path: Path, content: str) -> None:
    _assert_safe_descendant(root, path, label="Trial analysis")
    if path.is_symlink():
        raise ValueError(f"Trial analysis must not be a symlink: {path}")
    existing = path.stat(follow_symlinks=False) if path.exists() else None
    if existing is not None and not stat.S_ISREG(existing.st_mode):
        raise ValueError(f"Trial analysis must be a regular file: {path}")
    mode = stat.S_IMODE(existing.st_mode) if existing is not None else 0o644
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            if existing is not None and hasattr(os, "fchown"):
                os.fchown(handle.fileno(), existing.st_uid, existing.st_gid)
            if hasattr(os, "fchmod"):
                os.fchmod(handle.fileno(), mode)
            os.fsync(handle.fileno())
        temporary.replace(path)
        try:
            directory_descriptor = os.open(path.parent, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def render_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"
