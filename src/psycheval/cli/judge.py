"""CLI boundary for retained prompts and independent Judge runs."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
import yaml

from psycheval.judge_runs.files import read_text
from psycheval.judge_runs.service import JudgeService
from psycheval.state.paths import resolve_workspace_root


def export_new(path, text):
    # Exports must never replace a Task, Trial or another retained run.
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def make_judge_app():
    app = typer.Typer(
        help="Inspect prompts, preview drafts and run selected rubrics.",
        rich_markup_mode=None,
        pretty_exceptions_enable=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )

    def command(action):
        def invoke(
            ctx: typer.Context,
            root: Annotated[str | None, typer.Option("--root", "-r")] = None,
            source_ref: Annotated[str | None, typer.Option("--source-ref")] = None,
            path: Annotated[str | None, typer.Option("--path", "-p")] = None,
            step: Annotated[str | None, typer.Option("--step")] = None,
            rubric: Annotated[list[str] | None, typer.Option("--rubric")] = None,
            all_rubrics: Annotated[bool, typer.Option("--all")] = False,
            profile: Annotated[str | None, typer.Option("--profile")] = None,
            judge_config: Annotated[Path | None, typer.Option("--judge-config")] = None,
            task: Annotated[str | None, typer.Option("--task")] = None,
            instruction: Annotated[str | None, typer.Option("--instruction")] = None,
            export_config: Annotated[
                Path | None, typer.Option("--export-config")
            ] = None,
            json_output: Annotated[bool, typer.Option("--json")] = False,
            output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
        ):
            exit_code = 0
            try:
                allowed = {
                    "root",
                    "source_ref",
                    "path",
                    "step",
                    "json_output",
                    "output",
                }
                allowed.update(
                    {
                        "inspect": {"export_config"},
                        "prompt": {"rubric"},
                        "preview": {
                            "rubric",
                            "all_rubrics",
                            "profile",
                            "judge_config",
                            "task",
                            "instruction",
                        },
                        "run": {
                            "rubric",
                            "all_rubrics",
                            "profile",
                            "judge_config",
                            "task",
                            "instruction",
                        },
                    }[action]
                )
                for parameter in ctx.command.params:
                    supplied = ctx.get_parameter_source(parameter.name)
                    if (
                        parameter.name not in allowed
                        and supplied is not None
                        and supplied.name == "COMMANDLINE"
                    ):
                        raise ValueError(
                            f"{parameter.opts[0]} is not supported by judge {action}"
                        )
                service = JudgeService(resolve_workspace_root(root))
                source = dict(source_ref=source_ref, path=path, step=step)
                if action == "prompt":
                    if not rubric or all_rubrics:
                        raise ValueError("prompt requires one or more --rubric values")
                    value = {
                        "prompts": [service.prompt(item, **source) for item in rubric]
                    }
                elif action == "inspect":
                    value = service.inspect(**source)
                    if export_config:
                        if value["config"] is None:
                            raise ValueError(
                                "source has no generic Judge configuration"
                            )
                        export_new(
                            export_config,
                            yaml.safe_dump(
                                value["config"], allow_unicode=True, sort_keys=False
                            ),
                        )
                else:
                    draft = (
                        read_text(
                            judge_config.absolute().parent,
                            judge_config.absolute(),
                            1024 * 1024,
                        )
                        if judge_config
                        else None
                    )
                    arguments = dict(
                        **source,
                        rubric_ids=rubric,
                        all_rubrics=all_rubrics,
                        profile=profile,
                        judge_config=draft,
                        task=task,
                        instruction=instruction,
                    )
                    if action == "run":
                        value = asyncio.run(service.run(**arguments))
                        exit_code = 0 if value["state"] == "complete" else 1
                    else:
                        value = service.preview(**arguments)
                rendered = (
                    json.dumps(value, ensure_ascii=False, indent=2) + "\n"
                    if json_output or output
                    else render(action, value)
                )
                if output:
                    if str(output) == "\0peval-default-output":
                        output = Path(
                            f"judge-{action}-{datetime.now():%Y%m%d-%H%M%S}.json"
                        )
                    export_new(output, rendered)
                    if not json_output:
                        typer.echo(str(output.absolute()))
                else:
                    typer.echo(rendered, nl=False)
            except KeyboardInterrupt:
                value = {"state": "cancelled", "checks": [], "errors": {}}
                typer.echo(json.dumps(value) if json_output else "Cancelled")
                exit_code = 1
            except (OSError, ValueError) as exc:
                typer.echo(f"Error: {exc}", err=True)
                exit_code = 2
            if exit_code:
                raise typer.Exit(exit_code)

        return invoke

    for action in ("inspect", "prompt", "preview", "run"):
        app.command(action)(command(action))
    return app


def render(action, value):
    if action == "inspect":
        lines = [
            f"Source: {value['source']}",
            f"Generic Judge: {'supported' if value['supported'] else 'unavailable'}",
        ]
        if value.get("missing"):
            lines.append("Missing: " + ", ".join(value["missing"]))
        for item in value["baseline"]:
            lines.append(
                f"{item['id']}: {item['status']} · {item['rubric']['question']}"
            )
        return "\n".join(lines) + "\n"
    if action == "prompt":
        lines = []
        for item in value["prompts"]:
            lines.append(
                f"{item['id']} · {item['status']} · {item['source']} (redacted snapshot)"
            )
            for message in item.get("messages") or []:
                lines.extend([f"[{message['role']}]", message["content"]])
        return "\n\n".join(lines) + "\n"
    if action == "preview":
        lines = ["Unsent preview", f"Profile: {value['profile']}"]
        for rubric_id, messages in value["messages"].items():
            lines.append(rubric_id)
            for message in messages:
                lines.extend([f"[{message['role']}]", message["content"]])
        return "\n\n".join(lines) + "\n"
    if action == "run":
        lines = [f"{value['state']} · {value['profile']}"]
        old = {item["id"]: item for item in value.get("baseline", [])}
        for item in value.get("checks", []):
            lines.append(
                f"{item['id']}: {old.get(item['id'], {}).get('status', 'no baseline')} -> {'pass' if item['passed'] else 'fail'} · {item['reason']}"
            )
        lines.extend(
            f"{key}: unassessed · {reason}"
            for key, reason in value.get("errors", {}).items()
        )
        lines.extend(
            [
                value.get("reason", ""),
                "Independent diagnostic run; canonical scores unchanged.",
            ]
        )
        return "\n".join(lines) + "\n"
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"
