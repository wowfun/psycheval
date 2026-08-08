# peval-py Reports

## Normalized Report

A report is a derived, serializable view of normalized source sessions. It
retains stable source keys, source metadata, trajectory content, summary data,
and comparison data required by static rendering and workspace import.

The canonical trajectory and the peval-py sidecar have the ownership defined by
[020. ATIF and peval-py Sidecar Ownership](../020-state-and-data-model/spec.md#atif-and-peval-py-sidecar-ownership).
Report metadata is a projection of those inputs. Values mirrored for existing
Leaderboard or Timeline consumers are derived from the canonical trajectory and
do not become a second trajectory authority.

Report generation is deterministic for the same normalized inputs and options.
Redaction is applied before serialized output is written. A report never edits
its source files.

## Static Presentation

Static HTML is self-contained and usable without a server. Its comparison
surface follows this row-count behavior:

- Zero report rows: no comparison surface.
- One report row: Leaderboard and Overview are available; Summary is omitted.
- Two or more report rows: Summary is available.

Static presentation does not inherit live-workspace empty-state behavior merely
because both surfaces use the same Web modules.

## Output Formats

The CLI may emit normalized JSON, strictly validated ATIF-v1.7 data,
spreadsheet output, and self-contained HTML according to the selected command.
Stateful workspace
exports and their query/selection scopes are specified by
[310. Workspace Presentation](../310-eval-workspace/presentation.md).

## Related Topics

- [peval-py](spec.md)
- [020. State and Data Model](../020-state-and-data-model/spec.md)
- [310. Evaluation Workspace](../310-eval-workspace/spec.md)
