from __future__ import annotations

import re
from enum import Enum
from typing import Annotated, TypeVar

import typer

from psycheval.cli.arguments import CliArgs
from psycheval.outputs import DEFAULT_OUTPUT

APP_HELP = (
    "Convert, inspect, and organize retained agent trajectories and analysis "
    "artifacts through init, export, import, view, and serve workflows."
)
INSPECT_EPILOG = """\
Inspect mode emits a compact fixed JSON digest for triage. Use --steps for
selected step evidence, --max-content-chars to bound previews, or -m raw for
the full peval-compatible JSON report.
"""
OUTPUT_DEFAULT_MARKER = "\0peval-default-output"
_NEGATIVE_NUMBER = re.compile(r"-\d+(?:\.\d+)?")
_T = TypeVar("_T")


class ViewMode(str, Enum):
    inspect = "inspect"
    raw = "raw"


def make_app(*, help: str, add_completion: bool = False) -> typer.Typer:
    return typer.Typer(
        help=help,
        add_completion=add_completion,
        rich_markup_mode=None,
        pretty_exceptions_enable=False,
        no_args_is_help=False,
        suggest_commands=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )


app = make_app(help=APP_HELP, add_completion=True)
view_app = make_app(help="Render a peval-style report for a supported scenario.")
export_app = make_app(help="Export normalized data for a supported scenario.")
import_app = make_app(help="Import analysis files into peval workspace artifacts.")
publish_app = make_app(help="Publish reviewed evaluation reports.")
harbor_app = make_app(help="Prepare and summarize external Harbor evaluations.")


AdapterOption = Annotated[
    list[str] | None,
    typer.Option(
        "-a",
        "--adapter",
        help="Input adapter id; defaults to config or psychevo",
    ),
]
PathOption = Annotated[
    list[str] | None,
    typer.Option(
        "-p",
        "--path",
        metavar="PATH",
        help=(
            "Source path: JSONL, report JSON, trajectory artifact, Trial cell "
            "or descendant, or Harbor Trial root for view; repeatable"
        ),
    ),
]
DbOption = Annotated[
    list[str] | None,
    typer.Option(
        "-d",
        "--db",
        metavar="PATH",
        help="Adapter-owned SQLite state database; repeatable for view trajectory",
    ),
]
SessionIdOption = Annotated[
    list[str] | None,
    typer.Option(
        "-s",
        "--session-id",
        metavar="ID",
        help="DB session id; use dN=ID when multiple DB inputs are present",
    ),
]
MaxContentCharsOption = Annotated[
    int | None,
    typer.Option(help="Bound source content and inspect preview text"),
]
OutputOption = Annotated[
    str | None,
    typer.Option(
        "-o",
        "--output",
        metavar="PATH",
        help=(
            "Write to PATH; omit PATH after -o/--output for an "
            "adapter/session-based default filename"
        ),
    ),
]
RootOption = Annotated[
    str | None,
    typer.Option(
        "-r",
        "--root",
        metavar="DIR",
        help=(
            "Existing peval workspace root for config discovery; "
            "run peval init -r DIR first"
        ),
    ),
]
AgentNameOption = Annotated[
    str | None,
    typer.Option(help="Override ATIF agent name"),
]
AgentVersionOption = Annotated[
    str | None,
    typer.Option(help="Override ATIF agent version"),
]
ModelOption = Annotated[str | None, typer.Option(help="Override ATIF agent model name")]
NoRedactOption = Annotated[
    bool,
    typer.Option("--no-redact", help="Disable secret redaction"),
]
NoteOption = Annotated[
    list[str] | None,
    typer.Option(
        "-n",
        "--note",
        metavar="N=TEXT",
        help=(
            "Full report or serve only: add a report note at 0 or a one-based "
            "session note; repeatable"
        ),
    ),
]
SourceAliasOption = Annotated[
    list[str] | None,
    typer.Option(
        "--source-alias",
        metavar="N=TEXT",
        help=(
            "Full report or serve only: display alias for a one-based input "
            "session; repeatable"
        ),
    ),
]


