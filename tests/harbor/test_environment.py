from __future__ import annotations

import asyncio
import logging
import os
import platform
import sys
from pathlib import Path

import pytest
from harbor.models.task.config import (
    EnvironmentConfig,
    NetworkMode,
    NetworkPolicy,
    TaskOS,
)
from harbor.models.trial.paths import TrialPaths
from harbor.utils.scripts import quote_windows_shell_arg

from psycheval.harbor.environment import HostEnvironment

_LINUX_ONLY = pytest.mark.skipif(
    platform.system() != "Linux", reason="test exercises the Linux process adapter"
)


def make_environment(
    tmp_path: Path,
    *,
    allow: object = True,
    config: EnvironmentConfig | None = None,
    extra_mounts: list[dict] | None = None,
) -> HostEnvironment:
    environment_dir = tmp_path / "task" / "environment"
    environment_dir.mkdir(parents=True)
    (environment_dir / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    trial_paths = TrialPaths(tmp_path / "trial")
    trial_paths.mkdir()
    artifact_mount = trial_paths.artifacts_dir / "logs" / "artifacts"
    artifact_mount.mkdir(parents=True)
    mounts = [
        {"type": "bind", "source": str(trial_paths.agent_dir), "target": "/logs/agent"},
        {
            "type": "bind",
            "source": str(trial_paths.verifier_dir),
            "target": "/logs/verifier",
        },
        {"type": "bind", "source": str(artifact_mount), "target": "/logs/artifacts"},
    ]
    mounts.extend(extra_mounts or [])
    return HostEnvironment(
        environment_dir=environment_dir,
        environment_name="test",
        session_id="test-env",
        trial_paths=trial_paths,
        task_env_config=config or EnvironmentConfig(workdir="/app"),
        logger=logging.getLogger("test"),
        mounts=mounts,
        allow_host_execution=allow,
    )


def test_requires_explicit_host_execution_opt_in(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="allow_host_execution=true"):
        make_environment(tmp_path, allow=False)


def test_rejects_resource_requests(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot enforce Task resources: cpus"):
        make_environment(tmp_path, config=EnvironmentConfig(workdir="/app", cpus=2))


def test_rejects_network_policy_it_cannot_enforce(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="network_mode='no-network'"):
        environment_dir = tmp_path / "task" / "environment"
        environment_dir.mkdir(parents=True)
        paths = TrialPaths(tmp_path / "trial")
        paths.mkdir()
        HostEnvironment(
            environment_dir=environment_dir,
            environment_name="test",
            session_id="test-env",
            trial_paths=paths,
            task_env_config=EnvironmentConfig(workdir="/app"),
            logger=logging.getLogger("test"),
            network_policy=NetworkPolicy(network_mode=NetworkMode.NO_NETWORK),
            allow_host_execution=True,
        )


def test_rejects_force_build(tmp_path: Path) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path)
        with pytest.raises(ValueError, match="does not build Docker images"):
            await environment.start(force_build=True)

    asyncio.run(scenario())


@_LINUX_ONLY
def test_exec_translates_paths_and_sets_portable_environment(tmp_path: Path) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            source = tmp_path / "source.txt"
            source.write_text("fixture", encoding="utf-8")
            await environment.upload_file(source, "/tests/source.txt")
            result = await environment.exec(
                "printf '%s|%s|' \"$PSYCHEVAL_WORKDIR\" "
                '"$PSYCHEVAL_TESTS_DIR"; cat /tests/source.txt',
                env={"CALL_ENV": "present"},
            )
            assert result.return_code == 0
            workdir, tests_dir, payload = (result.stdout or "").split("|", 2)
            assert workdir.startswith("/tmp/psycheval-harbor-")
            assert tests_dir.startswith("/tmp/psycheval-harbor-")
            assert payload == "fixture"
            url_result = await environment.exec("printf '%s' 'https://example.com/app'")
            assert url_result.stdout == "https://example.com/app"
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@_LINUX_ONLY
def test_linux_command_translation_preserves_composed_home_paths(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            result = await environment.exec("printf '%s|%s' ~/app ${HOME}/app")
            expected = str(Path(os.environ["HOME"]) / "app")
            assert result.return_code == 0
            assert result.stdout == f"{expected}|{expected}"
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@_LINUX_ONLY
def test_linux_paths_preserve_native_relative_c_and_backslash_names(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            sources = []
            for index, payload in enumerate(
                (
                    "virtual",
                    "relative-c",
                    "slash",
                    "backslash",
                    "virtual-leading",
                    "backslash-leading",
                )
            ):
                source = tmp_path / f"source-{index}.txt"
                source.write_text(payload, encoding="utf-8")
                sources.append(source)
            await environment.upload_file(sources[0], "/app/collision.txt")
            await environment.upload_file(sources[1], "C:/app/collision.txt")
            await environment.upload_file(sources[2], "folder/item.txt")
            await environment.upload_file(sources[3], r"folder\item.txt")
            await environment.upload_file(sources[4], "/app/leading.txt")
            await environment.upload_file(sources[5], r"\app\leading.txt")

            result = await environment.exec(
                "cat /app/collision.txt; printf '|'; "
                "cat 'C:/app/collision.txt'; printf '|'; "
                "cat folder/item.txt; printf '|'; "
                "cat 'folder\\item.txt'; printf '|'; "
                "cat /app/leading.txt; printf '|'; cat '\\app\\leading.txt'"
            )
            assert result.return_code == 0
            assert result.stdout == (
                "virtual|relative-c|slash|backslash|virtual-leading|backslash-leading"
            )
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@_LINUX_ONLY
def test_host_subprocess_uses_the_isolated_test_environment(tmp_path: Path) -> None:
    assert os.environ["HARBOR_TELEMETRY"] == "0"
    assert Path(os.environ["HOME"]).is_relative_to(tmp_path)
    assert Path(os.environ["XDG_CONFIG_HOME"]).is_relative_to(tmp_path)
    assert "OPENAI_API_KEY" not in os.environ
    assert "PEVAL_FIXTURE_API_TOKEN" not in os.environ

    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            result = await environment.exec(
                "printf '%s|%s|%s|%s' \"$HARBOR_TELEMETRY\" "
                '"$XDG_CONFIG_HOME" "${OPENAI_API_KEY-unset}" '
                '"${PEVAL_FIXTURE_API_TOKEN-unset}"'
            )
            telemetry, config_home, api_key, api_token = (result.stdout or "").split(
                "|", 3
            )
            assert telemetry == "0"
            assert Path(config_home).is_relative_to(tmp_path)
            assert api_key == "unset"
            assert api_token == "unset"
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@_LINUX_ONLY
def test_exec_preserves_shell_paths_when_trial_path_contains_spaces(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path / "jobs with spaces")
        await environment.start(force_build=False)
        try:
            instruction = environment.trial_paths.agent_dir / "instruction.txt"
            instruction.write_text("exact payload", encoding="utf-8")
            result = await environment.exec(
                "read -r value < '/logs/agent/instruction.txt'; "
                'printf %s "$value" > /logs/verifier/result.txt'
            )
            assert result.return_code == 0
            assert result.stderr == ""
            assert (environment.trial_paths.verifier_dir / "result.txt").read_text(
                encoding="utf-8"
            ) == "exact payload"
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def test_rejects_duplicate_managed_mount_target(tmp_path: Path) -> None:
    substituted = tmp_path / "substituted-agent-logs"
    substituted.mkdir()
    with pytest.raises(ValueError, match="duplicate mount target"):
        make_environment(
            tmp_path,
            extra_mounts=[
                {
                    "type": "bind",
                    "source": str(substituted),
                    "target": "/logs/agent",
                }
            ],
        )


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ({"source": "wrong"}, "source"),
        ({"type": "volume"}, "type"),
        ({"read_only": True}, "writable"),
    ],
)
def test_rejects_mounts_that_do_not_match_harbor_trial_ownership(
    tmp_path: Path, replacement: dict, message: str
) -> None:
    environment_dir = tmp_path / "task" / "environment"
    environment_dir.mkdir(parents=True)
    trial_paths = TrialPaths(tmp_path / "trial")
    trial_paths.mkdir()
    mount = {
        "type": "bind",
        "source": str(trial_paths.agent_dir),
        "target": "/logs/agent",
    }
    mount.update(replacement)
    with pytest.raises(ValueError, match=message):
        HostEnvironment(
            environment_dir=environment_dir,
            environment_name="test",
            session_id="test-env",
            trial_paths=trial_paths,
            task_env_config=EnvironmentConfig(workdir="/app"),
            logger=logging.getLogger("test"),
            mounts=[mount],
            allow_host_execution=True,
        )


@_LINUX_ONLY
def test_timeout_terminates_the_process_group(tmp_path: Path) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        marker = tmp_path / "late-marker"
        try:
            with pytest.raises(asyncio.TimeoutError):
                await environment.exec(
                    f"(sleep 0.4; touch {marker}) & wait", timeout_sec=0.05
                )
            await asyncio.sleep(0.5)
            assert not marker.exists()
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


@_LINUX_ONLY
def test_rejects_user_switching(tmp_path: Path) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            with pytest.raises(ValueError, match="cannot switch"):
                await environment.exec("true", user=os.getuid() + 10000)
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def test_windows_host_reports_native_os_and_capability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "psycheval.harbor.environment.platform.system", lambda: "Windows"
    )

    environment = make_environment(tmp_path)

    assert environment.os == TaskOS.WINDOWS
    assert environment.capabilities.windows is True
    assert environment.capabilities.mounted is True


