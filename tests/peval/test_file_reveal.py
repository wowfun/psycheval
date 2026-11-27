from __future__ import annotations

import http.client
import json
import subprocess
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from psycheval.config import HarborDataset, HarborMount, ToolConfig
from psycheval.serve import (
    FileRevealUnavailable,
    ServeAccess,
    ServeRuntime,
    reveal_in_file_manager,
)
from psycheval.serve.api import create_app
from psycheval.serve.api_access import is_localhost_request
from psycheval.state import CatalogQuery, open_workspace_state
from psycheval.state.verification_files import verification_file_tree
from tests.peval.asgi_server import LocalHTTPServer, make_handler
from tests.peval.test_harbor_evidence import write_evidence_trial, write_task
from tests.peval.test_workbuddy_datasets import _write_workbuddy_bundle


def _make_request(
    *,
    client_host: str | None = "127.0.0.1",
    host_header: str | None = "127.0.0.1:8765",
    extra_headers: dict[str, str] | None = None,
) -> Request:
    raw_headers: list[tuple[bytes, bytes]] = []
    if host_header is not None:
        raw_headers.append((b"host", host_header.encode("latin-1")))
    for name, value in (extra_headers or {}).items():
        raw_headers.append((name.lower().encode("latin-1"), value.encode("latin-1")))
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": raw_headers,
        "client": (client_host, 54321) if client_host is not None else None,
        "server": ("127.0.0.1", 8765),
    }
    return Request(scope)


@pytest.mark.parametrize(
    ("client_host", "host_header", "extra_headers", "expected"),
    [
        ("127.0.0.1", "127.0.0.1:8765", None, True),
        ("127.0.0.2", "localhost:8765", None, True),
        ("::1", "[::1]:8765", None, True),
        ("::1", "localhost.", None, True),
        ("::ffff:127.0.0.1", "127.0.0.1:8765", None, True),
        ("192.168.1.20", "192.168.1.10:8765", None, False),
        ("192.168.1.20", "localhost:8765", None, False),
        ("127.0.0.1", "192.168.1.10:8765", None, False),
        ("127.0.0.1", "eval.internal:8765", None, False),
        ("127.0.0.1", "user@localhost:8765", None, False),
        ("127.0.0.1", None, None, False),
        (None, "localhost:8765", None, False),
        ("testclient", "localhost:8765", None, False),
        ("127.0.0.1", "localhost:8765", {"X-Forwarded-For": "203.0.113.10"}, False),
        ("127.0.0.1", "localhost:8765", {"Forwarded": "for=203.0.113.10"}, False),
        ("127.0.0.1", "localhost:8765", {"X-Forwarded-Host": "eval.example"}, False),
        ("127.0.0.1", "localhost:8765", {"X-Real-IP": "203.0.113.10"}, False),
    ],
)
def test_is_localhost_request_matrix(
    client_host: str | None,
    host_header: str | None,
    extra_headers: dict[str, str] | None,
    expected: bool,
) -> None:
    request = _make_request(
        client_host=client_host,
        host_header=host_header,
        extra_headers=extra_headers,
    )
    assert is_localhost_request(request) is expected