def many(values: list[_T] | None) -> tuple[_T, ...] | None:
    return tuple(values) if values is not None else None


def output_value(value: str | None) -> object | None:
    return DEFAULT_OUTPUT if value == OUTPUT_DEFAULT_MARKER else value


def input_values(
    *,
    adapter: list[str] | None,
    path: list[str] | None,
    db: list[str] | None,
    session_id: list[str] | None,
    max_content_chars: int | None,
) -> dict[str, object]:
    return {
        "adapter": many(adapter),
        "path": many(path),
        "db": many(db),
        "session_id": many(session_id),
        "max_content_chars": max_content_chars,
    }


def execute(args: CliArgs) -> None:
    from psycheval.cli.main import run_cli_args

    exit_code = run_cli_args(args)
    if exit_code:
        raise typer.Exit(exit_code)


@app.command(
    "init",
    help="Create or repair the minimal peval serve state.",
    short_help="Initialize peval serve state",
)
def init_command(
    root: Annotated[
        str | None,
        typer.Option(
            "-r",
            "--root",
            metavar="DIR",
            help="Workspace root; defaults to the current directory",
        ),
    ] = None,
    skill: Annotated[
        list[str] | None,
        typer.Option(
            "--skill",
            metavar="DIR",
            help="Install one local Agent Skill directory into the workspace",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print machine-readable init results"),
    ] = False,
) -> None:
    skill_values = skill or []
    if len(skill_values) > 1:
        raise typer.BadParameter(
            "may be provided only once; run init again to install another Skill",
            param_hint="--skill",
        )
    execute(
        CliArgs(
            command="init",
            root=root,
            skill_dir=skill_values[0] if skill_values else None,
            json=json_output,
        )
    )


@view_app.command("tr", hidden=True)
@view_app.command(
    "trajectory",
    help=(
        "Inspect retained agent trajectories by default. Use -m raw only when "
        "a full peval-compatible JSON report is needed."
    ),
    short_help="View one or more retained agent trajectories",
    epilog=INSPECT_EPILOG,
)
def view_trajectory(
    adapter: AdapterOption = None,
    path: PathOption = None,
    db: DbOption = None,
    session_id: SessionIdOption = None,
    max_content_chars: MaxContentCharsOption = None,
    output: OutputOption = None,
    agent_name: Annotated[
        str | None,
        typer.Option(help="Raw mode only: override ATIF agent name"),
    ] = None,
    agent_version: Annotated[
        str | None,
        typer.Option(help="Raw mode only: override ATIF agent version"),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option(help="Raw mode only: override ATIF agent model name"),
    ] = None,
    no_redact: Annotated[
        bool,
        typer.Option("--no-redact", help="Raw mode only: disable secret redaction"),
    ] = False,
    root: RootOption = None,
    source_ref: Annotated[
        list[str] | None,
        typer.Option(
            "--source-ref",
            metavar="REF",
            help="Workspace source reference; repeatable",
        ),
    ] = None,
    mode: Annotated[
        ViewMode,
        typer.Option(
            "-m",
            "--mode",
            help="View mode: inspect emits bounded JSON; raw emits a full report",
        ),
    ] = ViewMode.inspect,
    list_sessions: Annotated[
        bool,
        typer.Option("-l", "--list", help="List DB sessions and exit"),
    ] = False,
    list_interactive: Annotated[
        bool,
        typer.Option(
            "-li",
            "--list-interactive",
            help="List DB sessions, prompt for selection, and render selected sessions",
        ),
    ] = False,
    note: NoteOption = None,
    source_alias: SourceAliasOption = None,
    head: Annotated[
        int | None,
        typer.Option(help="Inspect first N steps per source; defaults to 2"),
    ] = None,
    tail: Annotated[
        int | None,
        typer.Option(help="Inspect last N steps per source; defaults to 2"),
    ] = None,
    top: Annotated[
        int | None,
        typer.Option(help="Inspect top N ranked rows per source; defaults to 5"),
    ] = None,
    steps: Annotated[
        list[str] | None,
        typer.Option(
            metavar="IDS",
            help=(
                "Show selected step_id evidence only; comma lists and start:end "
                "ranges supported"
            ),
        ),
    ] = None,
    tool_call: Annotated[
        list[str] | None,
        typer.Option(
            metavar="ID",
            help=(
                "Include a tool call and its matching result by tool_call_id; "
                "repeatable"
            ),
        ),
    ] = None,
    source: Annotated[
        list[int] | None,
        typer.Option(
            metavar="N",
            help="Inspect only a one-based source index; repeatable",
        ),
    ] = None,
) -> None:
    execute(
        CliArgs(
            command="view",
            scenario="trajectory",
            **input_values(
                adapter=adapter,
                path=path,
                db=db,
                session_id=session_id,
                max_content_chars=max_content_chars,
            ),
            output=output_value(output),
            agent_name=agent_name,
            agent_version=agent_version,
            model=model,
            no_redact=no_redact,
            root=root,
            source_refs=many(source_ref),
            mode=mode.value,
            list_sessions=list_sessions,
            list_interactive=list_interactive,
            note=many(note) or (),
            source_alias=many(source_alias) or (),
            head=head,
            tail=tail,
            top=top,
            steps=many(steps),
            tool_call=many(tool_call),
            source=many(source),
        )
    )


@export_app.command("tr", hidden=True)
@export_app.command(
    "trajectory",
    help=(
        "Export one session as an ATIF v1.7 trajectory. Unlike view, export "
        "accepts exactly one effective -p/--path or -d/--db session. Some DB "
        "adapters can select a default session when -s/--session-id is omitted."
    ),
    short_help="Export one retained agent trajectory as ATIF JSON",
)
def export_trajectory(
    adapter: AdapterOption = None,
    path: PathOption = None,
    db: DbOption = None,
    session_id: SessionIdOption = None,
    max_content_chars: MaxContentCharsOption = None,
    output: OutputOption = None,
    agent_name: AgentNameOption = None,
    agent_version: AgentVersionOption = None,
    model: ModelOption = None,
    no_redact: NoRedactOption = False,
    root: RootOption = None,
) -> None:
    execute(
        CliArgs(
            command="export",
            scenario="trajectory",
            **input_values(
                adapter=adapter,
                path=path,
                db=db,
                session_id=session_id,
                max_content_chars=max_content_chars,
            ),
            output=output_value(output),
            agent_name=agent_name,
            agent_version=agent_version,
            model=model,
            no_redact=no_redact,
            root=root,
        )
    )


@import_app.command(
    "analysis",
    help=(
        "Import JSON or Markdown analysis reports into a selected workspace Trial cell."
    ),
    short_help="Import Trial analysis reports",
)
def import_analysis(
    root: Annotated[
        str,
        typer.Option(
            "-r",
            "--root",
            metavar="DIR",
            help="Existing peval workspace root",
        ),
    ],
    source_ref: Annotated[
        str,
        typer.Option(
            "--source-ref",
            metavar="REF",
            help=(
                "Existing local source reference with form "
                "runs/<evaluation>/<agent>/<session>/<cell>"
            ),
        ),
    ],
    path: Annotated[
        list[str],
        typer.Option(
            "-p",
            "--path",
            metavar="PATH",
            help="Analysis report path; repeat once for JSON and once for Markdown",
        ),
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print machine-readable import results"),
    ] = False,
) -> None:
    execute(
        CliArgs(
            command="import",
            scenario="analysis",
            root=root,
            source_ref=source_ref,
            path=tuple(path),
            json=json_output,
        )
    )


@publish_app.command(
    "evaluation-report",
    help="Atomically publish a reviewed Markdown report for one workspace source.",
    short_help="Publish an evaluation report",
)
def publish_evaluation_report(
    root: Annotated[
        str,
        typer.Option("-r", "--root", metavar="DIR", help="Existing peval workspace"),
    ],
    source_ref: Annotated[
        str,
        typer.Option("--source-ref", metavar="REF", help="Workspace source reference"),
    ],
    path: Annotated[
        str,
        typer.Option("-p", "--path", metavar="PATH", help="Reviewed Markdown draft"),
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print a structured publication receipt"),
    ] = False,
) -> None:
    execute(
        CliArgs(
            command="publish-evaluation-report",
            root=root,
            source_ref=source_ref,
            path=(path,),
            json=json_output,
        )
    )


app.add_typer(
    view_app,
    name="view",
    short_help="Render a report",
)
app.add_typer(
    export_app,
    name="export",
    short_help="Export normalized data",
)
app.add_typer(
    import_app,
    name="import",
    short_help="Import workspace artifacts",
)
app.add_typer(
    publish_app,
    name="publish",
    short_help="Publish evaluation artifacts",
)
app.add_typer(
    harbor_app,
    name="harbor",
    short_help="Prepare and summarize Harbor evaluations",
)


@harbor_app.command(
    "prepare",
    help="Prepare a registered WorkBuddy Office Dataset for Harbor 0.21.",
)
def harbor_prepare(
    dataset: Annotated[
        str, typer.Option("--dataset", help="Registered WorkBuddy Dataset id")
    ],
    config: Annotated[
        str, typer.Option("--config", metavar="PATH", help="Base Harbor Job YAML")
    ],
    root: RootOption = None,
) -> None:
    execute(
        CliArgs(
            command="harbor-prepare",
            root=root,
            dataset_id=dataset,
            config_path=config,
        )
    )


@harbor_app.command(
    "summarize",
    help="Compute the official WorkBuddy aggregate for a prepared plan.",
)
def harbor_summarize(
    plan: Annotated[str, typer.Option("--plan", help="Prepared run plan id")],
    root: RootOption = None,
    provisional: Annotated[
        bool, typer.Option("--provisional", help="Allow unfinished Jobs")
    ] = False,
) -> None:
    execute(
        CliArgs(
            command="harbor-summarize",
            root=root,
            plan_id=plan,
            provisional=provisional,
        )
    )


@app.command(
    "serve",
    help=(
        "Start the local peval saved workspace UI. Source flags persist and "
        "refresh sources before serving."
    ),
    short_help="Serve the local saved trajectory workspace UI",
)
def serve_command(
    adapter: AdapterOption = None,
    path: PathOption = None,
    db: DbOption = None,
    session_id: SessionIdOption = None,
    max_content_chars: MaxContentCharsOption = None,
    agent_name: AgentNameOption = None,
    agent_version: AgentVersionOption = None,
    model: ModelOption = None,
    no_redact: NoRedactOption = False,
    note: NoteOption = None,
    source_alias: SourceAliasOption = None,
    root: Annotated[
        str | None,
        typer.Option(
            "-r",
            "--root",
            metavar="DIR",
            help="Peval workspace root; otherwise discover peval.toml",
        ),
    ] = None,
    host: Annotated[
        str,
        typer.Option(
            help=("Bind address; non-local addresses require PEVAL_ADMIN_PASSWORD")
        ),
    ] = "127.0.0.1",
    port: Annotated[
        int | None,
        typer.Option(help="Bind port; omitted tries 58010 through 58029"),
    ] = None,
) -> None:
    execute(
        CliArgs(
            command="serve",
            **input_values(
                adapter=adapter,
                path=path,
                db=db,
                session_id=session_id,
                max_content_chars=max_content_chars,
            ),
            agent_name=agent_name,
            agent_version=agent_version,
            model=model,
            no_redact=no_redact,
            note=many(note) or (),
            source_alias=many(source_alias) or (),
            root=root,
            host=host,
            port=port,
        )
    )


def normalize_argv(argv: list[str]) -> list[str]:
    normalized: list[str] = []
    for index, token in enumerate(argv):
        normalized.append(token)
        if token not in {"-o", "--output"}:
            continue
        following = argv[index + 1] if index + 1 < len(argv) else None
        if following is None or is_option_token(following):
            normalized.append(OUTPUT_DEFAULT_MARKER)
    return normalized


def is_option_token(value: str) -> bool:
    return (
        value.startswith("-") and value != "-" and not _NEGATIVE_NUMBER.fullmatch(value)
    )
