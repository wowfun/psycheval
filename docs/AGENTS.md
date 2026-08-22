# Documentation Ownership

- Describe the current repository, not migrations or archived specifications.
- `architecture.md` owns the system map and seams; `reference/` owns stable
  semantics; `user/` owns executable workflows; `development.md` and
  `testing.md` own contribution guidance.
- Source and tests own exact schemas, defaults, enums, payloads, and errors.
- English is authoritative. Review the four paired Chinese CLI guides with their
  English sources and record their hashes together.
- Link to the owner instead of copying facts. Do not create navigation indexes.
- Run `uv run python scripts/check_docs.py` after documentation changes.
