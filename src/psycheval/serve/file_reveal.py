from __future__ import annotations

import ctypes
import os
import platform
import shutil
import stat
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

__all__ = [
    "FileRevealUnavailable",
    "reveal_in_file_manager",
]


class FileRevealUnavailable(RuntimeError):
    pass


_WINDOWS_SHELL_LOCK = threading.Lock()
_WINDOWS_SHELL_PROTOTYPES: tuple[Any, Any, Any, Any, Any] | None = None


def reveal_in_file_manager(path: Path) -> None:
    """Open the local host file manager and highlight an existing regular file."""
    target = Path(path)
    if not target.is_absolute():
        raise ValueError("reveal target must be an absolute path")
    try:
        info = target.stat(follow_symlinks=False)
    except OSError as exc:
        raise ValueError("reveal target unavailable") from exc
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("reveal target must be a regular file")

    if sys.platform == "win32":
        _reveal_windows(target)
        return
    if sys.platform == "darwin":
        _reveal_macos(target)
        return
    if sys.platform.startswith("linux"):
        _reveal_linux(target)
        return
    raise FileRevealUnavailable(
        f"native file manager reveal is unsupported on {sys.platform}"
    )


def _windows_shell_functions() -> tuple[Any, Any, Any, Any, Any]:
    global _WINDOWS_SHELL_PROTOTYPES
    with _WINDOWS_SHELL_LOCK:
        if _WINDOWS_SHELL_PROTOTYPES is not None:
            return _WINDOWS_SHELL_PROTOTYPES
        ole32 = ctypes.windll.ole32  # type: ignore[attr-defined]
        shell32 = ctypes.windll.shell32  # type: ignore[attr-defined]

        co_initialize = ole32.CoInitializeEx
        co_initialize.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        co_initialize.restype = ctypes.c_long

        co_uninitialize = ole32.CoUninitialize
        co_uninitialize.argtypes = []
        co_uninitialize.restype = None

        il_create = shell32.ILCreateFromPathW
        il_create.argtypes = [ctypes.c_wchar_p]
        il_create.restype = ctypes.c_void_p

        open_and_select = shell32.SHOpenFolderAndSelectItems
        open_and_select.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_ulong,
        ]
        open_and_select.restype = ctypes.c_long

        il_free = shell32.ILFree
        il_free.argtypes = [ctypes.c_void_p]
        il_free.restype = None

        _WINDOWS_SHELL_PROTOTYPES = (
            co_initialize,
            co_uninitialize,
            il_create,
            open_and_select,
            il_free,
        )
        return _WINDOWS_SHELL_PROTOTYPES


