# PBench Testing

## Scope

This attachment defines deterministic Task validation and opt-in live Agent
evaluation for PBench.

## Deterministic Validation

- Validate each committed Task's discovery, authoring contract, and verifier
  directly with explicit ATIF, source, and artifact fixtures. PBench Task
  validation does not require a synthetic Harbor Trial or per-Task harness
  scenario.
- Assert all four Tasks and the authoring scaffold ship equivalent thin
  `test.sh` and `test.bat` entrypoints that invoke the installed verifier.
- Generic Psycheval integration fixtures, rather than PBench Tasks, own native
  Linux `test.sh` and Windows `test.bat` Harbor execution coverage. WSL, Wine,
  and Git Bash are not native Windows acceptance environments.
- Assert Dataset discovery finds exactly `web-search-01`, `web-fetch-01`, and
  `trend-digest-01` in `pbench-v1.0`, and `browser-control-01` in
  `pbench-v1.0-plus`.
- For search and fetch, cover the positive trajectory and failures for the wrong
  tool, every accepted exact alias and glob family, forbidden exact and glob
  aliases, wrong arguments or URL, a failed observation or non-zero exit code,
  evidence from another `tool_call_id`, cross-branch evidence, and missing final
  terms.
- For browser control, additionally cover missing, unsafe, symlinked, empty, or
  format-invalid screenshots, a missing final screenshot reference, and both the
  browser and `computer_action` branches.
- For Trend Digest, use a fixed UTC clock and local GitHub, Nitter RSS, and
  Hacker News API response fixtures. Cover XLSX parsing, rolling 24-hour boundaries,
  Nitter fallback, per-account status, top-story ordering, source failures,
  successful Shell-family skill calls, missing skill names, failed or non-zero
  skill executions, stale or previous-step trajectory evidence, report
  filename/front-matter mismatches, exact source URLs adjacent to ordinary prose
  punctuation without accepting longer URL prefixes, final answers naming the
  wrong step artifact, and snapshot/report omissions. Assert the Task remains valid without any
  `solution/` directory and do not invoke Harbor's Oracle Agent.
- Assert each Trend Digest step instruction remains one sentence while naming
  its exact UTC filename pattern and every front-matter field used for grading.
- Assert the Trend Digest manifest's ordered steps, mean reward strategy,
  per-step verifier modes, and `min_reward` gates directly. Generic multi-step
  integration fixtures own runtime resume, persistence, aggregation, and early-
  termination behavior.
- Every complete positive verifier fixture has total reward `1`. Partial X fetch
  failures may produce a lower coverage and total reward while retaining perfect
  source, freshness, format, and final-answer dimensions.

## Live Evaluation

Psychevo Web Search and Web Fetch evaluations are opt-in and require an
available Psychevo runtime, model/provider configuration, and real Web access.
Browser Control additionally requires a compatible browser-capable Agent and is
not implied by Psychevo search/fetch support.

Trend Digest live evaluation is also opt-in because GitHub, public Nitter
instances, and Hacker News are external and time-varying. Classify complete X
source outage separately from an Agent failure, and preserve per-account
failure status in the report and reward details.

Report live results per Task with Trial count, exceptions, reward, failed
checks, and artifact locations. Classify provider, network, browser, harness,
and upstream-site failures separately from Agent failures.

## Related Topics

- [PBench](spec.md)
- [100. Psycheval Testing](../100-psycheval/testing.md)
