# Native prepared files

This authoring example uses `HostEnvironment` and `HostVerifier` on Windows or
Linux. It needs only Python's standard library, the installed Psycheval package,
and Git for the default workspace baseline. It is not a maintained Dataset member.

`prepare.py` reads the bundled reference date and transforms the source data
into the Agent's `input.json`. The source date is fixed by the Task so reruns
remain reproducible; the framework does not supply a clock. Preparation selects
`input.json` for the initial-input snapshot and retains its reference date in
private preparation state. Without a preparation
script, put already prepared inputs in `environment/data/` for automatic copying.

The Agent writes `output.json` and briefly explains its calculation and date
source in the final reply. This remains a small file-transformation example;
no tools or particular calculation method are required. The total is a JSON
number, excluding booleans and strings; equivalent forms such as `6.0` are
accepted. The date is the unchanged ISO calendar-date string. Malformed UTF-8,
duplicate keys, nonstandard constants, a non-object, or an output of 64 KiB or
more fail both checks. A valid object with just one correct field can earn that
field's credit; extra fields do not earn credit.

Harbor collects the explicitly declared output before verification. Under the
Native Host mapping, `paths.artifacts` identifies
`Trial/artifacts/logs/artifacts`; the explicit destination is its grandparent's
`output.json`. The grader requires that mapping and reads only that retained
output, never the workspace or a similarly named convention file. Missing or
unsafe output fails checks. Unavailable runtime paths, corrupt private GT,
retained inputs or preparation state, or disagreements between their totals
and dates are verifier errors. The original fixed source date and private GT
remain unchanged; a fresh clock is never read while grading.

One `EvidenceWriter` captures the retained input, preparation reference and
original output bytes, then publishes source text, validation facts and the
current final reply using the public `final_answer_text` helper. Grading reads
those same snapshots. Changing the workspace input after preparation therefore
cannot change the expected answer. Native Host is trusted execution; these
paths are a framework contract, not strong isolation from same-user processes.

The deterministic total check has weight 3 and the date check weight 1. With
Judge disabled, a correct total and wrong date score 0.75. The optional YAML
Judge uses only the published input, output, facts and final reply to assess
the brief explanation. It cannot replace either calculation check. A complete
Judge assessment merges 90% of the rule score with 10% explanation credit;
correct numbers with an unsupported or missing explanation thus score 0.9.
The required `verified_output` evidence is published only when both objective
checks pass; otherwise the rubric fails locally without a model request. A
correct total and wrong date therefore score 0.675 with Judge enabled, even if
the model would have accepted the explanation.
If the trajectory is absent, that limitation is published and the explanation
cannot earn credit. Disabled or incomplete Judge assessment retains the rule
score and does not establish that explanation quality was assessed. Judge
connection settings belong to the evaluation runtime, not this example.

Use the [native Host configuration](../../../docs/user/downstream-vendoring.md)
with this Task path. The [Harbor contract](../../../docs/reference/harbor.md)
defines preparation, and the
[Harbor verifier contract](../../../docs/reference/harbor-verifier.md) defines
script arguments, JSON results, and scoring. Source-copy
installations must follow the linked vendoring guide for both entrypoints and
custom-script imports; ordinary Psycheval installations need no import changes.
