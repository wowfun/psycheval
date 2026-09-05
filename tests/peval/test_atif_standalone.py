from __future__ import annotations

import ast
import shutil
import subprocess
import sys
from pathlib import Path


def test_atif_imports_only_the_standard_library_including_type_only_imports() -> None:
    source = Path(__file__).resolve().parents[2] / "src/psycheval/atif.py"
    for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            assert all(
                alias.name.split(".")[0] in sys.stdlib_module_names
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            assert (
                node.level == 0
                and (node.module or "").split(".")[0] in sys.stdlib_module_names
            )


def test_renamed_atif_file_works_without_site_packages(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "src/psycheval/atif.py"
    copied = tmp_path / "trajectory_contract.py"
    shutil.copyfile(source, copied)
    code = r"""
import copy
import importlib.util
import json
import sys

spec = importlib.util.spec_from_file_location("trajectory_contract", sys.argv[1])
atif = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atif)
trajectory = {
    "schema_version": "ATIF-v1.7",
    "agent": {"name": "downstream", "version": "1"},
    "steps": [{"step_id": 1, "source": "user", "message": "hello"}],
}
original = copy.deepcopy(trajectory)
atif.validate_atif_trajectory(trajectory)
assert trajectory == original
assert atif.is_atif_trajectory(trajectory)
assert atif.is_atif_content([{"type": "text", "text": "hello"}])
assert not atif.is_atif_content(["plain list"])
assert atif.iso_timestamp_ms("1970-01-01T01:00:01+01:00") == 1000
assert atif.iso_timestamp_ms("1970-01-01T00:00:01") == 1000
assert atif.iso_timestamp_ms("invalid") is None
with open(sys.argv[2], "w", encoding="utf-8") as stream:
    json.dump(trajectory, stream)
assert atif.read_atif_json_path(sys.argv[2]) == trajectory
assert atif.is_atif_json_path(sys.argv[2])
invalid = copy.deepcopy(trajectory)
invalid["steps"][0]["foreign_field"] = 1
bad_reference = copy.deepcopy(trajectory)
bad_reference["steps"][0] = {
    "step_id": 1, "source": "agent", "message": "",
    "observation": {"results": [{"source_call_id": "missing", "content": "done"}]},
}
for value, message in [(invalid, "foreign_field"), (bad_reference, "source_call_id")]:
    before = copy.deepcopy(value)
    try:
        atif.validate_atif_trajectory(value)
    except ValueError as exc:
        assert "trajectory.steps[0]" in str(exc) and message in str(exc), str(exc)
    else:
        raise AssertionError("invalid evidence was accepted")
    assert value == before
assert not any(name.split(".")[0] in {"psycheval", "harbor", "pydantic"} for name in sys.modules)
assert sys.flags.no_site and sys.flags.isolated
"""
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-c",
            code,
            str(copied),
            str(tmp_path / "atif.json"),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert copied.read_bytes() == source.read_bytes()
