from __future__ import annotations

import sys
from dataclasses import replace

from psycheval.atif import validate_atif_trajectory
from psycheval.cli.arguments import CliArgs
from psycheval.cli.sessions import (
    interactive_session_selection,
    print_session_lists,
)
from psycheval.cli.workspace import (
    rewrite_trial_cell_path_args,
    validated_workspace_root,
    workspace_root_for_args,
)
from psycheval.config import apply_overrides, config_for_adapter, load_config
from psycheval.html import render_html
from psycheval.inputs import load_inputs, parse_adapter_assignments
from psycheval.outputs import (
    announce_written,
    resolve_export_output,
    resolve_report_format,
    resolve_report_output,
    write_json,
    write_text,
)
from psycheval.pipeline import (
    build_report_from_loaded_inputs,
    config_for_session,
    convert_session,
)


def main(argv: list[str] | None = None) -> int:
    from psycheval.cli.app import app, normalize_argv

    raw_args = list(sys.argv[1:] if argv is None else argv)
    try:
        app(args=normalize_argv(raw_args), prog_name="peval")
    except SystemExit as exc:
        if exc.code is None:
            return 0
        return exc.code if isinstance(exc.code, int) else 1
    return 0


def run_cli_args(args: CliArgs) -> int:
    try:
        args = rewrite_trial_cell_path_args(args)
        if args.command == "init":
            from psycheval.workspace import run_init_command

            run_init_command(args)
            return 0
        if args.command == "import":
            from psycheval.analysis import run_import_analysis_command

            workspace_root = validated_workspace_root(args)
            run_import_analysis_command(args, workspace_root)
            return 0
        if args.command == "serve":
            from psycheval.serve import run_serve_command

            run_serve_command(args)
            return 0
        workspace_root, _inferred_workspace_root = workspace_root_for_args(args)
        config = apply_overrides(
            load_config(args.config, workspace_root=workspace_root),
            args,
        )
        adapter_assignments = parse_adapter_assignments(
            getattr(args, "adapter", None) or [],
            config.adapter,
        )
        config = config_for_adapter(config, adapter_assignments.default_adapter)
        if args.command == "view" and getattr(args, "mode", "inspect") == "inspect":
            from psycheval.inspection import validate_inspect_raw_only_args

            validate_inspect_raw_only_args(args)
        if args.command == "view" and getattr(args, "list_sessions", False):
            print_session_lists(args, adapter_assignments, config)
            return 0
        if args.command == "view" and getattr(args, "list_interactive", False):
            selected = interactive_session_selection(args, adapter_assignments, config)
            if not selected:
                return 0
            args = replace(args, session_id=tuple(selected))
        if args.command == "view" and getattr(args, "mode", "inspect") == "inspect":
            from psycheval.inspection import (
                build_inspect_payload,
                resolve_inspect_output,
                validate_inspect_args,
            )

            validate_inspect_args(args)
            announce_written(
                write_json(
                    build_inspect_payload(args, adapter_assignments, config),
                    resolve_inspect_output(args),
                )
            )
            return 0
        if args.command == "view" and getattr(args, "mode", "inspect") == "raw":
            from psycheval.inspection import validate_raw_args

            validate_raw_args(args)
        loaded_inputs = load_inputs(args, adapter_assignments, config=config)
        if args.command == "export":
            if len(loaded_inputs.sessions) != 1:
                raise ValueError("export trajectory accepts exactly one input session")
            session = loaded_inputs.sessions[0]
            session_config = config_for_session(session, config)
            if session.snapshot_trajectory is not None:
                validate_atif_trajectory(session.snapshot_trajectory)
                write_json(
                    session.snapshot_trajectory,
                    resolve_export_output(
                        args, session.snapshot_trajectory, session_config
                    ),
                )
                return 0
            conversion = convert_session(session, config)
            write_json(
                conversion.trajectory,
                resolve_export_output(args, conversion.trajectory, session_config),
            )
            return 0
        report = build_report_from_loaded_inputs(
            loaded_inputs,
            config,
            getattr(args, "note", None) or [],
        )
        fmt = resolve_report_format(args)
        output = resolve_report_output(args, fmt, report, config, timestamped=True)
        if fmt == "json":
            written = write_json(report, output)
        elif fmt == "html":
            written = write_text(render_html(report, locale=config.locale), output)
        else:
            raise ValueError(f"unsupported report format: {fmt}")
        if args.command == "view":
            announce_written(written)
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI boundary.
        print(f"peval: {exc}", file=sys.stderr)
        return 1