def _reveal_windows(path: Path) -> None:
    errors: list[str] = []
    try:
        _reveal_windows_shell_api(path)
        return
    except OSError as exc:
        errors.append(f"SHOpenFolderAndSelectItems: {exc}")

    explorer = shutil.which("explorer.exe")
    if not explorer:
        errors.append("explorer.exe: not found")
        raise FileRevealUnavailable(
            f"native file manager unavailable: {'; '.join(errors)}"
        )
    try:
        subprocess.Popen(
            [explorer, "/select,", str(path)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        errors.append(f"explorer.exe: {exc.strerror or type(exc).__name__}")
        raise FileRevealUnavailable(
            f"native file manager unavailable: {'; '.join(errors)}"
        ) from exc


def _reveal_windows_shell_api(path: Path) -> None:
    (
        co_initialize,
        co_uninitialize,
        il_create,
        open_and_select,
        il_free,
    ) = _windows_shell_functions()

    coinit_apartment = 0x2
    rpc_e_changed_mode = 0x80010106
    init_hr = co_initialize(None, coinit_apartment) & 0xFFFFFFFF
    should_uninit = init_hr in {0, 1}
    if not should_uninit and init_hr != rpc_e_changed_mode:
        raise OSError(f"CoInitializeEx failed: 0x{init_hr:08x}")
    try:
        pidl = il_create(str(path))
        if not pidl:
            raise OSError("ILCreateFromPathW returned null")
        try:
            hr = open_and_select(pidl, 0, None, 0)
            if hr < 0:
                raise OSError(
                    f"SHOpenFolderAndSelectItems failed: 0x{hr & 0xFFFFFFFF:08x}"
                )
        finally:
            il_free(pidl)
    finally:
        if should_uninit:
            co_uninitialize()


def _subprocess_failure(tool: str, exc: OSError | subprocess.SubprocessError) -> str:
    if isinstance(exc, subprocess.TimeoutExpired):
        return f"{tool}: timed out"
    if isinstance(exc, OSError):
        return f"{tool}: {exc.strerror or type(exc).__name__}"
    return f"{tool}: launch failed"


def _reveal_macos(path: Path) -> None:
    executable = shutil.which("open")
    if not executable:
        raise FileRevealUnavailable("native file manager unavailable: open not found")
    try:
        result = subprocess.run(
            [executable, "-R", str(path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise FileRevealUnavailable(
            f"native file manager unavailable: {_subprocess_failure('open', exc)}"
        ) from exc
    if result.returncode != 0:
        raise FileRevealUnavailable(
            f"native file manager unavailable: open exited with status {result.returncode}"
        )


def _is_wsl() -> bool:
    return bool(
        os.environ.get("WSL_DISTRO_NAME")
        or os.environ.get("WSL_INTEROP")
        or "microsoft" in platform.release().lower()
    )


def _reveal_wsl(path: Path, errors: list[str]) -> bool:
    wslpath = shutil.which("wslpath")
    explorer = shutil.which("explorer.exe")
    if not wslpath or not explorer:
        return False
    try:
        converted = subprocess.run(
            [wslpath, "-w", str(path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        errors.append(_subprocess_failure("wslpath", exc))
        return False
    win_path = converted.stdout.strip()
    if converted.returncode != 0 or not win_path:
        errors.append(f"wslpath: exit status {converted.returncode}")
        return False
    try:
        subprocess.Popen(
            [explorer, "/select,", win_path],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except OSError as exc:
        errors.append(_subprocess_failure("explorer.exe", exc))
        return False


def _reveal_linux(path: Path) -> None:
    errors: list[str] = []
    if _is_wsl() and _reveal_wsl(path, errors):
        return

    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        detail = (
            "; ".join([*errors, "no desktop display session"])
            if errors
            else "no desktop display session"
        )
        raise FileRevealUnavailable(f"native file manager unavailable: {detail}")

    uri = path.as_uri()
    gdbus = shutil.which("gdbus")
    if gdbus:
        try:
            result = subprocess.run(
                [
                    gdbus,
                    "call",
                    "--session",
                    "--dest",
                    "org.freedesktop.FileManager1",
                    "--object-path",
                    "/org/freedesktop/FileManager1",
                    "--method",
                    "org.freedesktop.FileManager1.ShowItems",
                    f"['{uri}']",
                    "",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return
            errors.append(f"gdbus: exit status {result.returncode}")
        except (OSError, subprocess.SubprocessError) as exc:
            errors.append(_subprocess_failure("gdbus", exc))
    else:
        dbus_send = shutil.which("dbus-send")
        if dbus_send:
            try:
                result = subprocess.run(
                    [
                        dbus_send,
                        "--session",
                        "--print-reply",
                        "--dest=org.freedesktop.FileManager1",
                        "/org/freedesktop/FileManager1",
                        "org.freedesktop.FileManager1.ShowItems",
                        f"array:string:{uri}",
                        "string:",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return
                errors.append(f"dbus-send: exit status {result.returncode}")
            except (OSError, subprocess.SubprocessError) as exc:
                errors.append(_subprocess_failure("dbus-send", exc))

    xdg_open = shutil.which("xdg-open")
    if xdg_open:
        try:
            subprocess.Popen(
                [xdg_open, str(path.parent)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return
        except OSError as exc:
            errors.append(_subprocess_failure("xdg-open", exc))
    else:
        errors.append("xdg-open: not found")

    detail = "; ".join(errors) if errors else "no supported file manager found"
    raise FileRevealUnavailable(f"native file manager unavailable: {detail}")
