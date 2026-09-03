"""Bounded projection of WorkBuddy-owned Harbor verifier evidence."""

from __future__ import annotations

import hashlib
import json
import math
import mimetypes
import os
import re
import stat
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Literal

from psycheval.harbor.datasets import DatasetFormat

JSON_MAX_BYTES = 1024 * 1024
TEXT_PREVIEW_MAX_BYTES = 128 * 1024
ARTIFACT_DOWNLOAD_MAX_BYTES = 32 * 1024 * 1024
ARTIFACT_TOTAL_MAX_BYTES = 128 * 1024 * 1024
ARTIFACT_LIMIT = 128
_PUBLIC_NAME = re.compile(r"[A-Za-z0-9_.:-]{1,128}")
_PUBLIC_TYPE = re.compile(r"[A-Za-z0-9_.+-]{1,32}")
_SAFE_SUFFIX = re.compile(r"\.[A-Za-z0-9]{1,16}")
_IMAGE_TYPES = {
    ".gif": "image/gif",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
_TEXT_TYPES = {
    ".csv": "text/csv; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".log": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".yaml": "application/yaml; charset=utf-8",
    ".yml": "application/yaml; charset=utf-8",
}


@dataclass(frozen=True, slots=True)
class HarborVerifierEvidence:
    status: Literal["present", "missing", "malformed"]
    score: float | None
    score_source: str | None
    harbor_reward: float | None
    reward_consistency: Literal["matched", "drifted", "missing", "malformed"]
    tests: dict[str, Any]
    components: dict[str, float]
    llm_judge: dict[str, Any] | None
    artifacts: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...]
    revision: str

    def to_dict(self, *, include_artifacts: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "score": self.score,
            "score_source": self.score_source,
            "harbor_reward": self.harbor_reward,
            "reward_consistency": self.reward_consistency,
            "tests": dict(self.tests),
            "components": dict(self.components),
            "llm_judge": self.llm_judge,
            "warnings": list(self.warnings),
            "revision": self.revision,
        }
        if include_artifacts:
            payload["artifacts"] = [dict(item) for item in self.artifacts]
        return {
            key: value for key, value in payload.items() if value not in (None, {}, [])
        }


@dataclass(frozen=True, slots=True)
class HarborVerifierArtifact:
    filename: str
    media_type: str
    content: bytes


@dataclass(slots=True)
class HarborVerifierArtifactStream:
    filename: str
    media_type: str
    size: int
    _handle: BinaryIO

    @property
    def chunks(self) -> Iterator[bytes]:
        def iterate() -> Iterator[bytes]:
            try:
                while content := self._handle.read(64 * 1024):
                    yield content
            finally:
                self.close()

        return iterate()

    def close(self) -> None:
        if not self._handle.closed:
            self._handle.close()


@dataclass(frozen=True, slots=True)
class _ArtifactSpec:
    opaque_id: str
    name: str
    raw_path: PurePosixPath | None
    preview_path: PurePosixPath | None


def read_harbor_verifier_evidence(
    data_dir: Path,
    *,
    containment_root: Path,
    dataset_format: DatasetFormat,
    harbor_reward: int | float | None,
) -> HarborVerifierEvidence:
    """Read only the documented safe subset of one effective Trial data dir."""

    verifier_dir = data_dir / "verifier"
    warnings: list[str] = []
    digest = hashlib.sha256()
    score_payload: dict[str, Any] | None = None
    score_status: Literal["present", "missing", "malformed"] = "missing"
    try:
        score_payload, score_bytes = _read_json_optional(
            containment_root, verifier_dir / "score.json"
        )
        if score_payload is not None:
            score_status = "present"
            digest.update(b"score\0" + score_bytes + b"\0")
    except (OSError, ValueError) as exc:
        score_status = "malformed"
        warnings.append(f"verifier score ignored: {exc}")

    score, score_source = _canonical_score(score_payload)
    if dataset_format == "workbuddy.v1":
        if score_status != "present":
            score, score_source = 0.0, score_status
        elif score is None:
            score_status = "malformed"
            score, score_source = 0.0, "malformed"
            warnings.append("verifier score has no usable canonical score field")

    normalized_harbor_reward = _finite_number(harbor_reward)
    if normalized_harbor_reward is None:
        consistency: Literal["matched", "drifted", "missing", "malformed"] = "missing"
    elif score_status == "malformed" or score is None:
        consistency = "malformed"
    elif math.isclose(score, normalized_harbor_reward, abs_tol=5e-4):
        consistency = "matched"
    else:
        consistency = "drifted"

    manifest: dict[str, Any] | None = None
    try:
        manifest, manifest_bytes = _read_json_optional(
            containment_root, verifier_dir / "artifact_manifest.json"
        )
        if manifest is not None:
            digest.update(b"manifest\0" + manifest_bytes + b"\0")
    except (OSError, ValueError) as exc:
        warnings.append(f"artifact manifest ignored: {exc}")
    specs, artifact_rows, artifact_warnings, artifact_revision = _artifact_specs(
        verifier_dir,
        containment_root,
        manifest,
    )
    del specs
    warnings.extend(artifact_warnings)
    digest.update(artifact_revision.encode("ascii"))

    llm_judge: dict[str, Any] | None = None
    try:
        judge_payload, judge_bytes = _read_json_optional(
            containment_root, verifier_dir / "llm_judge.json"
        )
        if judge_payload is not None:
            llm_judge = _project_llm_judge(judge_payload)
            digest.update(b"judge\0" + judge_bytes + b"\0")
    except (OSError, ValueError) as exc:
        warnings.append(f"LLM judge summary ignored: {exc}")

    tests = _project_tests(score_payload)
    components = _project_components(score_payload)
    digest.update(score_status.encode("ascii") + b"\0")
    for warning in warnings:
        digest.update(warning.encode("utf-8") + b"\0")
    return HarborVerifierEvidence(
        status=score_status,
        score=score,
        score_source=score_source,
        harbor_reward=normalized_harbor_reward,
        reward_consistency=consistency,
        tests=tests,
        components=components,
        llm_judge=llm_judge,
        artifacts=tuple(artifact_rows),
        warnings=tuple(warnings),
        revision=digest.hexdigest(),
    )


