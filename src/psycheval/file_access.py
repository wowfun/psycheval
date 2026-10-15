"""Non-following application file handles; callers own containment and limits."""

import errno
import math
import os
import stat
import threading
import time
from contextlib import contextmanager
from functools import cache
from weakref import WeakValueDictionary

_LEASE_LOCKS = WeakValueDictionary()
_LEASE_REGISTRY_LOCK = threading.Lock()
DEFAULT_LEASE_TIMEOUT_SEC = 30.0


class FileLeaseTimeout(TimeoutError):
    """A writer did not acquire its lease before the contention deadline."""


def _open_lease_descriptor(path):
    if os.name == "nt":
        return _windows_descriptor(path, writable=True, create=True)
    return os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)


@contextmanager
def blocking_file_lease(
    path, *, label, timeout_sec=DEFAULT_LEASE_TIMEOUT_SEC, blocking=True
):
    """Acquire a dedicated coordination file, never an application content file.

    Windows byte-range locking initializes an empty file with ``b"0"``.
    Bound acquisition waiting; retain ownership until the body and unlock finish.
    """
    if (
        isinstance(timeout_sec, bool)
        or not isinstance(timeout_sec, (int, float))
        or not math.isfinite(timeout_sec)
        or timeout_sec <= 0
    ):
        raise ValueError("File lease timeout must be finite and positive")
    deadline = time.monotonic() + timeout_sec

    def timed_out():
        return FileLeaseTimeout(
            f"{label} acquisition timed out; another writer is busy"
        )

    identity = os.path.normcase(os.path.abspath(path))
    with _LEASE_REGISTRY_LOCK:
        lock = _LEASE_LOCKS.get(identity)
        if lock is None:
            lock = threading.Lock()
            _LEASE_LOCKS[identity] = lock
    acquired = (
        lock.acquire(timeout=max(0, deadline - time.monotonic()))
        if blocking
        else lock.acquire(blocking=False)
    )
    if not acquired:
        raise timed_out()
    try:
        if path.is_symlink():
            raise ValueError(f"{label} must not be a symlink: {path}")
        try:
            before = path.stat(follow_symlinks=False)
        except FileNotFoundError:
            before = None
        descriptor = _open_lease_descriptor(path)
        with os.fdopen(descriptor, "r+b") as handle:
            opened = os.fstat(handle.fileno())
            current = path.stat(follow_symlinks=False)
            if (
                not stat.S_ISREG(opened.st_mode)
                or getattr(opened, "st_file_attributes", 0)
                & stat.FILE_ATTRIBUTE_REPARSE_POINT
            ):
                raise ValueError(f"{label} must be a regular file: {path}")
            if (
                not stat.S_ISREG(current.st_mode)
                or not os.path.samestat(current, opened)
                or before is not None
                and not os.path.samestat(before, opened)
            ):
                raise ValueError(f"{label} changed while opening: {path}")
            try:
                import fcntl
            except ImportError:
                import msvcrt

                if os.fstat(handle.fileno()).st_size == 0:
                    handle.write(b"0")
                    handle.flush()
                    os.fsync(handle.fileno())

                def acquire():
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)

                def unlock():
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:

                def acquire():
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

                def unlock():
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

            while True:
                if blocking and time.monotonic() >= deadline:
                    raise timed_out()
                try:
                    acquire()
                    break
                except OSError as exc:
                    if exc.errno not in {
                        errno.EACCES,
                        errno.EAGAIN,
                        errno.EDEADLK,
                    } and getattr(exc, "winerror", None) not in {32, 33, 36}:
                        raise
                    if not blocking:
                        raise timed_out() from exc
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))

            primary = None
            try:
                yield
            except BaseException as exc:
                primary = exc
                raise
            finally:
                try:
                    unlock()
                except OSError as exc:
                    if primary is None:
                        raise
                    primary.add_note(f"{label} unlock failed: {exc}")
    finally:
        lock.release()


def open_read_descriptor(path):
    if os.name == "nt":
        return _windows_reader(path)
    return os.open(
        path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    )


def _windows_reader(path):
    return _windows_descriptor(path)


@cache
def _windows_file_api():
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    return kernel


def _windows_descriptor(path, *, writable=False, create=False):
    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel = _windows_file_api()
    # GENERIC_READ, SHARE_READ|WRITE|DELETE, OPEN_EXISTING, OPEN_REPARSE_POINT.
    desired = 0xC0000000 if writable else 0x80000000
    handle = kernel.CreateFileW(
        str(path), desired, 7, None, 4 if create else 3, 0x00200000, None
    )
    if handle == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return msvcrt.open_osfhandle(
            handle, (os.O_RDWR if writable else os.O_RDONLY) | os.O_BINARY
        )
    except BaseException:
        kernel.CloseHandle(handle)
        raise
