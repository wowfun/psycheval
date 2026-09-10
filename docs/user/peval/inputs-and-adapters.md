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

## WorkBuddy with Harbor

Any Harbor Task declaring the WorkBuddy verifier contract can run in a compatible
environment. Install the pinned runtime using the
[installation workflow](../downstream-vendoring.md#install-the-workbuddy-runtime)
and provision the Task and Agent dependencies. Registration in Psycheval is
optional for execution.

This Python workflow uses a preinstalled OpenCode CLI on a trusted native Host.
Replace the Task collection path and model identifier with your own:

```python
import subprocess
from pathlib import Path

import yaml
from harbor.models.job.config import DatasetConfig, JobConfig
from harbor.models.trial.config import AgentConfig, EnvironmentConfig
from psycheval.harbor.workbuddy import compute_official_metrics, prepare_workbuddy_job

base = JobConfig(
    datasets=[DatasetConfig(path=Path("path/to/tasks").resolve())],
    agents=[AgentConfig(
        import_path="psycheval.harbor.opencode:HostOpenCodeAgent",
        model_name="provider/model",
    )],
    environment=EnvironmentConfig(
        import_path="psycheval.harbor.environment:HostEnvironment",
        kwargs={"host_access": {"filesystem": True, "process": True}},
    ),
)
config = prepare_workbuddy_job(base)
yaml_path = Path("job.yaml")
yaml_path.write_text(yaml.safe_dump(config.model_dump(mode="json")), encoding="utf-8")
subprocess.run(["harbor", "run", "-c", str(yaml_path)], check=True)
job_dir = config.jobs_dir / config.job_name
print(compute_official_metrics(job_dir))
```

Harbor defaults to one attempt, a timeout multiplier of 1.0, and
`./jobs/<job_name>`. Set `base.n_attempts = 3` and
`base.timeout_multiplier = 2.0` before preparation when reproducing that
WorkBuddy benchmark configuration. Host workspaces default to `~/workspaces`.
Preparation returns a private model and writes no files. YAML export and
execution in this example belong to the application.

For a single Task, use `JobConfig.tasks`; for a subset, use Harbor's
`DatasetConfig.task_names`, `exclude_task_names`, and `n_tasks`. Declare Skills
and MCP servers through the native Task/Agent fields. Task names never trigger
special configuration. Metrics use the retained Job lock for the selected Task
denominator, including missing results, and return an on-demand snapshot.

To browse results, register the Dataset on **Configuration** and add
`config.jobs_dir` as a Jobs mount associated with that Dataset. A WorkBuddy
registration uses `format = "workbuddy.v1"`; use `allow_partial = true` if a
manifest declares more Tasks than the cropped bundle contains. See
[workspace controls](workspace.md). Trial detail reads canonical verifier scores
and Harbor rewards directly; no separate WorkBuddy summary is stored.

The Host is trusted native execution. It stages scoring materials outside the
Agent workspace and uses neutral generated paths to reduce incidental evaluation
clues. It does not reproduce container builds or isolate access. Tasks still
require their own platform and dependencies. The recognized Windows Python/pytest
format has a Bash-free adapter; see the
[native Windows workflow](../downstream-vendoring.md#run-on-native-windows).
The [Harbor contract](../../reference/harbor.md#workbuddy-tasks) owns exact semantics.

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
