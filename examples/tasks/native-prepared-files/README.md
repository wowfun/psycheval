# Native prepared files

This authoring example uses `HostEnvironment` and `HostVerifier` on Windows or
Linux. It needs only Python's standard library, the installed Psycheval package,
and Git for the default workspace baseline. It is not a maintained Dataset member.

`prepare.py` reads the bundled reference date and transforms the source data
into the Agent's `input.json`. The source date is fixed by the Task so reruns
remain reproducible; the framework does not supply a clock. Without a preparation
script, put already prepared inputs in `environment/data/` for automatic copying.

The Agent writes `output.json`. The custom script compares it with private GT:
the total carries weight 3 and the date carries weight 1. A correct total with
an incorrect date scores 0.75. Missing or invalid Agent output fails checks;
a broken GT file is a verifier error. The script can also read an available ATIF
at `context["paths"]["agent_logs"]/trajectory.json`; this example does not require
trajectory evidence.

Use the [native Host configuration](../../../docs/user/downstream-vendoring.md)
with this Task path. The [Harbor contract](../../../docs/reference/harbor.md)
defines preparation, script arguments, JSON results, and scoring. For source-copy
installations, update the two Task entrypoints to the installed verifier module.
