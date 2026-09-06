from __future__ import annotations

import sys
from pathlib import Path

from psycheval.adapters import adapter_for, available_adapter_ids
from psycheval.cli.arguments import CliArgs
from psycheval.inputs import (
    adapter_for_input_path,
    resolve_db_input,
)
from psycheval.session_select import (
    format_session_table,
    inspect_adapter_sessions,
    parse_session_selection,
)


def print_session_lists(
    args: CliArgs,
    adapter_assignments,
    config,
) -> None:
    inputs = session_inputs_with_adapters(args, adapter_assignments, config)
    for input_db in inputs:
        if len(inputs) > 1:
            print(f"{input_db['selector']} {input_db['path']} ({input_db['adapter']})")
        print_session_warnings(input_db)
        print(format_session_table(input_db["sessions"]), end="")


def interactive_session_selection(
    args: CliArgs,
    adapter_assignments,
    config,
) -> list[str]:
    if getattr(args, "session_id", None):
        raise ValueError("--list-interactive cannot be combined with --session-id")
    if not sys.stdin.isatty():
        raise ValueError("--list-interactive requires an interactive terminal")
    inputs = session_inputs_with_adapters(args, adapter_assignments, config)
    if len(inputs) != 1:
        raise ValueError(
            "--list-interactive requires exactly one session-selectable input; "
            "use repeated -s pN=ID or dN=ID for multiple inputs"
        )
    input_db = inputs[0]
    print_session_warnings(input_db)
    print(format_session_table(input_db["sessions"]), end="")
    raw = input("Select sessions (for example 1,3-5 or all; blank cancels): ")
    indexes = parse_session_selection(raw, len(input_db["sessions"]))
    return [
        f"{input_db['selector']}={input_db['sessions'][index - 1].session_id}"
        for index in indexes
    ]


def print_session_warnings(source: dict) -> None:
    for warning in source["warnings"]:
        print(f"warning: {warning}", file=sys.stderr)


def session_inputs_with_adapters(
    args: CliArgs,
    adapter_assignments,
    config,
) -> list[dict]:

    dbs = list(getattr(args, "db", None) or [])
    available = set(available_adapter_ids())
    inputs = []
    for index, raw_path in enumerate(getattr(args, "path", None) or [], start=1):
        path = Path(raw_path).expanduser()
        if not path.is_dir():
            continue
        adapter = adapter_for_input_path(
            str(path), index, adapter_assignments, "path", available
        )
        if not callable(getattr(adapter_for(adapter), "resolve_session_path", None)):
            raise ValueError(f"adapter {adapter} does not support session directories")
        listing = inspect_adapter_sessions(adapter, str(path))
        inputs.append(
            {
                "selector": f"p{index}",
                "path": str(path),
                "adapter": adapter,
                "sessions": listing.sessions,
                "warnings": listing.warnings,
            }
        )
    for index, path in enumerate(dbs, start=1):
        resolved_path, token_adapter = resolve_db_input(
            path, index, adapter_assignments, config
        )
        adapter = token_adapter or adapter_for_input_path(
            resolved_path,
            index,
            adapter_assignments,
            "db",
            available,
        )
        listing = inspect_adapter_sessions(adapter, resolved_path)
        inputs.append(
            {
                "selector": f"d{index}",
                "path": resolved_path,
                "adapter": adapter,
                "sessions": listing.sessions,
                "warnings": listing.warnings,
            }
        )
    if not inputs:
        raise ValueError("--list requires a session directory or --db")
    return inputs