def read_harbor_verifier_artifact(
    data_dir: Path,
    *,
    containment_root: Path,
    artifact_id: str,
    purpose: Literal["preview", "download"],
) -> HarborVerifierArtifact:
    """Resolve an opaque artifact ID by re-reading the bounded manifest."""

    spec, path = _resolve_artifact_path(
        data_dir,
        containment_root=containment_root,
        artifact_id=artifact_id,
        purpose=purpose,
    )
    content = _read_regular(
        containment_root,
        path,
        max_bytes=(
            TEXT_PREVIEW_MAX_BYTES
            if purpose == "preview"
            else ARTIFACT_DOWNLOAD_MAX_BYTES
        ),
    )
    media_type = (
        _preview_media_type(path) if purpose == "preview" else _media_type(path)
    )
    if purpose == "preview" and not media_type.startswith("image/"):
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("verifier text artifact is not UTF-8") from exc
    return HarborVerifierArtifact(
        filename=_download_name(spec.name, path.suffix),
        media_type=media_type,
        content=content,
    )


def open_harbor_verifier_artifact_download(
    data_dir: Path,
    *,
    containment_root: Path,
    artifact_id: str,
) -> HarborVerifierArtifactStream:
    """Open one bounded artifact for incremental HTTP download."""

    spec, path = _resolve_artifact_path(
        data_dir,
        containment_root=containment_root,
        artifact_id=artifact_id,
        purpose="download",
    )
    handle, opened = _open_regular(
        containment_root,
        path,
        max_bytes=ARTIFACT_DOWNLOAD_MAX_BYTES,
    )
    return HarborVerifierArtifactStream(
        filename=_download_name(spec.name, path.suffix),
        media_type=_media_type(path),
        size=opened.st_size,
        _handle=handle,
    )


def _resolve_artifact_path(
    data_dir: Path,
    *,
    containment_root: Path,
    artifact_id: str,
    purpose: Literal["preview", "download"],
) -> tuple[_ArtifactSpec, Path]:
    verifier_dir = data_dir / "verifier"
    manifest, _content = _read_json_optional(
        containment_root, verifier_dir / "artifact_manifest.json"
    )
    specs, _rows, _warnings, _revision = _artifact_specs(
        verifier_dir, containment_root, manifest
    )
    spec = next((item for item in specs if item.opaque_id == artifact_id), None)
    if spec is None:
        raise ValueError("unknown verifier artifact")
    relative = spec.preview_path if purpose == "preview" else spec.raw_path
    if relative is None and purpose == "download":
        relative = spec.preview_path
    if relative is None:
        raise ValueError(f"verifier artifact has no {purpose} representation")
    path = verifier_dir.joinpath(*relative.parts)
    if purpose == "preview":
        _preview_media_type(path)
    return spec, path


def _canonical_score(payload: dict[str, Any] | None) -> tuple[float | None, str | None]:
    if not isinstance(payload, dict):
        return None, None
    if payload.get("test_status") == "build_error":
        return 0.0, "build_error"
    for key in ("reward", "overall", "test_pass_rate"):
        value = _unit_number(payload.get(key))
        if value is not None:
            return value, key
    passed = _nonnegative_int(payload.get("tests_passed"))
    total = _nonnegative_int(payload.get("tests_total"))
    if passed is not None and total:
        return min(passed / total, 1.0), "tests_passed_over_tests_total"
    return None, None


