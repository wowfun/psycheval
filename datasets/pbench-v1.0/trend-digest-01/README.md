# Trend Digest

This PBench Task evaluates a three-step research workflow. The Agent collects
GitHub weekly trends, the previous 24 hours of posts from an Excel watchlist,
and the current Hacker News top stories, then writes one Chinese Markdown
report per step. See each file under [`steps/`](steps/) for the exact prompt.

## Environment

The workspace uses Python 3.12 with public network access and no third-party
Python packages. `/app/input/x-users.xlsx` contains the X watchlist.
`/app/skills` contains fetch-only `x-daily` and `hackernews-daily` skills;
GitHub is retrieved directly from its weekly Trending page. The default Agent
timeout is 15 minutes per step.

Public Nitter instances are best-effort. A successfully fetched account with no
posts is `no_updates`; an account for which every instance fails is
`fetch_failed`. The latter must remain visible in the report and reduces
coverage. A complete X outage stops the Trial before Hacker News.

## Outputs and scoring

Each step publishes exactly one UTC-named file under `/logs/artifacts`. Harbor
archives it beneath `steps/<name>/artifacts/logs/artifacts/` before starting the
next step. Names use `<platform>-YYYYMMDDTHHMMSSZ.md`. Every report's front
matter contains `platform`, matching UTC `generated_at`, and `source`; GitHub
also uses `window: weekly`, X uses the snapshot's `window_start` and
`window_end`, and Hacker News uses the snapshot's `snapshot_at`. The current
step's final answer must name that file exactly.

| Reward | Weight | Measures |
| --- | ---: | --- |
| `source_evidence` | 30% | A successful current-step GitHub retrieval or skill invocation and a valid normalized snapshot. |
| `freshness` | 25% | Weekly GitHub, rolling 24-hour X, or current HN timestamps and matching front matter. |
| `coverage` | 30% | Required repositories, accounts/posts, or stories represented in the report. |
| `format` | 15% | One correctly named Markdown artifact with matching UTC front matter and Chinese summaries. |
| `final_answer` | Gate | The final answer names the current report's exact filename. |

The deterministic Task-local verifier reads only the live current-step
trajectory, artifact directory, and matching snapshot. It reuses the installed
Psycheval verifier for required calls, artifact glob expansion, and final-answer
checks. X and Hacker News require a successful `*exec*`, `*terminal*`,
`*shell*`, or `bash` call whose arguments contain the corresponding skill name.
A failed final answer sets the step reward to zero. Harbor averages reward keys
across steps; GitHub and X require perfect source, freshness, format, and
final-answer dimensions before the Trial continues.

## Layout

```text
trend-digest-01/
├── environment/
│   ├── input/x-users.xlsx
│   └── skills/{x-daily,hackernews-daily}/
├── steps/{github,x,hacker-news}/
│   ├── instruction.md
│   └── tests/grader.json
├── tests/                      # Shared Linux/Windows verifier
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
  --environment-kwarg allow_host_execution=true \
  [AGENT OPTIONS]
```

The live command accesses time-varying external services. Repository tests use
fixed clocks and local HTTP-response fixtures instead.
