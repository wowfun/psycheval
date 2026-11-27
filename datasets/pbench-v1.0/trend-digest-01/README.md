# Trend Digest

This PBench Task evaluates a three-step research workflow. The Agent collects
GitHub weekly trends, the previous 24 hours of posts from an Excel watchlist,
and the current Hacker News top stories, then writes one Chinese Markdown
report per step. See each file under [`steps/`](steps/) for the exact prompt.

## Environment

The fetch Skills use Python 3.12+ with public network access and only the standard
library. `input/x-users.xlsx` contains the X watchlist.
`skills/` contains fetch-only `x-daily` and `hackernews-daily` skills;
GitHub is retrieved directly from its weekly Trending page. The default Agent
timeout is 15 minutes per step; verification has 180 seconds per step.

Native `prepare(workdir, state_dir) -> list[str]` copies the static Excel and
Skills, validates the fixed watchlist, and selects `input` and `skills` for the
initial input snapshot. It creates `.trend-digest/` for later fetch outputs and
records UTC preparation time and input hashes in `state_dir/preparation.json`,
outside the Agent workspace. It performs no network
requests and writes no reports. Preparation time is diagnostic: X's 24-hour
window and the HN snapshot are anchored to actual fetching. The Dockerfile
continues to copy static inputs for container execution. Fetch commands default
to workspace-relative paths, both on Host and under the container's `/app` cwd.
Python bytecode caches are excluded from prepared inputs and their hashes.
Tests can supply `PBENCH_TREND_NOW` as an explicit UTC preparation/verification
clock; live runs use actual UTC time.

Verification requires the installed Psycheval package and its locked dependencies
in the verifier interpreter. The Dockerfile supplies static Agent inputs only;
container runners must also provision that package and native verification
context in their verifier environment. It is not a self-contained verifier image.

Public Nitter instances are best-effort. A successfully fetched account with no
posts is `no_updates`; an account for which every instance fails is
`fetch_failed`. The latter must remain visible in the report and reduces
coverage. When all accounts fail, the fetch command exits nonzero and receives
no successful-source credit. An honestly delivered per-account failure report
can still continue to the independent Hacker News step; it cannot receive full
coverage or substantive-summary credit. GitHub retains its successful-source
continuation gate. Snapshot completeness and quality affect partial credit.
X's substantive-summary rubrics additionally require `successful_sources`,
published only when the validated snapshot contains at least one successfully
fetched account (including a confirmed `no_updates`). All-failed fetches leave
this artifact explicitly unavailable, so those two rubrics fail locally without
model calls; the honest-Chinese rubric can still assess the report and failure
snapshot. This precondition describes retained validated evidence, not independent
remote truth. Its text shares the same 1 MiB report/source publication budget.
The Chinese-presence diagnostic accepts prose or tables without a character-count
threshold and carries no independent score; semantic Chinese quality belongs to
the Judge. GitHub repository slots use
repository headings in HTML/Markdown or absolute repository URLs in text evidence.
UTF-8 reports may carry a BOM, as produced by Windows PowerShell. Timestamps
still require an explicit UTC offset.

## Outputs and scoring

Each step publishes exactly one UTC-named file in `TREND_ARTIFACTS_DIR`, which
maps `/logs/artifacts` to the native Host path. Harbor
archives it beneath `steps/<name>/artifacts/logs/artifacts/` before starting the
next step. Names use `<platform>-YYYYMMDDTHHMMSSZ.md`. Every report's front
matter contains `platform`, matching UTC `generated_at`, and `source`; GitHub
also uses `window: weekly`, X uses the snapshot's `window_start` and
`window_end`, and Hacker News uses the snapshot's `snapshot_at`. The current
step's final answer must name that file exactly.

