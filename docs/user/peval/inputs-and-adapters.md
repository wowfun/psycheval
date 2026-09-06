# Inputs and Adapters

[简体中文](../../i18n/zh-CN/user/peval/inputs-and-adapters.md)

## Files and ATIF

JSONL accepts one JSON object per line. A line may be a direct message or a
wrapper carrying message, usage, metadata, accounting, and session ordering.
The CLI also reads strict ATIF JSON, supported adapter JSON, Trial cells, and
their contained trajectory artifacts.

## Harbor Trial directories

Use the Harbor Trial root to retain evaluation outcome and provenance alongside
the trajectory:

```console
peval view tr -p <harbor-trial-dir>
```

No adapter selector is required. MultiStepTrial roots produce one source per
Harbor step in result order. Default inspect output can represent a failed or
running step without a trajectory; complete report mode requires every selected
source to have ATIF evidence. Passing `agent/trajectory.json` directly reads
only that ATIF file and does not infer its parent Trial.

In the workspace detail view, administrators can use **Refresh source** for a
linked Harbor Trial to reload its evidence. Copied snapshots have no refresh
action.

## WorkBuddy Office with Harbor

The WorkBuddy Office v1.0 bundle already contains 50 native Harbor Task
directories under `tasks/`; do not convert or copy them. Register the bundle
root on the **Configuration** page, or add a read-only registration to
`peval.toml`:

```toml
[[harbor.datasets]]
id = "workbuddy-office"
path = "/path/to/wb-bench-office-v1.0"
format = "workbuddy.v1"
```

For a cropped bundle, add `allow_partial = true` to that registration. Keep the
original manifest, shared verifier, and complete remaining Task directories.
Default registration still checks that every declared Task is present.

Install the supported external `workbuddy-bench` source revision in the same
environment as Psycheval:

```console
uv pip install --no-deps \
  "workbuddy-bench @ git+https://github.com/Tencent/workbuddy-bench.git@625b2233093ae4f23e76be28c1f341d41cc70373"
```

