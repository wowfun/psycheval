import json
import threading
from unittest.mock import patch

import pytest

from psycheval._inspection.reports import inspect_report_for_args
from psycheval.cli import main
from psycheval.cli.arguments import CliArgs
from psycheval.config import ToolConfig
from psycheval.conversion import convert_path
from psycheval.inputs import load_inputs, parse_adapter_assignments
from psycheval.report import build_report
from psycheval.serve.errors import HttpError
from psycheval.serve.sources import add_source_payload
from tests.peval.claude_support import event, family, write_events
from tests.peval.cli_inputs_support import write_trial_cell_artifacts
from tests.peval.peval_test_support import FIXTURES, create_messages_db
from tests.peval.serve_state_support import (
    LocalHTTPServer,
    make_handler,
    open_workspace_state,
    peval_workspace,
    request_json,
)


def project_with_two_sessions(path):
    family(path)
    write_events(
        path / "newer.jsonl",
        [event("user", seq=50, content="Newer", sessionId="newer")],
    )
    return path


def test_cli_listing_rejects_unsupported_directory_adapter(tmp_path):
    from psycheval.cli.sessions import session_inputs_with_adapters

    args = CliArgs(command="view", path=(str(tmp_path),))
    assignments = parse_adapter_assignments(["opencode"], "opencode")
    with pytest.raises(
        ValueError, match="adapter opencode does not support session directories"
    ):
        session_inputs_with_adapters(args, assignments, ToolConfig())


def test_directory_multiselect_scans_catalog_once(tmp_path):
    from psycheval.adapters import claude

    project = project_with_two_sessions(tmp_path / ".claude")
    with patch.object(claude, "_scan_session", wraps=claude._scan_session) as scan:
        loaded = load_inputs(
            CliArgs(command="view", path=(str(project),), session_id=("#1", "#2")),
            parse_adapter_assignments(["claude"], "opencode"),
            config=ToolConfig(adapter="claude"),
        )
    assert len(loaded.sessions) == 2
    assert scan.call_count == 2


@pytest.mark.parametrize(
    "selection", [{"session_id": "root-session"}, {"session_ids": ["root-session"]}]
)
def test_path_batch_rejects_session_selection_before_import(tmp_path, selection):
    root = peval_workspace(tmp_path / "workspace")
    first = project_with_two_sessions(root / "first/.claude")
    second = project_with_two_sessions(root / "second/.claude")
    store = open_workspace_state(str(root))
    try:
        with pytest.raises(HttpError, match="require exactly one source"):
            add_source_payload(
                store,
                ToolConfig(workspace_root=str(root)),
                {
                    "path": f"{first}\n{second}",
                    "adapter": "claude",
                    **selection,
                },
            )
        assert store.source_payload() == []
    finally:
        store.close()


def test_report_inspection_rejects_missing_child_identity(tmp_path):
    from psycheval._inspection.reports import report_from_direct_json

    trajectory = convert_path(
        str(family(tmp_path)), ToolConfig(adapter="claude")
    ).trajectory
    trajectory["subagent_trajectories"][0].pop("trajectory_id")
    with pytest.raises(ValueError, match="trajectory_id"):
        report_from_direct_json(
            {"trajectory": [trajectory], "trajectory_meta": [{}]},
            tmp_path / "report.json",
        )


def test_cli_directory_listing_latest_multiselect_and_single_family_export(
    tmp_path, capsys
):
    project = project_with_two_sessions(tmp_path / ".claude")
    (project / "bad.jsonl").write_text("{bad", encoding="utf-8")
    assert main(["view", "tr", "-p", str(project), "--list"]) == 0
    captured = capsys.readouterr()
    output = captured.out
    assert "bad.jsonl" in captured.err
    assert output.index("newer") < output.index("root-session")
    assert "updated_at (UTC)" in output
    assert "2026-01-01T00:00:50.000Z" in output
    assert "2026-01-01T00:00:08.000Z" in output
    report = tmp_path / "report.json"
    assert main(["view", "tr", "-m", "raw", "-p", str(project), "-o", str(report)]) == 0
    assert json.loads(report.read_text())["trajectory"][0]["session_id"] == "newer"
    assert (
        main(
            [
                "view",
                "tr",
                "-m",
                "raw",
                "-p",
                str(project),
                "-s",
                "root-session",
                "-s",
                "#1",
                "-o",
                str(report),
            ]
        )
        == 0
    )
    assert [t["session_id"] for t in json.loads(report.read_text())["trajectory"]] == [
        "root-session",
        "newer",
    ]
    output = tmp_path / "export.json"
    assert (
        main(
            [
                "export",
                "tr",
                "-p",
                str(project),
                "-s",
                "root-session",
                "-o",
                str(output),
            ]
        )
        == 0
    )
    assert len(json.loads(output.read_text())["subagent_trajectories"]) == 6
    before = output.read_bytes()
    assert (
        main(
            [
                "export",
                "tr",
                "-p",
                str(project),
                "-s",
                "root-session",
                "-s",
                "newer",
                "-o",
                str(output),
            ]
        )
        != 0
    )
    assert output.read_bytes() == before


