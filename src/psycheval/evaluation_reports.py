from __future__ import annotations

import errno
import os
import stat
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Iterator

from psycheval.config import load_config
from psycheval.evaluation_report_identity import evaluation_report_ref
from psycheval.state import ServeStateStore, workspace_paths
from psycheval.state.catalog import WorkspaceCatalog
from psycheval.state.workspace_harbor import (
    HARBOR_ANALYSIS_MAX_BYTES,
    _assert_safe_descendant,
    _read_bytes_no_follow,
)
from psycheval.state.workspace_source_models import (
    HARBOR_ANALYSIS_MD_FILE,
    HARBOR_SOURCE_KIND,
    SourceCandidate,
    SourceDocument,
)
from psycheval.state.workspace_sources import WorkspaceSources

EVALUATION_REPORT_MAX_BYTES = HARBOR_ANALYSIS_MAX_BYTES
EVALUATION_REPORT_LOCK_FILE = ".peval-analysis.lock"
_EVALUATION_REPORT_THREAD_LOCK = threading.Lock()


@dataclass(frozen=True)
class EvaluationReportTarget:
    requested_ref: str
    source_ref: str
    source_refs: tuple[str, ...]
    source_keys: tuple[str, ...]
    report_dir: Path
    report_path: Path
    harbor: bool
    selected_documents: tuple[SourceDocument, ...]
    candidates: tuple[SourceCandidate, ...] = ()


@dataclass(frozen=True)
class EvaluationReportDocument:
    source_ref: str
    report_ref: str
    report_path: str
    content: str


@dataclass(frozen=True)
class EvaluationReportReceipt:
    source_ref: str
    report_ref: str
    report_path: str
    replaced: bool
    catalog_reconciled: bool = True
    catalog_generation: int | None = None

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "source_ref": self.source_ref,
            "report_ref": self.report_ref,
            "report_path": self.report_path,
            "replaced": self.replaced,
            "catalog_reconciled": self.catalog_reconciled,
            "catalog_generation": self.catalog_generation,
        }


class EvaluationReportCommittedError(RuntimeError):
    def __init__(
        self,
        receipt: EvaluationReportReceipt,
        error: Exception,
        *,
        message: str,
    ) -> None:
        self.receipt = {
            **receipt.to_jsonable(),
            "catalog_reconciled": False,
        }
        super().__init__(f"{message}: {error}")


class EvaluationReportReconcileError(EvaluationReportCommittedError):
    def __init__(self, receipt: EvaluationReportReceipt, error: Exception) -> None:
        super().__init__(
            receipt,
            error,
            message=(
                "Evaluation report was committed but catalog reconciliation failed"
            ),
        )


class EvaluationReportDurabilityError(EvaluationReportCommittedError):
    def __init__(self, receipt: EvaluationReportReceipt, error: Exception) -> None:
        super().__init__(
            receipt,
            error,
            message=("Evaluation report was replaced but directory durability failed"),
        )


class _AtomicReplaceCommittedError(RuntimeError):
    pass


