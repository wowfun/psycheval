from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from psycheval.skill_install import (
    SkillInstallResult,
    install_skill,
    prepare_skill_install,
)
from psycheval.state import STATE_SCHEMA_VERSION, ServeStateStore, workspace_paths


@dataclass(frozen=True)
class InitWorkspaceResult:
    schema_version: int
    root: Path
    peval_config: Path
    log_path: Path
    agent_skill: SkillInstallResult | None

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "root": str(self.root),
            "peval_config": str(self.peval_config),
            "log_path": str(self.log_path),
            "agent_skill": (
                self.agent_skill.to_jsonable() if self.agent_skill is not None else None
            ),
        }


def init_workspace(
    root: str | None = None, *, skill_dir: str | None = None
) -> InitWorkspaceResult:
    root_path = Path(root).expanduser() if root else Path.cwd()
    resolved_root = root_path.resolve()
    skill_request = (
        prepare_skill_install(resolved_root, skill_dir)
        if skill_dir is not None
        else None
    )
    paths = workspace_paths(root_path)
    store = ServeStateStore(paths)
    store.close()
    agent_skill = install_skill(skill_request) if skill_request is not None else None
    return InitWorkspaceResult(
        schema_version=STATE_SCHEMA_VERSION,
        root=paths.root,
        peval_config=paths.config_path,
        log_path=paths.log_path,
        agent_skill=agent_skill,
    )


def render_init_text(result: InitWorkspaceResult) -> str:
    text = (
        f"peval workspace: {result.root}\n"
        f"peval config: {result.peval_config}\n"
        f"serve log: {result.log_path}\n"
    )
    if result.agent_skill is None:
        return text
    return (
        text
        + f"Agent Skill ({result.agent_skill.action}): {result.agent_skill.path}\n"
        + "Start a new Copilot session after an Agent Skill install or replacement.\n"
    )


def run_init_command(args: Any) -> None:
    result = init_workspace(
        getattr(args, "root", None), skill_dir=getattr(args, "skill_dir", None)
    )
    if getattr(args, "json", False):
        print(json.dumps(result.to_jsonable(), ensure_ascii=False, indent=2))
    else:
        print(render_init_text(result), end="")
