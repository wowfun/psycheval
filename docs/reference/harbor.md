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

Psycheval recognizes a registered `workbuddy.dataset.v1` bundle as a read-only
Dataset whose Harbor Tasks live below the manifest's `layout.task_root`.
Registration validates the bounded UTF-8 manifest, declared CompositeVerifier
contract, contained task root, task count, bounded UTF-8 Task text, shared
verifier inputs, and regular workspace archives. Discovery never imports or
executes external package code. Ordinary mount and workbench reads resolve only
the bounded manifest, contained task root, declared count, and immediate Task
names; the shared Task index validates Task content as it is associated with
Trials. Registration and `peval harbor prepare` remain the explicit full-bundle
validation gates, so read paths do not re-walk every Task merely to locate the
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
