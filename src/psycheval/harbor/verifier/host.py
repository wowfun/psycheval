"""Explicit runtime-path protocol for Harbor test scripts on a native Host."""

from harbor.models.verifier.result import VerifierResult
from harbor.verifier.verifier import Verifier

from ..environment import HostEnvironment


class HostVerifier(Verifier):
    """Run Harbor's verifier with native paths available to trusted test scripts."""

    async def verify(self) -> VerifierResult:
        if not isinstance(self.environment, HostEnvironment):
            raise TypeError("HostVerifier requires HostEnvironment")
        with self.environment.scoped_exec_env(self.environment.runtime_config_env()):
            return await super().verify()
