from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.native_office import write_native_office
from tests.fixtures.workbuddy import write_office_bundle

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/psycheval/harbor"
RUNNER = ROOT / "tests/fixtures/vendored_harbor.py"


@pytest.fixture
def copied_harbor(tmp_path: Path) -> Path:
    package = tmp_path / "downstream/_vendor/harbor_copy"
    package.parent.mkdir(parents=True)
    shutil.copytree(SOURCE, package, ignore=shutil.ignore_patterns("__pycache__"))
    for parent in (package.parent, package.parent.parent):
        (parent / "__init__.py").write_text("", encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize(
    "scenario", ["imports", "verifier", "psychevo", "workbuddy", "host"]
)
def test_copied_harbor_runs_without_the_original_package(
    copied_harbor: Path, scenario: str
) -> None:
    if scenario == "host" and sys.platform != "linux":
        pytest.skip("synthetic host command uses Linux shell quoting")
    if scenario == "workbuddy":
        write_office_bundle(copied_harbor / "bundle")
    completed = subprocess.run(
        [sys.executable, "-I", str(RUNNER), str(copied_harbor), scenario],
        cwd=copied_harbor,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    for source in SOURCE.rglob("*.py"):
        copied = (
            copied_harbor
            / "downstream/_vendor/harbor_copy"
            / source.relative_to(SOURCE)
        )
        assert copied.read_bytes() == source.read_bytes()


def test_harbor_internal_imports_are_relocatable_even_in_type_annotations() -> None:
    for path in SOURCE.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and not node.level:
                assert (node.module or "").split(".")[0] != "psycheval", path
            elif isinstance(node, ast.Import):
                assert all(
                    alias.name.split(".")[0] != "psycheval" for alias in node.names
                ), path


@pytest.mark.skipif(
    os.environ.get("PEVAL_WORKBUDDY_RUNTIME_TESTS") != "1",
    reason="opt-in pinned WorkBuddy runtime integration",
)
def test_copied_native_verifier_uses_the_real_runtime(copied_harbor):
    write_native_office(copied_harbor / "bundle", "def test_pass():\n    assert True\n")
    completed = subprocess.run(
        [sys.executable, "-I", str(RUNNER), str(copied_harbor), "native_office"],
        cwd=copied_harbor,
        text=True,
        capture_output=True,
        timeout=180 if sys.platform == "win32" else 60,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
