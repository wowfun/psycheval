# Viewing Trajectories

Use the smallest `peval view tr` command that exposes the evidence needed for
the analysis.

## Harbor Trials

Pass the Trial root, not a file below it, to retain Harbor evaluation context:

```console
peval view tr -p <trial-dir>
```

A single-step Trial produces one source. A MultiStepTrial produces one source
per Harbor step in `result.step_results` order; extra retained step directories
follow in deterministic name order with a warning. Repeat `-p` to compare
Trials. Input order is preserved, and `--source N` selects from the expanded,
one-based source list.

The default inspect output includes the trajectory digest plus a `harbor`
object with task, Job, Trial, optional Harbor step, rewards, parent Trial
evaluation, provenance, warnings, failures, and trajectory availability.

If a running or failed source has no trajectory, inspect mode still reports its
Harbor diagnostic. Complete report mode fails instead of creating an empty ATIF
trajectory.

## Narrow Evidence

Use head, tail, and top limits for a compact overview:

```console
peval view tr -p <trial-dir> --head 3 --tail 3 --top 5
```

Select ATIF trajectory step IDs after identifying the Harbor source:

```console
peval view tr -p <trial-dir> --source <source-number> --steps <step-ids>
```

Select a retained tool call and its corresponding result:

```console
peval view tr -p <trial-dir> --source <source-number> --tool-call <tool-call-id>
```

`--steps` addresses ATIF events inside a source; it does not select a Harbor
MultiStep phase. Use `--source` for the latter.

## Complete Reports

Use a complete JSON report only when the analysis needs full retained content:

```console
peval view tr -m raw -p <trial-dir> -o <report.json>
```

Do not use complete report mode when any selected Harbor source reports
`trajectory_available=false`.

## Other Retained Sources

The same view command accepts strict ATIF JSON, supported adapter JSON/JSONL,
adapter databases, Psycheval Trial cells, and saved workspace snapshots. A
direct `agent/trajectory.json` is intentionally treated as ATIF rather than as
its parent Harbor Trial.

List an adapter database before choosing an unknown session:

```console
peval view tr -r <workspace> -a <adapter> -d <adapter-db> --list
```

List saved workspace sources with an explicit workspace root:

```console
peval view tr -r <workspace> -d <workspace>/state.db --list
```

Treat inspect summaries as projections. When a finding depends on exact
content, narrow the source first and verify it against the retained trajectory
and metadata represented by the complete report.
