from __future__ import annotations

import shlex

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.utils.trajectory_validator import TrajectoryValidator

from psycheval_harbor import __version__


class ExternalHarnessAgent(BaseAgent):
    """Run a caller-provided harness that writes canonical ATIF output."""

    SUPPORTS_ATIF = True

    def __init__(self, *args, command: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.command = (command or "").strip()
        if not self.command:
            raise ValueError("ExternalHarnessAgent requires --agent-kwarg command=...")
        if "\x00" in self.command:
            raise ValueError("ExternalHarnessAgent command contains NUL")

    @staticmethod
    def name() -> str:
        return "psycheval-external-harness"

    def version(self) -> str:
        return __version__

    async def setup(self, environment: BaseEnvironment) -> None:
        return None

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        instruction_path = self.logs_dir / "instruction.txt"
        instruction_path.write_text(instruction, encoding="utf-8")
        virtual_instruction = "/logs/agent/instruction.txt"
        result = await environment.exec(
            f"{self.command} < {shlex.quote(virtual_instruction)}",
            cwd="/app",
        )
        (self.logs_dir / "external-harness.stdout.log").write_text(
            result.stdout or "", encoding="utf-8"
        )
        (self.logs_dir / "external-harness.stderr.log").write_text(
            result.stderr or "", encoding="utf-8"
        )
        if result.return_code != 0:
            diagnostic = (result.stderr or result.stdout or "no output").strip()
            raise RuntimeError(
                f"external harness exited with {result.return_code}: {diagnostic[-2000:]}"
            )
        trajectory_path = self.logs_dir / "trajectory.json"
        if not trajectory_path.is_file():
            raise RuntimeError(
                "external harness did not write /logs/agent/trajectory.json"
            )
        validator = TrajectoryValidator()
        if not validator.validate(trajectory_path):
            raise RuntimeError(
                "external harness wrote invalid ATIF: " + "; ".join(validator.errors)
            )
        context.metadata = {
            "harness_return_code": result.return_code,
            "trajectory": str(trajectory_path),
        }