def test_reveal_in_file_manager_validates_target_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="absolute"):
        reveal_in_file_manager(Path("relative.txt"))
    with pytest.raises(ValueError, match="unavailable"):
        reveal_in_file_manager(tmp_path / "missing.txt")
    with pytest.raises(ValueError, match="regular file"):
        reveal_in_file_manager(tmp_path)
    real = tmp_path / "real.txt"
    real.write_text("ok", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(real)
    except OSError:
        return
    with pytest.raises(ValueError, match="regular file"):
        reveal_in_file_manager(link)


@pytest.mark.parametrize("init_hr", [0, 0x80010106])
def test_reveal_windows_uses_shell_api_and_handles_com_init(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, init_hr: int
) -> None:
    target = tmp_path / "中文, space file.txt"
    target.write_text("ok", encoding="utf-8")
    ole32 = MagicMock()
    shell32 = MagicMock()
    ole32.CoInitializeEx.return_value = init_hr
    shell32.ILCreateFromPathW.return_value = 0x123456789ABCDEF
    shell32.SHOpenFolderAndSelectItems.return_value = 0
    windll = SimpleNamespace(ole32=ole32, shell32=shell32)

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr("ctypes.windll", windll, raising=False)
    monkeypatch.setattr("psycheval.serve.file_reveal._WINDOWS_SHELL_PROTOTYPES", None)

    reveal_in_file_manager(target)

    shell32.ILCreateFromPathW.assert_called_once_with(str(target))
    shell32.SHOpenFolderAndSelectItems.assert_called_once_with(
        0x123456789ABCDEF, 0, None, 0
    )
    shell32.ILFree.assert_called_once_with(0x123456789ABCDEF)
    if init_hr == 0:
        ole32.CoUninitialize.assert_called_once_with()
    else:
        ole32.CoUninitialize.assert_not_called()


def test_reveal_windows_falls_back_to_explorer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "my report.txt"
    target.write_text("ok", encoding="utf-8")
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        "psycheval.serve.file_reveal._reveal_windows_shell_api",
        MagicMock(side_effect=OSError("shell api failed")),
    )
    monkeypatch.setattr(
        "shutil.which",
        lambda name: "C:\\Windows\\explorer.exe" if name == "explorer.exe" else None,
    )
    popen = MagicMock()
    monkeypatch.setattr("subprocess.Popen", popen)

    reveal_in_file_manager(target)
    popen.assert_called_once_with(
        ["C:\\Windows\\explorer.exe", "/select,", str(target)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Programming errors are not swallowed by the explorer.exe fallback.
    monkeypatch.setattr(
        "psycheval.serve.file_reveal._reveal_windows_shell_api",
        MagicMock(side_effect=RuntimeError("unexpected bug")),
    )
    with pytest.raises(RuntimeError, match="unexpected bug"):
        reveal_in_file_manager(target)


def test_reveal_macos_runs_open_dash_r(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "score.json"
    target.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(
        "shutil.which", lambda name: "/usr/bin/open" if name == "open" else None
    )
    run = MagicMock(return_value=subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr("subprocess.run", run)

    reveal_in_file_manager(target)
    run.assert_called_once_with(
        ["/usr/bin/open", "-R", str(target)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    run.return_value = subprocess.CompletedProcess(
        [], 1, "", f"Finder failed for {target}"
    )
    with pytest.raises(FileRevealUnavailable, match="status 1") as exc_info:
        reveal_in_file_manager(target)
    assert str(target) not in str(exc_info.value)

    # Timeout errors must not disclose absolute paths.
    run.side_effect = subprocess.TimeoutExpired(
        cmd=["/usr/bin/open", "-R", str(target)], timeout=10
    )
    with pytest.raises(FileRevealUnavailable, match="timed out") as exc_info:
        reveal_in_file_manager(target)
    assert str(target) not in str(exc_info.value)
    assert str(tmp_path) not in str(exc_info.value)


def test_reveal_linux_wsl_dbus_xdg_and_headless(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "中文 report.txt"
    target.write_text("ok", encoding="utf-8")
    monkeypatch.setattr(sys, "platform", "linux")

    # 1. WSL uses wslpath + explorer.exe.
    monkeypatch.setattr("psycheval.serve.file_reveal._is_wsl", lambda: True)
    monkeypatch.setattr(
        "shutil.which",
        lambda name: {
            "wslpath": "/usr/bin/wslpath",
            "explorer.exe": "/mnt/c/Windows/explorer.exe",
        }.get(name),
    )
    monkeypatch.setattr(
        "subprocess.run",
        MagicMock(
            return_value=subprocess.CompletedProcess(
                [], 0, "D:\\temp\\report.txt\n", ""
            )
        ),
    )
    popen = MagicMock()
    monkeypatch.setattr("subprocess.Popen", popen)
    reveal_in_file_manager(target)
    popen.assert_called_once_with(
        ["/mnt/c/Windows/explorer.exe", "/select,", "D:\\temp\\report.txt"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # 2. Native Linux headless fails with FileRevealUnavailable.
    monkeypatch.setattr("psycheval.serve.file_reveal._is_wsl", lambda: False)
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    with pytest.raises(FileRevealUnavailable, match="no desktop display session"):
        reveal_in_file_manager(target)

    # 3. Native Linux with DISPLAY prefers gdbus org.freedesktop.FileManager1.ShowItems.
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setattr(
        "shutil.which", lambda name: "/usr/bin/gdbus" if name == "gdbus" else None
    )
    run = MagicMock(return_value=subprocess.CompletedProcess([], 0, "()\n", ""))
    monkeypatch.setattr("subprocess.run", run)
    reveal_in_file_manager(target)
    args = run.call_args.args[0]
    assert args[0] == "/usr/bin/gdbus"
    assert "org.freedesktop.FileManager1.ShowItems" in args
    assert f"['{target.as_uri()}']" in args

    # 4. Native Linux falls back to xdg-open on parent directory when D-Bus fails.
    monkeypatch.setattr(
        "shutil.which",
        lambda name: {
            "dbus-send": "/usr/bin/dbus-send",
            "xdg-open": "/usr/bin/xdg-open",
        }.get(name),
    )
    monkeypatch.setattr(
        "subprocess.run",
        MagicMock(return_value=subprocess.CompletedProcess([], 1, "", "no service")),
    )
    popen = MagicMock()
    monkeypatch.setattr("subprocess.Popen", popen)
    reveal_in_file_manager(target)
    popen.assert_called_once_with(
        ["/usr/bin/xdg-open", str(target.parent)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _setup_workspace(tmp_path: Path):
    native = tmp_path / "native"
    write_task(native / "alpha", "org/alpha")
    (native / "alpha/environment/data").mkdir(parents=True, exist_ok=True)
    (native / "alpha/environment/data/raw.bin").write_bytes(b"\x00\x01\xff")
    bundle = _write_workbuddy_bundle(tmp_path / "office")

    trial = tmp_path / "jobs/job-one/trial-one"
    write_evidence_trial(trial)
    (trial / "verifier").mkdir(parents=True, exist_ok=True)
    (trial / "verifier/score.json").write_text('{"reward": 1}', encoding="utf-8")
    (trial / "artifacts").mkdir(parents=True, exist_ok=True)
    (trial / "artifacts/chart.png").write_bytes(b"\x89PNG\r\n")
    (trial / "artifacts/archive.bin").write_bytes(b"\xff\xfe")

    (tmp_path / "peval.toml").write_text(
        'locale = "en"\n'
        f'[[harbor.datasets]]\nid = "native"\npath = {json.dumps(str(native))}\n'
        f'[[harbor.datasets]]\nid = "office"\npath = {json.dumps(str(bundle))}\nformat = "workbuddy.v1"\n'
        f'[[harbor.mounts]]\nid = "jobs"\npath = {json.dumps(str(tmp_path / "jobs"))}\ndataset_ids = ["office"]\n',
        encoding="utf-8",
    )
    store = open_workspace_state(str(tmp_path))
    config = ToolConfig(
        workspace_root=str(tmp_path),
        locale="en",
        harbor_datasets=(
            HarborDataset(id="native", path=str(native)),
            HarborDataset(id="office", path=str(bundle), format="workbuddy.v1"),
        ),
        harbor_mounts=(
            HarborMount(
                id="jobs", path=str(tmp_path / "jobs"), dataset_ids=("office",)
            ),
        ),
    )
    runtime = ServeRuntime(store, config)
    source_key = runtime.catalog.query(CatalogQuery()).items[0].source_key
    tree = verification_file_tree(trial, tmp_path / "jobs")
    file_ids = {item["path"]: item["id"] for item in tree if item["kind"] == "file"}
    return store, runtime, source_key, file_ids, native, bundle, trial


def test_http_reveal_routes_enforce_localhost_admin_and_containment(
    tmp_path: Path,
) -> None:
    store, runtime, source_key, file_ids, native, bundle, trial = _setup_workspace(
        tmp_path
    )
    access = ServeAccess("secret-pass")
    server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime, access=access))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"

    def req(
        method: str,
        path: str,
        payload: dict | None = None,
        *,
        cookie: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, bytes]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        req_headers = {"Origin": origin}
        if body is not None:
            req_headers["Content-Type"] = "application/json"
        if cookie:
            req_headers["Cookie"] = cookie
        req_headers.update(headers or {})
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        conn.request(method, path, body=body, headers=req_headers)
        resp = conn.getresponse()
        data = resp.read()
        resp_headers = {k.lower(): v for k, v in resp.getheaders()}
        conn.close()
        return resp.status, (
            data if method != "LOGIN" else resp_headers.get("set-cookie", "").encode()
        )

    try:
        # Guest receives local_client=False in HTML and 403 on reveal routes.
        status, guest_html = req("GET", "/")
        assert status == 200
        assert '"local_client": false' in guest_html.decode("utf-8")

        ver_url = f"/api/verification-files/{source_key}/{file_ids['verifier/score.json']}/reveal"
        task_url = "/api/harbor/datasets/native/tasks/alpha/reveal"
        assert req("POST", ver_url, {})[0] == 403
        assert req("POST", task_url, {"path": "instruction.md"})[0] == 403

        # Login as admin on localhost.
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        conn.request(
            "POST",
            "/api/session",
            body=json.dumps({"password": "secret-pass"}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Origin": origin},
        )
        login_resp = conn.getresponse()
        login_resp.read()
        cookie = login_resp.getheader("Set-Cookie").split(";", 1)[0]
        conn.close()

        # Admin on localhost gets local_client=True; forwarded request gets local_client=False.
        status, admin_html = req("GET", "/", cookie=cookie)
        assert status == 200
        assert '"local_client": true' in admin_html.decode("utf-8")
        status, proxied_html = req(
            "GET", "/", cookie=cookie, headers={"X-Forwarded-For": "203.0.113.9"}
        )
        assert status == 200
        assert '"local_client": false' in proxied_html.decode("utf-8")

        revealed: list[Path] = []
        with patch(
            "psycheval.serve.file_reveal.reveal_in_file_manager",
            side_effect=revealed.append,
        ):
            # Trial Verification: text, image, and metadata-only binary all succeed.
            for rel in (
                "verifier/score.json",
                "artifacts/chart.png",
                "artifacts/archive.bin",
            ):
                status, body = req(
                    "POST",
                    f"/api/verification-files/{source_key}/{file_ids[rel]}/reveal",
                    {},
                    cookie=cookie,
                )
                assert status == 200, body
                assert json.loads(body) == {"revealed": True}
                assert str(trial) not in body.decode("utf-8")
            assert revealed == [
                (trial / "verifier/score.json").resolve(),
                (trial / "artifacts/chart.png").resolve(),
                (trial / "artifacts/archive.bin").resolve(),
            ]

            # Native Harbor task (text + binary) and read-only WorkBuddy task succeed.
            revealed.clear()
            for url, rel, expected_path in (
                (
                    task_url,
                    "instruction.md",
                    (native / "alpha/instruction.md").resolve(),
                ),
                (
                    task_url,
                    "environment/data/raw.bin",
                    (native / "alpha/environment/data/raw.bin").resolve(),
                ),
                (
                    "/api/harbor/datasets/office/tasks/office-one/reveal",
                    "instruction.md",
                    (bundle / "tasks/office-one/instruction.md").resolve(),
                ),
            ):
                status, body = req("POST", url, {"path": rel}, cookie=cookie)
                assert status == 200, body
                assert json.loads(body) == {"revealed": True}
                assert revealed[-1] == expected_path

            # Reject forwarding headers, non-local Host, cross-origin, and non-JSON.
            assert (
                req(
                    "POST",
                    task_url,
                    {"path": "instruction.md"},
                    cookie=cookie,
                    headers={"X-Forwarded-For": "198.51.100.7"},
                )[0]
                == 403
            )
            assert (
                req(
                    "POST",
                    task_url,
                    {"path": "instruction.md"},
                    cookie=cookie,
                    headers={
                        "Host": "192.168.1.50:8765",
                        "Origin": "http://192.168.1.50:8765",
                    },
                )[0]
                == 403
            )
            assert (
                req(
                    "POST",
                    task_url,
                    {"path": "instruction.md"},
                    cookie=cookie,
                    headers={"Origin": "http://evil.example"},
                )[0]
                == 403
            )
            assert (
                req(
                    "POST",
                    task_url,
                    {"path": "instruction.md"},
                    cookie=cookie,
                    headers={"Content-Type": "text/plain"},
                )[0]
                == 415
            )

            # Reject traversal, directory target, missing file, and unknown file_id.
            assert (
                req("POST", task_url, {"path": "../peval.toml"}, cookie=cookie)[0]
                == 400
            )
            assert (
                req("POST", task_url, {"path": "environment"}, cookie=cookie)[0] == 400
            )
            assert (
                req("POST", task_url, {"path": "does-not-exist.txt"}, cookie=cookie)[0]
                == 404
            )
            assert (
                req(
                    "POST",
                    f"/api/verification-files/{source_key}/{'0' * 24}/reveal",
                    {},
                    cookie=cookie,
                )[0]
                == 404
            )
            assert (
                req(
                    "POST",
                    f"/api/verification-files/{source_key}/not-hex/reveal",
                    {},
                    cookie=cookie,
                )[0]
                == 404
            )

        # Headless / unavailable OS backend maps to 503.
        with patch(
            "psycheval.serve.file_reveal.reveal_in_file_manager",
            side_effect=FileRevealUnavailable("no desktop display session"),
        ):
            assert req("POST", ver_url, {}, cookie=cookie)[0] == 503
            assert (
                req("POST", task_url, {"path": "instruction.md"}, cookie=cookie)[0]
                == 503
            )

        # Remote peer IP is rejected even with forged Host: localhost.
        app = create_app(runtime, ServeAccess(None))
        remote_client = TestClient(app, client=("192.168.1.20", 40000))
        remote_resp = remote_client.post(
            task_url,
            json={"path": "instruction.md"},
            headers={"Host": "localhost:8765", "Origin": "http://localhost:8765"},
        )
        assert remote_resp.status_code == 403
        remote_html = remote_client.get("/", headers={"Host": "localhost:8765"})
        assert remote_html.status_code == 200
        assert '"local_client": false' in remote_html.text
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        runtime.close()
        store.close()