def test_windows_exec_uses_cmd_and_translates_runtime_aliases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "psycheval.harbor.environment.platform.system", lambda: "Windows"
    )
    monkeypatch.setenv("COMSPEC", r"C:\Windows\System32\cmd.exe")
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    async def create_process(*args, **kwargs):
        calls.append((args, kwargs))
        return _CompletedProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create_process)

    async def scenario() -> None:
        environment = make_environment(tmp_path / "jobs with spaces")
        await environment.start(force_build=False)
        try:
            source = tmp_path / "source.txt"
            source.write_text("fixture", encoding="utf-8")
            await environment.upload_file(source, "C:/tests/source.txt")
            result = await environment.exec(
                "type C:/tests/source.txt > C:/logs/verifier/result.txt",
                cwd="C:/app",
            )
            assert result.return_code == 0
            assert calls
            args, kwargs = calls[0]
            assert args[:4] == (
                r"C:\Windows\System32\cmd.exe",
                "/D",
                "/S",
                "/C",
            )
            translated = str(args[4])
            assert "C:/tests" not in translated
            assert r"C:\tests" not in translated
            assert "C:/logs" not in translated
            assert r"C:\logs" not in translated
            assert "source.txt" in translated
            assert "result.txt" in translated
            assert '"' in translated
            assert Path(kwargs["cwd"]).name == "app"
            assert "creationflags" in kwargs
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def test_windows_exec_preserves_a_leading_quoted_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "psycheval.harbor.environment.platform.system", lambda: "Windows"
    )
    monkeypatch.setenv("COMSPEC", r"C:\Windows\System32\cmd.exe")
    calls: list[tuple[object, ...]] = []

    async def create_process(*args, **kwargs):
        del kwargs
        calls.append(args)
        return _CompletedProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create_process)

    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            result = await environment.exec(
                r'"C:\Program Files\Python312\python.exe" -m fixture'
            )
            assert result.return_code == 0
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())
    assert calls[0][:4] == (
        r"C:\Windows\System32\cmd.exe",
        "/D",
        "/S",
        "/C",
    )
    assert calls[0][4] == (r'""C:\Program Files\Python312\python.exe" -m fixture"')


