# Harbor Integration

Psycheval supports the public Harbor `0.21.0` contract through
`psycheval.harbor`.

## Public seams

- `psycheval.harbor.agent:ExternalHarnessAgent` runs a configured external
  process and loads its current-invocation ATIF output.
- `psycheval.harbor.environment:HostEnvironment` executes directly on a trusted
  native host.
- `psycheval.harbor.hermes:HermesAgent` is the pinned Harbor compatibility
  adapter for current Hermes provider and exact-session behavior.
- `psycheval-psychevo-harness` is the external-harness command for Psychevo.
- `psycheval.harbor.verifier` implements shared evidence and artifact scoring.
- `psycheval.harbor.datasets` resolves registered flat Harbor Datasets and
  `workbuddy.dataset.v1` bundles without importing Dataset-owned Python code.

## WorkBuddy Office bundles

The Python Dataset services take keyword-only `dataset_id`, `path`, and
`format` (default `"harbor"`), and return `ResolvedHarborDataset`. The
application owns workspace registration and mount selection. WorkBuddy's
`prepare_workbuddy_plan` takes `output_root`, `dataset_id`, `dataset_path`, and
`base_config`; it fully validates the WorkBuddy Dataset itself.
`summarize_workbuddy_plan` takes `output_root`, `plan_id`, and optional
`provisional`. Both return their canonical document and write only owned
artifacts below `output_root/harbor-plans` and `output_root/harbor-jobs`.
`discover_workbuddy_summaries` reads an explicit output root and Dataset ID set.
These services neither discover a workspace nor read or write its `peval.toml`,
and do not print. The `peval` CLI owns those application operations.
Empty or whitespace-only path strings are rejected; `"."` and `Path(".")`
explicitly select the current directory. A `Path` object has already normalized
its input, so `Path("")` has the same meaning as `Path(".")`. Dataset identifiers
must be strings and are trimmed before validation; retained plan IDs are exact
identities and are not trimmed. Dataset services report invalid inputs as
`HarborDatasetError`, and plan documents use the validated Dataset identity.

The caller owns a trusted output directory. Psycheval checks for directory
symlinks at reservation and read boundaries and rechecks newly created
directories. These checks do not isolate concurrent directory replacement:
the caller must prevent replacement of output directories while preparation,
summarization, or the external WorkBuddy scorer uses them. YAML and JSON outputs
use exclusively created temporary files and atomic replacement; failed writes
leave an existing destination intact.

Psycheval recognizes a registered `workbuddy.dataset.v1` bundle as a read-only
Dataset whose Harbor Tasks live below the manifest's `layout.task_root`.
Dataset workbench registration and updates validate the bounded UTF-8 manifest,
declared CompositeVerifier contract, contained task root, task count, bounded
UTF-8 Task text, shared verifier inputs, and regular workspace archives.
Discovery never imports or executes external package code. Ordinary mount and
workbench reads resolve only the bounded manifest, contained task root, declared
count, and immediate Task names; the shared Task index validates Task content
as it is associated with Trials. Loading a hand-edited `peval.toml` performs the same lightweight layout
resolution as other read paths, not full registration validation. Workbench
registration/updates and `peval harbor prepare` are the full-bundle validation
gates, so read paths do not re-walk every Task merely to locate the
allowlisted root. A selected read-only Task derives its revision from current
tree metadata instead of hashing archive bodies, and an existing instruction is
the default preview even though it is not editable. Bundle and plan readers use
non-blocking, no-follow file opens before accepting regular files.

`workbuddy.v1` currently denotes the pinned WorkBuddy Office v1.0 profile, not
an open-ended family of WorkBuddy manifests. A different WorkBuddy Dataset
profile requires an explicit Psycheval contract update.

`peval harbor prepare` converts a validated WorkBuddy registration plus one
ordinary Harbor `0.21.0` Job config into a reproducible run plan. It does not run
Harbor. The plan owns an isolated Jobs root and two configs: the normal Office
tasks and the one Skill/MCP task. This split is required because Harbor `0.21.0`
has no per-Task Agent override. The external `workbuddy_bench` runtime supplies
`workbuddy_bench.judge:CompositeVerifier`; Psycheval does not vendor that runtime
or replace its scoring policy. The supported runtime source is commit
`625b2233093ae4f23e76be28c1f341d41cc70373`; source installations are checked
against that commit in addition to package version `0.1.0`.

With no verifier LLM variables, the run uses WorkBuddy's deterministic rule
score. The optional variables `WORKBUDDY_VERIFIER_LLM_BASE_URL`,
`WORKBUDDY_VERIFIER_LLM_API_KEY`, and `WORKBUDDY_VERIFIER_LLM_MODEL` are
all-or-none; `WORKBUDDY_VERIFIER_LLM_MAX_OUTPUT_TOKENS` is optional. Secret values
remain environment references and are never copied into a plan manifest.

`peval harbor summarize` calls WorkBuddy's installed `compute_job_metrics`
against the isolated two-Job root and all 50 expected Tasks. By default both Jobs
must be terminal; `--provisional` permits a partial snapshot. Summarization
revalidates the installed runtime and requires the identity recorded by
preparation. The known
`recruiting-search-skill-mock-mcp-hardened` source defects and its public-network
exception remain included and prominently warned; Psycheval neither patches nor
reweights that Task.

