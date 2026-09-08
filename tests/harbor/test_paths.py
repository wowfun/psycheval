from __future__ import annotations

import re
from pathlib import Path

import pytest
from harbor.models.task.config import TaskOS

from psycheval.harbor.paths import HostPathMapper, trial_short_uuid


def test_posix_mapper_translates_virtual_relative_and_native_paths(
    tmp_path: Path,
) -> None:
    mapper = HostPathMapper(
        host_os=TaskOS.LINUX,
        mappings={
            "/app": tmp_path / "app",
            "/app/project": tmp_path / "project",
        },
        task_workdir="/app/project",
    )

    assert mapper.split("/app/project/input.txt") == (
        "/app/project",
        ("input.txt",),
    )
    assert mapper.translate("/app/project/input.txt") == (
        tmp_path / "project" / "input.txt"
    )
    assert mapper.translate("relative.txt") == tmp_path / "project" / "relative.txt"
    native = tmp_path / "native.txt"
    assert mapper.translate(native) == native
    assert mapper.translate_environment({"INPUT": "/app/project/input.txt"}) == {
        "INPUT": str(tmp_path / "project" / "input.txt")
    }


@pytest.mark.parametrize(
    "value",
    ["/app/../outside", "relative/../outside"],
)
def test_mapper_rejects_traversal(value: str, tmp_path: Path) -> None:
    mapper = HostPathMapper(
        host_os=TaskOS.LINUX,
        mappings={"/app": tmp_path / "app"},
        task_workdir="/app",
    )

    with pytest.raises(ValueError, match="unsupported HostEnvironment path"):
        mapper.translate(value)


def test_windows_mapper_accepts_drive_aliases_and_preserves_native_paths(
    tmp_path: Path,
) -> None:
    mapper = HostPathMapper(
        host_os=TaskOS.WINDOWS,
        mappings={"/app": tmp_path / "app"},
        task_workdir="/app",
    )

    assert mapper.split("C:\\APP\\input.txt") == ("/app", ("input.txt",))
    assert mapper.translate("c:/app/input.txt") == tmp_path / "app" / "input.txt"
    assert mapper.translate("D:/tools/python.exe") == Path("D:/tools/python.exe")
    assert mapper.translate_environment(
        {"PATH": "C:/app/bin;D:/tools", "INPUT": "C:/app/input.txt"}
    ) == {
        "PATH": f"{tmp_path / 'app' / 'bin'};D:/tools",
        "INPUT": str(tmp_path / "app" / "input.txt"),
    }

    with pytest.raises(ValueError, match="unsupported HostEnvironment path"):
        mapper.translate("C:/app/../outside")


def test_trial_short_uuid_reuses_valid_trial_suffix() -> None:
    assert trial_short_uuid("task__YfQLWrD") == "YfQLWrD"
    assert re.fullmatch(r"[2-9A-HJ-NP-Za-km-z]{7}", trial_short_uuid("task"))