The step-local `grader.json` owns deterministic weights. Three source-call checks
each carry weight 1. GitHub and X artifact existence and final-answer names have
zero quality weight and remain required continuation checks; the last HN step
retains their 0.05 delivery weights. Report metadata checks each carry only
0.05, while Chinese-presence is diagnostic-only. GitHub repository slots each
carry weight 1, and weekly-source identification carries 1. Hacker News story
slots each carry 1, with snapshot validity, source and freshness at 0.5 each.
X per-account fetch coverage and complete posts each carry 1, truthful status
binding carries 0.25, and snapshot validity, window and freshness each carry 0.5.
X and HN require a recorded
`*exec*`, `*terminal*`, `*shell*`, `bash`, `Bash`, or `pwsh` call with the skill name in its
arguments. Shared `tests/test_outputs.py` checks report structure and freshness,
ten fixed GitHub repository slots, eleven fixed watchlist accounts, or twelve
fixed HN story slots. Repository/story slots bind one source item to one independent
report unit in the correct order; HN metrics belong to that same unit. Repeated
or merged items cannot fill separate slots. HN metric labels accept ordinary
Markdown emphasis and bilingual parentheses, such as `**得分（score）**：947`
and `**评论数（comment_count）**：651`; display syntax does not change the required
source value or the story to which it belongs. X rejects duplicate account sections
and unsupported post links or duplicate posts in the snapshot; failed fetches never gain empty-post
credit. Missing output cannot shrink the scoring denominator.
GitHub accepts web/fetch tools or shell execution; local read tools alone do not
establish a source fetch.

GitHub source evidence starts with successful, current-step fetch observations.
When a shell fetch saves the weekly page with `curl -o/--output`, `wget -O`,
PowerShell `-OutFile`/`Content | Out-File`, or a Node `fetch(...)` and explicit
`fs.writeFileSync(...)` in the same retained call, later successful reads of that same path may supply the
page evidence. Literal paths are resolved against the recorded working directory
and an explicit leading `cd`/`Set-Location`; basename-only matches are not enough.
Supported readers are file-read tools, `cat`/`Get-Content`/`type`, Python
`open`/`Path` reads, and Node `readFileSync`. PowerShell `$env:NAME/path` and
Node `process.env.NAME + '/path'` reads and writes can be matched symbolically by
the same variable name and suffix, without reading the verifier's environment or
host files. Node paths must be quoted literals or this explicit environment-plus-
literal form; computed paths and arbitrary local JSON do not establish provenance.
Other shell expressions are not evaluated. Copied context,
failed calls, unrelated files and final answers are excluded. WorkBuddy shell
observations have their structured command-echo wrapper removed; other observation
formats are retained as recorded tool output.
The collector indexes retained calls and their observations once per grading
attempt, then links weekly and repository evidence in call order. It uses
retained observations, not files left on the host.

Ranked JSON arrays or JSON lines with contiguous `rank` values starting at 1 and
a repository identifier in `name`, `repo`, `full_name`, `path`, `url`, or `html_url`
are accepted alongside HTML/Markdown headings and URLs. Identifiers can be
`owner/repo`, `/owner/repo` or full GitHub URLs; whitespace around the slash is
allowed. Multiple valid identifiers in one record must agree. Non-JSON log lines
around JSON-line records do not supply repository slots. A JSON object may wrap
one such array with scalar metadata, such as `{total: 11, top10: [...]}`. Multiple
arrays, nested collections, invalid rank/identity records, or an inconsistent
`total` are rejected; a wrapper cannot bypass the same fetch/read provenance.
The first complete observation with at least ten distinct repositories
establishes the first ten slots; partial lists are not stitched together.
Successful fetches of that weekly URL and their linked reads retain distinct bodies verbatim
with fetch/read call identifiers for Judge evidence, including subsequent
extraction of descriptions.
Successful fetches of the selected ten repositories on `github.com` or
`raw.githubusercontent.com`, and reads linked to those downloads, are also
included as supporting evidence (for example README text). Repository identity
must match the owner/name exactly, not a longer prefix. These supporting sources
never determine or add ranking slots.
Identical bodies are published once with all associated fetch/read provenance.
Report and source text share a 1 MiB publication budget, matching the default
Judge evidence budget. The complete report has priority. If complete source
evidence cannot fit, it is marked unavailable with an explicit budget reason;
no body is silently shortened. Required unavailable evidence produces local
rubric failures under the shared Judge contract, rather than an accidental
oversized-input fallback. The original observations remain in the trajectory.
These provenance links identify recorded tool
results; they do not make agent-authored parsing code or source content trusted.

