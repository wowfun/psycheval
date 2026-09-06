import json

import pytest

from psycheval.adapters.claude import ClaudeAdapter
from psycheval.cli import main
from psycheval.cli.arguments import CliArgs
from psycheval.config import ToolConfig, default_workspace_config_text, load_config
from psycheval.conversion import convert_path
from psycheval.inputs import load_inputs, parse_adapter_assignments
from psycheval.serve.api_models import SourceImportRequest
from psycheval.serve.errors import HttpError
from psycheval.serve.payloads import source_args_from_payload
from psycheval.serve.sources import add_source_payload, sessions_payload
from tests.peval.claude_support import event, family, write_events
from tests.peval.serve_state_support import open_workspace_state, peval_workspace


def test_session_root_default_and_config_resolution(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    root = peval_workspace(tmp_path / "workspace")
    assert ToolConfig().adapter_default_session_roots["claude"] == "~/.claude/projects/"
    assert (
        'default_session_root = "~/.claude/projects/"'
        in default_workspace_config_text()
    )
    retained = family(tmp_path / "home/.claude/projects/project")
    assert ClaudeAdapter().resolve_session_id("root-session", ToolConfig()) == str(
        retained
    )
    for value, expected in [
        ('"sessions"', root / "sessions"),
        ('"~/sessions"', tmp_path / "home/sessions"),
    ]:
        (root / "peval.toml").write_text(
            f"[adapters.claude]\ndefault_session_root = {value}\n", encoding="utf-8"
        )
        config = load_config(workspace_root=root)
        assert config.adapter_default_session_roots["claude"] == str(expected)
        assert (
            "default_session_root" not in config.for_adapter("claude").adapter_options
        )
    for value in ["123", '""']:
        (root / "peval.toml").write_text(
            f"[adapters.claude]\ndefault_session_root = {value}\n", encoding="utf-8"
        )
        with pytest.raises(ValueError, match="default_session_root"):
            load_config(workspace_root=root)


def test_lookup_is_bounded_and_validates_exact_identity(tmp_path):
    adapter = ClaudeAdapter()
    config = ToolConfig(adapter_default_session_roots={"claude": str(tmp_path)})
    path = family(tmp_path / "project")
    # Unrelated corrupt logs do not interfere with exact-ID lookup.
    (path.parent / "unrelated.jsonl").write_text("{bad", encoding="utf-8")
    assert adapter.resolve_session_id("root-session", config) == str(path)
    for identifier in ["../root-session", "#1", "p1=root-session", "missing"]:
        with pytest.raises(ValueError, match="invalid Claude session ID|not found"):
            adapter.resolve_session_id(identifier, config)
    deeper = family(tmp_path / "nested/project")
    assert adapter.resolve_session_id("root-session", config) == str(path)
    root_copy = tmp_path / "root-session.jsonl"
    root_copy.write_bytes(path.read_bytes())
    with pytest.raises(ValueError, match="ambiguous Claude session ID"):
        adapter.resolve_session_id("root-session", config)
    root_copy.unlink()
    write_events(
        root_copy, [event("user", content="Wrong identity", sessionId="other")]
    )
    with pytest.raises(ValueError, match="identity does not match"):
        adapter.resolve_session_id("root-session", config)
    root_copy.write_text("{bad", encoding="utf-8")
    with pytest.raises(ValueError, match="JSONL line 1"):
        adapter.resolve_session_id("root-session", config)
    root_copy.unlink()
    path.unlink()
    with pytest.raises(ValueError, match="not found"):
        adapter.resolve_session_id("root-session", config)
    assert deeper.is_file()


def test_lookup_skips_symlinked_projects_and_files(tmp_path):
    path = family(tmp_path / "outside")
    root = tmp_path / "sessions"
    root.mkdir()
    try:
        (root / "project").symlink_to(path.parent, target_is_directory=True)
        (root / "root-session.jsonl").symlink_to(path)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ValueError, match="not found"):
        ClaudeAdapter().resolve_session_id(
            "root-session",
            ToolConfig(adapter_default_session_roots={"claude": str(root)}),
        )