class EvaluationReports:
    """Own canonical evaluation-report reads and atomic source-scoped upserts."""

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

    def resolve(self, source_ref: str) -> EvaluationReportTarget:
        return self._resolve(source_ref, include_documents=True)

    def _resolve(
        self,
        source_ref: str,
        *,
        include_documents: bool,
    ) -> EvaluationReportTarget:
        requested = str(source_ref or "").strip()
        if requested.startswith("harbor/"):
            return self._resolve_harbor(
                requested,
                include_documents=include_documents,
            )
        document = self.sources.load_ref(
            requested,
            include_evaluation_report=include_documents,
        )
        if document.source.get("kind") == HARBOR_SOURCE_KIND:
            raise ValueError(f"invalid local source reference: {requested}")
        if (
            not document.readable
            or document.trajectory is None
            or document.meta is None
        ):
            raise ValueError(
                document.last_error or f"local source is not readable: {requested}"
            )
        report_dir = self.sources.annotation_dir(document.source_ref)
        return EvaluationReportTarget(
            requested_ref=requested,
            source_ref=document.source_ref,
            source_refs=(document.source_ref,),
            source_keys=(document.source_key,),
            report_dir=report_dir,
            report_path=report_dir / HARBOR_ANALYSIS_MD_FILE,
            harbor=False,
            selected_documents=(document,) if include_documents else (),
        )

    def documents(self, source_refs: Iterable[str]) -> list[SourceDocument]:
        documents: list[SourceDocument] = []
        for source_ref in source_refs:
            target = self.resolve(source_ref)
            documents.extend(target.selected_documents)
        return documents

    def read(self, source_ref: str) -> EvaluationReportDocument | None:
        target = self._resolve(source_ref, include_documents=False)
        try:
            content = _read_optional_report(target.report_dir, target.report_path)
        except (OSError, ValueError):
            return None
        if content is None:
            return None
        return EvaluationReportDocument(
            source_ref=target.source_ref,
            report_ref=evaluation_report_ref(target.source_ref),
            report_path=HARBOR_ANALYSIS_MD_FILE,
            content=content,
        )

    def publish(
        self,
        source_ref: str,
        draft_path: str | Path,
    ) -> EvaluationReportReceipt:
        draft = _read_text_file(
            Path(draft_path).expanduser(),
            label="Evaluation report draft",
            max_bytes=EVALUATION_REPORT_MAX_BYTES,
            require_nonempty=True,
        )
        catalog: WorkspaceCatalog | None = None
        committed: EvaluationReportReceipt | None = None
        initial = self._resolve(source_ref, include_documents=False)

        def action() -> EvaluationReportReceipt:
            nonlocal committed
            target = self._resolve(source_ref, include_documents=False)
            if target.report_dir != initial.report_dir:
                raise ValueError("evaluation report target changed during publication")
            self._validate_publishable(target)
            replaced_existing = (
                target.report_path.exists() or target.report_path.is_symlink()
            )
            receipt = EvaluationReportReceipt(
                source_ref=target.source_ref,
                report_ref=evaluation_report_ref(target.source_ref),
                report_path=HARBOR_ANALYSIS_MD_FILE,
                replaced=replaced_existing,
            )
            try:
                _atomic_replace_text(target.report_dir, target.report_path, draft)
            except _AtomicReplaceCommittedError as exc:
                committed = receipt
                raise EvaluationReportDurabilityError(receipt, exc) from exc
            committed = receipt
            return committed

        try:
            # Acquire the source lock before the catalog writer lease. This lets
            # concurrent publications queue instead of racing the catalog's
            # deliberately non-blocking workspace lock, and gives Markdown
            # imports the same lock order.
            with _evaluation_report_lease(initial.report_dir):
                catalog = WorkspaceCatalog(self.store, self.config)
                generation, receipt = catalog.mutate(action)
        except EvaluationReportCommittedError:
            raise
        except Exception as exc:
            if committed is not None:
                raise EvaluationReportReconcileError(committed, exc) from exc
            raise
        finally:
            if catalog is not None:
                catalog.close()
        return replace(receipt, catalog_generation=generation)

    def _resolve_harbor(
        self,
        requested: str,
        *,
        include_documents: bool,
    ) -> EvaluationReportTarget:
        parts = Path(requested).parts
        if (
            len(parts) not in {4, 6}
            or parts[0] != "harbor"
            or (len(parts) == 6 and parts[4] != "steps")
        ):
            raise ValueError(f"invalid Harbor source reference: {requested}")
        source_ref = "/".join(parts[:4])
        selected = tuple(
            self.sources.harbor_candidates_for_ref(
                requested,
                include_evaluation_report=include_documents,
            )
        )
        if not selected:
            raise ValueError(f"unknown source reference: {requested}")
        all_candidates = tuple(
            self.sources.harbor_candidates_for_ref(
                source_ref,
                include_evaluation_report=include_documents,
            )
        )
        report_dir = all_candidates[0].path
        if any(candidate.path != report_dir for candidate in all_candidates):
            raise ValueError(f"Harbor phases do not share one Trial root: {source_ref}")
        selected_documents = (
            tuple(self.sources.load(candidate) for candidate in selected)
            if include_documents
            else ()
        )
        return EvaluationReportTarget(
            requested_ref=requested,
            source_ref=source_ref,
            source_refs=tuple(candidate.source_ref for candidate in all_candidates),
            source_keys=tuple(
                str(candidate.source_key)
                for candidate in all_candidates
                if candidate.source_key is not None
            ),
            report_dir=report_dir,
            report_path=report_dir / HARBOR_ANALYSIS_MD_FILE,
            harbor=True,
            selected_documents=selected_documents,
            candidates=all_candidates,
        )

    @staticmethod
    def _validate_publishable(target: EvaluationReportTarget) -> None:
        if not target.harbor:
            return
        for candidate in target.candidates:
            evidence = candidate.harbor_evidence
            if evidence is None:
                raise ValueError(f"Harbor evidence is unavailable: {target.source_ref}")
            result = evidence.trial_values.get("result.json")
            if not isinstance(result, dict) or not result.get("finished_at"):
                raise ValueError(
                    "Evaluation reports can only be published after the Harbor Trial "
                    "finishes"
                )


