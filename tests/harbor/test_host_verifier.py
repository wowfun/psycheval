import asyncio
import json
import sys

import pytest
from harbor.models.verifier.result import VerifierResult
from harbor.verifier.verifier import Verifier

from psycheval.harbor.verifier.host import HostVerifier
from tests.harbor.test_environment import make_environment


@pytest.mark.parametrize("outcome", ["success", "failure", "cancel"])
def test_host_verifier_protocol_is_scoped_to_verification(
    tmp_path, monkeypatch, outcome
):
    async def scenario():
        host = make_environment(tmp_path / "host")
        await host.start(False)
        verifier = object.__new__(HostVerifier)
        verifier.environment = host
        failure = (
            asyncio.CancelledError() if outcome == "cancel" else RuntimeError("fixture")
        )

        async def verify(self):
            result = await host.exec_argv(
                [
                    sys.executable,
                    "-c",
                    "import json,os; print(open(os.environ['PEVAL_CONFIG'], encoding='utf-8').read())",
                ]
            )
            assert result.return_code == 0, result.stderr
            config = json.loads(result.stdout)
            assert config["paths"]["agent_logs"] == str(host.trial_paths.agent_dir)
            assert config["paths"]["verifier_logs"] == str(
                host.trial_paths.verifier_dir
            )
            if outcome != "success":
                raise failure
            return VerifierResult(rewards={"reward": 1.0})

        monkeypatch.setattr(Verifier, "verify", verify)
        try:
            if outcome == "success":
                assert (await verifier.verify()).rewards == {"reward": 1.0}
            else:
                with pytest.raises(type(failure)) as caught:
                    await verifier.verify()
                assert caught.value is failure
            ordinary = await host.exec_argv(
                [
                    sys.executable,
                    "-c",
                    "import os; assert 'PEVAL_CONFIG' not in os.environ",
                ]
            )
            assert ordinary.return_code == 0, ordinary.stderr
        finally:
            await host.stop(True)

    asyncio.run(scenario())


def test_host_verifier_rejects_other_environments():
    verifier = object.__new__(HostVerifier)
    verifier.environment = object()
    with pytest.raises(TypeError, match="requires HostEnvironment"):
        asyncio.run(verifier.verify())
