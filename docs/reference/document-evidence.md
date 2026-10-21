# Document inspection and evidence

`psycheval.harbor.documents` exposes `select_document`, `inspect_document`, and
typed, immutable format-specific reports with `to_markdown()`. Inspection returns
facts; Tasks own thresholds, required content, checks, and rewards. Both document
inspection and `psycheval.harbor.evidence` remain relocatable with the Harbor
subtree and do not import workspace, UI, model, or WorkBuddy execution code.

Install `psycheval[pdf]`, `[pptx]`, `[xlsx]`, or `[docx]` for one format, or
`psycheval[documents]` for all four. Parser imports are deferred until inspection;
evidence publication only uses the standard library. Missing optional dependencies
raise `MissingDocumentDependency` with the extra name, rather than failing a Task
check. Transitive import failures also name the missing module. Dependencies must
be installed before verification, never by the grader.
The PPTX extra pins python-pptx exactly because placeholder inheritance and
OOXML access affect grading facts; upgrades require the style regression target.

## Inspection

`select_document(roots, format=..., preferred_stem=..., max_entries=100000,
max_depth=64)` incrementally discovers
regular files, excludes symbolic links, Windows reparse points and Office lock
files, and deduplicates overlapping roots. A unique preferred stem wins; otherwise
a unique candidate is selected. Missing and ambiguous results contain candidate
paths and a reason and never choose by modification time. Root depth is zero.
Exceeding a scan budget or encountering an unreadable entry returns no selection
and an explicit incomplete-scan reason, even if a candidate was already found:
an incomplete scan cannot establish uniqueness. Directory contents are streamed;
deduplication uses lexical absolute paths without resolving each entry.

`inspect_document(path_or_snapshot, format=None, pptx_options=None, limits=...)` reads one
bounded immutable `SourceSnapshot`. Passing a snapshot reuses its bytes. Reports
retain that snapshot so subsequent publication cannot observe a different file.
Corrupt, unsupported or encrypted documents raise `DocumentParseError`;
filesystem and configuration errors remain verifier errors. Unknown individual
styles have explicit diagnostic messages and do not invalidate readable text.
Known backend parse errors are normalized; unexpected programming errors are not
converted into failed document checks.

| Format | Facts and faithful text |
| --- | --- |
| PDF | Page order, extracted text and page dimensions; empty pages remain present. |
| PPTX | Slides, recursive leaf shapes, bounds, paragraphs, runs, table cells, effective font sizes/colors, selected title and background colors. |
| XLSX | Sheet order/visibility, nonempty cells and addresses, merged ranges; formulas and cached results are separate. |
| DOCX | Body paragraphs and tables in document order, nested table content, run text and heading styles; merged cells retain spans. |

PPTX title selection prefers a nonempty title placeholder. Without one, paragraphs
containing a Unicode letter (including Chinese characters) take precedence over
standalone numbers, punctuation and symbols, so decorative concept numbers do not
displace a textual heading. If no such paragraph exists, numeric titles remain
eligible. Within that candidate set, the largest effective paragraph font wins,
breaking ties by top position, shape order and paragraph order. Selection does not
use font color; an explicitly marked numeric title placeholder still takes priority.
`PptxOptions` makes the fallback font size and full-canvas background coverage
explicit (defaults 18 points and 0.95). Theme, layout and master inheritance,
alpha composition, gradient stops and transformed group coordinates are resolved
from OOXML. Unresolved colors are never assumed to pass a color requirement.
Background color collections contain distinct possible RGB values, not one value per
overlapping transparent shape. Incomplete or degenerate group transforms retain
their leaf text with `bounds=None` and a `geometry_error`; dependent spatial
style facts remain unresolved. Title and background diagnostics are independent:
an unresolvable title font does not prevent inspection of the page background.

Text extraction preserves page/shape/paragraph, sheet/cell or body-block
boundaries. It does not substitute notes, document properties, agent answers,
images or error messages for body text. PDF extraction is not OCR; DOCX does not
have a reliable rendered page count; XLSX cached values may be absent and are
never recalculated. Rendering, application automation and pixel judgments are
outside these interfaces.
XLSX inspection loads the same bytes twice to retain formulas and cached results.
Its sparse stored-cell traversal avoids expanding empty rectangular ranges; the
two workbook models still contribute to parser peak memory.

