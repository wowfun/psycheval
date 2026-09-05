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
`format` (default `"harbor"`), and `allow_partial` (default `false`), and return `ResolvedHarborDataset`. The
application owns workspace registration and mount selection. WorkBuddy's
`prepare_workbuddy_plan` takes `output_root`, `dataset_id`, `dataset_path`, and
`base_config`, optional `task_selection` and `limit`, and `allow_partial`;
it fully validates the present WorkBuddy Dataset content itself. `task_selection`
is a list of exact Task directory names, sorted before applying a positive limit. An explicit
empty selection, repeated names, or unavailable names is an error.
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

An explicitly registered `allow_partial=true` WorkBuddy bundle may omit whole
Task directories while retaining the original manifest count. Empty bundles,
more Tasks than declared, and invalid present content remain errors. The flag
is accepted only for WorkBuddy, propagates through configuration and workbench
registration, and does not modify the source manifest. Without it, preparation
requires all 50 Office Tasks.

`workbuddy.v1` currently denotes the pinned WorkBuddy Office v1.0 profile, not
an open-ended family of WorkBuddy manifests. A different WorkBuddy Dataset
profile requires an explicit Psycheval contract update.

`peval harbor prepare` converts a validated WorkBuddy registration plus one
ordinary Harbor `0.21.0` Job config into a reproducible run plan. It does not run
Harbor. The plan owns an isolated Jobs root and one or two nonempty configs:
selected normal Office tasks and, when selected, the Skill/MCP task. Only that
selection extracts a Skill and injects MCP configuration. This split is required because Harbor `0.21.0`
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
against the isolated Jobs root and the selected expected Tasks. Missing selected
Tasks contribute zero under the upstream metric policy; unexpected Task results
are errors. By default every Job must be terminal; `--provisional` permits an
unfinished snapshot. Version 2 plan and summary documents record full/subset
scope, declared and available counts, and selection independently of completion.
Only version 2 plans and summaries are supported. Version 1 artifacts cannot be
read or discovered; run `prepare` to create a new plan.
Summarization
revalidates the installed runtime and requires the identity recorded by
preparation. The known
`recruiting-search-skill-mock-mcp-hardened` source defects and its public-network
exception are prominently warned when that Task is selected. Its scoring rules
and weights remain unchanged.

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

`HostEnvironment.exec_argv` accepts a nonempty argument sequence and the same
cwd, environment, timeout, and user controls as `exec`. It starts the executable
directly, sharing logging, runtime configuration, and process cleanup with shell
execution. Arguments and explicit per-call `env` values are literal; callers map
their virtual paths explicitly through `native_path`. Task, persistent, and
scoped environment values retain environment-path mapping in both execution
modes. Precedence remains Task < persistent < per-call < scoped environment;
an active scope overrides even a literal per-call value. Arbitrary argument text is never
interpreted as a shell program. `exec` retains the native
host shell contract. Agents may independently use PowerShell or Git Bash.
For Windows shell execution, `PATH` and `PYTHONPATH` overrides use native
semicolon-separated entries; each virtual path is mapped independently while
native entries are preserved.

Timeouts cover both process completion and draining captured output. Timeout
and cancellation cleanup target the Linux process group or Windows Job even
after the command's parent exits. Windows creates an
unnamed Job Object and assigns a waiting, isolated Python launcher before
allowing it to start the requested argv. Closing the Job terminates remaining
descendants; this also avoids a child-spawn race during assignment. See
[Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).
The launcher's stdin is reserved for this gate.
Job ownership ends on successful command completion as well as cancellation or
timeout. Remaining descendants are terminated even if they were deliberately
backgrounded; a Windows exec call does not provide a persistent service lifetime.
Existing Jobs use Windows' [nested Job support](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs).
If assignment is denied by host restrictions, startup fails before the target
command runs and reports the Windows error plus existing Job membership when
it can be queried. The adapter does not request breakaway from the host's Job.
On Linux, successful completion leaves descendants alive if they have closed
the captured output pipes. Callers must manage those processes separately.

Windows virtual roots match without case sensitivity, with or without the `C:`
alias; suffix components retain their letter case. Windows virtual paths reject
embedded drive prefixes and alternate-data-stream
syntax, so joining a suffix cannot discard the mapped native root.

Windows Host WorkBuddy plans select Psycheval's Office native verifier. It runs
the supported Office profile's preparation, pytest, scorer, and artifact steps
without Bash, using Git and the current interpreter's Office Python packages.
Agent-specific command dependencies remain the Agent's responsibility. Linux
and container plans use the upstream verifier. Host MCP commands use the host
interpreter; container MCP commands use the container interpreter.
Host preflight checks Git on Windows, Bash and Git on Linux, and Office Python
imports. It does not check the selected Agent's installer tools, such as curl,
Node, or npm; callers provision those separately.
Native verification requires successful Git add, staged-diff capture, and reset
before publishing `agent.patch`. These commands explicitly target the Trial
workspace's `.git` and working tree; a missing repository cannot fall back to an
ancestor repository. A failed preparation step aborts verification
with its command, exit code, and diagnostic; a successful empty diff is valid.

The planner validates source profiles before reserving a plan. Each verification
checks source file safety, then validates and adapts its Trial-owned grader copy
in one pass before loading plugins. Plan-time validation is not reused as proof
that a later runtime copy is valid. Only
recognized file-access paths and interpreter launch sites are adapted; logical
path comparisons, gold data, instructions, and scoring conditions remain intact.
The verifier retains an adaptation audit with source and transformed digests.
Unsupported execution shapes fail explicitly. The fixed external WorkBuddy
runtime still owns scoring, LLM judging, and final score aggregation.
The recognized Python path sites are `Path`, `sys.path.insert`,
`os.environ.get`, argument-parser defaults, `DEFAULT_OUTPUT_PATH`, and
`_default_output_path`. These sites accept standalone string literals;
interpolated virtual paths are rejected. Invalid paths, malformed Python, and
rewrite failures are reported as `OfficeProfileError` before plan creation.
The manifest's known POSIX `PYTHONPATH` prefixes are parsed into
entries and rebuilt with the host separator. Explicit environment path lists
use the host separator as well; native drive-letter colons are preserved.
Native Python steps include the profile's declared import paths, including the
fallback score and reward snippets. The source Bash heredocs add no such prefix.

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

The complete `src/psycheval/harbor` subtree is a relocatable source-copy unit.
Its internal imports stay relative; it needs no other Psycheval modules or
workspace. Namespace changes do not rename `PEVAL_CONFIG`, runtime JSON fields,
schema identifiers, or Agent identities. The caller owns downstream Job and
Task commands; copying source does not rewrite external Dataset scripts.

`src/psycheval/atif.py` is a separate copy unit. It can be renamed, uses only the
standard library, and validates without modifying its input. It also owns
`is_atif_content` and `iso_timestamp_ms`. Recognition helpers detect candidate
ATIF; call `validate_atif_trajectory` for strict validation. Adapter conversion
belongs to `psycheval.conversion` and is outside that copy unit. Harbor's
`Trajectory` model remains available directly from `harbor.models.trajectories`.

Follow [Vendoring Harbor integration downstream](../user/downstream-vendoring.md)
for source layout, dependency and WorkBuddy installation, Job configuration,
and runtime checks.
