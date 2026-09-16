from __future__ import annotations

import asyncio
import socket
import sys

SERVE_LOOP_FACTORY = "psycheval.serve.event_loop:create_serve_loop"


def create_serve_loop() -> asyncio.AbstractEventLoop:
    if sys.platform == "win32":
        return _WindowsServeLoop()
    return asyncio.new_event_loop()


class _ServeSocket(socket.socket):
    def shutdown(self, how: int) -> None:
        try:
            super().shutdown(how)
        except ConnectionResetError as exc:
            if getattr(exc, "winerror", None) != 10054:
                raise


if sys.platform == "win32":

    class _WindowsServeLoop(asyncio.ProactorEventLoop):
        def _make_socket_transport(
            self, sock, protocol, waiter=None, extra=None, server=None
        ):
            # Proactor closes and detaches the transport only after shutdown().
            # Adopt the socket without changing stdlib transports or subprocess pipes.
            wrapped = _ServeSocket(
                sock.family, sock.type, sock.proto, fileno=sock.fileno()
            )
            sock.detach()
            wrapped.setblocking(False)
            return super()._make_socket_transport(
                wrapped, protocol, waiter, extra, server
            )
