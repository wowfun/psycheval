# Viewing Source Evidence

Prefer workspace source references because they preserve normalized local or
Harbor identity without exposing mount paths:

```console
peval view tr -r <workspace> --source-ref <ref>
```

A local reference returns its imported session. A Harbor parent Trial reference
returns every phase in Harbor result order, while a `/steps/<name>` reference
returns only that phase. Repeat `--source-ref` to compare sources; input order is
preserved after parent expansion.

The default inspect output is bounded. Use `--head`, `--tail`, and `--top` for a
compact overview, then select ATIF event IDs or tool calls only after identifying
the relevant phase:

```console
peval view tr -r <workspace> --source-ref <ref> --steps <step-ids>
peval view tr -r <workspace> --source-ref <ref> --tool-call <tool-call-id>
```

An ATIF step is an event inside a Harbor phase; it is not a MultiStep phase.
When `trajectory_available` is false, analyze only the retained status,
exception, reward, and provenance.

Direct Harbor Trial paths remain useful outside a configured workspace:

```console
peval view tr -p <trial-dir>
```

Passing `agent/trajectory.json` directly intentionally loses Harbor Task, Job,
Trial, reward, and provenance context.
