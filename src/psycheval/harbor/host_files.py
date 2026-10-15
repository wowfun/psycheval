"""Cancellable native Host file operations and initial workspace preparation."""

from __future__ import annotations

import asyncio
import hashlib
import os
import stat
import subprocess
import tarfile
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from . import windows

_WORKBUDDY_ARCHIVE_FILE_LIMIT = 64 * 1024 * 1024
_WORKBUDDY_ARCHIVE_TOTAL_LIMIT = 256 * 1024 * 1024
_WORKBUDDY_ARCHIVE_ENTRY_LIMIT = 100_000


def _check_filesystem_cancel(cancel: threading.Event | None) -> None:
    if cancel is not None and cancel.is_set():
        raise asyncio.CancelledError("Host filesystem operation cancelled")


def _read_regular_nofollow(path: Path, *, max_bytes: int) -> bytes:
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
            raise ValueError("file is not regular")
        if opened.st_size > max_bytes:
            raise ValueError(f"file exceeds {max_bytes} bytes")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            content = handle.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise ValueError(f"file exceeds {max_bytes} bytes")
        return content
    finally:
        os.close(descriptor)


@contextmanager
def _open_workspace_archive(archive: Path) -> Iterator[tarfile.TarFile]:
    descriptor = -1
    try:
        before = archive.stat(follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("WorkBuddy workspace archive cannot be extracted")
        flags = (
            os.O_RDONLY
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        descriptor = os.open(archive, flags)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or (
            before.st_ino
            and opened.st_ino
            and (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            raise ValueError("WorkBuddy workspace archive cannot be extracted")
        raw = os.fdopen(descriptor, "rb")
        descriptor = -1
        with raw:
            try:
                stream = tarfile.open(fileobj=raw, mode="r:gz")
            except (OSError, tarfile.TarError) as exc:
                raise ValueError(
                    "WorkBuddy workspace archive cannot be extracted"
                ) from exc
            with stream:
                yield stream
    except OSError as exc:
        raise ValueError("WorkBuddy workspace archive cannot be extracted") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _extract_workspace_archive(
    archive: Path, destination: Path, *, cancel: threading.Event | None = None
) -> None:
    total = 0
    seen: dict[PurePosixPath, tuple[str, int, int, bytes]] = {}
    try:
        with _open_workspace_archive(archive) as stream:
            for index, member in enumerate(stream, start=1):
                _check_filesystem_cancel(cancel)
                if index > _WORKBUDDY_ARCHIVE_ENTRY_LIMIT:
                    raise ValueError(
                        "WorkBuddy workspace archive exceeds 100000 entries"
                    )
                relative = PurePosixPath(member.name)
                if member.isdir() and member.name in {".", "./"}:
                    continue
                if (
                    relative.is_absolute()
                    or "\\" in member.name
                    or ":" in member.name
                    or not relative.parts
                    or any(
                        part.endswith((" ", ".")) or part.lower() == ".git"
                        for part in relative.parts
                    )
                ):
                    raise ValueError("WorkBuddy workspace archive path is unsafe")
                if (
                    member.issym()
                    or member.islnk()
                    or not (member.isdir() or member.isfile())
                ):
                    raise ValueError("WorkBuddy workspace archive has unsafe entries")
                target = destination.joinpath(*relative.parts)
                if member.isdir():
                    identity = ("directory", member.mode & 0o777, 0, b"")
                    previous = seen.get(relative)
                    if previous is not None and previous != identity:
                        raise ValueError(
                            "WorkBuddy workspace archive has conflicting duplicate paths"
                        )
                    seen[relative] = identity
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if member.size > _WORKBUDDY_ARCHIVE_FILE_LIMIT:
                    raise ValueError("WorkBuddy workspace archive file exceeds 64 MiB")
                total += member.size
                if total > _WORKBUDDY_ARCHIVE_TOTAL_LIMIT:
                    raise ValueError("WorkBuddy workspace archive exceeds 256 MiB")
                target.parent.mkdir(parents=True, exist_ok=True)
                source = stream.extractfile(member)
                if source is None:
                    raise ValueError("WorkBuddy workspace archive file cannot be read")
                content = source.read(_WORKBUDDY_ARCHIVE_FILE_LIMIT + 1)
                if len(content) != member.size:
                    raise ValueError("WorkBuddy workspace archive file is truncated")
                identity = (
                    "file",
                    member.mode & 0o777,
                    member.size,
                    hashlib.sha256(content).digest(),
                )
                previous = seen.get(relative)
                if previous is not None:
                    if previous != identity:
                        raise ValueError(
                            "WorkBuddy workspace archive has conflicting duplicate paths"
                        )
                    continue
                seen[relative] = identity
                _check_filesystem_cancel(cancel)
                try:
                    with target.open("xb") as output:
                        output.write(content)
                except FileExistsError as exc:
                    raise ValueError(
                        "WorkBuddy workspace archive has conflicting duplicate paths"
                    ) from exc
                target.chmod(member.mode & 0o777)
    except (OSError, tarfile.TarError) as exc:
        raise ValueError("WorkBuddy workspace archive cannot be extracted") from exc


def _initialize_git_baseline(
    workspace: Path, *, project: bool = False, cancel: threading.Event | None = None
) -> None:
    commands = (
        ("init", "-q", "-b", "main"),
        ("config", "user.email", "dev@project"),
        ("config", "user.name", "Developer"),
        ("add", "-A", *(("--force",) if project else ())),
        ("commit", "--allow-empty", "--no-verify", "-q", "-m", "initial setup"),
    )
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    for arguments in commands:
        _check_filesystem_cancel(cancel)
        try:
            result = subprocess.run(
                [
                    "git",
                    "-c",
                    "core.hooksPath=" + os.devnull,
                    "-c",
                    "commit.gpgSign=false",
                    "-C",
                    str(workspace),
                    *arguments,
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError(
                "Host workspace could not create its Git baseline"
            ) from exc
        if result.returncode != 0:
            diagnostic = (result.stderr or result.stdout).strip()
            raise ValueError(
                "Host workspace could not create its Git baseline"
                + (f": {diagnostic}" if diagnostic else "")
            )


def _workspace_entry_info(path: Path) -> os.stat_result:
    info = path.stat(follow_symlinks=False)
    if _is_link_info(info):
        raise ValueError(f"workspace source contains a link or junction: {path}")
    if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
        raise ValueError(f"workspace source contains a special file: {path}")
    return info


def _is_link_info(info: os.stat_result) -> bool:
    return bool(
        stat.S_ISLNK(info.st_mode)
        or getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def _is_native_link(path: Path) -> bool:
    try:
        return _is_link_info(path.stat(follow_symlinks=False))
    except FileNotFoundError:
        return False


def _native_regular_file_info(path: Path) -> os.stat_result:
    try:
        info = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise ValueError(f"native filesystem source is not readable: {path}") from exc
    if _is_link_info(info) or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"native filesystem source is not a regular file: {path}")
    return info


def _copy_native_file(
    source: Path, target: Path, *, cancel: threading.Event | None = None
) -> None:
    """Copy one regular file from an already checked native path safely."""

    _check_filesystem_cancel(cancel)
    before = _native_regular_file_info(source)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    descriptor = os.open(source, flags)
    try:
        opened = os.fstat(descriptor)
        if (
            _is_link_info(opened)
            or not stat.S_ISREG(opened.st_mode)
            or not os.path.samestat(before, opened)
        ):
            raise ValueError(
                f"native filesystem source changed while copying: {source}"
            )
        # Harbor collects mounted artifacts onto their existing host files.
        # Preserve the file and every hardlink alias in that case.
        if target.exists() and os.path.samestat(opened, target.stat()):
            return
        with os.fdopen(descriptor, "rb") as incoming:
            descriptor = -1
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary_fd, temporary_name = tempfile.mkstemp(
                prefix=".peval-copy-", dir=target.parent
            )
            temporary = Path(temporary_name)
            try:
                with os.fdopen(temporary_fd, "wb") as outgoing:
                    while True:
                        _check_filesystem_cancel(cancel)
                        chunk = incoming.read(1024 * 1024)
                        _check_filesystem_cancel(cancel)
                        if not chunk:
                            break
                        outgoing.write(chunk)
                temporary.chmod(stat.S_IMODE(opened.st_mode))
                os.utime(temporary, ns=(opened.st_atime_ns, opened.st_mtime_ns))
                _check_filesystem_cancel(cancel)
                temporary.replace(target)
            finally:
                try:
                    temporary.unlink(missing_ok=True)
                except PermissionError as exc:
                    windows.retry_readonly_removal(os.unlink, str(temporary), exc)
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _copy_project_tree(
    source: Path,
    destination: Path,
    *,
    cancel: threading.Event | None = None,
    overwrite: bool = False,
) -> None:
    _check_filesystem_cancel(cancel)
    if not stat.S_ISDIR(_workspace_entry_info(source).st_mode):
        raise ValueError(f"workspace source must be a directory: {source}")
    pending = [(source.iterdir(), destination)]
    while pending:
        _check_filesystem_cancel(cancel)
        entries, current_destination = pending[-1]
        entry = next(entries, None)
        if entry is None:
            pending.pop()
            continue
        if entry.name.lower() == ".git":
            continue
        info = _workspace_entry_info(entry)
        target = current_destination / entry.name
        if os.path.lexists(target):
            _workspace_entry_info(target)
        if stat.S_ISDIR(info.st_mode):
            if target.exists() and not target.is_dir():
                raise ValueError(f"workspace merge conflict: {target}")
            target.mkdir(exist_ok=True)
            pending.append((entry.iterdir(), target))
        else:
            if target.exists():
                if not overwrite or not stat.S_ISREG(target.stat().st_mode):
                    raise ValueError(f"workspace merge conflict: {target}")
                _copy_native_file(entry, target, cancel=cancel)
                continue
            flags = (
                os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            )
            flags |= getattr(os, "O_NONBLOCK", 0)
            with os.fdopen(os.open(entry, flags), "rb") as incoming:
                opened = os.fstat(incoming.fileno())
                if not stat.S_ISREG(opened.st_mode) or not os.path.samestat(
                    info, opened
                ):
                    raise ValueError(f"workspace source changed while copying: {entry}")
                try:
                    with target.open("xb") as outgoing:
                        while True:
                            _check_filesystem_cancel(cancel)
                            chunk = incoming.read(1024 * 1024)
                            _check_filesystem_cancel(cancel)
                            if not chunk:
                                break
                            outgoing.write(chunk)
                except FileExistsError as exc:
                    raise ValueError(f"workspace merge conflict: {target}") from exc
            target.chmod(stat.S_IMODE(info.st_mode))


def _validate_project_directory(source: Path) -> None:
    source = source.expanduser().absolute()
    try:
        for ancestor in (source, *source.parents):
            if not stat.S_ISDIR(_workspace_entry_info(ancestor).st_mode):
                raise ValueError(f"workspace source must be a directory: {source}")
    except OSError as exc:
        raise ValueError(f"cannot access workspace source directory: {source}") from exc
