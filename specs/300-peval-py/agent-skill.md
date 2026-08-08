# peval-py Agent Skill

## Skill Contract

`skills/peval-py` is an Agent Skill that teaches an agent to invoke the installed
`peval-py` command, choose inputs and adapters, inspect results, and create
reports. It is not imported by the peval-py Python package and is not repository
maintenance automation.

The Skill owns its `SKILL.md`, references, and helper scripts as one portable
directory. Internal links remain relative to that directory. Examples favor
deterministic fixtures and never require real user configuration or credentials.

The Skill describes public command behavior and links to canonical user
documentation. It does not duplicate the full CLI specification or generated
option inventory.

## Related Topics

- [peval-py](spec.md)
- [001. Repository Architecture](../001-architecture/spec.md)