def _project_tests(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    result: dict[str, Any] = {}
    passed = _nonnegative_int(payload.get("tests_passed"))
    total = _nonnegative_int(payload.get("tests_total"))
    status = payload.get("test_status")
    if passed is not None:
        result["passed"] = passed
    if total is not None:
        result["total"] = total
    if isinstance(status, str) and _PUBLIC_NAME.fullmatch(status):
        result["status"] = status
    return result


def _project_components(payload: dict[str, Any] | None) -> dict[str, float]:
    if not isinstance(payload, dict):
        return {}
    result: dict[str, float] = {}
    for key in (
        "overall",
        "test_pass_rate",
        "rule_component_score",
        "llm_judge_component_score",
    ):
        value = _unit_number(payload.get(key))
        if value is not None:
            result[key] = value
    return result


def _project_llm_judge(payload: dict[str, Any]) -> dict[str, Any] | None:
    result: dict[str, Any] = {}
    status = payload.get("judge_status")
    if isinstance(status, str) and _PUBLIC_NAME.fullmatch(status):
        result["status"] = status
    score = _unit_number(payload.get("llm_judge"))
    if score is not None:
        result["score"] = score
    rubrics: list[dict[str, Any]] = []
    raw_rubrics = payload.get("rubrics")
    if isinstance(raw_rubrics, list):
        for raw in raw_rubrics[:ARTIFACT_LIMIT]:
            if not isinstance(raw, dict):
                continue
            item: dict[str, Any] = {}
            rubric_id = raw.get("id")
            verdict = raw.get("verdict") or raw.get("status")
            rubric_score = _unit_number(raw.get("score"))
            if isinstance(rubric_id, str) and _PUBLIC_NAME.fullmatch(rubric_id):
                item["id"] = rubric_id
            if isinstance(verdict, str) and _PUBLIC_NAME.fullmatch(verdict):
                item["verdict"] = verdict
            if rubric_score is not None:
                item["score"] = rubric_score
            if item:
                rubrics.append(item)
    if rubrics:
        result["rubrics"] = rubrics
    return result or None


def _artifact_specs(
    verifier_dir: Path,
    containment_root: Path,
    manifest: dict[str, Any] | None,
) -> tuple[list[_ArtifactSpec], list[dict[str, Any]], list[str], str]:
    specs: list[_ArtifactSpec] = []
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    digest = hashlib.sha256()
    inspected: dict[PurePosixPath, os.stat_result] = {}
    total_bytes = 0
    raw_items = manifest.get("artifacts") if isinstance(manifest, dict) else None
    if not isinstance(raw_items, list):
        return specs, rows, warnings, digest.hexdigest()
    if len(raw_items) > ARTIFACT_LIMIT:
        warnings.append(f"artifact manifest exceeds {ARTIFACT_LIMIT} entries")
    for index, raw in enumerate(raw_items[:ARTIFACT_LIMIT]):
        if not isinstance(raw, dict):
            warnings.append(f"artifact {index + 1} ignored: entry is not an object")
            continue
        try:
            name = _artifact_name(raw.get("id"), index)
            raw_path = _artifact_path(raw.get("verifier_raw_path"), "raw_artifacts")
            preview_path = _artifact_path(raw.get("text_path"), "artifact_text")
            if raw_path is None and preview_path is None:
                raise ValueError("no allowlisted verifier path")
            for relative in (raw_path, preview_path):
                if relative is not None and relative not in inspected:
                    remaining = ARTIFACT_TOTAL_MAX_BYTES - total_bytes
                    if remaining <= 0:
                        raise ValueError(
                            "artifact files exceed the aggregate byte limit"
                        )
                    opened = _inspect_regular(
                        containment_root,
                        verifier_dir.joinpath(*relative.parts),
                        max_bytes=min(ARTIFACT_DOWNLOAD_MAX_BYTES, remaining),
                    )
                    inspected[relative] = opened
                    total_bytes += opened.st_size
            identity = f"{name}\0{raw_path or ''}\0{preview_path or ''}"
            opaque_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
            spec = _ArtifactSpec(opaque_id, name, raw_path, preview_path)
            specs.append(spec)
            row: dict[str, Any] = {"id": opaque_id, "name": name}
            artifact_type = raw.get("type")
            if isinstance(artifact_type, str) and _PUBLIC_TYPE.fullmatch(artifact_type):
                row["type"] = artifact_type
            if isinstance(raw.get("required"), bool):
                row["required"] = raw["required"]
            extract_status = raw.get("extract_status")
            if isinstance(extract_status, str) and _PUBLIC_NAME.fullmatch(
                extract_status
            ):
                row["status"] = extract_status
            preview = _artifact_preview(preview_path, raw_path)
            if preview is not None:
                row["preview"] = preview
            row["download_available"] = raw_path is not None or preview_path is not None
            rows.append(row)
            digest.update(identity.encode("utf-8") + b"\0")
            for relative in (raw_path, preview_path):
                if relative is not None:
                    digest.update(
                        relative.as_posix().encode()
                        + b"\0"
                        + _stat_identity(inspected[relative])
                        + b"\0"
                    )
        except (OSError, ValueError) as exc:
            warnings.append(f"artifact {index + 1} ignored: {exc}")
    return specs, rows, warnings, digest.hexdigest()


def _artifact_preview(
    preview_path: PurePosixPath | None,
    raw_path: PurePosixPath | None,
) -> dict[str, Any] | None:
    if preview_path is not None:
        try:
            media_type = _preview_media_type(Path(preview_path.as_posix()))
        except ValueError:
            return None
        return {"kind": "image" if media_type.startswith("image/") else "text"}
    if (
        raw_path is not None
        and Path(raw_path.as_posix()).suffix.lower() in _IMAGE_TYPES
    ):
        return {"kind": "image"}
    return None


def _artifact_path(value: Any, prefix: str) -> PurePosixPath | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str) or "\\" in value:
        raise ValueError("artifact path is not a safe relative path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or path.parts[0] != prefix
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError(
            "artifact path is outside the allowlisted verifier directories"
        )
    return path


def _artifact_name(value: Any, index: int) -> str:
    if isinstance(value, str) and _PUBLIC_NAME.fullmatch(value):
        return value
    return f"artifact-{index + 1}"


def _read_json_optional(
    containment_root: Path, path: Path
) -> tuple[dict[str, Any] | None, bytes]:
    try:
        content = _read_regular(containment_root, path, max_bytes=JSON_MAX_BYTES)
    except FileNotFoundError:
        return None, b""
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"failed to parse {path.name} as a UTF-8 JSON object") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value, content


