# Psycheval CLI Reference

`peval` is the short installed name for the Psycheval CLI. It converts retained
Agent sessions to ATIF, builds reports, and organizes evaluation workspaces; it
is not a Python module and does not run Agents or score Tasks.

## Programmatic and command interfaces

`psycheval.cli.main(argv) -> int` is the programmatic interface and
`psycheval.cli.app` is its Typer application. The editable tool installation
exposes the `peval` command with `init`, `view trajectory`, `publish
evaluation-report`, `export trajectory`, `import analysis`,
and `serve`; `tr` is the trajectory alias.

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

WorkBuddy configuration and official metrics use the Python
[WorkBuddy interface](harbor.md#workbuddy-tasks). Applications run Harbor and
associate its Jobs directory through the existing workspace mount controls.
See the [Python workflow](../user/peval/inputs-and-adapters.md#workbuddy-with-harbor).

## Inputs and adapters

Built-in adapters are `psychevo`, `opencode`, `hermes`, and file adapters
`deepagents` and `claude`. Installed custom adapters register under the
`psycheval.adapters` entry-point group and implement at least one supported
conversion method.

Original JSONL, JSON, SQLite, ATIF, and Trial inputs are read-only. CLI path
selection may infer an adapter and fall back to configuration; workspace Path
and DB sources require unambiguous inference when set to automatic. Export
accepts one effective session, while raw reports may compare repeated inputs.

Claude Code accepts a retained JSONL file or a single project directory through
`-p`. Directory listing includes top-level main sessions, ordered by latest valid
event time descending, then session ID; unknown times always sort last. An omitted session selector chooses the
first session. Malformed or empty files and all files with an ambiguous duplicate
session ID are excluded; CLI listing and workspace session inspection show the
exclusion diagnostics. A sidechain record alone does not hide an otherwise main
session. Listing streams each file without retaining its conversation content.
One directory load reuses one listing for all selectors and concrete paths.
`--list` and `--list-interactive` support session directories and
databases. CLI and workspace session tables display the adapter's update time in
UTC, or `-` when unknown. Claude uses its latest valid event timestamp; Psychevo
and OpenCode use their stored session update time, and Hermes uses its latest
active message time, falling back to session end or start time.
Repeatable `-s` accepts IDs and list indexes; `pN=ID` selects a session
from path input N and `dN=ID` selects one from database input N. A bare selector
requires exactly one session-selectable input. Interactive selection requires
one such input and a terminal.

With no `-p` or `-d`, an explicit `-a claude -s <session-id>` resolves exact IDs
against `adapters.claude.default_session_root`. It checks `<id>.jsonl` in that
root and its immediate project directories, verifies the recorded identity,
and rejects missing, conflicting, or ambiguous matches. It skips linked files
and project directories and never recursively scans HOME or unrelated logs.
This lookup accepts exact IDs, not listing indexes or `pN`/`dN` selectors.
An explicitly supplied project directory may itself be a symbolic link. Listing
reads only that directory's top-level regular JSONL files; it does not traverse
nested directories or follow linked JSONL files. Linked subagent reads remain
subject to the [trajectory ownership checks](state-and-data.md#trajectories-and-sidecars).

Claude imports explicitly linked subagents recursively into the selected root's
ATIF. Directory selection resolves to concrete session files, so refreshing an
import keeps its selected session even when another session becomes newer. One
root with children is one exportable session and one workspace evaluation source.
The workspace session input accepts one Session ID, file, or directory per line,
including mixed batches, with independent results in input order shown beneath
the form. Existing paths
take precedence. With an explicit adapter, a bare identifier that is not an
existing path is resolved as a Session ID; `./` forces a relative path.
Inspection accepts one such input and offers the same directory session selection
or the one matching Claude session. Explicit `session_id`/`session_ids` selections
require one source and cannot be combined with multiple path lines.
An unrecognized directory reports that an adapter must be chosen; an explicitly
selected adapter without directory support reports that capability mismatch.

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
