# peval-py

Language: English | [简体中文](README.zh-CN.md)

`peval-py` is the lightweight Python edition of `peval` for retained agent
trajectories. It reads JSONL sessions or adapter-owned SQLite databases and
writes ATIF JSON or static peval-style reports.

## Install From A Checkout

Install the local Python tool once with `uv`:

```bash
uv tool install --editable ./tools/peval-py
```

Then use the shorter command directly:

```bash
peval-py --help
peval-py view tr --help
```

The CLI uses plain-text help and exposes Typer's shell completion setup at the
root command. Inspect the script or install it explicitly; ordinary commands do
not change shell configuration:

```bash
peval-py --show-completion
peval-py --install-completion
```

Run it from the source tree without installing:

```bash
uv run --project tools/peval-py peval-py --help
```

## Build A Local Binary

`peval-py` uses `pandas` for inspect-mode tabular analysis; `uv` installs that
runtime dependency from `tools/peval-py/pyproject.toml`. Build on the same
operating system and CPU architecture where you plan to run the file. Keep
generated artifacts under `.local/`; the repository ignores that directory.

PyInstaller is the simplest single-file path:

```bash
cd /path/to/psycheval

uv run --project tools/peval-py --with pyinstaller pyinstaller \
  --onefile \
  --name peval-py \
  --paths tools/peval-py/src \
  --distpath .local/peval-py-build/dist \
  --workpath .local/peval-py-build/work \
  --specpath .local/peval-py-build/spec \
  tools/peval-py/src/peval_py/cli/__main__.py
```

Run the packaged command and check a fixture-backed report:

```bash
.local/peval-py-build/dist/peval-py --help

.local/peval-py-build/dist/peval-py view tr \
  -m raw \
  -a opencode \
  -p tools/peval-py/tests/fixtures/common_session.jsonl \
  -o .local/peval-py-build/report.json

python3 -m json.tool .local/peval-py-build/report.json >/dev/null
```

Nuitka is another option if you want a compiled-Python build and have a native
C compiler, but check its output size and startup behavior on your target
platform before choosing it.

## Usage Guide

Use `-a ADAPTER` to set the default adapter for all inputs. For comparison
reports, repeat `-a` with `pN=ADAPTER` or `dN=ADAPTER` to parse individual
path or DB inputs with different adapters.

`view tr` defaults to bounded inspect mode for large-file-friendly exploration:

```bash
peval-py view tr -a opencode -p session.jsonl
```

Inspect output is a compact fixed JSON digest with session identity, token
totals, active duration in seconds, step/tool duration distributions, top
duration/token rows, and tool errors when available. `--head` and `--tail`
default to 2, `--top` defaults to 5, `--steps <ids>` adds selected step
evidence and accepts comma/range selectors such as `1,3:5`, and `--tool-call
<tool_call_id>` independently shows a tool call with its matching tool result
when retained data provides one. `--max-content-chars` bounds inspect preview
text. Bare `-o` writes a timestamped report file and prints the saved path to
stdout.

Use `-m raw` when you want the full peval JSON or HTML report:

```bash
peval-py view tr -m raw -a opencode -p session.jsonl -f html -o report.html
```

Raw report mode also accepts conversion/display overrides such as
`--agent-name`, `--agent-version`, `--model`, and `--no-redact`; default inspect
mode rejects those flags.

Adapter TOML tables may set `default_db_path`; relative values resolve from
the TOML file that defines them. Use `-d @adapter` to expand that configured
DB path and bind the DB input to the same adapter.

Use `-r, --root DIR` with `view tr` or `export tr` when you want to load an
existing peval-py workspace's `peval-py.toml` from outside the workspace. This
selects workspace config such as locale, `analysis_eval_slug`, adapter
defaults, and `default_db_path`; it does not initialize or modify the
workspace. Run `peval-py init -r DIR` first when the workspace does not yet
contain `peval-py.toml`.

```bash
peval-py view tr -r .local/peval-py -d @opencode --list
peval-py export tr -r .local/peval-py -d @opencode -s <session-id> -o
```

Use `--source-alias N=TEXT` to add display-only source names. Aliases improve
report readability without changing session ids, trial keys, source identity,
or Evidence/Input Source paths. In the Leaderboard, the canonical Session
column stays unchanged. Harbor rows use a separate Task / Alias column that
falls back to Task name and keeps the Task visible beneath a custom alias.

