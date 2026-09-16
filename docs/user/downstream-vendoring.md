# Vendoring Harbor integration downstream

Use this workflow to embed Psycheval's Harbor integration in your own Python
package. You copy the integration source and install Harbor and any WorkBuddy
runtime into your downstream environment. Installing Psycheval itself is not
required. The [Harbor reference](../reference/harbor.md) owns the API and runtime
contracts.

The examples assume Python 3.12 or newer and an existing, installable `downstream`
package managed with uv. Run commands from that project's root and replace the
example package and data paths with your own.

## Copy the source and install dependencies

Copy the complete `src/psycheval/harbor` directory to
`src/downstream/_vendor/psycheval_harbor`. Preserve the internal layout and source
files, omit generated `__pycache__` directories, and include the repository's
[LICENSE](../../LICENSE) alongside the copy. Ensure that `downstream` and
`downstream._vendor` are importable parent packages. Record the Psycheval source
commit in your dependency tracking so later updates replace the same source unit.

Add the integration's dependencies to your downstream project:

```console
uv add "harbor==0.21.0" "PyYAML>=6.0,<7" "pathspec>=1.0,<2" "httpx>=0.28,<1"
```

Commit the resulting `pyproject.toml` and `uv.lock`; use `uv sync --locked` to
reproduce the environment. The direct dependency constraints are maintained in
Psycheval's [pyproject.toml](../../pyproject.toml). Harbor installs its own
transitive dependencies.

Install your downstream package in this environment, including the copied
subtree in its package configuration. Harbor and child harnesses must be able
to import it while running from a Task workdir, outside your checkout. A uv
project with a configured build system installs its package during sync.

## Set the copied import paths

For an external harness Job, use your package namespace:

```yaml
environment:
  import_path: downstream._vendor.psycheval_harbor.environment:HostEnvironment
  kwargs:
    host_access:
      filesystem: true
      process: true
agents:
  - import_path: downstream._vendor.psycheval_harbor.agent:ExternalHarnessAgent
    kwargs:
      command: python -m downstream._vendor.psycheval_harbor.psychevo_harness
verifier:
  import_path: downstream._vendor.psycheval_harbor.verifier.host:HostVerifier
```

Run the Job through `uv run harbor run -c job.yaml` so the Harbor process and its
children use the downstream environment. The Psychevo harness also requires a
working `pevo` executable. Use the environment's Python executable for Task
verifier scripts. The selected Host verifier supplies the path-mapping protocol
while those scripts run:

```console
python -m downstream._vendor.psycheval_harbor.verifier /tests/grader.json
```

Resolve an existing flat Harbor Dataset directly from its root:

```python
from downstream._vendor.psycheval_harbor.datasets import resolve_harbor_dataset

dataset = resolve_harbor_dataset(dataset_id="suite", path="/data/tasks")
```