def _read_optional_report(root: Path, path: Path) -> str | None:
    if not path.exists() and not path.is_symlink():
        return None
    text = _read_text_file(
        path,
        label="Evaluation report",
        max_bytes=EVALUATION_REPORT_MAX_BYTES,
        require_nonempty=False,
        containment_root=root,
    )
    return text if text.strip() else None


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
        content = _read_bytes_no_follow(
            root,
            lexical,
            max_bytes=max_bytes,
            label=label,
        )
    except ValueError as exc:
        if isinstance(exc.__cause__, FileNotFoundError):
            raise ValueError(f"{label} not found: {path}") from exc
        raise
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} must be UTF-8: {path}") from exc
    if require_nonempty and not text.strip():
        raise ValueError(f"{label} must not be empty: {path}")
    return text


@contextmanager
def _evaluation_report_lease(report_dir: Path) -> Iterator[None]:
    lock_path = report_dir / EVALUATION_REPORT_LOCK_FILE
    _assert_safe_descendant(report_dir, lock_path, label="Evaluation report lock")
    with _EVALUATION_REPORT_THREAD_LOCK:
        if lock_path.is_symlink():
            raise ValueError(
                f"Evaluation report lock must not be a symlink: {lock_path}"
            )
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(lock_path, flags, 0o600)
        except OSError as exc:
            raise ValueError(
                f"Evaluation report lock must be a regular file: {lock_path}"
            ) from exc
        handle = os.fdopen(descriptor, "r+b")
        lock_kind: str | None = None
        try:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise ValueError(
                    f"Evaluation report lock must be a regular file: {lock_path}"
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
                _acquire_windows_file_lock(handle, msvcrt)
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


def _acquire_windows_file_lock(handle: Any, msvcrt: Any) -> None:
    """Match POSIX blocking-lock semantics beyond msvcrt's ten-second retry."""
    retryable_errors = {errno.EACCES, errno.EAGAIN, errno.EDEADLK}
    retryable_windows_errors = {32, 33, 36}
    while True:
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            return
        except OSError as exc:
            if (
                exc.errno not in retryable_errors
                and getattr(exc, "winerror", None) not in retryable_windows_errors
            ):
                raise


def _atomic_replace_text(root: Path, path: Path, content: str) -> None:
    _assert_safe_descendant(root, path, label="Evaluation report")
    if path.is_symlink():
        raise ValueError(f"Evaluation report must not be a symlink: {path}")
    existing = path.stat(follow_symlinks=False) if path.exists() else None
    if existing is not None and not stat.S_ISREG(existing.st_mode):
        raise ValueError(f"Evaluation report must be a regular file: {path}")
    mode = stat.S_IMODE(existing.st_mode) if existing is not None else 0o644
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    replaced = False
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content.encode("utf-8"))
            handle.flush()
            if existing is not None and hasattr(os, "fchown"):
                os.fchown(handle.fileno(), existing.st_uid, existing.st_gid)
            if hasattr(os, "fchmod"):
                os.fchmod(handle.fileno(), mode)
            os.fsync(handle.fileno())
        temporary.replace(path)
        replaced = True
        try:
            _fsync_replaced_file_directory(path.parent)
        except _AtomicReplaceCommittedError:
            raise
        except Exception as exc:
            raise _AtomicReplaceCommittedError(
                f"could not finalize report replacement: {path}"
            ) from exc
    finally:
        if not replaced:
            temporary.unlink(missing_ok=True)


def _fsync_replaced_file_directory(directory: Path) -> None:
    try:
        descriptor = os.open(directory, os.O_RDONLY)
    except OSError as exc:
        if os.name == "nt":
            return
        raise _AtomicReplaceCommittedError(
            f"could not open report directory for fsync: {directory}"
        ) from exc
    failure: OSError | None = None
    try:
        os.fsync(descriptor)
    except OSError as exc:
        failure = exc
    try:
        os.close(descriptor)
    except OSError as exc:
        if failure is None:
            failure = exc
    if failure is not None:
        raise _AtomicReplaceCommittedError(
            f"could not fsync report directory: {directory}"
        ) from failure