`--no-deps` preserves the existing Harbor 0.21.0 dependency environment. For
downstream package and lockfile setup, follow
[WorkBuddy runtime installation](../downstream-vendoring.md#install-the-workbuddy-runtime).

Then create a base Harbor Job file containing exactly one Agent. This example
deliberately opts into Psycheval's trusted Linux host environment and uses
OpenCode:

```yaml
job_name: workbuddy-base
n_concurrent_trials: 1
agents:
  - name: opencode
    model_name: xiaomi-token-plan-cn/mimo-v2.5-pro
environment:
  import_path: psycheval.harbor.environment:HostEnvironment
  kwargs:
    allow_host_execution: true
```

Prepare the isolated two-Job plan, run the commands it prints, and compute the
official aggregate after both Jobs finish:

```console
peval harbor prepare -r .local/evaluation \
  --dataset workbuddy-office --config workbuddy-base.yaml
PEVAL_CONFIG=.local/evaluation/peval.toml harbor run -c <printed-normal-config>
PEVAL_CONFIG=.local/evaluation/peval.toml harbor run -c <printed-special-config>
peval harbor summarize -r .local/evaluation --plan <printed-plan-id>
```

For a single Task or a subset, add repeatable `--task/-t` options or a positive
`--limit/-l` to prepare. Filtering uses exact Task directory names; the limit
applies after sorting. Run each returned config, which may be a single Job.
Summaries label subset scope separately from unfinished (`--provisional`) runs.

Windows Host preparation selects a Bash-free Office verifier. Use a
Windows-capable Agent or harness; see the
[native Windows workflow](../downstream-vendoring.md#run-on-native-windows).
The CLI prints PowerShell run commands on Windows.

Host execution expands each Task's workspace archive and creates its clean Git
baseline, but it is not a sandbox and does not reproduce container resource or
network isolation. Use it only for trusted Tasks on Linux or Windows. A Docker-capable
Harbor environment remains the portable path. The special recruiting Task is
kept in the denominator when selected even though the source bundle has documented
missing-input, network-contract, and sanity-check defects; preparation prints
those warnings. The **Datasets** page allows browsing this registration but
offers no mutation controls. Trial detail uses `verifier/score.json` as the
WorkBuddy score, retains Harbor reward separately, and exposes only bounded
verifier evidence. See the [Harbor reference](../../reference/harbor.md) for the
exact runtime, verifier LLM, and aggregation contracts.

```console
peval export tr -a opencode -p session.jsonl -o
peval view tr -m raw -p trajectory-opencode-session.json -o
```

Built-in adapter selection is described by the
[CLI reference](../../reference/cli.md). Use `-d @adapter` for a configured
default DB. List and select retained sessions with `--list`,
`--list-interactive`, and repeatable `-s` selectors:

```console
peval view tr -d @opencode --list
peval view tr -m raw -d @hermes -s '#2' -o
```

With several databases, bind adapters and session IDs by one-based DB index:

```console
peval view tr -m raw \
  -d ~/.hermes/state.db \
  -d ~/.local/share/opencode/opencode.db \
  -a d1=hermes -a d2=opencode \
  -s d1=<hermes-id> -s d2=<opencode-id> -o
```

## Claude Code

Import by ID with an explicit adapter, or read a retained file directly. Both
include its explicitly linked subagents:

```console
peval view tr -a claude -s <session-id>
peval export tr -a claude -s <session-id> -o
```

ID lookup defaults to `~/.claude/projects/`. To use a different root, set it in
`peval.toml` (relative paths resolve from that config file):

```toml
[adapters.claude]
default_session_root = "/path/to/claude/projects"
```

A file path also works for a session copied outside that root:

```console
peval view tr -a claude -p ~/.claude/projects/<project>/<session-id>.jsonl
```

List a project's main sessions, then select by ID or list index:

```console
peval view tr -a claude -p ~/.claude/projects/<project> --list
peval view tr -a claude -p ~/.claude/projects/<project> -s '#1'
peval export tr -a claude -p ~/.claude/projects/<project> -s <session-id> -o
```

Omitting `-s` selects the most recently active session. For several session
directories, qualify selections with `-s p1=<id>` and `-s p2=<id>`; DB selections
continue to use `dN`. `--list-interactive` offers terminal selection.

On **Configuration**, use the single **Session ID or file / directory path**
field. Enter one item per line; IDs and paths can be mixed, and each line reports
its own result. Choose **claude** when entering IDs or paths that do not identify
the adapter. Use **Add source** to import the entered items directly.

For selection, enter one ID or project directory and choose **Inspect sessions**,
then **Add selected**. A directory lists its main sessions; an ID shows its
matching session. Existing paths take precedence over IDs; prefix a relative
path with `./` to treat it as a path even when it does not exist. Editing the
input or adapter clears the previous selection. Inspection shows excluded-file
diagnostics alongside the selectable sessions.
The session table shows update times in UTC to help identify recent activity.
The selected root remains one evaluation source. When it has child trajectories,
its detail view and sidebar provide tree navigation and links between parent tool
results and children. Use **Copy** on the right of a tree row to copy that
session's last Agent message, or use a step block's **Copy** button to copy that
block's content. Each trajectory shows its own metrics. **Refresh
source** in the detail view rereads a native Claude import's selected file and
its linked children; exporting writes a self-contained ATIF tree.

The directory and accounting semantics are owned by the
[CLI reference](../../reference/cli.md) and
[trajectory contract](../../reference/state-and-data.md#trajectories-and-sidecars).

## Custom adapters

An installed distribution registers an adapter in its own `pyproject.toml`:

```toml
[project.entry-points."psycheval.adapters"]
custom = "custom_adapter:CustomAdapter"
```

The adapter implements a supported record, path, or database conversion method;
its exact protocol is owned by source and tests. Put settings under
`[adapters.<id>]` in `peval.toml`.
