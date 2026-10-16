"""Isolated credential-transport acceptance; never uses desktop keys."""

import base64
import hashlib
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from uuid import uuid4

import pytest

from psycheval.harbor import workbuddy_agent
from psycheval.harbor.workbuddy_bootstrap import (
    BootstrapError,
    _server_process,
    transfer,
)

windows = pytest.mark.skipif(sys.platform != "win32", reason="native Windows pipes")
NODE = shutil.which("node") or "node"


@windows
def test_pinned_server_identity_rejects_exit_and_later_process_birth():
    server = subprocess.Popen(
        [sys.executable, "-I", "-S", "-c", "import time; time.sleep(30)"]
    )
    try:
        with pytest.raises(BootstrapError, match="identity mismatch"):
            with _server_process(server.pid, require_older_server=True):
                pytest.fail("a server born after the helper was accepted")
        with _server_process(server.pid) as check_alive:
            check_alive()
            server.kill()
            server.wait(timeout=5)
            with pytest.raises(BootstrapError, match="identity mismatch"):
                check_alive()
    finally:
        if server.poll() is None:
            server.kill()
        server.wait(timeout=5)


@windows
@pytest.mark.parametrize(
    "trusted,response",
    [
        (True, "valid"),
        (False, "valid"),
        (True, "invalid"),
        (True, "silent"),
        (True, "oversized"),
    ],
)
def test_credential_pipe_checks_server_before_writing(trusted, response):
    pipe = "\\\\.\\pipe\\peval-wb-" + uuid4().hex
    source = r"""
      const net = require('node:net');
      const server = net.createServer(socket => {
        let bytes = 0;
        socket.on('data', chunk => {
          bytes += chunk.length;
          if (process.argv[2] !== 'silent') socket.end(process.argv[2] === 'oversized' ? 'x'.repeat(4097) + '\n' : process.argv[2] === 'invalid' ? '{"ok":false}\n' : '{"ok":true,"policy":"fields"}\n');
        });
        socket.on('close', () => {console.log(bytes); server.close();});
      });
      server.listen(process.argv[1], () => console.log('ready'));
    """
    server = subprocess.Popen(
        [NODE, "-e", source, pipe, response],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    ready = queue.Queue()
    threading.Thread(
        target=lambda: ready.put(server.stdout.readline()), daemon=True
    ).start()
    try:
        assert ready.get(timeout=15).strip() == "ready"
        payload = b'{"bootstrap":{"symmetricKey":{"keyBase64":"FIXTURE_KEY_BYTES"}}}\n'
        if trusted and response == "valid":
            result = subprocess.run(
                [
                    sys.executable,
                    str(
                        Path(workbuddy_agent.__file__).with_name(
                            "workbuddy_bootstrap.py"
                        )
                    ),
                    pipe,
                    str(server.pid),
                    "5",
                ],
                input=payload,
                capture_output=True,
                timeout=10,
            )
            assert result.returncode == 0
            assert result.stdout == b"NATIVE_BOOTSTRAP_ACK_OK\n"
        elif not trusted:
            with pytest.raises(BootstrapError, match="identity mismatch"):
                transfer(pipe, os.getpid(), payload, 5)
        else:
            with pytest.raises(BootstrapError, match="acknowledgement|timed out"):
                transfer(pipe, server.pid, payload, 0.3)
        stdout, stderr = server.communicate(timeout=10)
        assert int(stdout.strip()) == (len(payload) if trusted else 0)
        assert stderr == ""
    finally:
        if server.poll() is None:
            server.kill()
        server.communicate()


@windows
def test_full_bootstrap_keeps_credentials_out_of_logs_and_tool_environment(tmp_path):
    native = tmp_path / "native.cjs"
    native.write_text(
        "process._linkedBinding = () => ({loggerGet: () => JSON.stringify({version:1, atRestSecretKey:'FIXTURE_MASTER_KEY'})});",
        encoding="utf-8",
    )
    cli = tmp_path / "cli.cjs"
    cli.write_text(
        r"""
      const net = require('node:net'), {spawnSync} = require('node:child_process');
      const ready = process.env.CODEBUDDY_SIDECAR_READY_SOCKET;
      const boot = process.env.CODEBUDDY_SIDECAR_CREDENTIAL_BOOTSTRAP_SOCKET;
      const token = process.env.CODEBUDDY_SIDECAR_READY_TOKEN;
      const sessionId = process.env.CODEBUDDY_SIDECAR_READY_SESSION_ID;
      for (const key of Object.keys(process.env)) if (key.startsWith('CODEBUDDY_SIDECAR_')) delete process.env[key];
      const server = net.createServer(socket => {
        let text = '';
        socket.setEncoding('utf8');
        socket.on('data', chunk => {
          text += chunk;
          if (!text.includes('\n')) return;
          const payload = JSON.parse(text);
          require('node:assert/strict').equal(payload.token, token);
          socket.end('{"ok":true,"policy":"fields"}\n');
          server.close();
          const request = net.createConnection(ready, () => request.write(JSON.stringify({id:'fixture-ready', method:'session.ready', params:{protocolVersion:1, token, sessionId, pid:process.pid}})+'\n'));
          request.on('data', () => {
            const child = spawnSync(process.execPath, ['-e', "process.stdout.write(JSON.stringify(Object.keys(process.env).filter(key=>key.startsWith('CODEBUDDY_SIDECAR_')||key.startsWith('PEVAL_WORKBUDDY_BOOTSTRAP_'))))"], {encoding:'utf8', windowsHide:true});
            process.stdout.write(child.stdout);
            request.end();
          });
        });
      });
      server.listen(boot);
    """,
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            NODE,
            "--require",
            str(native),
            str(Path(workbuddy_agent.__file__).with_name("workbuddy_bootstrap.cjs")),
            str(cli),
        ],
        env={
            **os.environ,
            "PEVAL_WORKBUDDY_BOOTSTRAP_PYTHON": sys.executable,
            "PEVAL_WORKBUDDY_BOOTSTRAP_TIMEOUT_MS": "10000",
        },
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr.decode()
    assert result.stdout == b"[]"
    assert b"NATIVE_BOOTSTRAP_ACK_OK" in result.stderr
    for secret in [
        b"FIXTURE_MASTER_KEY",
        hashlib.sha256(b"FIXTURE_MASTER_KEY").digest(),
        hashlib.sha256(b"FIXTURE_MASTER_KEY").hexdigest().encode(),
        base64.b64encode(hashlib.sha256(b"FIXTURE_MASTER_KEY").digest()),
    ]:
        assert secret not in result.stdout + result.stderr


@pytest.mark.parametrize("attack", ["replace", "grow"])
def test_seed_read_checks_the_opened_identity_and_size(tmp_path, monkeypatch, attack):
    source = tmp_path / "seed.json"
    source.write_bytes(b"{}")
    original = workbuddy_agent.open_read_descriptor
    monkeypatch.setattr(workbuddy_agent, "MAX_WORKBUDDY_CONFIG_BYTES", 16)

    def changed(path):
        if attack == "replace":
            replacement = tmp_path / "replacement.json"
            replacement.write_bytes(b'{"private":true}')
            replacement.replace(path)
        else:
            path.write_bytes(b"x" * 17)
        return original(path)

    monkeypatch.setattr(workbuddy_agent, "open_read_descriptor", changed)
    with pytest.raises(ValueError, match="changed|byte limit"):
        workbuddy_agent._read_seed(source)


def test_inspection_model_seed_substitutes_inert_provider_keys(tmp_path):
    path = tmp_path / "models.json"
    path.write_text(
        json.dumps(
            [
                {"id": "a", "name": "A", "apiKey": "PRIVATE_A"},
                {"id": "b", "name": "B", "apiKey": "PRIVATE_B"},
            ]
        ),
        encoding="utf-8",
    )
    content = workbuddy_agent._model_seed(path, None, inspection=True)
    assert [item["id"] for item in json.loads(content)] == ["a", "b"]
    assert b"PRIVATE" not in content
    assert all(
        item["apiKey"] == "peval-inspection-placeholder" for item in json.loads(content)
    )


def test_explicit_seed_limit_remains_independent_of_the_module_default(
    tmp_path, monkeypatch
):
    source = tmp_path / "seed.json"
    source.write_bytes(b"123")
    monkeypatch.setattr(workbuddy_agent, "MAX_WORKBUDDY_CONFIG_BYTES", 1)
    assert workbuddy_agent._read_seed(source, maximum=3) == b"123"
    with pytest.raises(ValueError, match="bounded regular file"):
        workbuddy_agent._read_seed(source)


def test_selected_seed_uses_the_native_custom_model_namespace(tmp_path):
    path = tmp_path / "models.json"
    path.write_text(
        json.dumps(
            [{"id": "a", "apiKey": "PRIVATE_A"}, {"id": "b", "apiKey": "PRIVATE_B"}]
        ),
        encoding="utf-8",
    )
    content = workbuddy_agent._model_seed(path, "custom-local:a", inspection=False)
    assert [item["id"] for item in json.loads(content)] == ["a"]
    assert b"PRIVATE_A" in content and b"PRIVATE_B" not in content
    assert json.loads(workbuddy_agent._model_seed(path, "a", inspection=False)) == []
