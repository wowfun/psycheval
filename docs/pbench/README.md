# PBench

PBench is a maintained pair of Harbor Datasets for generic Agent capabilities.
Version 1.0 covers Web Search and direct Web Fetch; Version 1.0 Plus covers
browser form control.

## Dataset

```text
datasets/pbench-v1.0/
├── web-search-01/
└── web-fetch-01/

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

For deterministic validation, run one Task at a time with the matching canned
scenario shown in the [Psycheval guide](../psycheval/README.md).

Psychevo currently supplies real Search and Fetch tool trajectories. Browser
Control requires an Agent with the specified browser tools; it is not implied
by Psychevo Search/Fetch support.

## Tasks

| Task | Harbor name | Required behavior |
| --- | --- | --- |
| `web-search-01` | `pbench-v1.0/web-search-01` | Search for IANA Example Domains, return both domains and the source URL, without fetch or shell shortcuts. |
| `web-fetch-01` | `pbench-v1.0/web-fetch-01` | Fetch the exact IANA URL and return its displayed date, without search or shell shortcuts. |
| `browser-control-01` | `pbench-v1.0-plus/browser-control-01` | Type and submit Selenium's Web Form, report the result, and save the required screenshot. |

See [Scoring](scoring.md) for evidence rules and
[Authoring](authoring.md) for the example scaffold.