def test_windows_rejects_every_explicit_user(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "psycheval.harbor.environment.platform.system", lambda: "Windows"
    )

    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            with pytest.raises(ValueError, match="does not support user switching"):
                await environment.exec("ver", user="root")
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


def test_windows_timeout_terminates_the_process_tree_with_taskkill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "psycheval.harbor.environment.platform.system", lambda: "Windows"
    )
    target = _HangingProcess()
    invocations: list[tuple[object, ...]] = []

    async def create_process(*args, **kwargs):
        del kwargs
        invocations.append(args)
        if len(invocations) == 1:
            return target
        return _TaskkillProcess(target)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create_process)

    async def scenario() -> None:
        environment = make_environment(tmp_path)
        await environment.start(force_build=False)
        try:
            with pytest.raises(asyncio.TimeoutError):
                await environment.exec("ping -t localhost", timeout_sec=0.001)
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())
    assert len(invocations) == 2
    assert invocations[1] == (
        "taskkill",
        "/PID",
        str(target.pid),
        "/T",
        "/F",
    )


def test_unsupported_native_host_fails_at_construction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "psycheval.harbor.environment.platform.system", lambda: "Darwin"
    )

    with pytest.raises(RuntimeError, match="Linux and Windows hosts"):
        make_environment(tmp_path)


@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="native Windows process-tree acceptance runs only on Windows",
)
@pytest.mark.parametrize("termination", ["timeout", "cancel"])
def test_native_windows_termination_removes_child_process_tree(
    tmp_path: Path, termination: str
) -> None:
    async def scenario() -> None:
        environment = make_environment(tmp_path / "native jobs with spaces")
        await environment.start(force_build=False)
        marker = tmp_path / f"late-{termination}.txt"
        source = tmp_path / "spawn-child.py"
        source.write_text(
            "import subprocess, sys, time\n"
            "subprocess.Popen([sys.executable, '-c', "
            f"\"import pathlib, time; time.sleep(1); pathlib.Path({str(marker)!r}).write_text('late')\"])\n"
            "time.sleep(30)\n",
            encoding="utf-8",
        )
        await environment.upload_file(source, "C:/app/spawn-child.py")
        command = f"{quote_windows_shell_arg(sys.executable)} C:/app/spawn-child.py"
        try:
            if termination == "timeout":
                with pytest.raises(asyncio.TimeoutError):
                    await environment.exec(command, timeout_sec=0.3)
            else:
                task = asyncio.create_task(environment.exec(command))
                await asyncio.sleep(0.3)
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            await asyncio.sleep(1.2)
            assert not marker.exists()
        finally:
            await environment.stop(delete=True)

    asyncio.run(scenario())


class _EmptyStream:
    async def read(self, _size: int) -> bytes:
        return b""


class _CompletedProcess:
    def __init__(self) -> None:
        self.pid = 1001
        self.returncode: int | None = None
        self.stdout = _EmptyStream()
        self.stderr = _EmptyStream()

    async def wait(self) -> int:
        self.returncode = 0
        return 0


class _HangingProcess(_CompletedProcess):
    def __init__(self) -> None:
        super().__init__()
        self.pid = 4242

    async def wait(self) -> int:
        while self.returncode is None:
            await asyncio.sleep(3600)
        return self.returncode


class _TaskkillProcess(_CompletedProcess):
    def __init__(self, target: _HangingProcess) -> None:
        super().__init__()
        self._target = target

    async def wait(self) -> int:
        self._target.returncode = 1
        return await super().wait()

    async def communicate(self) -> tuple[bytes, bytes]:
        await self.wait()
        return b"", b""