def test_inspect_preserves_directory_expansion_between_direct_atif_and_db(tmp_path):
    project = project_with_two_sessions(tmp_path / ".claude")
    direct = tmp_path / "direct.json"
    direct.write_text(
        json.dumps(
            convert_path(
                str(project / "newer.jsonl"), ToolConfig(adapter="claude")
            ).trajectory
        )
    )
    db = tmp_path / "db.sqlite"
    create_messages_db(db)
    args = CliArgs(
        command="view",
        path=(str(direct), str(project)),
        db=(str(db),),
        session_id=("p2=root-session", "p2=newer", "d1=db-a"),
    )
    assignments = parse_adapter_assignments(["d1=psychevo"], "psychevo")
    report = inspect_report_for_args(args, assignments, ToolConfig())
    assert [t["session_id"] for t in report["trajectory"]] == [
        "newer",
        "root-session",
        "newer",
        "db-a",
    ]
    with pytest.raises(ValueError, match="bare --session-id"):
        load_inputs(
            CliArgs(
                command="view",
                path=(str(project),),
                db=(str(db),),
                session_id=("newer",),
            ),
            assignments,
            config=ToolConfig(),
        )


def test_directory_interactive_selection_and_non_tty(tmp_path, capsys):
    project = project_with_two_sessions(tmp_path / ".claude")
    output = tmp_path / "report.json"
    argv = [
        "view",
        "tr",
        "-m",
        "raw",
        "-p",
        str(project),
        "--list-interactive",
        "-o",
        str(output),
    ]
    with patch("sys.stdin.isatty", return_value=False):
        assert main(argv) != 0
    assert "interactive terminal" in capsys.readouterr().err
    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("builtins.input", return_value="2,1"),
    ):
        assert main(argv) == 0
    assert [t["session_id"] for t in json.loads(output.read_text())["trajectory"]] == [
        "root-session",
        "newer",
    ]