GitHub and X use the shared
[continuation contract](../../../docs/reference/harbor-verifier.md#continuation-checks)
with `min_reward = { continuation = 1.0 }`. GitHub requires
`required_call_1_tool`, `required_call_1_arguments`,
`required_call_1_observation`, `required_artifacts`, and `final_answer` to pass.
X requires the same checks except `required_call_1_observation`, allowing a correctly
reported upstream outage to continue without hiding its failed coverage.
Other checks award partial credit without independently blocking continuation.
Harbor averages step quality rewards. Each step's own `continuation` controls
execution; its root Trial average is not a pass/fail status. A failed GitHub or
X final answer stops continuation without changing other quality credit.

Each step's `tests/judge.yaml` adds three equally weighted rubrics: faithful
summaries, concrete information value, and clear Chinese with honest statements
about no updates, fetching failures, and insufficient evidence. The custom
script publishes the current report and validated source evidence through
[`EvidenceWriter`](../../../docs/reference/document-evidence.md#evidence-publication),
including its manifest and per-attempt cleanup. The report and the original
retained GitHub trajectory or X/HN JSON snapshot are captured once; published
text names that captured source in the manifest. GitHub source text retains
fetch/read call identifiers, while X/HN records retain account handles or story
IDs and ranks so the Judge can bind a summary to its own source item. X/HN
snapshots are Agent-workspace fetch outputs, not independent proof of remote
truth; provenance identifies the bytes used for grading. HN additionally publishes
`supporting_sources`, derived from the captured retained trajectory. Each original
or discussion URL is bound to its snapshot rank and story ID, with fetch/read call
identifiers. Only successful current-step fetches and later reads linked to their
saved paths can supply these observations; unrelated files, copied history and
URL-prefix matches cannot. Complete distinct bodies are preserved with every
associated story/URL, never combined to invent another story's evidence.
For a story whose original URL identifies a GitHub repository, same-repository
GitHub or raw README observations may additionally appear as
`Source kind: repository_support`, bound to that story's rank, ID and exact
owner/repository identity. Longer repository-name prefixes and other repositories
cannot supply this support. These observations retain their original fetch/read
provenance and remain first-party repository material.
Missing
observations produce explicit per-story diagnostics; an observation may still
contain only a title, a shell page or truncated text, so it does not imply that a
full article was available. A metadata-only digest can be faithful within that
declared scope. The report, snapshot text and supporting observations together
share the 1 MiB text budget, in that priority order; complete supporting evidence
that cannot fit is explicitly unavailable rather than silently shortened.
The Judge does not
browse or repeat counts, links, or timestamp
checks. Quality expectations are also stated in the step instructions.
Invalid X time windows are excluded from Judge source evidence even for empty
post lists. Fixed rubric/check declarations are tested against the supplied
Excel watchlist; Agent-modified workbook content cannot redefine scoring items.

The [Harbor YAML Judge contract](../../../docs/reference/harbor-verifier.md#yaml-llm-judge)
defines configuration and result handling. It is disabled by default. Enable
it through `verifier.env` with `PEVAL_JUDGE_ENABLED=true`, an API base URL, model,
and optional credential reference. A complete assessment combines 35% rule
score and 65% LLM score; incomplete API/protocol results retain the rule score
and diagnostics. LLM quality never changes continuation gates.

## Layout

```text
trend-digest-01/
├── environment/
│   ├── Dockerfile
│   ├── prepare.py
│   └── data/
│       ├── input/x-users.xlsx
│       └── skills/{x-daily,hackernews-daily}/
├── steps/{github,x,hacker-news}/
│   ├── instruction.md
│   └── tests/{grader.json,judge.yaml}
├── tests/                      # Shared custom checks and CLI launchers
└── task.toml
```

## Running

The Task does not ship Oracle solutions. For a resume-capable Agent, add its
normal Agent/model options and enable native continuation:

```bash
uv run harbor run \
  --path datasets/pbench-v1.0/trend-digest-01 \
  --resume-trajectory \
  --env psycheval.harbor.environment:HostEnvironment \
  --verifier-import-path psycheval.harbor.verifier.host:HostVerifier \
  --environment-kwarg 'host_access={"filesystem":true,"process":true}' \
  [AGENT OPTIONS]
```

The live command accesses time-varying external services. Repository tests use
fixed clocks and local HTTP-response fixtures instead.
For `HostOpenCodeAgent`, omit `--resume-trajectory`: that adapter starts a fresh
conversation for each step while the Task workspace remains shared. On native
Windows, run Harbor with Python UTF-8 mode as described in the
[native installation workflow](../../../docs/user/downstream-vendoring.md#run-on-native-windows).
