import time
from pathlib import PureWindowsPath
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from psycheval.config import ToolConfig
from psycheval.serve.api_models import (
    ConfigPatchRequest,
    DatasetCreateRequest,
    DatasetPatchRequest,
    MountCreateRequest,
    MountPatchRequest,
    ReportImportRequest,
    SourceImportRequest,
)
from psycheval.serve.errors import HttpError
from psycheval.serve.path_inputs import required_path_token
from psycheval.serve.payloads import source_path_values
from psycheval.serve.runtime import ServeRuntime
from psycheval.serve.sources import add_source_payload, path_batch_lines
from psycheval.state import open_workspace_state
from tests.peval.asgi_server import make_handler


@pytest.mark.parametrize(
    "control",
    [
        "\x00",
        "\x0b",
        "\x0c",
        "\x1b",
        "\x1c",
        "\x1d",
        "\x1e",
        "\x7f",
        "\x85",
        "\u2028",
        "\u2029",
    ],
)
@pytest.mark.parametrize("key", ["path", "db"])
@pytest.mark.parametrize("position", ["inside", "prefix", "suffix"])
def test_import_path_tokens_reject_control_characters(tmp_path, control, key, position):
    store = SimpleNamespace(paths=SimpleNamespace(root=tmp_path))
    raw = {
        "inside": f'"a{control}b"',
        "prefix": control + "a",
        "suffix": "a" + control,
    }[position]
    with pytest.raises(HttpError, match="control characters"):
        source_path_values(store, {key: raw}, key)


def test_batch_selection_ignores_quoted_empty_lines():
    request = SourceImportRequest(path='""\n"data.jsonl"\n\' \'', session_id="one")
    assert path_batch_lines(request.payload()) == ['"data.jsonl"']


def test_source_batches_only_accept_lf_and_crlf_separators():
    assert path_batch_lines({"path": '"one"\r\n"two"\n'}) == ['"one"', '"two"']
    for control in ("\v", "\f", "\x1e", "\x85", "\u2028", "\u2029", "\r"):
        with pytest.raises(ValidationError, match="control characters"):
            SourceImportRequest(path=f'"one{control}two"')


def test_report_import_normalizes_a_filesystem_path():
    assert ReportImportRequest(path=' "D:\\reports\\my report.md" ').path == (
        r"D:\reports\my report.md"
    )


@pytest.mark.parametrize(
    "path",
    [
        r"D:\Projects\含 空格\datasets",
        r"\\server\share\data sets",
        "relative path",
        "~/data",
    ],
)
@pytest.mark.parametrize("quote", ['"', "'", ""])
def test_browser_paths_are_literal_tokens_before_resolution(path, quote):
    raw = f"  {quote}{path}{quote}  "
    assert DatasetCreateRequest(source="existing", path=raw).path == path
    assert DatasetPatchRequest(new_id="data", path=raw).path == path
    assert MountCreateRequest(path=raw).path == path
    assert MountPatchRequest(new_id="jobs", path=raw).path == path
    assert ConfigPatchRequest(adapter_defaults={"opencode": raw}).adapter_defaults == {
        "opencode": path
    }
    if path.startswith(("D:", "\\\\")):
        assert PureWindowsPath(required_path_token(raw)).is_absolute()


@pytest.mark.parametrize("value", ["", '""', "''", '"  "', "a\x00b", '"a\nb"'])
def test_empty_or_control_character_paths_fail_at_the_http_boundary(value):
    with pytest.raises(ValidationError) as failure:
        DatasetCreateRequest(source="existing", path=value)
    assert failure.value.errors()[0]["loc"] == ("path",)


def test_quoted_tokens_are_not_shell_commands_or_recursive_unquoting():
    assert required_path_token("\"'folder'\"") == "'folder'"
    assert required_path_token('"unpaired') == '"unpaired'
    assert required_path_token('"a\\b $HOME %USERPROFILE% `command`"') == (
        "a\\b $HOME %USERPROFILE% `command`"
    )
    assert ConfigPatchRequest(adapter_defaults={"opencode": None}).adapter_defaults == {
        "opencode": None
    }