def test_workspace_directory_http_selection_and_refresh_keeps_root_identity(tmp_path):
    root = peval_workspace(tmp_path / "workspace")
    project = project_with_two_sessions(root / ".claude")
    (project / "bad.jsonl").write_text("{bad", encoding="utf-8")
    config = ToolConfig(workspace_root=str(root))
    store = open_workspace_state(str(root))
    server = LocalHTTPServer(("127.0.0.1", 0), make_handler(store, config))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_port
    try:
        status, _, payload = request_json(
            port,
            "POST",
            "/api/session-inspections",
            {"path": str(project)},
            origin=f"http://127.0.0.1:{port}",
        )
        assert status == 200
        assert payload["adapter"] == "claude"
        assert len(payload["warnings"]) == 1
        assert "bad.jsonl" in payload["warnings"][0]
        assert [s["session_id"] for s in payload["sessions"]] == [
            "newer",
            "root-session",
        ]
        assert [s["updated_at_ms"] for s in payload["sessions"]] == [
            1767225650000,
            1767225608000,
        ]
        status, _, payload = request_json(
            port,
            "POST",
            "/api/source-import-operations",
            {"path": str(project), "session_ids": ["root-session", "newer"]},
            origin=f"http://127.0.0.1:{port}",
        )
        assert status == 200
        assert len(store.source_payload()) == 2
        row = next(
            row for row in store.source_payload() if row["session_id"] == "root-session"
        )
        assert row["refreshable"] is True
        key = row["source_key"]
        child_path = project / "root-session/subagents/agent-child-1.jsonl"
        with child_path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    event(
                        "user", agent="child-1", seq=59, content="Added child evidence"
                    )
                )
                + "\n"
            )
        store.refresh_source(row, config)
        assert {row["source_key"] for row in store.source_payload()} == {
            key,
            next(
                row["source_key"]
                for row in store.source_payload()
                if row["session_id"] == "newer"
            ),
        }
        report = store.report_for_rows([store.source_by_key(key)], config)
        child = report["trajectory"][0]["subagent_trajectories"][1]
        assert child["steps"][-1]["message"] == "Added child evidence"
        (project / "root-session.jsonl").unlink()
        store.refresh_source(store.source_by_key(key), config)
        assert store.source_by_key(key)["last_status"] == "error"
        assert (
            store.report_for_rows([store.source_by_key(key)], config)["trajectory"]
            == report["trajectory"]
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        store.close()


def test_workspace_multiple_selected_directory_sessions_keep_order(tmp_path):
    root = peval_workspace(tmp_path / "workspace")
    project = project_with_two_sessions(root / ".claude")
    store = open_workspace_state(str(root))
    try:
        result = add_source_payload(
            store,
            ToolConfig(workspace_root=str(root)),
            {"path": str(project), "session_ids": ["root-session", "newer"]},
        )
        assert len(result.keys) == 2
        assert [store.source_by_key(key)["session_id"] for key in result.keys] == [
            "root-session",
            "newer",
        ]
    finally:
        store.close()


@pytest.mark.parametrize("kind", ["path", "db"])
def test_non_claude_imports_do_not_persist_native_refresh_binding(tmp_path, kind):
    root = peval_workspace(tmp_path / "workspace")
    if kind == "path":
        native = root / "common_session.jsonl"
        native.write_bytes((FIXTURES / native.name).read_bytes())
        payload = {"path": str(native), "adapter": "opencode"}
    else:
        native = root / "state.db"
        create_messages_db(native)
        payload = {"db": str(native), "adapter": "psychevo"}
    config = ToolConfig(workspace_root=str(root))
    store = open_workspace_state(str(root))
    try:
        keys = add_source_payload(store, config, payload).keys
        assert keys
        for key in keys:
            row = store.source_by_key(key)
            assert row["refreshable"] is False
            overlay = store.read_source_state(
                store.resolve_artifact_dir(row["artifact_dir"])
            )
            assert overlay.get("refresh_binding") is None
    finally:
        store.close()


def test_copying_claude_cells_does_not_activate_original_refresh_binding(tmp_path):
    root = peval_workspace(tmp_path / "original")
    source = family(root / ".claude")
    store = open_workspace_state(str(root))
    destination = peval_workspace(tmp_path / "destination")
    copied_store = open_workspace_state(str(destination))
    try:
        key = add_source_payload(
            store, ToolConfig(workspace_root=str(root)), {"path": str(source)}
        ).keys[0]
        cell = store.source_by_key(key)["input_path"]
        result = add_source_payload(
            copied_store, ToolConfig(workspace_root=str(destination)), {"path": cell}
        )
        copied = copied_store.source_by_key(result.keys[0])
        assert copied["snapshot"] is True
        assert copied["refreshable"] is False
        assert (
            len(
                copied_store.report_for_rows([copied])["trajectory"][0][
                    "subagent_trajectories"
                ]
            )
            == 6
        )
    finally:
        store.close()
        copied_store.close()


def test_multiple_directories_keep_selectors_around_cell_and_plain_file(tmp_path):
    first = project_with_two_sessions(tmp_path / "first/.claude")
    cell = tmp_path / "cell"
    write_trial_cell_artifacts(cell)
    second = tmp_path / "second/.claude"
    write_events(
        second / "other.jsonl",
        [event("user", content="Other session", sessionId="other")],
    )
    plain = write_events(
        tmp_path / "copied.log",
        [event("user", content="Copied file", sessionId="loose")],
    )
    args = CliArgs(
        command="view",
        path=tuple(str(path) for path in (first, cell, second, plain)),
        session_id=("p1=newer", "p1=root-session", "p3=other"),
    )
    assignments = parse_adapter_assignments(["p4=claude"], "psychevo")
    report = inspect_report_for_args(args, assignments, ToolConfig())
    assert [t["session_id"] for t in report["trajectory"]] == [
        "newer",
        "root-session",
        "artifact-session",
        "other",
        "loose",
    ]


def test_inspect_expands_home_before_recognizing_direct_report(tmp_path, monkeypatch):
    source = family(tmp_path / ".claude")
    config = ToolConfig(adapter="claude")
    expected = build_report(convert_path(str(source), config), config, "fixture")
    (tmp_path / "view.json").write_text(json.dumps(expected), encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    actual = inspect_report_for_args(
        CliArgs(command="view", path=("~/view.json",)),
        parse_adapter_assignments([], "psychevo"),
        ToolConfig(),
    )
    assert actual["trajectory"] == expected["trajectory"]


@pytest.mark.parametrize(
    "adapter,diagnostic",
    [
        (None, "could not infer adapter"),
        ("opencode", "adapter opencode does not support session directories"),
    ],
)
def test_copied_project_import_explains_adapter_problem(tmp_path, adapter, diagnostic):
    root = peval_workspace(tmp_path / "workspace")
    project = project_with_two_sessions(root / "my-project")
    store = open_workspace_state(str(root))
    try:
        with pytest.raises((HttpError, ValueError), match=diagnostic):
            add_source_payload(
                store,
                ToolConfig(workspace_root=str(root)),
                {
                    "path": str(project),
                    **({"adapter": adapter} if adapter else {}),
                },
            )
        assert store.source_payload() == []
    finally:
        store.close()


@pytest.mark.parametrize("kind", ["atif", "report"])
def test_direct_inspection_projects_child_runtime_metadata(tmp_path, kind):
    native = family(tmp_path / ".claude")
    native_conversion = convert_path(str(native), ToolConfig(adapter="claude"))
    native_meta = build_report(
        native_conversion, ToolConfig(adapter="claude"), "native"
    )["trajectory_meta"][0]
    trajectory = native_conversion.trajectory
    exported = tmp_path / "portable.json"
    exported.write_text(json.dumps(trajectory), encoding="utf-8")
    expected = build_report(
        convert_path(str(exported), ToolConfig()), ToolConfig(adapter="atif"), "fixture"
    )
    child_id = "claude:root-session:agent:child-0"
    grand_id = "claude:root-session:agent:grand-0"
    if kind == "report":
        exported.write_text(
            json.dumps(
                {
                    "trajectory": [trajectory],
                    "trajectory_meta": [
                        {
                            "trial_key": "owned",
                            "adapter": "atif",
                            "status": "failed",
                            "score": 0,
                            "warnings": ["root diagnosis"],
                            "subagent_meta": {
                                child_id: {"warnings": ["child diagnosis"]}
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
    before = exported.read_bytes()
    actual = inspect_report_for_args(
        CliArgs(command="view", path=(str(exported),)),
        parse_adapter_assignments([], "psychevo"),
        ToolConfig(),
    )
    root = actual["trajectory_meta"][0]
    child = root["subagent_meta"][child_id]
    expected_child = expected["trajectory_meta"][0]["subagent_meta"][child_id]
    assert (
        expected["trajectory_meta"][0]["duration_ms"]
        == native_meta["duration_ms"]
        == 21_000
    )
    assert (
        expected_child["duration_ms"]
        == native_meta["subagent_meta"][child_id]["duration_ms"]
        == 3000
    )
    assert child["subagent_meta"][grand_id]["duration_ms"] is None
    for key in (
        "started_at_ms",
        "finished_at_ms",
        "wall_duration_ms",
        "duration_ms",
        "steps",
    ):
        assert child[key] == expected_child[key]
        assert (
            child["subagent_meta"][grand_id][key]
            == expected_child["subagent_meta"][grand_id][key]
        )
    assert child["adapter"] == "atif"
    assert child["subagent_meta"][grand_id]["adapter"] == "atif"
    if kind == "report":
        assert root["status"] == "failed" and root["score"] == 0
        assert root["warnings"] == ["root diagnosis"]
        assert child["warnings"] == ["child diagnosis"]
    else:
        assert root["duration_ms"] == 21_000
    assert actual["trajectory"] == [trajectory]
    assert exported.read_bytes() == before
