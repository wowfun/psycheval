# PBench

PBench is a maintained Harbor Dataset for generic Agent capabilities. Version
1.0 currently covers Web Search, direct Web Fetch, and browser form control.

## Dataset

```text
datasets/pbench-v1.0/
├── web-search/
├── web-fetch/
└── browser-control/
```

Harbor treats the three immediate child directories as Tasks. From a Psycheval
source checkout, run a compatible Agent across the local Dataset with the
explicit trusted-host environment so the installed project interpreter is
available to each verifier:

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
trusted Task and Agent code directly on the Linux host; it is not a sandbox.

For deterministic validation, run one Task at a time with the matching canned
scenario shown in the [Psycheval guide](../psycheval/README.md).

Psychevo currently supplies real Search and Fetch tool trajectories. Browser
Control requires an Agent with the specified browser tools; it is not implied
by Psychevo Search/Fetch support.

## Tasks

| Task | Required behavior |
| --- | --- |
| `web-search` | Search for IANA Example Domains, return both domains and the source URL, without fetch or shell shortcuts. |
| `web-fetch` | Fetch the exact IANA URL and return its displayed date, without search or shell shortcuts. |
| `browser-control` | Type and submit Selenium's Web Form, report the result, and save the required screenshot. |

See [Scoring](scoring.md) for evidence rules and
[Authoring](authoring.md) for the example scaffold.
