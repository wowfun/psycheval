# Reports

## Compare Sessions

`view tr` defaults to a bounded inspect digest. Add `-m raw` for a complete
JSON or HTML report. Raw mode accepts repeated path, DB, and session inputs;
each expanded session becomes one report row with a stable source key and one
selectable Trial.

```bash
peval-py view tr -m raw \
  -d ~/.psychevo/state.db \
  -s <session-a> -s <session-b> \
  -n 0="Report context" \
  -n 2="Session B follow-up" \
  --source-alias 2="Candidate" \
  -o
```

Note index `0` is report-level; positive indexes follow expanded session order.
Aliases are display-only and never change session, trajectory, Trial, source, or
evidence identity.

Static reports contain no comparison surface at zero rows. At one row they show
Leaderboard and Overview but omit Summary; Summary begins at two rows.

## Output and Redaction

The output suffix selects JSON or self-contained HTML unless `--format` is
explicit. Bare `-o` creates a derived name. `export tr` is intentionally
single-session; repeated inputs are for `view tr`.

Reports redact obvious secret-bearing keys, authorization headers, bearer
tokens, and common token assignments by default. `--no-redact` explicitly
disables this protection. Numeric usage and accounting totals stay visible.

Use `--max-content-chars` to bound large messages and tool payloads. Unmatched
tool results remain visible as standalone observation steps and produce a
conversion warning.

## Reading A Report

The selected Trial shows Run and Result summaries, optional Notes and Usage
Breakdown, and its trajectory steps. Tool observations remain attached to the
Agent step with the matching call. Failed tools remain visible.

When sources omit per-step token counts, HTML may show an `≈` visual estimate.
Timing fills are likewise presentation cues. Neither estimate is written into
ATIF or report JSON.

## Cached Analysis and Cell Notes

With a workspace root, peval-py reads exact Trial-cell files without modifying
the source trajectory:

```text
runs/<eval>/<agent>/<session>/<cell>/analysis.json
runs/<eval>/<agent>/<session>/<cell>/analysis.md
runs/<eval>/<agent>/<session>/<cell>/notes.md
```

Matching analysis is exposed under `annotations.analysis`; cell notes are
`annotations.notes` entries with source `cell`. Missing or malformed optional
analysis is ignored. Session-root analysis and notes are reserved and are not
projected into Trial reports.

## Localization

Set `locale = "zh-CN"` in config or the workspace `peval-py.toml`. `zh` aliases
to `zh-CN`; `en-US` normalizes to `en`. Serve provides an English/Chinese
selector that persists the workspace locale; static reports use render-time
config.
