# Trial Analysis Publication

## Criterion provenance

The named criterion comes from the currently allowlisted live Task directory at
`environment/skills/<name>`. A recorded Task digest mismatch or a package ref
that is not locally comparable does not block analysis, but the report must keep
the publisher-provided warning prominent. Do not claim the live skill is
byte-identical to the skill available during the Trial unless the provenance
supports that claim.

A missing, ambiguous, invalid, unreadable, linked, non-UTF-8, or oversized Task
skill is not an invitation to guess. Stop that Trial's analysis and report the
diagnostic.

## Draft and publish boundary

Drafting is read-only and belongs in plan mode. Publication mutates Harbor's
Trial-root `analysis.md`, so it requires a manual mode switch and explicit user
confirmation. Never publish merely because a draft exists or because another
Trial in the batch was approved.

The publisher owns the report identity and provenance preamble. Do not hand-edit
that preamble to hide a mismatch. The body should follow the provided template
and use the user's language.

Creation fails when a report already exists. Replacement requires the exact
current analysis revision presented during preflight. Evidence or criterion
changes invalidate approval even when the Markdown draft itself did not change.

The returned receipt is the authority for what was committed. Catalog refresh
is derived and recoverable; if publication succeeds but reconciliation fails,
state that distinction exactly.