Skill extraction rejects `.git` path components case-insensitively and accepts
the Skill root archive entry only as a directory. Extracted files retain their
read and execute permissions but lose group/other write permission; conflicting
duplicate archive entries are still compared using their original modes.

## Host configuration

Host execution is opt-in with `allow_host_execution=true` and is not a sandbox.
The parent `PEVAL_CONFIG` may name a user `peval.toml`; Harbor reads only
`[harbor.host].workdir_root`. Omission defaults to `~/workspaces`, while an
empty string keeps Trial-temporary workdirs. Unknown host fields fail closed and
the user file is never modified.

Each child process receives `PEVAL_CONFIG` pointing to a permission-restricted
effective `peval.json`. That runtime document contains native paths, the Python
executable, and, for external harnesses, protocol version 2 with `run` or
`resume`. The user TOML and effective JSON are different interfaces despite
sharing the environment-variable locator at different process boundaries.
Command environment overrides are applied to the host process. When a command
overrides `HOME` without explicitly setting `NVM_DIR`, HostEnvironment removes
the inherited host `NVM_DIR` so Node installers cannot accidentally target a
different home; an explicit command `NVM_DIR` remains authoritative.

HostEnvironment supports native Linux and Windows adapters. Windows acceptance
requires the remote Windows CI job; Linux or WSL results do not establish native
Windows behavior.

`bootstrap_workbuddy_workspace=true` is an additional explicit trusted-host
opt-in for WorkBuddy Office Tasks. It accepts only a bounded YAML document with
that bundle's inert Compose metadata shape, safely expands the regular
`workspace.tar.gz` into the mapped
workspace, exposes that directory to Task commands as `/workspace`, and creates
the clean Git baseline required by diff capture. Repeated archive members are
accepted only when their type, mode, size, and content are identical. A
bootstrap opens the archive non-blockingly without following a replacement
symlink, ignores inherited `GIT_*` process state, and disables repository hooks
while creating the baseline. Extracted WorkBuddy Skill paths apply the same cross-platform
absolute, traversal, and separator checks. A
prepared host Job also clears unenforceable Task resource requests, disables
image builds, and uses host-relative MCP paths. It does not execute Dockerfile
instructions or install their declared system/Python dependencies; those remain
an exact preflight responsibility of the host. This mode provides no container,
network, user, or resource isolation.

## Harness behavior

ExternalHarnessAgent supplies the instruction on stdin, uses the selected Task
or mounted workspace cwd, removes stale trajectory output before invocation,
and fails on invalid commands, timeout, non-zero exit, missing output, or
malformed ATIF. Resume requires retained native state and cannot silently start
a fresh session.

Psychevo state is Trial-owned under Agent logs, so evaluation does not open the
user's persistent database. Hermes likewise resumes and exports an exact native
session. Both project only the current invocation for step-local scoring.

## Copying into a downstream package

Copy the entire `src/psycheval/harbor` directory into your importable package,
for example `downstream/_vendor/psycheval_harbor`. Keep its internal layout and
copy the repository's [LICENSE](../../LICENSE) alongside it. Record the source
commit in your downstream dependency tracking so later updates can replace the
same source unit. No source rewriting or Psycheval installation is required.

Use Python 3.12 or newer with `harbor==0.21.0`, PyYAML, and pathspec; their direct
dependency constraints are maintained in [pyproject.toml](../../pyproject.toml).
WorkBuddy execution additionally needs the runtime and host dependencies
described above. Harbor has its own transitive dependencies; source copying
does not remove those. The copied subtree needs no Psycheval workspace, Web
assets, report code, or adapter entry-point registry.

Set Harbor Job import paths to the copied modules:

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

Use the environment's Python executable in Task verifier scripts:

```console
python -m downstream._vendor.psycheval_harbor.verifier /tests/grader.json
```

The host and Agent supply `PEVAL_CONFIG` as described above. Namespace changes
do not rename that locator, runtime JSON fields, schema identifiers, or Agent
identities. The caller owns downstream Job and Task commands; copying this
subtree does not rewrite external Dataset scripts.

For direct Dataset and WorkBuddy use:

```python
from downstream._vendor.psycheval_harbor.datasets import resolve_harbor_dataset
from downstream._vendor.psycheval_harbor.workbuddy import (
    prepare_workbuddy_plan,
    summarize_workbuddy_plan,
)

dataset = resolve_harbor_dataset(dataset_id="suite", path="/data/tasks")
plan = prepare_workbuddy_plan(
    output_root="/evaluation",
    dataset_id="office",
    dataset_path="/data/workbuddy",
    base_config="/evaluation/base.yaml",
)
# Run the two returned Job configs with Harbor before summarizing.
summary = summarize_workbuddy_plan(output_root="/evaluation", plan_id=plan["plan_id"])
```

For standalone ATIF validation, copy only `src/psycheval/atif.py` plus LICENSE.
The file can be renamed, uses only the standard library, and validates without
modifying its input. It also owns `is_atif_content` and `iso_timestamp_ms`.
Recognition helpers detect candidate ATIF; call `validate_atif_trajectory` for
strict validation. Adapter conversion belongs to `psycheval.conversion` and is
not part of that copy unit. Harbor's `Trajectory` model remains available
directly from `harbor.models.trajectories`.

```python
from downstream._vendor.atif import validate_atif_trajectory

validate_atif_trajectory(trajectory)  # Raises ValueError with a field path.
```
