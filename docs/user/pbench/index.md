# PBench User Guide

PBench is Psycheval's maintained Harbor Dataset. Its current Tasks and scoring
model are owned by the [PBench reference](../../reference/pbench.md).

From a trusted source checkout, run a compatible Agent with the explicit host
environment so Task verifiers can use the installed project interpreter:

```console
uv run harbor run \
  -p datasets/pbench-v1.0 \
  --env psycheval.harbor.environment:HostEnvironment \
  --environment-kwarg allow_host_execution=true \
  [AGENT OPTIONS]
```

This opts into host execution; read its safety rules in the
[Harbor reference](../../reference/harbor.md) first. Use
[Authoring](authoring.md) for Task workflow and [Scoring](scoring.md) when
interpreting verifier output.
