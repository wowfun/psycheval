# PBench

PBench is a maintained pair of Harbor Datasets for generic Agent capabilities.
Version 1.0 covers Web Search, direct Web Fetch, and a multi-step trend digest;
Version 1.0 Plus covers browser form control.

## Dataset

```text
datasets/pbench-v1.0/
├── web-search-01/
├── web-fetch-01/
└── trend-digest-01/

datasets/pbench-v1.0-plus/
└── browser-control-01/
```

Harbor treats each immediate child directory as a Task. From a Psycheval source
checkout, run a compatible Agent across either local Dataset with the explicit
trusted-host environment so the installed project interpreter is available to
each verifier:

```bash
uv run harbor run \
  -p datasets/pbench-v1.0 \
  --env psycheval.harbor.environment:HostEnvironment \
  --environment-kwarg allow_host_execution=true \
  [AGENT OPTIONS]
```

The Task Dockerfiles intentionally contain only the Agent workspace. The
default Docker environment cannot run the source-checkout verifier because it
does not contain an installed Psycheval distribution. HostEnvironment executes
trusted Task and Agent code directly on a native Linux or Windows host; it is
not a sandbox.

Each Task ships thin `tests/test.sh` and `tests/test.bat` entrypoints backed by
one installed Python grader. Linux and WSL select the shell entrypoint; native
Windows HostEnvironment selects the Batch entrypoint. The static Task manifests
remain Linux-targeted, so this portability does not claim Harbor Windows
container support.

Deterministic validation loads each Task's explicit ATIF, source, and artifact
fixtures directly into its verifier. Generic synthetic Tasks, not PBench Tasks,
exercise complete Harbor single-step and multi-step lifecycle behavior.

`trend-digest-01` has three ordered steps. A real resume-capable Agent run adds
`--resume-trajectory`, so a compatible Agent receives `run`, `resume`, and
`resume`; omitting the flag runs all three steps with fresh Agent context while
retaining the shared workspace. The Task publishes each platform report under
that step's archived `artifacts/logs/artifacts/` directory and requires the
current final answer to name the report exactly. It intentionally ships without
Oracle solutions. Its deterministic tests validate each step's verifier and
manifest directly rather than manufacturing a full PBench Trial.

Psychevo currently supplies real Search and Fetch tool trajectories. Browser
Control requires an Agent with the specified browser tools; it is not implied
by Psychevo Search/Fetch support.

## Tasks

| Task | Harbor name | Required behavior |
| --- | --- | --- |
| `web-search-01` | `pbench-v1.0/web-search-01` | Search for IANA Example Domains, return both domains and the source URL, without fetch or shell shortcuts. |
| `web-fetch-01` | `pbench-v1.0/web-fetch-01` | Fetch the exact IANA URL and return its displayed date, without search or shell shortcuts. |
| `trend-digest-01` | `pbench-v1.0/trend-digest-01` | Produce step-local GitHub weekly, watched-account X 24-hour, and current Hacker News reports using direct Web evidence and two bundled fetch-only skills. |
| `browser-control-01` | `pbench-v1.0-plus/browser-control-01` | Type and submit Selenium's Web Form, report the result, save the required screenshot, and name it in the final answer. |

Trend Digest live runs require public access to GitHub, Hacker News, and at
least one usable Nitter instance. Network/provider failures are time-varying;
the deterministic suite substitutes fixed local source fixtures. Skill execution is
graded from a successful current-step Shell-family call whose arguments contain
the configured skill name, plus the normalized snapshot. See the Task's own
[`README.md`](../../datasets/pbench-v1.0/trend-digest-01/README.md) for the Excel,
report, resume, and partial-degradation contracts.

See [Scoring](scoring.md) for evidence rules and
[Authoring](authoring.md) for the example scaffold.