## Evidence publication

Use one `EvidenceWriter(verifier_logs)` context per verification attempt.
`capture(id, path_or_snapshot, max_bytes=64 * 1024 * 1024)` retains the source as `raw_<format>` and returns
the snapshot. `add_text(id, text, source_id=..., path=...)` writes Markdown
evidence; empty text is marked missing. `unavailable(id, reason, status=...)`
records missing or failed extraction explicitly. IDs and output paths are
validated before writing; generated output never traverses links.
The same capture byte limit applies to paths and existing snapshots. Set it to
`limits.source_bytes` when using a raised inspection source limit.
Writer options `max_total_bytes`, `max_artifacts`, and `max_text_bytes` default
to 256 MiB, 64 records, and 4 MiB per text artifact. Total bytes include the
manifest, which is additionally capped at 1 MiB. `EvidenceLimitError` is raised
before an over-budget write; callers may explicitly publish `unavailable`
instead. Oversized evidence is never silently truncated.

The writer owns `artifact_manifest.json`, `artifact_text/`, and `raw_artifacts/`.
It clears those outputs on entry, writes each file atomically, and publishes the
manifest last on successful exit. Failed attempts do not publish a successful
manifest. Captured originals remain available for diagnosis, including when
document parsing fails. Other verifier logs are not removed.

Raw records contain the original `source_path`, retained `verifier_raw_path`, type,
byte count and SHA-256. Text records use `type: md`, their Markdown `source_path`
and `text_path`, extraction status, byte count and SHA-256, with an optional
`source_artifact_id`. `judge.yaml` references text IDs; originals are not sent
to the Judge implicitly. This is the existing artifact-manifest protocol, also
readable by the Office shared Judge; it does not change either scoring protocol.
`source_path` describes provenance, not a downloadable verifier path. Consumers
resolve only `verifier_raw_path` and `text_path` under their allowlisted roots.

`DocumentLimits` bounds source bytes, OOXML archive entries and expanded bytes,
logical pages (PDF/PPTX pages or XLSX sheets), report facts, and extracted UTF-8
text. Facts include shapes (including groups), paragraphs, runs, tables, cells
(including stored blank spreadsheet cells) and merged ranges. PPTX counts every
traversed shape, including master/layout shapes visited for each slide's background
analysis, before filtering placeholders. Inheritance trees disabled for that
analysis are not traversed or charged. `color_operations` bounds PPTX color work
across the whole document: resolving colors and transforms, composing candidates,
collecting palettes and materializing report colors. Repeated candidates count
even when deduplicated; slide boundaries and inherited styles do not reset this
budget. Candidate streams are charged before collection, so translucent overlays
and gradients cannot expand palettes without consuming it. Exceeding this budget
fails inspection, rather than becoming an unresolved-style diagnostic. Limits are
checked as facts are produced; `to_markdown()` also checks the report's text
budget including formatting. Text budgets count UTF-8 bytes, including multibyte
characters and Markdown separators. Exceeding a content budget raises
`DocumentLimitError`, a `DocumentParseError` subtype. Limits fail explicitly,
with no silent truncation.

These bound inputs, outputs and the inspector's color expansion, not all CPU or
peak-memory use.
Third-party parsers can allocate or decompress PDF streams before returning
text or facts. Parser execution therefore still needs the verifier's process
timeout and environment resource controls for hostile inputs. Existing Judge text-read
budgets continue to apply independently; see [Harbor](harbor.md#yaml-llm-judge).

```python
from psycheval.harbor.documents import inspect_document, select_document
from psycheval.harbor.evidence import EvidenceWriter

selection = select_document([workdir, artifacts], format="pptx")
with EvidenceWriter(verifier_logs) as evidence:
    if selection.selected is None:
        evidence.unavailable("presentation_text", selection.reason)
    else:
        source = evidence.capture("presentation_pptx", selection.selected)
        report = inspect_document(source)
        evidence.add_text(
            "presentation_text",
            report.to_markdown(),
            source_id="presentation_pptx",
            path="artifact_text/presentation.md",
        )
```

Tasks catch `DocumentParseError` when unreadable output should fail a declared
check. They must not catch missing dependencies or publication errors as an
ordinary failed check. Content inside evidence remains untrusted assessment data.
