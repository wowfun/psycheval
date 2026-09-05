"""Native Windows path, process, and runtime-copy mechanics for Harbor adapters.

Importable on any host; Office profile policy belongs to workbuddy_verifier.
"""

from __future__ import annotations

import ast
import asyncio
import ctypes
import os
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath

from harbor.models.task.config import TaskOS
from harbor.utils.scripts import quote_windows_shell_arg

_ABSOLUTE = re.compile(r"^[A-Za-z]:[/\\]")


def quote_powershell_literal(value: str) -> str:
    if any(character in value for character in ("\x00", "\r", "\n")):
        raise ValueError("PowerShell command literals must be single-line and NUL-free")
    return "'" + value.replace("'", "''") + "'"


def powershell_command(argv: Sequence[str]) -> str:
    if not argv or not argv[0]:
        raise ValueError("PowerShell command requires a nonempty executable")
    return "& " + " ".join(quote_powershell_literal(arg) for arg in argv)


def is_absolute_path(value: str) -> bool:
    return bool(_ABSOLUTE.match(value) or value.startswith("\\\\"))


def normalize_environment_path(
    value: str, *, label: str, allow_root: bool = False
) -> str:
    if "\x00" in value:
        raise ValueError(f"{label} contains NUL")
    normalized = value.replace("\\", "/")
    if _ABSOLUTE.match(normalized):
        if normalized[0].lower() != "c":
            raise ValueError(f"{label} must use the C: environment drive")
        normalized = normalized[2:]
    if not normalized.startswith("/") or normalized.startswith("//"):
        raise ValueError(f"{label} must be an absolute environment path")
    if ".." in normalized.split("/"):
        raise ValueError(f"{label} cannot traverse a parent")
    if ":" in normalized:
        raise ValueError(f"{label} cannot contain an embedded drive or stream")
    canonical = PurePosixPath(normalized).as_posix()
    if not allow_root and canonical == "/":
        raise ValueError(f"{label} must be a non-root absolute environment path")
    return canonical


def split_virtual_path(
    value: str, roots: Sequence[str]
) -> tuple[str, tuple[str, ...]] | None:
    normalized = value.replace("\\", "/")
    candidate = normalized.casefold()
    for virtual in sorted(set(roots), key=len, reverse=True):
        for alias in (virtual, f"C:{virtual}"):
            comparison = alias.casefold()
            if candidate == comparison:
                return virtual, ()
            if candidate.startswith(comparison + "/"):
                parts = PurePosixPath(normalized[len(alias) + 1 :]).parts
                if ".." in parts or any(
                    ":" in part or "\x00" in part for part in parts
                ):
                    raise ValueError(f"unsupported HostEnvironment path: {value}")
                return virtual, tuple(part for part in parts if part != ".")
    return None


def translate_literal(value: str, mappings: Mapping[str, Path]) -> str | None:
    match = split_virtual_path(value, tuple(mappings))
    if match is None:
        return None
    virtual, suffix = match
    return str(mappings[virtual].joinpath(*suffix))


def translate_environment(
    env: Mapping[str, str], mappings: Mapping[str, Path], *, path_separator: str = ";"
) -> dict[str, str]:
    """Map virtual values using Windows path-list syntax by default.

    The caller owns which values need mapping; explicit argv env is literal.
    Native verification on other hosts supplies its own path separator.
    """
    translated = {}
    for key, value in env.items():
        if key.upper() in {"PATH", "PYTHONPATH"}:
            translated[key] = path_separator.join(
                translate_literal(part, mappings) or part
                for part in value.split(path_separator)
            )
        else:
            translated[key] = translate_literal(value, mappings) or value
    return translated


