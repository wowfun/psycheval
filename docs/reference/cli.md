# Psycheval CLI Reference

`peval` is the short installed name for the Psycheval CLI. It converts retained
Agent sessions to ATIF, builds reports, and organizes evaluation workspaces; it
is not a Python module and does not run Agents or score Tasks.

## Programmatic and command interfaces

`psycheval.cli.main(argv) -> int` is the programmatic interface and
`psycheval.cli.app` is its Typer application. The distribution installs
the `peval` command with `init`, `view trajectory`, `export trajectory`,
`import analysis`, and `serve`; `tr` is the trajectory alias.

Help and errors are plain terminal text. `-h` and `--help` are equivalent.
Root completion options emit or explicitly install shell completion; ordinary
execution never changes shell configuration. Repeatable sources and selectors,
optional-value bare `-o`, and command exit codes are part of the tested CLI
contract.

Configuration comes only from the workspace selected with `-r`/`--root`, the
current directory and its parents, or `PEVAL_ROOT`. Commands do not accept a
separate config-file path.

## Inputs and adapters

Built-in adapters are `psychevo`, `opencode`, `hermes`, and path-only
`deepagents`. Installed custom adapters register under the
`psycheval.adapters` entry-point group and implement at least one supported
conversion method.

Original JSONL, JSON, SQLite, ATIF, and Trial inputs are read-only. CLI path
selection may infer an adapter and fall back to configuration; workspace Path
and DB sources require unambiguous inference when set to automatic. Export
accepts one effective session, while raw reports may compare repeated inputs.

`view tr -p <trial-dir>` recognizes a Harbor Trial root without an adapter
selector and preserves its Job, Trial, result, reward, timing, failure, Task,
and provenance context. Passing `agent/trajectory.json` reads only that ATIF
document; descendants and globs are not promoted to their parent Harbor Trial.
MultiStepTrial roots expand to one source per Harbor step in recorded result
order. A source without a trajectory remains visible as an inspect diagnostic,
but complete report mode fails rather than synthesizing ATIF evidence.

## Outputs

`view tr` defaults to a bounded inspection digest. `-m raw` produces a complete
JSON report. A bare `-o` chooses a timestamped `.json` path. `export tr` produces
strict ATIF-v1.7. `view tr` has no format option; an explicit `.html` output path
is rejected before any file is written.
Obvious secrets are redacted before serialization unless `--no-redact` is
explicit. Presentation estimates are not written back as portable ATIF facts.

The Live Workspace is the browser presentation surface; the CLI does not emit
offline HTML reports. Wheels contain its authored HTML, CSS, and ESM assets
under `psycheval.assets`, but not the Node test harness or manifests.