Copying source does not rewrite external Dataset scripts or Job configurations.
Keep the `PEVAL_CONFIG` locator and runtime document fields unchanged; see
[Host configuration](../reference/harbor.md#host-configuration) for their meaning
and the trusted-host execution boundary.

## Configure a host workspace

Configure the copied Host directly in an ordinary Harbor Job:

```yaml
environment:
  import_path: downstream._vendor.psycheval_harbor.environment:HostEnvironment
  kwargs:
    host_access:
      filesystem: true
      process: true
    workdir_root: /workspaces
    workspace_source: /projects/my-project
```

Use native absolute paths for direct Harbor runs. Omit `workspace_source` to
initialize from the Task alone, and use the default `~/workspaces` root or an explicit absolute root. The default `workspace_baseline: git` requires Git and process
access; a filesystem-only Agent must set `workspace_baseline: none`. The
[host contract](../reference/harbor.md#host-configuration) defines merge conflicts,
copy exclusions, ownership, and WorkBuddy restrictions.

After Harbor has started the environment, a downstream Agent can use the
generic Host filesystem and process capabilities according to its own execution
model:

```python
async def run(self, instruction, environment, context):
    work_dir = environment.work_dir
    await environment.ensure_dirs(["/workspace/output"], chmod=False)
    # The Agent chooses how to execute its instruction using this work_dir.
```

No Host subclass or private initializer is needed. `path_mapper`, transfers,
and native filesystem operations use the same initialized workspace. An Agent
that needs local process execution must request both policy capabilities; an
Agent that owns another execution backend can use filesystem-only access with
`workspace_baseline: none`.

For a generic filesystem-only downstream Agent:

```yaml
environment:
  import_path: downstream._vendor.psycheval_harbor.environment:HostEnvironment
  kwargs:
    host_access:
      filesystem: true
      process: false
    workspace_baseline: none
```

Its `exec` and `exec_argv` calls fail explicitly; uploads, downloads, directory
operations, and `path_mapper` remain available after startup.

For WorkBuddy configuration adaptation, set an absolute `workdir_root` in the `JobConfig`
or pass explicitly parsed `HostSettings`. `runtime_config.load_host_settings`
resolves paths relative to its selected TOML file; the adapter accepts only
absolute roots. The [Host contract](../reference/harbor.md#host-configuration)
owns the precedence and path rules. The Python workflow below needs no TOML
file or Psycheval workspace registration.

## Install the WorkBuddy runtime

WorkBuddy verification and metrics require the external
`workbuddy-bench` distribution in the same environment as Harbor and the copied
integration. Keep its import namespace `workbuddy_bench`: the verifiers reuse
its scoring engine, and summaries use its official metrics module. Copying only its Python directory would omit the distribution metadata
used by runtime validation.

Pin the reference Git revision as a normal downstream dependency for reproducible
installation:

```console
uv add "workbuddy-bench @ git+https://github.com/Tencent/workbuddy-bench.git@625b2233093ae4f23e76be28c1f341d41cc70373"
```

Keep the `harbor==0.21.0` constraint added above. In the supported WorkBuddy
[pyproject.toml](https://github.com/Tencent/workbuddy-bench/blob/625b2233093ae4f23e76be28c1f341d41cc70373/pyproject.toml),
the Harbor `v0.18.0` pin belongs to the upstream development `tool.uv.sources`
table; its package dependencies declare `harbor` without that pin. Downstream
dependency resolution should retain your explicit Harbor constraint. uv records
the Git source in your project and lockfile; see
[uv's Git dependency workflow](https://docs.astral.sh/uv/concepts/projects/dependencies/#git).

### Add to an existing environment

To augment an environment that already has Harbor 0.21.0 and its complete
dependencies, install the pinned runtime directly:

```console
uv pip install --python .venv/bin/python --no-deps "workbuddy-bench @ git+https://github.com/Tencent/workbuddy-bench.git@625b2233093ae4f23e76be28c1f341d41cc70373"
```

On Windows, use `.venv/Scripts/python.exe`. `--no-deps` preserves the existing
dependency environment. WorkBuddy's Pydantic, PyYAML, FastAPI, Uvicorn, and HTTPX
requirements are already covered by a complete Harbor installation. This
command changes the environment only; an exact `uv sync` can remove packages
absent from the downstream lockfile. Use the project dependency workflow above
for an environment managed by `uv sync`.
The remaining `uv add` and `uv run` examples assume that project workflow.

### Check the installation

Run this with that environment's Python, using your copied module path:

```python
from importlib.metadata import version

from downstream._vendor.psycheval_harbor.workbuddy import validate_workbuddy_runtime
from workbuddy_bench.scorer.metrics import compute_job_metrics

assert version("harbor") == "0.21.0"
assert callable(compute_job_metrics)
print(validate_workbuddy_runtime())
```

For the Git installation above, the result contains version `0.1.0` and commit
`625b2233093ae4f23e76be28c1f341d41cc70373`. Runtime validation follows the
[WorkBuddy compatibility contract](../reference/harbor.md#workbuddy-tasks).
If dependency resolution cannot find Harbor 0.21.0, check the configured package
index or mirror before changing the required version.

## Prepare and run WorkBuddy

Obtain Tasks separately and provision their native dependencies. Configure
Harbor's Task collection, Agent, and execution environment explicitly. Preparation
accepts any WorkBuddy verifier contract, without an Office ID or count check.
For example, with a preinstalled OpenCode CLI:

```python
import subprocess
from pathlib import Path

import yaml
from harbor.models.job.config import DatasetConfig, JobConfig
from harbor.models.trial.config import AgentConfig, EnvironmentConfig
from downstream._vendor.psycheval_harbor.workbuddy import (
    compute_official_metrics,
    prepare_workbuddy_job,
)

base = JobConfig(
    datasets=[DatasetConfig(path=Path("path/to/tasks").resolve())],
    agents=[
        AgentConfig(
            import_path="downstream._vendor.psycheval_harbor.opencode:HostOpenCodeAgent",
            model_name="provider/model",
        )
    ],
    environment=EnvironmentConfig(
        import_path="downstream._vendor.psycheval_harbor.environment:HostEnvironment",
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

The adapter returns a private JobConfig without creating files. The application
owns YAML export and Harbor execution; native defaults apply. Set attempts and
timeout multiplier explicitly when reproducing a benchmark preset.

Select individual Tasks with `JobConfig.tasks`, or use `DatasetConfig.task_names`,
`exclude_task_names`, and `n_tasks`. Skills and MCP servers use native Task/Agent
fields. No registration or full-bundle count is required to execute a selection.
To browse retained results, associate `config.jobs_dir` with a registered Dataset
using the [workspace controls](peval/workspace.md). The
[WorkBuddy contract](../reference/harbor.md#workbuddy-tasks) owns plugin, path,
metrics, and read-only source semantics.

## Run on native Windows

Use Python 3.12+, Git when the Task requires it, Task dependencies, and a Windows-capable
Agent or external harness. The Office verifier needs no Bash. The Agent may use
PowerShell or Git Bash independently; its installer and tools have their own
requirements.

For a preinstalled OpenCode CLI, configure the native host adapter on a fresh
JobConfig from the Python workflow above:

```python
base = JobConfig(datasets=[DatasetConfig(path=Path("path/to/tasks").resolve())])
base.n_attempts = 1
base.agents = [
    AgentConfig(
        import_path="downstream._vendor.psycheval_harbor.opencode:HostOpenCodeAgent",
        model_name="provider-name/model-name",
        env={"OPENCODE_PROVIDER_KEY": "${OPENCODE_PROVIDER_KEY}"},
        kwargs={
            "opencode_config": {
                "provider": {
                    "provider-name": {
                        "options": {"apiKey": "{env:OPENCODE_PROVIDER_KEY}"},
                    },
                },
            },
        },
    ),
]
base.environment = EnvironmentConfig(
    import_path="downstream._vendor.psycheval_harbor.environment:HostEnvironment",
    kwargs={"host_access": {"filesystem": True, "process": True}},
)
```

Set `OPENCODE_PROVIDER_KEY` in the launching process. The adapter uses separate
Trial state; see its [contract](../reference/harbor.md#native-opencode) for supported
configuration and retained evidence.

For a downstream harness implementing the
[external-harness contract](../reference/harbor.md#harness-behavior), replace
`base.agents` while keeping that explicit Host environment:

```python
base.agents = [
    AgentConfig(
        import_path="downstream._vendor.psycheval_harbor.agent:ExternalHarnessAgent",
        kwargs={
            "command": '"C:/path/to/downstream/.venv/Scripts/python.exe" -m downstream.harness',
        },
    ),
]
```

Replace the interpreter path and harness module. Call `prepare_workbuddy_job(base)`
from Windows using native absolute paths, then export the returned model as in
the workflow above. Enable UTF-8 for Harbor's Task reader and console:

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
uv run --no-sync harbor run -c <config-path>
```

The native verifier adapts only Trial-owned copies and retains an
`office-adaptation.json` audit under verifier logs. Source bundles and scoring
conditions remain unchanged. Source adaptation is best effort, with unrecognized
grader expressions retained and recorded in the audit. See
[Host configuration](../reference/harbor.md#host-configuration)
for process, path, and native-platform acceptance semantics.

## Copy ATIF validation separately

To validate ATIF without Harbor, copy only `src/psycheval/atif.py` and LICENSE.
You can rename the file to fit your package. It uses only the standard library:

```python
from downstream._vendor.atif import validate_atif_trajectory

validate_atif_trajectory(trajectory)  # Raises ValueError with a field path.
```

Keep adapter conversion in `psycheval.conversion`; it is outside this copy unit.
The repository's [source-copy tests](../testing.md#downstream-source-copy-checks)
exercise renamed imports, synthetic run/resume, WorkBuddy configuration adaptation, and ATIF
validation without real providers or credentials.