def rewrite_python(source: str, edits: Sequence[tuple[ast.AST, str]]) -> str:
    """Apply caller-approved expression edits without reformatting other source.

    AST positions are UTF-8 byte offsets. Reject overlap and invalid output;
    the caller owns which expressions are eligible and retains its audit.
    """
    lines = source.encode("utf-8").splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    spans = []
    for node, replacement in edits:
        start = offsets[node.lineno - 1] + node.col_offset
        end = offsets[node.end_lineno - 1] + node.end_col_offset
        spans.append((start, end, replacement.encode("utf-8")))
    content = source.encode("utf-8")
    previous = len(content)
    for start, end, replacement in sorted(spans, reverse=True):
        if not 0 <= start < end <= previous:
            raise ValueError("overlapping or invalid Python adaptation edits")
        content = content[:start] + replacement + content[end:]
        previous = start
    result = content.decode("utf-8")
    compile(result, "<adapted grader>", "exec")
    return result


def translate_command(command: str, mappings: dict[str, Path]) -> str:
    aliases = sorted(
        {
            alias
            for virtual in mappings
            for alias in (
                virtual,
                f"C:{virtual}",
                f"C:{virtual}".replace("/", "\\"),
            )
        },
        key=len,
        reverse=True,
    )
    alias_pattern = "|".join(re.escape(alias) for alias in aliases)
    path_pattern = re.compile(
        rf"(?<![A-Za-z0-9_:/\\.-])"
        rf"(?P<path>(?:{alias_pattern})(?:[/\\][^\s;|&()<>\"']*)?)"
        rf"(?=$|[\s;|&()<>])",
        flags=re.IGNORECASE,
    )

    def translate_unquoted(value: str) -> str:
        def replacement(match: re.Match[str]) -> str:
            translated = translate_literal(match.group("path"), mappings)
            if translated is None:
                return match.group(0)
            return quote_windows_shell_arg(translated)

        return path_pattern.sub(replacement, value)

    pieces: list[str] = []
    unquoted_start = 0
    index = 0
    while index < len(command):
        if command[index] != '"':
            index += 1
            continue
        pieces.append(translate_unquoted(command[unquoted_start:index]))
        end = command.find('"', index + 1)
        if end < 0:
            pieces.append(command[index:])
            return "".join(pieces)
        content = command[index + 1 : end]
        translated_literal = translate_literal(content, mappings)
        if translated_literal is None:
            pieces.append(command[index : end + 1])
        else:
            pieces.append(quote_windows_shell_arg(translated_literal))
        index = end + 1
        unquoted_start = index
    pieces.append(translate_unquoted(command[unquoted_start:]))
    return "".join(pieces)


