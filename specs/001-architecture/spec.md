---
name: Repository Architecture
---

# Repository Architecture

The repository is organized by independently understandable modules and their
interfaces rather than by a single workspace abstraction.

## Scope

This topic defines repository topology, delivery units, dependency direction,
and ownership of specifications, code, datasets, examples, and documentation.
It does not prescribe the internal function layout of a small module.

## Repository Topology

- The root Python project is the independently buildable `psycheval`
  distribution, implemented under `src/psycheval` and tested under `tests`.
- Harbor-specific implementations live below the public
  `psycheval.harbor` namespace.
- `datasets/` contains maintained evaluation datasets. A versioned PBench
  directory is a Harbor local Dataset whose immediate child directories are
  Tasks.
- `examples/` contains learning and authoring examples, not the maintained
  evaluation catalog.
- `tools/peval-py/` is an independently buildable auxiliary product with its own
  Python and Web build graphs and lockfile.
- `skills/peval-py/` is an independently consumable Agent Skill that invokes the
  peval-py command interface.
- `specs/` owns stable normative contracts. `docs/` owns task-oriented user
  guidance. Neither copies the other wholesale.

## Dependency Direction

- `psycheval` may depend on Harbor's published interface.
- PBench Tasks may depend on Harbor's Task format and on an installed Psycheval
  verifier, but not on repository-relative source paths.
- peval-py may consume standard trajectory and report formats, but does not
  import `psycheval`.
- `psycheval` does not import peval-py.
- Documentation and examples may reference public interfaces; production code
  must not depend on them.

Shared formats do not create a shared implementation module. A common code seam
is introduced only after multiple concrete implementations genuinely vary at
that seam.

## Public Interfaces

The root project publishes Python imports and console scripts. Harbor itself
remains the user-facing execution CLI; Psycheval does not wrap it with a second
command layer.

PBench is addressed by a Dataset path. peval-py is addressed by its existing
`peval-py` command and Python package. Repository paths that are not documented
as public are implementation details.

## Change Ownership

- A stable rule changes first in its source specification.
- Code and behavior tests implement that rule.
- User documentation explains the resulting workflow without redefining it.
- `CHANGELOG.md` records the delivered user-visible change after implementation.

## Related Topics

- [000. Psycheval Foundation](../000-foundation/spec.md)
- [100. Psycheval](../100-psycheval/spec.md)
- [200. PBench](../200-pbench/spec.md)
- [300. peval-py](../300-peval-py/spec.md)
- [310. Evaluation Workspace](../310-eval-workspace/spec.md)
