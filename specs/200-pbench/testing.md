# PBench Testing

## Scope

This attachment defines deterministic Task validation and opt-in live Agent
evaluation for PBench.

## Deterministic Validation

- Validate each committed Task with Harbor 0.20.0 and an explicit canned
  scenario. One canned command is not required to auto-route the entire Dataset.
- At least one deterministic Trial uses the documented HostEnvironment command
  and executes the Task's `test.sh` through the injected project interpreter.
- Assert Dataset discovery finds exactly the three immediate Task directories.
- For search and fetch, cover the positive trajectory and failures for the wrong
  tool, forbidden tools, wrong arguments or URL, a failed observation, evidence
  from another `tool_call_id`, and missing final terms.
- For browser control, additionally cover missing, unsafe, symlinked, empty, or
  format-invalid screenshots.
- Every successful Trial has zero exceptions and binary reward `1`.

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
