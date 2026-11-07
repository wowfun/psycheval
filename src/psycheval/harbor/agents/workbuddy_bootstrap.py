"""Transfer native bootstrap bytes only to the exact Windows CLI process.

Executed as a standalone, owned helper; credentials arrive on private stdin.
"""

from __future__ import annotations

import ctypes
import json
import math
import sys
import time
from contextlib import contextmanager
from ctypes import wintypes

MAX_BOOTSTRAP_BYTES = 4096


class Overlapped(ctypes.Structure):
    _fields_ = [
        ("internal", ctypes.c_size_t),
        ("internal_high", ctypes.c_size_t),
        ("offset", wintypes.DWORD),
        ("offset_high", wintypes.DWORD),
        ("event", wintypes.HANDLE),
    ]


class BootstrapError(RuntimeError):
    """Categorical errors never contain native credential payloads."""


@contextmanager
def _server_process(expected_pid, *, require_older_server=False):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        *[ctypes.POINTER(wintypes.FILETIME)] * 4,
    ]

    def birth(handle):
        values = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(
            handle, *(ctypes.byref(value) for value in values)
        ):
            raise BootstrapError("bootstrap server identity unavailable")
        return (values[0].dwHighDateTime << 32) | values[0].dwLowDateTime

    handle = kernel.OpenProcess(0x1000 | 0x100000, False, expected_pid)
    if not handle:
        raise BootstrapError("bootstrap server identity unavailable")
    try:
        if require_older_server and birth(handle) > birth(kernel.GetCurrentProcess()):
            raise BootstrapError("bootstrap server identity mismatch")

        def check_alive():
            if kernel.WaitForSingleObject(handle, 0) != 258:
                raise BootstrapError("bootstrap server identity mismatch")

        check_alive()
        yield check_alive
    finally:
        kernel.CloseHandle(handle)


def transfer(pipe, expected_pid, payload, timeout, *, require_older_server=False):
    with _server_process(
        expected_pid, require_older_server=require_older_server
    ) as check_alive:
        _transfer(pipe, expected_pid, payload, timeout, check_alive)