In comparison reports, the Leaderboard Duration column is derived from JSON
`trajectory_meta[].duration_ms`, which stores active agent/tool work time. Long
retained-session idle gaps are kept separately as `wall_duration_ms`. The
Leaderboard and `serve` Source Manager also show Last Turn End from
`trajectory_meta.finished_at_ms`.

When a peval-py workspace root is selected with `view tr -r <workspace>` or
discovered from the current directory, reports also try to read cached peval
cell analysis from
`runs/<analysis_eval_slug>/<agent-id>/<session-id>/<cell_key>/analysis.json`
and `analysis.md`. The default slug is `default`; matching summaries and
Markdown reports appear in the selected Trial Analysis section and in JSON
`annotations.analysis[]`. The `<cell_key>` is the rendered Trial key normalized
for a path segment.

The same task tree can also provide manual Trial notes at
`runs/<analysis_eval_slug>/<agent-id>/<session-id>/<cell_key>/notes.md`.
These appear in JSON `annotations.notes[]` before CLI notes. In
`peval-py serve`, local Trial artifacts use that cell-local `notes.md`, while
Harbor sources use `harbor/<mount-id>/<job>/<trial>/notes.md` in the workspace;
immutable local snapshot artifacts remain read-only. Session-root `analysis.json`,
`analysis.md`, and `notes.md` are reserved for session-level artifacts and are
not read into Trial reports in this version.
When serving snapshots or mounted Harbor Trials, current workspace-side `analysis.json`,
`analysis.md`, and `notes.md` are overlaid when the active report is composed,
so reload or Refresh can show note/analysis changes even if the original source
DB or file no longer refreshes successfully.

`peval-py serve` keeps static reports CDN-based, but serves ECharts local-first
from `<workspace>/.cache/echarts/6.0.0/echarts.min.js` and falls back to the
fixed CDN URL if the local script fails. Its Source Manager exposes configured
default DB paths through the SQLite DB form's Save/Clear default actions, alias
editing, Last Turn End sorting, and an
English/Simplified Chinese selector that persists top-level `locale` in
`peval-py.toml`. Its Harbor section adds, edits, and removes read-only mounts
with a stable ID, one Jobs root, and optional Task/Dataset paths. The Path source
field also accepts another workspace root,
`runs/`, `runs/<analysis_eval_slug>`, or a directory above Trial cells; serve
recursively imports complete cells into the current workspace as snapshots and
leaves the external workspace unchanged.

Allowlisted Harbor Tasks contribute live keywords to display tags. The
Leaderboard, Saved Views, Summary, Selected Trial evidence, JSON/snapshot
reports, inspection, and XLSX exports also expose Task, Job, Trial, provider,
reward dimensions, timing, and provenance. Live Task metadata stays usable when
its digest differs from the historical Trial lock and is labeled accordingly.
Package or Git artifact refs remain provenance and are not compared with a live
local Task digest.

`peval-py serve` can also attach an existing Markdown or HTML analysis report
to one or more sessions. Select visible Leaderboard rows, choose
`Attach report (N)`, and pick one local `.md`, `.markdown`, `.html`, or `.htm`
file. The Reports column opens attached files in a sandboxed left-side preview.
Use the toolbar's Reports Manager to preview imported reports, replace their
bindings across readable active and archived sessions, or permanently delete
them. This workflow is serve-only and does not change exported report JSON or
static HTML reports.

Each imported report is copied to `<workspace>/reports/<id>/` with a
`state.json` that contains only logical source references:

```json
{
  "source_refs": [
    "runs/default/agent-a/c2/c2_t001"
  ]
}
```

References may also use `harbor/<mount-id>/<job>/<trial>`. You can edit these
bindings by hand. A source that cannot be found is retained without rewriting
`state.json`, and its association returns if the same source reference becomes
readable again. Imports accept one UTF-8 file up to 20 MiB and
copy only that file. Relative sibling images, styles, scripts, and other assets
are not imported; embed them in the report or use external URLs when needed.

For reporting, comparison, and custom adapter examples, read
[peval-py Documentation](../../docs/peval-py/README.md).
