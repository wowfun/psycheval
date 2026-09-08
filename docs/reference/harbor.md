# Harbor Integration

Psycheval supports the public Harbor `0.21.0` contract through
`psycheval.harbor`.

## Public seams

- `psycheval.harbor.agent:ExternalHarnessAgent` runs a configured external
  process and loads its current-invocation ATIF output.
- `psycheval.harbor.environment:HostEnvironment` executes directly on a trusted
  native host.
- `psycheval.harbor.environment:HostAccessPolicy` describes independent
  filesystem and process permissions for a Host.
- `psycheval.harbor.paths:HostPathMapper` and
  `psycheval.harbor.paths:trial_short_uuid` are the small public seams for
  explicit path translation and workspace naming.
- `psycheval.harbor.hermes:HermesAgent` is the pinned Harbor compatibility
  adapter for current Hermes provider and exact-session behavior.
- `psycheval.harbor.opencode:HostOpenCodeAgent` runs an already installed
  OpenCode CLI through `HostEnvironment` on native Windows or Linux.
- `psycheval-psychevo-harness` is the external-harness command for Psychevo.
- `psycheval.harbor.verifier` implements shared evidence and artifact scoring.
- `psycheval.harbor.datasets` resolves registered flat Harbor Datasets and
  `workbuddy.dataset.v1` bundles without importing Dataset-owned Python code.

## Native OpenCode