def _read_regular(root: Path, path: Path, *, max_bytes: int) -> bytes:
    handle, _opened = _open_regular(root, path, max_bytes=max_bytes)
    with handle:
        try:
            content = handle.read(max_bytes + 1)
        except BlockingIOError as exc:
            raise ValueError(f"verifier evidence is not readable: {path.name}") from exc
    if len(content) > max_bytes:
        raise ValueError(f"verifier evidence exceeds {max_bytes} bytes: {path.name}")
    return content


def _inspect_regular(root: Path, path: Path, *, max_bytes: int) -> os.stat_result:
    handle, opened = _open_regular(root, path, max_bytes=max_bytes)
    handle.close()
    return opened


def _open_regular(
    root: Path,
    path: Path,
    *,
    max_bytes: int,
) -> tuple[BinaryIO, os.stat_result]:
    _assert_contained(root, path)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError(f"verifier evidence is not a regular file: {path.name}")
        if opened.st_size > max_bytes:
            raise ValueError(
                f"verifier evidence exceeds {max_bytes} bytes: {path.name}"
            )
        handle = os.fdopen(descriptor, "rb")
        descriptor = -1
        return handle, opened
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _stat_identity(value: os.stat_result) -> bytes:
    fields = (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )
    return ":".join(str(item) for item in fields).encode("ascii")


def _assert_contained(root: Path, path: Path) -> None:
    absolute_root = Path(os.path.abspath(root))
    absolute_path = Path(os.path.abspath(path))
    try:
        relative = absolute_path.relative_to(absolute_root)
    except ValueError as exc:
        raise ValueError("verifier evidence escapes its Trial root") from exc
    current = absolute_root
    if current.is_symlink():
        raise ValueError("verifier evidence root is a symbolic link")
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError("verifier evidence traverses a symbolic link")


def _media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in _IMAGE_TYPES:
        return _IMAGE_TYPES[suffix]
    if suffix in _TEXT_TYPES:
        return _TEXT_TYPES[suffix]
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def _preview_media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in _IMAGE_TYPES:
        return _IMAGE_TYPES[suffix]
    if suffix in _TEXT_TYPES:
        return _TEXT_TYPES[suffix]
    raise ValueError("verifier artifact type is not previewable")


def _download_name(name: str, suffix: str) -> str:
    if _SAFE_SUFFIX.fullmatch(suffix) is None:
        suffix = ""
    return (
        name
        if not suffix or name.lower().endswith(suffix.lower())
        else f"{name}{suffix}"
    )


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _unit_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and 0 <= number <= 1 else None


def _nonnegative_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None
