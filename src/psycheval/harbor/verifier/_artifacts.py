from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath


def resolve_required_artifacts(
    artifacts_dir: Path, patterns: list[str]
) -> tuple[list[str], list[str]]:
    resolved: set[str] = set()
    invalid: list[str] = []
    for pattern in patterns:
        _validate_pattern(pattern)
        matches = sorted(
            artifacts_dir.glob(pattern), key=lambda candidate: candidate.as_posix()
        )
        if not matches:
            invalid.append(f"{pattern} matched no artifacts")
            continue
        for match in matches:
            relative = match.relative_to(artifacts_dir).as_posix()
            resolved.add(relative)
            if reason := _invalid_artifact(artifacts_dir, relative):
                invalid.append(reason)
    return sorted(resolved), invalid


def _validate_pattern(pattern: str) -> None:
    posix_path = PurePosixPath(pattern)
    if (
        not pattern
        or "\\" in pattern
        or posix_path.is_absolute()
        or PureWindowsPath(pattern).is_absolute()
        or posix_path == PurePosixPath(".")
        or ".." in posix_path.parts
    ):
        raise ValueError(
            f"required artifact {pattern!r} must be a relative POSIX glob below "
            "the artifact root"
        )


def _invalid_artifact(artifacts_dir: Path, relative: str) -> str | None:
    relative_path = Path(relative)
    if (
        relative_path.is_absolute()
        or relative_path == Path(".")
        or ".." in relative_path.parts
    ):
        raise ValueError(
            f"required artifact {relative!r} must be a relative path below the "
            "artifact root"
        )
    root = artifacts_dir.resolve()
    candidate = artifacts_dir / relative_path
    current = artifacts_dir
    for part in relative_path.parts:
        current = current / part
        if current.is_symlink():
            return f"{relative} is or traverses a symlink"
    try:
        candidate.resolve().relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"required artifact {relative!r} must be a relative path below the "
            "artifact root"
        ) from exc
    if not candidate.is_file():
        return f"{relative} is not a regular file"
    if candidate.stat().st_size == 0:
        return f"{relative} is empty"
    if candidate.suffix.lower() == ".png":
        with candidate.open("rb") as artifact:
            if artifact.read(8) != b"\x89PNG\r\n\x1a\n":
                return f"{relative} does not have a PNG signature"
    return None
