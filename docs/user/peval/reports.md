# Reports

[简体中文](../../i18n/zh-CN/user/peval/reports.md)

Use `--steps`, `--tool-call`, or `--source` to narrow evidence. Add `-m raw`
when you need a complete JSON or self-contained HTML report.

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
