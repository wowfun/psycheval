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

Native `environment/prepare.py` copies the static Excel and Skills, validates
the fixed watchlist, creates `.trend-digest/`, and records UTC preparation time
and input hashes in `.trend-digest/preparation.json`. It performs no network
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
coverage. When all accounts fail, the fetch command exits nonzero and the source
observation gate stops continuation. A successful source call and valid delivery allow subsequent steps;
snapshot completeness and quality affect partial credit.
The Chinese-summary presence check accepts Chinese prose or table descriptions;
it counts report body text, not front matter, and does not require a literal
heading named “摘要”. GitHub repository slots use
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

Every deterministic check declared in each step's `grader.json` has equal
weight. Built-in checks score source calls, successful observations, artifact
delivery, and exact final-answer filenames. X and HN require a successful
`*exec*`, `*terminal*`, `*shell*`, or `bash` call with the skill name in its
arguments. Shared `tests/test_outputs.py` adds report structure and freshness,
ten fixed GitHub repository slots, eleven fixed watchlist accounts (fetch
status, report status, and complete in-window posts for each), or twelve fixed
HN story slots. Missing output cannot shrink the scoring denominator.
GitHub accepts web/fetch tools or shell execution; local read tools alone do not
establish a source fetch.

GitHub and X continue only when `required_tool`, `required_arguments`,
`required_observation`, `required_artifacts`, and `final_answer` each score 1.
Other checks award partial credit without independently blocking continuation.
Harbor averages step rewards. A failed final answer is a failed item and
continuation gate; it does not multiply all other scores by zero.

Each step's `tests/judge.yaml` adds three equally weighted rubrics: faithful
summaries, concrete information value, and clear Chinese with honest statements
about no updates, fetching failures, and insufficient evidence. The custom
script writes the current report and validated source evidence under
`judge-evidence/`; GitHub uses successful tool observations and X/HN use their
snapshots. The Judge does not browse or repeat counts, links, or timestamp
checks. Quality expectations are also stated in the step instructions.
Invalid X time windows are excluded from Judge source evidence even for empty
post lists. Fixed rubric/check declarations are tested against the supplied
Excel watchlist; Agent-modified workbook content cannot redefine scoring items.

The [Harbor YAML Judge contract](../../../docs/reference/harbor.md#yaml-llm-judge)
defines configuration and result handling. It is disabled by default. Enable
it through `verifier.env` with `PEVAL_JUDGE_ENABLED=true`, an API base URL, model,
and optional credential reference. A complete assessment combines 80% rule
score and 20% LLM score; incomplete API/protocol results retain the rule score
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