For native OpenCode runs, select `HostOpenCodeAgent` by import path, provide
`model_name` as `provider/model`, and install OpenCode on the host first.
Its `executable` kwarg defaults to `opencode`; an optional `version` requires an
exact match. It accepts Harbor's `opencode_config`, `variant`, prompt template,
Skills, MCP servers, and Agent environment. Provider secrets belong in Agent
environment references and OpenCode `{env:NAME}` substitutions, not inline Job
configuration. No user OpenCode configuration or authentication file is copied.
The requested model is registered in the generated provider configuration;
Harbor's configured base URL applies to its OpenAI and Anthropic providers.
Caller `opencode_config` values override these defaults. Configuration sections
that the adapter extends must be objects, and `skills.paths` must be a list of
strings; invalid shapes fail during Agent construction.
Task MCP definitions supply defaults for each named server; caller MCP entries
merge over them, preserving options such as authentication, timeout, and an
explicit `enabled=false`. Caller-only servers remain available.
Each Trial owns separate OpenCode home, config, data, state, and cache directories
under its Agent logs. During both setup and execution, generated runtime paths
and OpenCode configuration take precedence over Agent environment overrides,
including Harbor's surrounding execution scope. Other Agent environment values
remain available, and the surrounding scope is restored afterward.
Configuration disables automatic updates, sharing, and
OpenCode's additional Git snapshots (the Environment owns the Task baseline), and
allows task tools by default; callers can override permissions in
`opencode_config`. OpenCode chooses its native tool shell, configurable through
that same object. Instructions arrive on stdin, independent of shell quoting and
Windows command-line length. Native JSON events and stderr stream to Agent logs,
including on cancellation, and Harbor's pinned OpenCode converter produces ATIF
and usage metrics. This adapter supports fresh runs only; resume and trajectory
loading are not supported.
The version probe uses the same isolated Trial configuration as execution and
retains `opencode-setup.log`. A probe exceeding its 30-second command timeout
reports that probe failure instead of Harbor's overall Agent setup timeout.

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
symlinks and junctions at reservation and read boundaries and rechecks newly
created directories. Windows short directory names are accepted as aliases of
the same directory. These checks do not isolate concurrent directory replacement:
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
or replace its scoring policy. Runtime validation requires package version
`0.1.0` and a callable `CompositeVerifier`. Available source commit metadata from
the installed distribution is recorded as provenance on a best-effort basis;
it is not a compatibility requirement and local source repositories are not
probed with Git. Use the
[runtime installation workflow](../user/downstream-vendoring.md#install-the-workbuddy-runtime)
to pin a reproducible dependency.

With no verifier LLM variables, the run uses WorkBuddy's deterministic rule
score. The optional variables `WORKBUDDY_VERIFIER_LLM_BASE_URL`,
`WORKBUDDY_VERIFIER_LLM_API_KEY`, and `WORKBUDDY_VERIFIER_LLM_MODEL` are
all-or-none; `WORKBUDDY_VERIFIER_LLM_MAX_OUTPUT_TOKENS` is optional. Secret values
remain environment references and are never copied into a plan manifest.

`peval harbor summarize` calls WorkBuddy's installed `compute_job_metrics`
using a temporary view of the isolated Jobs root and the selected expected Tasks.
Trial configuration supplies the full Task directory name; a complete expected
name in the Trial directory is the fallback when configuration is absent. The
view recognizes Trials by a Task configuration, a Trial-shaped result, or a
verifier score, rather than by a directory name alone. Job summaries without
Trial evidence are ignored even when the Job name contains `__`. The
view preserves score payloads and distinguishes equal Trial names in separate
Jobs. Published metrics retain original Trial names and the Jobs root. Retained
results are never renamed or modified. When a Trial configuration is present,
it must contain a valid `task.path`; malformed configuration fails summarization.
Directory-name identity is a fallback only when configuration is absent. Missing selected
Tasks contribute zero under the upstream metric policy; unexpected Task results
are errors. By default every Job must be terminal; `--provisional` permits an
unfinished snapshot. Version 2 plan and summary documents record full/subset
scope, declared and available counts, and selection independently of completion.
Only version 2 plans and summaries are supported. Version 1 artifacts cannot be
read or discovered; run `prepare` to create a new plan.
Summarization
revalidates the installed runtime and requires the package version recorded by
preparation; differences in source commit metadata do not prevent aggregation.
A source commit changing, appearing, or disappearing adds a summary warning; the
summary records the runtime metadata used for aggregation separately from the
plan's preparation metadata. The known
`recruiting-search-skill-mock-mcp-hardened` source defects and its public-network
exception are prominently warned when that Task is selected. Its scoring rules
and weights remain unchanged.

WorkBuddy workspace and Skill archives use portable relative paths: extraction
rejects drive prefixes, alternate data streams, and `.git` components at any
depth, including case variations. Path components ending in a dot or space are
rejected to prevent Windows filename aliases. A distinct archive path must not
overwrite an already extracted file, including through a native filename alias.
Skill extraction accepts the Skill root archive entry only as a directory. Extracted files retain their
read and execute permissions but lose group/other write permission; conflicting
duplicate archive entries are still compared using their original modes.

## Host configuration

`HostEnvironment` requires an explicit `host_access` policy. In Python this is
`HostAccessPolicy(filesystem=True, process=True)`; Job YAML uses the equivalent
`host_access: {filesystem: true, process: true}` object. Filesystem and process
fields require actual booleans; strings and integers are rejected. These
permissions are independent, although process permission requires filesystem
permission. Filesystem-only Hosts can prepare workspaces, map paths, and move
files, while `exec` and `exec_argv` fail with an explicit process-access error.
The Host is trusted native execution, not a sandbox. It accepts explicit
`workdir_root` and `workspace_source` paths; it does not read the parent
`PEVAL_CONFIG`. The root defaults to `~/workspaces`; `None` selects a
Trial-temporary root. Empty path strings are errors. Direct arguments expand
`~` and resolve relative to the construction working directory. Each automatic
workspace is exclusively created as `task_<short UUID>`, using the Trial suffix
when valid. Existing directories are never reused.

`workspace_baseline` is a construction option with values `"git"` (the default)
and `"none"`. Git baseline initialization is performed for owned workspace
contexts and requires `host_access.process=true`; a filesystem-only caller must
choose `workspace_baseline="none"` explicitly. WorkBuddy bootstrap always
selects the Git baseline. The Harbor-compatible `start(force_build)` signature
does not carry this setting.
Owned Task copies exclude inherited `.git` metadata before creating a fresh
baseline; source repositories are never initialized or committed by the Host.

`HostPathMapper(host_os, mappings, task_workdir)` is lifecycle-free and accepts
explicit virtual-to-native mappings. Its `split`, `translate`, and
`translate_environment` methods handle POSIX paths, Windows case-insensitive
and `C:` aliases, traversal checks, and native absolute paths. A native absolute
path that is not a virtual path passes through unchanged. `path_mapper`,
`native_path`, and `work_dir` are available only after successful startup; code
that needs a pre-start mapper constructs `HostPathMapper` directly.

The read-only `work_dir` property equals `native_path(".")`: the native Task
working directory after successful startup. It remains available after
`stop(delete=False)`, but not before startup, after failed startup, or after
deletion. Path mapping, command cwd, runtime configuration, and cleanup share
one workspace record. Startup failure or cancellation waits for outstanding
file operations before removing owned directories. Project copying checks for
cancellation between files and bounded data chunks; WorkBuddy extraction and
Git initialization check between entries or commands. An in-progress filesystem
or Git call must finish before cleanup. Calling `stop` during startup requests
the same cancellation. Copying, extraction, Git commands, and directory deletion
run off the event loop.
Filesystem operations require successful startup. Host-local directory creation,
resetting, type checks, uploads, downloads, and filtered downloads use the native
filesystem directly and do not require `exec`. A non-virtual native absolute path
passed to these operations is used as-is; `host_access.filesystem=true` therefore
grants trusted host filesystem access and is not a confinement boundary. Symlinks
and Windows reparse-point entries are not reported by type checks or copied by
directory downloads. Emptying a linked directory replaces the link without
traversing its target. Relative filesystem paths resolve against the Task workdir.
`ensure_dirs(..., virtual_workdir=True)` explicitly registers Agent-selected
virtual workdirs against the owned workspace; with a borrowed workspace, those
workdirs must lie within its mount target. ExternalHarnessAgent uses this option
for its environment workdir. Ordinary filesystem calls do not register mappings.
Downloads preserve file modes and timestamps; copying a file onto itself or a
hard-link alias leaves it intact. Filters on a mounted directory never erase
excluded source files. Recursive transfers and directory operations run off the
event loop with a bounded number of active filesystem workers per Host. Directory
downloads traverse incrementally. Cancellation and stop signal downloads between
entries and bounded data chunks, discard an incomplete file's temporary copy,
and drain active workers before releasing or deleting the runtime. Completed
files remain at the destination. An operating-system call already in progress
must return before cancellation can finish. Native transfers have no total-size
quota; callers own destination capacity and timeout policy. Process commands
require both successful startup and process permission.
`exec` and `exec_argv` resolve `cwd` through the same
mapper: omitted or relative values use the Task workdir, registered virtual
paths map into their configured directories, and other native absolute paths
are used directly. A missing cwd is created before launch. Passing a native cwd
does not register a transient mapping or transfer ownership; runtime deletion
does not remove that directory. While `stop` is in progress, the Host prevents new
filesystem operations and commands from starting, terminates registered processes,
and waits for their output
callbacks and cleanup before deleting runtime paths. Stop waits for in-flight
launch registration, then drains callbacks without holding the command-launch
lock. Commands waiting to launch recheck the stopping state, including commands
requested by output callbacks. Already running commands may execute concurrently.
Output callbacks must finish
or raise before their command can complete. A callback cannot call `start` or
`stop` on the same Host while its command is active; these calls raise to prevent
waiting on the callback itself. Raise from the callback to abort its command,
then manage the Host lifecycle from the command's caller.
If command cleanup also fails, the original command exception remains primary
and carries the cleanup failures as exception notes. Pending cleanup operations
are drained before the command releases its runtime.
Each command receives its own runtime JSON, retained until runtime deletion so
its configuration remains available after command completion. Runtime JSON writes
run off the event loop; cancellation waits for the write to finish before releasing
the command's runtime. After `stop(delete=False)` completes, commands may run again
in the retained workspace.
Calling `start` on a successfully started Host is idempotent, including after
`stop(delete=False)`.
`stop(delete=True)`
removes automatic workspaces; external workspace bind mounts are borrowed and
retain their existing Task-context merge behavior.

`workspace_source` must be an existing, accessible directory, validated during
construction before any workspace allocation. It copies the project into each
independent Trial.
It includes ordinary files, including untracked and Git-ignored files, but
excludes every `.git` entry from both the project and Task environment. Task
`environment/` content is then merged into the copy: directories may merge,
but every file or type collision is an error, even for identical files.
Links, Windows junctions, special files, and source/destination overlap are
rejected. The caller must keep source trees and output directories stable
during initialization. No process isolation is implied by copying a project.
With `workspace_baseline="git"`, Git commits the complete merged copy as a
clean initial baseline, including ignored files and empty projects, without
inherited `GIT_*` state or repository hooks. Sources are never modified.
Each baseline Git command has a 30-second timeout; exceeding it fails startup
and cleans up the owned workspace. `workspace_source` cannot be combined with a
workspace bind mount or WorkBuddy archive bootstrap. External workspace bind
mounts are borrowed and are not baseline-initialized. Separate verifier
environments retain their isolated Task test context without copying the project or
initializing a Git baseline.

The explicit `runtime_config.load_host_settings(path)` parser owns
`[harbor.host].workdir_root` in a caller-selected TOML file. Omission uses the
built-in root; an empty TOML value selects temporary workdirs. Relative roots
resolve against that TOML file. Unknown host fields fail closed and the file
is never modified. The peval CLI passes these settings to
`prepare_workbuddy_plan(..., host_settings=...)`. For host plans, an explicit
Job `workdir_root` takes precedence over caller settings, then the built-in
default. Relative Job roots resolve against the base YAML file. Generated Jobs
contain the resolved absolute root (or `null` for temporary workdirs), so their
launch commands need no parent `PEVAL_CONFIG` assignment.

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
Command output uses incremental UTF-8 decoding, preserving characters split
across process-output chunks in both returned text and streaming callbacks.

For Windows shell execution, `PATH` and `PYTHONPATH` overrides use native
semicolon-separated entries; each virtual path is mapped independently while
native entries are preserved. The launch gate preserves the rendered cmd
command text without applying executable-argument quoting to it a second time.

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

Windows Host WorkBuddy plans select Psycheval's Office native verifier. It accepts
the recognized workspace cwd whether the runtime supplies a string or a native
`Path` object, including Windows' backslash form of `/workspace`. It runs
pytest with its copied tests as the collection root, including when the workspace
and temporary tests occupy different Windows drives. Conftest discovery includes
the copied tests directory and its descendants, but excludes its ancestors and
the separate Agent workspace. The supported Office
profile's preparation, pytest, scorer, and artifact steps run
without Bash, using Git and the current interpreter's Office Python packages.
Agent-specific command dependencies remain the Agent's responsibility. Linux
and container plans use the upstream verifier. Host MCP commands use the host
interpreter; container MCP commands use the container interpreter.
Host WorkBuddy bootstrap records the native OS in the supplied in-memory Task
environment configuration after constructor validation, so Harbor's Skill upload
uses native platform behavior. This configuration belongs to one Trial; direct
callers using a reusable configuration must pass a separate copy for each Trial.
Source Task files remain unchanged. The standard `/harbor/skills` directory maps to owned
runtime storage, outside the task workspace, and is removed with that runtime.
Host preflight checks Git on Windows, Bash and Git on Linux, and Office Python
imports. It does not check the selected Agent's installer tools, such as curl,
Node, or npm; callers provision those separately.
Native verification requires successful Git add, staged-diff capture, and reset
before publishing `agent.patch`. These commands explicitly target the Trial
workspace's `.git` and working tree; a missing repository cannot fall back to an
ancestor repository. A failed preparation step aborts verification
with its command, exit code, and diagnostic; a successful empty diff is valid.

The planner checks the inputs required by the native pipeline before reserving
a plan. Each verification checks source file safety and adapts its Trial-owned
grader copy before loading plugins. Source adaptation is best effort: the rule
module is not required to match a fixed source fingerprint, and unknown grader
expressions remain unchanged with skipped adaptations recorded in the audit.
Skipped adaptations also produce a verifier log warning and a diagnostic in the
final score. Trial detail exposes that diagnostic as a best-effort score warning;
it does not invalidate the score or block execution.
Only recognized file-access paths, interpreter launch sites, and snapshot
traversal ordering are adapted; logical
path comparisons, gold data, instructions, and scoring conditions remain intact.
The verifier retains an adaptation audit with source and transformed digests.
The native pipeline requires a readable execution template with score/reward
snippets and a supported pytest command; incompatible execution interfaces fail
explicitly. Other changes to the source shell wrapper are not interpreted by
the native pipeline. The installed external WorkBuddy runtime still owns
scoring, LLM judging, and final score aggregation.
The recognized Python path sites are `Path`, the path argument of `open`,
`builtins.open`, `io.open`, and `os.open`, `sys.path.insert`,
`os.environ.get`, argument-parser defaults, `DEFAULT_OUTPUT_PATH`, and
`_default_output_path`. These sites accept standalone string literals;
interpolated virtual paths are left unchanged. Invalid mapped paths, malformed Python, and
rewrite failures are reported as `OfficeProfileError` before plan creation.
The recognized snapshot functions `_compute_snapshot`,
`_compute_workspace_snapshot`, and `_protected_root_rollup` retain POSIX's
case-sensitive path-component ordering when hashing file trees on Windows.
Only their known file traversal expression is adapted; file bytes, hash inputs,
gold hashes, and score conditions are unchanged. Unexpected traversal shapes
remain unchanged. The adaptation audit records successful rewrites as `path_order`
and unrecognized expressions as `skipped`.
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
