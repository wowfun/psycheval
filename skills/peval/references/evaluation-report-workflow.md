# Evaluation Report Publication

## Basis provenance

The user's evaluation brief determines the questions and intended basis. A
path, live Task, skill, Dataset/Task context, current report, or other attachment
is analysis material only in the role the user gives it. Its availability does
not prove relevance, authority, Agent use, or equivalence to the content that
existed when the source was recorded.

Keep these classes distinct in the report:

- retained source evidence recorded with the evaluated run;
- live context read during the current analysis;
- material supplied or characterized by the user; and
- analytical inference.

Missing or ambiguous basis narrows what can be concluded. Ask a focused question
when it leaves the target or evaluation brief unclear; otherwise state the
limitation instead of inventing a default rubric.

## Draft and publish boundary

Drafting is read-only and belongs in plan mode. After every requested change,
show the complete current Markdown draft. Publication mutates the canonical
source `analysis.md`, so it requires both a manual switch to execute/build mode
and explicit confirmation of that complete draft. A prior confirmation does not
cover later edits or another source.

Do not add an approval token, provenance preamble, revision, or publisher-only
content. Save and pass the exact approved Markdown body to the publisher. An
existing report uses the same command and confirmation path as a new report;
there is no separate replacement or force operation.

The returned receipt is the authority for what was committed. Catalog refresh
is derived and recoverable; if publication succeeds but reconciliation fails,
state that distinction exactly. Concurrent writers complete under the source
lock and the last completed publication is current.

## Batches

Normalize Harbor phases to their parent Trial, deduplicate targets, and process
each canonical source independently. Show and confirm one report before
publishing it. Report every receipt and failure without implying an
all-or-nothing transaction.