def test_explicit_project_link_lists_only_top_level_files_and_loads_owned_family(
    tmp_path,
):
    project = tmp_path / "projects/actual"
    native = family(project)
    outside = write_events(
        tmp_path / "outside/foreign.jsonl",
        [event("user", content="Outside", sessionId="foreign")],
    )
    alias = project.parent / "alias"
    try:
        alias.symlink_to(project, target_is_directory=True)
        (project / "linked.jsonl").symlink_to(outside)
        (project / "nested").symlink_to(outside.parent, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    adapter = ClaudeAdapter()
    listing = adapter.inspect_sessions(str(alias))
    assert [session.session_id for session in listing.sessions] == ["root-session"]
    assert listing.warnings == []
    resolved = adapter.resolve_session_path(str(alias), "root-session")
    assert resolved == str(alias / native.name)
    converted = convert_path(resolved, ToolConfig(adapter="claude"))
    assert len(converted.subagent_results) == 6
    assert len(converted.subagent_results[0].subagent_results) == 2
    assert converted.warnings == []


def test_pathless_cli_import_inspect_and_portable_export(tmp_path, capsys):
    root = peval_workspace(tmp_path / "workspace")
    path = family(root / "sessions/project")
    (root / "peval.toml").write_text(
        '[adapters.claude]\ndefault_session_root = "sessions"\n', encoding="utf-8"
    )
    config = load_config(workspace_root=root)
    args = CliArgs(command="view", session_id=("root-session",))
    loaded = load_inputs(
        args, parse_adapter_assignments(["claude"], "psychevo"), config=config
    )
    assert loaded.sessions[0].input_path == str(path)
    with pytest.raises(ValueError, match="explicit adapter"):
        load_inputs(args, parse_adapter_assignments([], "claude"), config=config)
    with pytest.raises(ValueError, match="does not support session ID lookup"):
        load_inputs(
            args, parse_adapter_assignments(["opencode"], "claude"), config=config
        )
    report = root / "report.json"
    assert (
        main(
            [
                "view",
                "tr",
                "-m",
                "raw",
                "--root",
                str(root),
                "-a",
                "claude",
                "-s",
                "root-session",
                "-o",
                str(report),
            ]
        )
        == 0
    ), capsys.readouterr().err
    assert (
        len(json.loads(report.read_text())["trajectory"][0]["subagent_trajectories"])
        == 6
    )
    artifact = root / "family.json"
    assert (
        main(
            [
                "export",
                "tr",
                "--root",
                str(root),
                "-a",
                "claude",
                "-s",
                "root-session",
                "-o",
                str(artifact),
            ]
        )
        == 0
    ), capsys.readouterr().err
    assert json.loads(artifact.read_text())["trajectory_id"] == "claude:root-session"


def test_unified_inputs_mix_ids_paths_and_independent_failures(tmp_path):
    root = peval_workspace(tmp_path / "workspace")
    family(root / "sessions/project")
    native = root / "copied.jsonl"
    write_events(native, [event("user", content="Copied", sessionId="copied")])
    config = ToolConfig(
        workspace_root=str(root),
        adapter_default_session_roots={"claude": str(root / "sessions")},
    )
    store = open_workspace_state(str(root))
    try:
        inspection = sessions_payload(
            store, {"path": "root-session", "adapter": "claude"}, config
        )
        assert [row["session_id"] for row in inspection["sessions"]] == ["root-session"]
        assert inspection["selection_required"] is False
        for payload in [
            {"session_id": "root-session", "adapter": "claude"},
            {"path": inspection["path"], "adapter": "claude"},
        ]:
            assert len(add_source_payload(store, config, payload).keys) == 1
        result = add_source_payload(
            store,
            config,
            {
                "path": "missing\nroot-session\ncopied.jsonl\n./not-a-file",
                "adapter": "claude",
            },
        )
        assert [row["status"] for row in result.import_results] == [
            "error",
            "ok",
            "ok",
            "error",
        ]
        assert [row["path"] for row in result.import_results] == [
            "missing",
            "root-session",
            "copied.jsonl",
            "./not-a-file",
        ]
        assert {row["session_id"] for row in store.source_payload()} == {
            "root-session",
            "copied",
        }
        with pytest.raises(HttpError, match="explicit adapter"):
            source_args_from_payload(store, {"path": "root-session"})
        # An existing relative filename wins over the adapter's ID grammar.
        existing = root / "root-session"
        existing.write_bytes(native.read_bytes())
        assert source_args_from_payload(
            store, {"path": "root-session", "adapter": "claude"}
        ).path == [str(existing)]
        with pytest.raises(HttpError, match="exactly one source"):
            sessions_payload(
                store, {"path": "sessions/project", "db": "state.db"}, config
            )
    finally:
        store.close()


@pytest.mark.parametrize(
    "selection",
    [{"session_id": "one"}, {"session_ids": ["one"]}, {"session_ids": ["one", "two"]}],
)
def test_api_rejects_selection_across_multiple_inputs(selection):
    with pytest.raises(ValueError, match="require exactly one source"):
        SourceImportRequest(path="first\nsecond", **selection)
