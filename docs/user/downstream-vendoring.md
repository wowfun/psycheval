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
uv add "harbor==0.21.0" "PyYAML>=6.0,<7" "pathspec>=1.0,<2"
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
    allow_host_execution: true
agents:
  - import_path: downstream._vendor.psycheval_harbor.agent:ExternalHarnessAgent
    kwargs:
      command: python -m downstream._vendor.psycheval_harbor.psychevo_harness
```

Run the Job through `uv run harbor run -c job.yaml` so the Harbor process and its
children use the downstream environment. The Psychevo harness also requires a
working `pevo` executable. Use the environment's Python executable for Task
verifier scripts:

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

## Install the WorkBuddy runtime

WorkBuddy Office planning and summarization require the external
`workbuddy-bench` distribution in the same environment as Harbor and the copied
integration. Keep its import namespace `workbuddy_bench`: the verifiers reuse
its scoring engine, and summaries use its official metrics module. Copying only its Python directory would omit the distribution metadata
used by runtime validation.

Use the supported Git revision as a normal downstream dependency:

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
`625b2233093ae4f23e76be28c1f341d41cc70373`. A missing distribution, mismatched
version or source commit, or unavailable `CompositeVerifier` fails validation.
If dependency resolution cannot find Harbor 0.21.0, check the configured package
index or mirror before changing the required version.

## Prepare and run WorkBuddy Office

Obtain the `wb-bench-office-v1.0` Dataset bundle separately. Installing
`workbuddy-bench` supplies the runtime, not the Dataset or the system tools used
by its Tasks. Pass the bundle root containing `dataset.toml` and `tasks/` to
`prepare_workbuddy_plan`; no Psycheval workspace registration is needed.
Prepare a new plan if existing artifacts use an unsupported schema; see
[supported plan and summary versions](../reference/harbor.md#workbuddy-office-bundles).

For trusted host execution, provision the Office Python dependencies in the
downstream environment:

```console
uv add beautifulsoup4 python-docx pymupdf openpyxl pandas pdfplumber Pillow python-pptx pytest
```

Provide Git on the host; the Linux verifier also requires Bash. Provision the
selected Agent's own tools and provider configuration separately. For example,
an Agent installer may require Bash, curl, or Node/npm. Run
`validate_workbuddy_host_dependencies()` from the copied `workbuddy` module to
check the required commands and Python imports. This preflight does not install
dependencies or establish container or network isolation; the
[host contract](../reference/harbor.md#host-configuration) describes the execution
boundary.

For Linux, save this as `workbuddy-base.yaml`, replacing `provider/model` with
your model. The Windows harness example follows below:

```yaml
n_concurrent_trials: 1
agents:
  - name: opencode
    model_name: provider/model
environment:
  import_path: downstream._vendor.psycheval_harbor.environment:HostEnvironment
  kwargs:
    allow_host_execution: true
```

Prepare a plan from your downstream application:

```python
from downstream._vendor.psycheval_harbor.workbuddy import prepare_workbuddy_plan

plan = prepare_workbuddy_plan(
    output_root="/evaluation",
    dataset_id="office",
    dataset_path="/data/wb-bench-office-v1.0",
    base_config="workbuddy-base.yaml",
)
print(plan["plan_id"])
for job in plan["jobs"]:
    print(job["config"])
for warning in plan["warnings"]:
    print(warning)
```

Run every returned configuration with `uv run harbor run -c <config-path>`. Keep
the same environment and the output directories until all returned Jobs finish. Then
summarize using the returned plan ID:

```python
from downstream._vendor.psycheval_harbor.workbuddy import summarize_workbuddy_plan

summary = summarize_workbuddy_plan(
    output_root="/evaluation",
    plan_id="<returned-plan-id>",
)
print(summary["metrics"])
```

Your application owns command output and orchestration. The library returns
documents and writes plan and summary artifacts without printing or updating
`peval.toml`. See the
[WorkBuddy contract](../reference/harbor.md#workbuddy-office-bundles) for output
directory ownership, provisional summaries, verifier LLM settings, and known
Office Task defects.

## Select tasks or use a cropped bundle

The same planning workflow accepts a single Task or a subset:

```python
plan = prepare_workbuddy_plan(
    output_root="/evaluation",
    dataset_id="office",
    dataset_path="/data/wb-bench-office-v1.0",
    base_config="workbuddy-base.yaml",
    task_selection=["api-usage-explain-cli-l3-001"],
)
```

Use `limit=5` to take the first five sorted Tasks, optionally after applying
`task_selection`. Names are exact Task directory names, not glob patterns.
Run only the returned Jobs. A normal-only selection does not extract the
recruiting Skill or configure its MCP server.

For a physically cropped bundle, pass `allow_partial=True`. Keep `dataset.toml`,
`shared/`, and complete selected Task directories; the original manifest count
may remain 50. Without this explicit flag, an incomplete download fails
validation. Do not remove individual grader or archive files to crop a Task.

When using the installed `peval` CLI, register the cropped bundle with
`allow_partial = true` in its `[[harbor.datasets]]` TOML table, then select Tasks:

```console
peval harbor prepare --root .local/evaluation --dataset office --config workbuddy-base.yaml -t api-usage-explain-cli-l3-001
```

The summary records `scope="subset"` independently of `provisional`. Its metric
denominator contains the selected Tasks, including missing selected results.
A completed single-Task run is a terminal subset, not a full benchmark result.

## Run on native Windows

Use Python 3.12+, Git, the Office Python packages above, and a Windows-capable
Agent or external harness. The Office verifier needs no Bash. The Agent may use
PowerShell or Git Bash independently; its installer and tools have their own
requirements.

For a downstream harness implementing the
[external-harness contract](../reference/harbor.md#harness-behavior), a base Job is:

```yaml
agents:
  - import_path: downstream._vendor.psycheval_harbor.agent:ExternalHarnessAgent
    kwargs:
      command: '"C:/agent-eval/.venv/Scripts/python.exe" -m downstream.harness'
environment:
  import_path: downstream._vendor.psycheval_harbor.environment:HostEnvironment
  kwargs:
    allow_host_execution: true
```

Replace the interpreter path and harness module. Call `prepare_workbuddy_plan`
from Windows using native paths such as `C:/evaluation` and `D:/datasets/office`.
It automatically selects the copied native Office verifier. Run the returned
configs in PowerShell with `uv run harbor run -c <config-path>`. The `peval`
CLI prints PowerShell commands on Windows, including its workspace config
assignment when needed.

The native verifier adapts only Trial-owned copies and retains an
`office-adaptation.json` audit under verifier logs. Source bundles and scoring
conditions remain unchanged. Unsupported Office execution templates fail
explicitly. See [Host configuration](../reference/harbor.md#host-configuration)
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
exercise renamed imports, synthetic run/resume, WorkBuddy planning, and ATIF
validation without real providers or credentials.