def _transfer(pipe, expected_pid, payload, timeout, check_alive):
    if (
        not pipe.startswith("\\\\.\\pipe\\peval-wb-")
        or len(pipe) > 240
        or expected_pid <= 0
        or not math.isfinite(timeout)
        or timeout <= 0
        or len(payload) > MAX_BOOTSTRAP_BYTES
    ):
        raise BootstrapError("invalid bootstrap configuration")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    for name, args, result in (
        (
            "CreateFileW",
            [
                wintypes.LPCWSTR,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.LPVOID,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.HANDLE,
            ],
            wintypes.HANDLE,
        ),
        (
            "GetNamedPipeServerProcessId",
            [wintypes.HANDLE, ctypes.POINTER(wintypes.ULONG)],
            wintypes.BOOL,
        ),
        (
            "WriteFile",
            [
                wintypes.HANDLE,
                wintypes.LPCVOID,
                wintypes.DWORD,
                ctypes.POINTER(wintypes.DWORD),
                wintypes.LPVOID,
            ],
            wintypes.BOOL,
        ),
        (
            "ReadFile",
            [
                wintypes.HANDLE,
                wintypes.LPVOID,
                wintypes.DWORD,
                ctypes.POINTER(wintypes.DWORD),
                wintypes.LPVOID,
            ],
            wintypes.BOOL,
        ),
        (
            "CreateEventW",
            [wintypes.LPVOID, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR],
            wintypes.HANDLE,
        ),
        ("WaitForSingleObject", [wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
        (
            "GetOverlappedResult",
            [
                wintypes.HANDLE,
                wintypes.LPVOID,
                ctypes.POINTER(wintypes.DWORD),
                wintypes.BOOL,
            ],
            wintypes.BOOL,
        ),
        ("CancelIoEx", [wintypes.HANDLE, wintypes.LPVOID], wintypes.BOOL),
        ("CloseHandle", [wintypes.HANDLE], wintypes.BOOL),
    ):
        function = getattr(kernel, name)
        function.argtypes, function.restype = args, result
    deadline = time.monotonic() + timeout
    while True:
        # Identification-only SQOS prevents a pipe server impersonating this helper.
        handle = kernel.CreateFileW(pipe, 0xC0000000, 0, None, 3, 0x40110000, None)
        if handle != wintypes.HANDLE(-1).value:
            break
        if ctypes.get_last_error() not in {2, 231} or time.monotonic() >= deadline:
            raise BootstrapError("bootstrap pipe unavailable")
        time.sleep(min(0.05, max(0, deadline - time.monotonic())))
    try:

        def io(operation, buffer, size):
            event = kernel.CreateEventW(None, True, False, None)
            if not event:
                raise BootstrapError("bootstrap event unavailable")
            pending, count = Overlapped(event=event), wintypes.DWORD()
            try:
                if not operation(
                    handle, buffer, size, ctypes.byref(count), ctypes.byref(pending)
                ):
                    if ctypes.get_last_error() != 997:
                        raise BootstrapError("bootstrap pipe IO failed")
                    remaining = max(0, deadline - time.monotonic())
                    if (
                        kernel.WaitForSingleObject(
                            event, min(math.ceil(remaining * 1000), 0xFFFFFFFE)
                        )
                        != 0
                    ):
                        kernel.CancelIoEx(handle, ctypes.byref(pending))
                        kernel.GetOverlappedResult(
                            handle, ctypes.byref(pending), ctypes.byref(count), True
                        )
                        raise BootstrapError("bootstrap pipe IO timed out")
                    if not kernel.GetOverlappedResult(
                        handle, ctypes.byref(pending), ctypes.byref(count), False
                    ):
                        raise BootstrapError("bootstrap pipe IO failed")
                return count.value
            finally:
                kernel.CloseHandle(event)

        pid = wintypes.ULONG()
        if (
            not kernel.GetNamedPipeServerProcessId(handle, ctypes.byref(pid))
            or pid.value != expected_pid
        ):
            raise BootstrapError("bootstrap server identity mismatch")
        check_alive()
        if io(kernel.WriteFile, payload, len(payload)) != len(payload):
            raise BootstrapError("bootstrap transfer failed")
        received = bytearray()
        while time.monotonic() < deadline:
            buffer = ctypes.create_string_buffer(MAX_BOOTSTRAP_BYTES + 1)
            count = io(kernel.ReadFile, buffer, len(buffer))
            if not count:
                raise BootstrapError("bootstrap pipe closed")
            received.extend(buffer.raw[:count])
            if len(received) > MAX_BOOTSTRAP_BYTES:
                raise BootstrapError("bootstrap acknowledgement exceeded its limit")
            if b"\n" in received:
                try:
                    ack = json.loads(received.split(b"\n", 1)[0].decode("utf-8"))
                except (ValueError, UnicodeError):
                    raise BootstrapError("invalid bootstrap acknowledgement") from None
                if (
                    not isinstance(ack, dict)
                    or ack.get("ok") is not True
                    or ack.get("policy") != "fields"
                ):
                    raise BootstrapError("invalid bootstrap acknowledgement")
                return
        raise BootstrapError("bootstrap acknowledgement timed out")
    finally:
        kernel.CloseHandle(handle)


def main():
    try:
        payload = sys.stdin.buffer.readline(MAX_BOOTSTRAP_BYTES + 1)
        transfer(
            sys.argv[1],
            int(sys.argv[2]),
            payload,
            float(sys.argv[3]),
            require_older_server=True,
        )
    except Exception:
        sys.stderr.write("NATIVE_BOOTSTRAP_FAILED\n")
        return 125
    sys.stdout.buffer.write(b"NATIVE_BOOTSTRAP_ACK_OK\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