def test_source_import_paths_remove_only_one_quote_pair(tmp_path):
    store = SimpleNamespace(paths=SimpleNamespace(root=tmp_path))
    raw = "\"'literal'\""
    assert path_batch_lines({"path": raw}) == [raw]
    assert source_path_values(store, {"path": raw}, "path") == [
        str(tmp_path / "'literal'")
    ]


@pytest.mark.parametrize(
    "path", [r"D:\Projects\含 空格\datasets", "/tmp/data", "relative path"]
)
def test_quoted_padding_is_normalized_consistently_across_browser_inputs(
    tmp_path, path
):
    raw = f'  "  {path}  "  '
    assert DatasetCreateRequest(source="existing", path=raw).path == path
    assert (
        ConfigPatchRequest(adapter_defaults={"opencode": raw}).adapter_defaults[
            "opencode"
        ]
        == path
    )
    store = SimpleNamespace(paths=SimpleNamespace(root=tmp_path))
    assert source_path_values(store, {"path": raw}, "path") == source_path_values(
        store, {"path": path}, "path"
    )


@pytest.mark.parametrize("value", ["a\x00b", "a\rb", "a\u2028b", 7, ["a"]])
def test_raw_source_payload_reports_bad_paths_before_loading(value):
    with pytest.raises(HttpError) as caught:
        add_source_payload(None, None, {"path": value})
    assert caught.value.status == 400


def test_http_quoted_paths_register_update_create_and_mount(tmp_path):
    root = tmp_path / "含 空格"
    workspace = root / ".local" / "evals"
    workspace.mkdir(parents=True)
    config_file = workspace / "peval.toml"
    config_file.write_text("", encoding="utf-8")
    dataset, replacement, jobs = (
        root / name for name in ("datasets", "replacement", "jobs")
    )
    for path in (dataset, replacement, jobs):
        path.mkdir()
    store = open_workspace_state(str(workspace))
    runtime = ServeRuntime(store, ToolConfig(workspace_root=str(workspace)))
    try:
        with TestClient(
            make_handler(runtime),
            base_url="http://127.0.0.1",
            headers={"Origin": "http://127.0.0.1"},
        ) as client:

            def write(method, path, payload, expected=202):
                etag = client.get("/api/config").headers["etag"]
                response = client.request(
                    method, path, json=payload, headers={"If-Match": etag}
                )
                assert response.status_code == expected, response.text
                if expected != 202:
                    return
                operation = response.json()
                operation_id = operation.get("id") or operation["operation_id"]
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    response = client.get(f"/api/operations/{operation_id}")
                    assert response.status_code == 200, response.text
                    operation = response.json()
                    if operation["state"] not in {"queued", "running"}:
                        assert operation["state"] == "succeeded", operation
                        return
                    time.sleep(0.01)
                pytest.fail(f"operation did not finish: {operation}")

            write(
                "POST",
                "/api/harbor/datasets",
                {"source": "existing", "path": f'  "{dataset}"  '},
            )
            config = client.get("/api/config").json()
            assert config["datasets"][0]["id"] == "datasets"
            assert config["datasets"][0]["path"] == str(dataset.resolve())
            before = config_file.read_bytes()
            for value, expected in [
                (f'"{dataset}"', 409),
                ('"missing"', 404),
                ('""', 422),
            ]:
                write(
                    "POST",
                    "/api/harbor/datasets",
                    {"source": "existing", "path": value},
                    expected,
                )
                assert config_file.read_bytes() == before
            write(
                "PATCH",
                "/api/harbor/datasets/datasets",
                {
                    "new_id": "datasets",
                    "path": f"'{replacement}'",
                    "mount_ids": [],
                },
            )
            write(
                "POST",
                "/api/harbor/datasets",
                {
                    "source": "new",
                    "id": "new",
                    "path": '"new dataset"',
                    "package_name": "local/new",
                },
            )
            assert (workspace / "new dataset" / "dataset.toml").is_file()
            write("POST", "/api/harbor/mounts", {"path": f'"{jobs}"'})
            config = client.get("/api/config").json()
            assert config["mounts"][0]["id"] == "jobs"
            assert config["mounts"][0]["path"] == str(jobs)
            assert config["datasets"][0]["path"] == str(replacement.resolve())
            assert list(dataset.iterdir()) == list(replacement.iterdir()) == []
    finally:
        runtime.close()
        runtime.wait_until_ready(timeout=5)
        store.close()
