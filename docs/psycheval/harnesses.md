# Psycheval Harnesses

ExternalHarnessAgent runs a caller-provided command. The command reads the Task
instruction from stdin and writes canonical ATIF v1.7 to the path exposed as
`PSYCHEVAL_AGENT_LOGS_DIR/trajectory.json`.

## Canned Harness

The canned harness provides deterministic `web-search`, `web-fetch`, and
`browser-control` trajectories. It is intended for verifier and integration
validation, not Agent-quality measurement.

```text
python -m psycheval.harbor.canned_harness --scenario web-search
```

## Psychevo Harness

The Psychevo harness runs `pevo run --format json`, retains its NDJSON and
stderr logs, and converts typed transcript events to ATIF without inventing
missing tool evidence.

```text
python -m psycheval.harbor.psychevo_harness --pevo /path/to/pevo
```

Psychevo Web Search and Web Fetch require configured model/provider access and
real public Web access. They are opt-in live evaluations, not CI checks.

## Diagnosing A Trial

Inspect these files in order:

1. `agent/psychevo.ndjson`
2. `agent/trajectory.json`
3. `verifier/checks.json`
4. `verifier/reward.json`
5. `agent/psychevo.stderr.log` and `trial.log`

A reward of zero means the completed trajectory missed a scoring condition. A
missing trajectory/reward, provider error, network failure, target-site block,
or conversion exception is a harness or infrastructure failure instead.

Harbor 0.20.0's default trace exporter still rejects truthful custom import-path
Agent identities in its built-in Agent-name conversion. Use the Trial result,
ATIF trajectory, checks, reward, artifacts, and Harbor viewer; do not masquerade
as a built-in Agent to work around the exporter.