class _ProcessJob:
    """Own a Win32 Job handle without importing Windows APIs on other hosts."""

    def __init__(self):
        size = ctypes.c_size_t
        dword = ctypes.c_uint32
        large = ctypes.c_int64

        class BasicLimits(ctypes.Structure):
            _fields_ = [
                ("process_time", large),
                ("job_time", large),
                ("flags", dword),
                ("minimum_working_set", size),
                ("maximum_working_set", size),
                ("active_processes", dword),
                ("affinity", size),
                ("priority", dword),
                ("scheduling", dword),
            ]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [
                ("basic", BasicLimits),
                ("io_counters", ctypes.c_uint64 * 6),
                ("process_memory", size),
                ("job_memory", size),
                ("peak_process_memory", size),
                ("peak_job_memory", size),
            ]

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        for name, args, result in (
            ("CreateJobObjectW", [ctypes.c_void_p, ctypes.c_wchar_p], ctypes.c_void_p),
            (
                "SetInformationJobObject",
                [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, dword],
                ctypes.c_int,
            ),
            ("OpenProcess", [dword, ctypes.c_int, dword], ctypes.c_void_p),
            (
                "AssignProcessToJobObject",
                [ctypes.c_void_p, ctypes.c_void_p],
                ctypes.c_int,
            ),
            (
                "IsProcessInJob",
                [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)],
                ctypes.c_int,
            ),
            ("CloseHandle", [ctypes.c_void_p], ctypes.c_int),
        ):
            function = getattr(kernel, name)
            function.argtypes = args
            function.restype = result
        self.kernel = kernel
        self.handle = kernel.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(
            self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
        ):
            error = ctypes.WinError(ctypes.get_last_error())
            self.close()
            raise error

    def assign(self, pid: int) -> None:
        handle = self.kernel.OpenProcess(0x0101, False, pid)  # SET_QUOTA | TERMINATE
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not self.kernel.AssignProcessToJobObject(self.handle, handle):
                code = ctypes.get_last_error()
                error = ctypes.WinError(code)
                try:
                    membership = str(self.contains(pid, any_job=True))
                except OSError:
                    membership = "unknown"
                raise RuntimeError(
                    f"Cannot assign HostEnvironment launcher {pid} to its Job "
                    f"(WinError {code}; existing Job membership: {membership}). "
                    "The host must permit nested Job assignment; the target command "
                    "has not started."
                ) from error
        finally:
            self.kernel.CloseHandle(handle)

    def contains(self, pid: int, *, any_job: bool = False) -> bool:
        handle = self.kernel.OpenProcess(
            0x1000, False, pid
        )  # QUERY_LIMITED_INFORMATION
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            result = ctypes.c_int()
            if not self.kernel.IsProcessInJob(
                handle, None if any_job else self.handle, ctypes.byref(result)
            ):
                raise ctypes.WinError(ctypes.get_last_error())
            return bool(result.value)
        finally:
            self.kernel.CloseHandle(handle)

    def close(self) -> None:
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


class WindowsProcessAdapter:
    os = TaskOS.WINDOWS

    def __init__(self):
        self._jobs: dict[asyncio.subprocess.Process, _ProcessJob] = {}

    async def spawn(self, argv: Sequence[str], **kwargs) -> asyncio.subprocess.Process:
        if "stdin" in kwargs:
            raise ValueError("stdin is reserved for the Windows launch gate")
        job = _ProcessJob()
        process = None
        try:
            # No child can be created until assignment succeeds. -I -S prevents
            # site/PYTHONPATH startup code from executing before this gate.
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-I",
                "-S",
                "-c",
                "import subprocess,sys; token=sys.stdin.buffer.read(1); "
                "sys.exit(subprocess.call(sys.argv[1:]) if token == b'1' else 125)",
                *argv,
                stdin=asyncio.subprocess.PIPE,
                **kwargs,
                **self.process_kwargs(),
            )
            job.assign(process.pid)
            self._jobs[process] = job
            process.stdin.write(b"1")
            await process.stdin.drain()
            process.stdin.close()
            return process
        except BaseException:
            job.close()
            if process is not None:
                self._jobs.pop(process, None)
                if process.returncode is None:
                    process.kill()
                await process.communicate()
            raise

    def release(self, process: asyncio.subprocess.Process) -> None:
        job = self._jobs.pop(process, None)
        if job is not None:
            job.close()

    def translate_command(self, command: str, mappings: dict[str, Path]) -> str:
        return translate_command(command, mappings)

    def shell_argv(self, command: str) -> tuple[str, ...]:
        shell_command = f'"{command}"' if command.lstrip().startswith('"') else command
        return (
            os.environ.get("COMSPEC", "cmd.exe"),
            "/D",
            "/S",
            "/C",
            shell_command,
        )

    def process_kwargs(self) -> dict[str, object]:
        return {
            "creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        }

    def validate_user(self, resolved_user: str | int | None) -> None:
        if resolved_user is not None:
            raise ValueError(
                "HostEnvironment on Windows does not support user switching; "
                f"received {resolved_user!r}"
            )

    async def terminate(self, process: asyncio.subprocess.Process) -> None:
        self.release(process)
        try:
            await asyncio.wait_for(process.wait(), timeout=2)
        except asyncio.TimeoutError:
            if process.returncode is None:
                process.kill()
            await process.wait()
