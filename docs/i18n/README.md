# Translations

English documentation is authoritative. The four Chinese peval user guides are
paired in `pairs.json`; each entry records the SHA-256 of its English source.
Update both pages, review them together, then run:

```console
uv run python scripts/check_docs.py --record-pairs
uv run python scripts/check_docs.py
```

A hash mismatch means the translation has not been acknowledged against the
current English source.
