# Reports

[简体中文](../../i18n/zh-CN/user/peval/reports.md)

Use `--steps`, `--tool-call`, or `--source` to narrow evidence. Add `-m raw`
when you need a complete JSON report. Use `peval serve` for browser presentation.

```console
peval view tr -m raw \
  -d ~/.psychevo/state.db \
  -s <session-a> -s <session-b> \
  -n 0="Report context" \
  -n 2="Session B follow-up" \
  --source-alias 2="Candidate" -o
```

Note index `0` belongs to the report; positive indexes follow expanded session
order. Aliases change presentation only, never evidence identity.

Use `--no-redact` only when the output location and audience are trusted. The
[CLI reference](../../reference/cli.md) owns output behavior; the
[state and data reference](../../reference/state-and-data.md) owns evidence and
presentation boundaries.

JSON reports include structured `metric_provenance` for default measurements,
including unavailable values. Hover over workbench metrics for source, formula,
coverage and missing reasons. Excel exports retain the numeric sheets and add a
provenance sheet. If its detail limit is reached, a final record states how many
source records were omitted; numeric rows remain intact. Historical values keep their original measurement basis.
