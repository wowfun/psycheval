# Psycheval CLI Reference

`peval` is the short installed name for the Psycheval CLI. It converts retained
Agent sessions to ATIF, builds reports, and organizes evaluation workspaces; it
is not a Python module and does not run Agents or score Tasks.

## Programmatic and command interfaces

`psycheval.cli.main(argv) -> int` is the programmatic interface and
`psycheval.cli.app` is its Typer application. The editable tool installation
exposes the `peval` command with `init`, `view trajectory`, `publish
evaluation-report`, `export trajectory`, `import analysis`, `harbor prepare`,
`harbor summarize`, and `serve`; `tr`
is the trajectory alias.

Help and errors are plain terminal text. `-h` and `--help` are equivalent.
Root completion options emit or explicitly install shell completion; ordinary
execution never changes shell configuration. Repeatable sources and selectors,
optional-value bare `-o`, and command exit codes are part of the tested CLI
contract.

`init` accepts at most one `--skill <skill-dir>`. Without it, initialization
does not create `.agents/`. The Skill path is resolved from the command's
current directory, independently of `--root`; repeated `--skill` options are an
error. JSON output always includes `agent_skill`, which is `null` without an
install and otherwise contains the installed path and `installed` or `replaced`
action.

Configuration comes only from the workspace selected with `-r`/`--root`, the
current directory and its parents, or `PEVAL_ROOT`. Commands do not accept a
separate config-file path.

`harbor prepare --dataset <id> --config <job.yaml>` requires one registered
`workbuddy.v1` Dataset and a base Harbor Job config containing exactly one Agent.
It rejects preselected Tasks, Datasets, source Jobs, install-only mode, and a
conflicting verifier; preserves the remaining Agent, model, environment, and
concurrency settings; defaults Office runs to three attempts and a timeout
multiplier of two; registers a new isolated Jobs mount; and prints each generated
`harbor run -c ...` commands followed by its summarize command. Generated names
avoid Harbor's reserved `__` delimiter.

Repeatable `--task/-t` selects exact Task directory names; `--limit/-l` takes a
positive number of Tasks after sorting the selection. The command prints one or
two nonempty Job configurations and uses PowerShell syntax on Windows. Cropped
bundles require an explicit `allow_partial=true` registration; selection and
summary scope follow the [WorkBuddy contract](harbor.md#workbuddy-office-bundles).

`harbor summarize --plan <plan-id>` reads that plan and retained Harbor results,
delegates score calculation to the installed WorkBuddy package, and writes a
derived WorkBuddy summary snapshot. It never substitutes the normal Saved View
aggregation.

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

With an initialized workspace, `view tr -r <root> --source-ref <ref>` resolves
either an existing local source or a Harbor source without requiring its path
as input; administrator CLI output may still contain the resolved source path.
A Harbor parent Trial reference expands all phases, while a `/steps/<name>`
reference selects one phase. A local source reference selects its one retained
cell.

`publish evaluation-report` accepts one reviewed Markdown draft and resolves
its `--source-ref` to the canonical report location:

```console
peval publish evaluation-report -r <workspace> \
  --source-ref <ref> -p <approved-draft.md> [--json]
```

Harbor parent and phase references write the parent Trial `analysis.md`; local
references write the existing cell `analysis.md`. A Harbor Trial must be
finished. Publication is an atomic upsert with no evidence, criterion, or
current-report revision arguments and no replace or force option. Repeated and
concurrent valid publications are serialized, and the last completed write
wins. JSON output identifies the normalized source, stable opaque report
reference, relative report location, replacement status, and catalog
reconciliation result without exposing a publication revision.

`import analysis` remains the local-source annotation command and rejects
Harbor source references. Its Markdown import shares the evaluation-report
lock, atomic writer, and catalog reconciliation; JSON import retains its
independent overlay behavior.

## Outputs

`view tr` defaults to a bounded inspection digest. `-m raw` produces a complete
JSON report. A bare `-o` chooses a timestamped `.json` path. `export tr` produces
strict ATIF-v1.7. `view tr` has no format option; an explicit `.html` output path
is rejected before any file is written.
Obvious secrets are redacted before serialization unless `--no-redact` is
explicit. Presentation estimates are not written back as portable ATIF facts.

The Live Workspace is the browser presentation surface; the CLI does not emit
offline HTML reports. The editable source-tool installation serves authored
HTML, CSS, and ESM assets from `psycheval.assets`; the Node test harness and
manifests remain repository-only development inputs.
