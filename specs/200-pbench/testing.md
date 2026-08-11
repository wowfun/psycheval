# PBench Testing

## Scope

This attachment defines deterministic Task validation and opt-in live Agent
evaluation for PBench.

## Deterministic Validation

- Validate each committed Task with Harbor 0.21.0 and an explicit canned
  scenario. One canned command is not required to auto-route the entire Dataset.
- Assert all three Tasks and the authoring scaffold ship equivalent thin
  `test.sh` and `test.bat` entrypoints that invoke the installed verifier.
- On Linux or WSL, at least one deterministic Trial uses the documented
  HostEnvironment command and executes the Task's `test.sh` through the injected
  project interpreter.
- On a native Windows runner, the same Task executes `test.bat` through the
  installed project interpreter, uses a Trial-owned path containing whitespace,
  returns reward `1`, and records zero exceptions. WSL, Wine, and Git Bash are
  not native Windows acceptance environments.
- Assert Dataset discovery finds exactly `web-search-01` and `web-fetch-01` in
  `pbench-v1.0`, and `browser-control-01` in `pbench-v1.0-plus`.
- For search and fetch, cover the positive trajectory and failures for the wrong
  tool, every accepted exact alias, forbidden aliases, wrong arguments or URL, a
  failed observation, evidence from another `tool_call_id`, cross-branch evidence,
  and missing final terms.
- For browser control, additionally cover missing, unsafe, symlinked, empty, or
  format-invalid screenshots and both the browser and `computer_action` branches.
- Every successful Trial has zero exceptions, every binary reward dimension is
  `1`, and total reward is `1`.

## Live Evaluation

Psychevo Web Search and Web Fetch evaluations are opt-in and require an
available Psychevo runtime, model/provider configuration, and real Web access.
Browser Control additionally requires a compatible browser-capable Agent and is
not implied by Psychevo search/fetch support.

Report live results per Task with Trial count, exceptions, reward, failed
checks, and artifact locations. Classify provider, network, browser, harness,
and upstream-site failures separately from Agent failures.

## Related Topics

- [PBench](spec.md)
- [100. Psycheval Testing](../100-psycheval/testing.md)
