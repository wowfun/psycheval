- Read [the architecture](docs/architecture.md) before changing product seams or
  repository layout, and read the nearest subtree `AGENTS.md` before editing.
- This is a pre-release project without compatibility promises. Update affected
  paths, entry points, fixtures, tests, and docs together instead of adding shims.
- Give each current fact one owner and link to it elsewhere. Do not maintain
  navigation indexes or duplicate machine-exact source and test contracts.
- Follow [documentation ownership](docs/AGENTS.md) for docs changes.
- Preserve evidence provenance, unrelated worktree changes, and user-authored
  workspaces; derived reports and catalogs must not rewrite their sources.

## Tests

- Add or update the closest deterministic behavior or invariant test.
- Select checks from [the testing guide](docs/testing.md); never use real
  credentials, profile databases, provider state, or user workspaces by default.
- Leave exhaustive platform matrices to CI and report only platforms exercised.
