"""Explicit runtime-path protocol for Harbor test scripts on a native Host."""

from harbor.models.task.task import strip_canary
from harbor.models.verifier.result import VerifierResult
from harbor.verifier.verifier import Verifier

from ..environment import HostEnvironment
from ..runtime_config import VerifierInvocation


class HostVerifier(Verifier):
    """Run Harbor's verifier with native paths available to trusted test scripts."""

    async def verify(self) -> VerifierResult:
        if not isinstance(self.environment, HostEnvironment):
            raise TypeError("HostVerifier requires HostEnvironment")
        if not self._skip_tests_upload:
            await self.environment.empty_dirs(["/tests"], chmod=False)
        instruction_path = (
            self.task.paths.step_instruction_path(self.step_name)
            if self.step_name is not None
            else self.task.paths.instruction_path
        )
        instruction = "\n\n".join(
            [
                strip_canary(instruction_path.read_text(encoding="utf-8")),
                *(
                    path.read_text(encoding="utf-8")
                    for path in self.task.extra_instruction_paths
                ),
            ]
        )
        context = VerifierInvocation(instruction, self.step_name)
        with self.environment.scoped_exec_env(
            self.environment.runtime_config_env(verifier=context)
        ):
            return await super().verify()
