from __future__ import annotations

import asyncio
import socket
import sys
from unittest.mock import patch

import pytest
import uvicorn

from psycheval.serve.event_loop import SERVE_LOOP_FACTORY, _ServeSocket


def serve_loop():
    factory = uvicorn.Config(None, loop=SERVE_LOOP_FACTORY).get_loop_factory()
    return factory()


def test_serve_loop_supports_subprocess_pipes() -> None:
    async def exercise():
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(b"serve-pipe-probe"), timeout=10
        )
        assert process.returncode == 0
        assert stdout == b"serve-pipe-probe"
        assert stderr == b""

    loop = serve_loop()
    try:
        loop.run_until_complete(exercise())
    finally:
        loop.close()


@pytest.mark.parametrize(
    "error",
    [
        OSError(5, "unrelated socket failure"),
        ConnectionResetError(10054, "reset without Windows error code"),
    ],
)
def test_shutdown_does_not_hide_other_socket_errors(error: OSError) -> None:
    with _ServeSocket() as sock:
        with patch.object(socket.socket, "shutdown", side_effect=error):
            with pytest.raises(type(error)) as raised:
                sock.shutdown(socket.SHUT_RDWR)
        assert raised.value is error


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Proactor transport")
@pytest.mark.parametrize("protocol_fails", [False, True])
def test_peer_reset_during_shutdown_finishes_transport_cleanup(protocol_fails) -> None:
    async def exercise():
        loop = asyncio.get_running_loop()
        assert isinstance(loop, asyncio.ProactorEventLoop)
        errors = []
        loop.set_exception_handler(lambda _loop, context: errors.append(context))
        connected = loop.create_future()
        disconnected = []
        protocol_error = ConnectionResetError(
            10054, "protocol callback failed", None, 10054
        )

        class Protocol(asyncio.Protocol):
            def connection_made(self, transport):
                connected.set_result(transport)

            def connection_lost(self, exc):
                disconnected.append(exc)
                if protocol_fails:
                    raise protocol_error

        server = await loop.create_server(Protocol, "127.0.0.1", 0)
        client = socket.socket()
        client.setblocking(False)
        transport = None
        try:
            await loop.sock_connect(client, server.sockets[0].getsockname())
            transport = await asyncio.wait_for(connected, timeout=5)
            accepted = transport.get_extra_info("socket")
            # Reproduce the reported kernel error at the real asyncio shutdown call.
            with patch.object(
                socket.socket,
                "shutdown",
                side_effect=ConnectionResetError(10054, "peer reset", None, 10054),
            ):
                transport.close()
                await asyncio.sleep(0)
                await asyncio.sleep(0)
            if protocol_fails:
                assert len(errors) == 1
                assert errors[0]["exception"] is protocol_error
            else:
                assert not errors, [str(context.get("exception")) for context in errors]
            assert accepted.fileno() == -1
            assert disconnected == [None]
            server.close()
            await asyncio.wait_for(server.wait_closed(), timeout=5)
        finally:
            client.close()
            if transport is not None and transport._sock is not None:
                transport._sock.close()
            server.close()

    loop = serve_loop()
    try:
        loop.run_until_complete(exercise())
    finally:
        loop.close()
