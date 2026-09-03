from __future__ import annotations

import io
import json
import os
import tarfile
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import yaml

from psycheval.cli import main
from psycheval.harbor.workbuddy import (
    LLM_OPTIONAL_ENV,
    LLM_REQUIRED_ENV,
    PLAN_FILE_LIMIT,
    discover_workbuddy_summaries,
)

SPECIAL_TASK = "recruiting-search-skill-mock-mcp-hardened"


def _write_office_bundle(root: Path) -> tuple[str, ...]:
    names = tuple([f"office-{index:02d}" for index in range(49)] + [SPECIAL_TASK])
    (root / "shared" / "verifier").mkdir(parents=True)
    for name in ("plugin.py", "manifest.py", "scoring.py"):
        (root / "shared" / "verifier" / name).write_text("# fixture\n")
    (root / "dataset.toml").write_text(
        """[dataset]
id = "wb-bench-office-v1.0"
schema = "workbuddy.dataset.v1"
version = "1.0"
task_count = 50

[verifier]
schema = "workbuddy.verifier.v1"
engine = "composite"

[layout]
task_root = "tasks"
environment = "environment"
workspace_archive = "environment/workspace.tar.gz"
tests = "tests"
grading_tests = "tests/grading"
gold = "tests/gold"
judge_config = "tests/judge.yaml"
""",
        encoding="utf-8",
    )
    for name in names:
        task = root / "tasks" / name
        (task / "environment").mkdir(parents=True)
        (task / "tests").mkdir()
        (task / "tests" / "test.sh").write_text("#!/bin/sh\nexit 0\n")
        (task / "instruction.md").write_text(f"Complete {name}.\n")
        (task / "task.toml").write_text(
            f'schema_version = "1.3"\n[task]\nname = "workbuddy/{name}"\n',
            encoding="utf-8",
        )
        archive = task / "environment" / "workspace.tar.gz"
        if name == SPECIAL_TASK:
            payload = b"---\nname: recruiting_search\n---\nUse the MCP.\n"
            info = tarfile.TarInfo("agent_pack/skills/recruiting_search/SKILL.md")
            info.size = len(payload)
            with tarfile.open(archive, "w:gz") as stream:
                stream.addfile(info, io.BytesIO(payload))
        else:
            archive.write_bytes(b"fixture")
    return names


def _write_workspace(root: Path, bundle: Path) -> Path:
    (root / "peval.toml").write_text(
        "[[harbor.datasets]]\n"
        'id = "office"\n'
        f"path = {json.dumps(str(bundle))}\n"
        'format = "workbuddy.v1"\n',
        encoding="utf-8",
    )
    base = root / "base.yaml"
    base.write_text(
        "job_name: ignored\n"
        "n_concurrent_trials: 1\n"
        "agents:\n"
        "  - name: opencode\n"
        "    model_name: xiaomi-token-plan-cn/mimo-v2.5-pro\n",
        encoding="utf-8",
    )
    return base


def _replace_special_skill_archive(bundle: Path, payloads: tuple[bytes, ...]) -> None:
    archive = bundle / "tasks" / SPECIAL_TASK / "environment" / "workspace.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        for payload in payloads:
            info = tarfile.TarInfo("agent_pack/skills/recruiting_search/SKILL.md")
            info.mode = 0o644
            info.size = len(payload)
            stream.addfile(info, io.BytesIO(payload))


class WorkBuddyCliTests(unittest.TestCase):
    def test_prepare_writes_two_harbor_configs_and_registers_isolated_jobs(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "bundle"
            names = _write_office_bundle(bundle)
            base = _write_workspace(root, bundle)
            stdout = io.StringIO()
            with (
                patch(
                    "psycheval.harbor.workbuddy.validate_workbuddy_runtime",
                    return_value={"version": "0.1.0", "commit": "fixture"},
                ),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "harbor",
                        "prepare",
                        "--root",
                        str(root),
                        "--dataset",
                        "office",
                        "--config",
                        str(base),
                    ]
                )

            self.assertEqual(exit_code, 0, stdout.getvalue())
            plans = list((root / "harbor-plans").glob("*/workbuddy-run-plan.json"))
            self.assertEqual(len(plans), 1)
            plan = json.loads(plans[0].read_text())
            self.assertEqual(plan["schema"], "psycheval.workbuddy-run-plan.v1")
            self.assertEqual(plan["expected_tasks"], list(names))
            self.assertEqual(len(plan["jobs"]), 2)
            self.assertTrue(any("case.yaml" in item for item in plan["warnings"]))
            configs = [
                yaml.safe_load(Path(item["config"]).read_text())
                for item in plan["jobs"]
            ]
            normal, special = configs
            self.assertEqual(len(normal["tasks"]), 49)
            self.assertEqual(len(special["tasks"]), 1)
            self.assertEqual(normal["n_attempts"], 3)
            self.assertEqual(normal["timeout_multiplier"], 2.0)
            self.assertEqual(
                normal["verifier"]["import_path"],
                "workbuddy_bench.judge:CompositeVerifier",
            )
            self.assertEqual(normal["jobs_dir"], special["jobs_dir"])
            self.assertNotIn("__", normal["job_name"])
            self.assertNotIn("__", special["job_name"])
            self.assertEqual(special["agents"][0]["skills"], [plan["skill_dir"]])
            self.assertEqual(
                special["agents"][0]["mcp_servers"][0]["transport"], "stdio"
            )
            self.assertIn("harbor run -c", stdout.getvalue())
            self.assertIn("peval harbor summarize", stdout.getvalue())
            configured = (root / "peval.toml").read_text()
            self.assertIn("[[harbor.mounts]]", configured)
            self.assertIn('dataset_ids = ["office"]', configured)

    def test_prepare_retries_an_existing_plan_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "bundle"
            _write_office_bundle(bundle)
            base = _write_workspace(root, bundle)
            existing_id = "workbuddy-office-existing"
            fresh_id = "workbuddy-office-fresh"
            existing = root / "harbor-plans" / existing_id
            existing.mkdir(parents=True)
            (existing / "keep.txt").write_text("keep\n", encoding="utf-8")
            stdout = io.StringIO()

            with (
                patch(
                    "psycheval.harbor.workbuddy.validate_workbuddy_runtime",
                    return_value={"version": "0.1.0", "commit": "fixture"},
                ),
                patch(
                    "psycheval.harbor.workbuddy._new_plan_id",
                    side_effect=(existing_id, fresh_id),
                ),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "harbor",
                        "prepare",
                        "--root",
                        str(root),
                        "--dataset",
                        "office",
                        "--config",
                        str(base),
                    ]
                )

            self.assertEqual(exit_code, 0, stdout.getvalue())
            self.assertEqual((existing / "keep.txt").read_text(), "keep\n")
            plan = json.loads(
                (
                    root / "harbor-plans" / fresh_id / "workbuddy-run-plan.json"
                ).read_text()
            )
            self.assertEqual(plan["plan_id"], fresh_id)

    def test_prepare_reports_exhausted_plan_identity_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "bundle"
            _write_office_bundle(bundle)
            base = _write_workspace(root, bundle)
            existing_id = "workbuddy-office-existing"
            (root / "harbor-plans" / existing_id).mkdir(parents=True)
            stderr = io.StringIO()

            with (
                patch(
                    "psycheval.harbor.workbuddy.validate_workbuddy_runtime",
                    return_value={"version": "0.1.0", "commit": "fixture"},
                ),
                patch(
                    "psycheval.harbor.workbuddy._new_plan_id",
                    return_value=existing_id,
                ),
                redirect_stderr(stderr),
            ):
                exit_code = main(
                    [
                        "harbor",
                        "prepare",
                        "--root",
                        str(root),
                        "--dataset",
                        "office",
                        "--config",
                        str(base),
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn(
                "cannot allocate a unique WorkBuddy run plan id", stderr.getvalue()
            )
            self.assertNotIn("Errno", stderr.getvalue())

    @unittest.skipUnless(
        getattr(os, "O_NONBLOCK", 0), "non-blocking opens are unavailable"
    )
    def test_prepare_opens_plan_inputs_nonblocking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "bundle"
            _write_office_bundle(bundle)
            base = _write_workspace(root, bundle)
            archive = (
                bundle / "tasks" / SPECIAL_TASK / "environment" / "workspace.tar.gz"
            )
            real_open = os.open
            opened_flags: dict[Path, list[int]] = {base: [], archive: []}

            def recording_open(
                path: str | bytes | os.PathLike[str],
                flags: int,
                *args: object,
                **kwargs: object,
            ) -> int:
                candidate = Path(path)
                if candidate in opened_flags:
                    opened_flags[candidate].append(flags)
                return real_open(path, flags, *args, **kwargs)

            with (
                patch(
                    "psycheval.harbor.workbuddy.validate_workbuddy_runtime",
                    return_value={"version": "0.1.0", "commit": "fixture"},
                ),
                patch("psycheval.harbor.workbuddy.os.open", recording_open),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(
                    [
                        "harbor",
                        "prepare",
                        "--root",
                        str(root),
                        "--dataset",
                        "office",
                        "--config",
                        str(base),
                    ]
                )

            self.assertEqual(exit_code, 0)
            for path, flags in opened_flags.items():
                self.assertTrue(flags, path)
                self.assertTrue(all(value & os.O_NONBLOCK for value in flags), path)

    def test_prepare_preserves_secret_references_and_rejects_partial_llm_env(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "bundle"
            _write_office_bundle(bundle)
            base = _write_workspace(root, bundle)
            with (
                patch(
                    "psycheval.harbor.workbuddy.validate_workbuddy_runtime",
                    return_value={"version": "0.1.0"},
                ),
                patch.dict(
                    "os.environ",
                    {"WORKBUDDY_VERIFIER_LLM_API_KEY": "top-secret"},
                    clear=False,
                ),
            ):
                stderr = io.StringIO()
                with redirect_stderr(stderr):
                    exit_code = main(
                        [
                            "harbor",
                            "prepare",
                            "-r",
                            str(root),
                            "--dataset",
                            "office",
                            "--config",
                            str(base),
                        ]
                    )
            self.assertEqual(exit_code, 1)
            self.assertIn("all be set", stderr.getvalue())
            self.assertNotIn("top-secret", stderr.getvalue())

    def test_prepare_rejects_base_task_ownership_and_multiple_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "bundle"
            _write_office_bundle(bundle)
            base = _write_workspace(root, bundle)
            base.write_text(
                "job_name: bad\n"
                "tasks: [{path: /tmp/already-owned}]\n"
                "agents: [{name: opencode}, {name: opencode}]\n"
            )
            with patch(
                "psycheval.harbor.workbuddy.validate_workbuddy_runtime",
                return_value={"version": "0.1.0"},
            ):
                stderr = io.StringIO()
                with redirect_stderr(stderr):
                    exit_code = main(
                        [
                            "harbor",
                            "prepare",
                            "-r",
                            str(root),
                            "--dataset",
                            "office",
                            "--config",
                            str(base),
                        ]
                    )
            self.assertEqual(exit_code, 1)
            self.assertIn("must not select tasks", stderr.getvalue())

    def test_prepare_rejects_an_oversized_base_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "bundle"
            _write_office_bundle(bundle)
            base = _write_workspace(root, bundle)
            base.write_bytes(b"#" * (PLAN_FILE_LIMIT + 1))
            with patch(
                "psycheval.harbor.workbuddy.validate_workbuddy_runtime",
                return_value={"version": "0.1.0"},
            ):
                stderr = io.StringIO()
                with redirect_stderr(stderr):
                    exit_code = main(
                        [
                            "harbor",
                            "prepare",
                            "-r",
                            str(root),
                            "--dataset",
                            "office",
                            "--config",
                            str(base),
                        ]
                    )
            self.assertEqual(exit_code, 1)
            self.assertIn("bounded regular file", stderr.getvalue())

    def test_prepare_accepts_identical_skill_duplicates_but_rejects_conflicts(
        self,
    ) -> None:
        payload = b"---\nname: recruiting_search\n---\nUse the MCP.\n"
        for payloads, expected_code in (
            ((payload, payload), 0),
            ((payload, payload + b"conflict\n"), 1),
        ):
            with (
                self.subTest(expected_code=expected_code),
                tempfile.TemporaryDirectory() as tmp,
            ):
                root = Path(tmp)
                bundle = root / "bundle"
                _write_office_bundle(bundle)
                _replace_special_skill_archive(bundle, payloads)
                base = _write_workspace(root, bundle)
                stdout = io.StringIO()
                stderr = io.StringIO()
                with (
                    patch(
                        "psycheval.harbor.workbuddy.validate_workbuddy_runtime",
                        return_value={"version": "0.1.0"},
                    ),
                    redirect_stdout(stdout),
                    redirect_stderr(stderr),
                ):
                    exit_code = main(
                        [
                            "harbor",
                            "prepare",
                            "-r",
                            str(root),
                            "--dataset",
                            "office",
                            "--config",
                            str(base),
                        ]
                    )
                self.assertEqual(exit_code, expected_code, stderr.getvalue())
                if expected_code:
                    self.assertIn("conflicting duplicate", stderr.getvalue())

    def test_prepare_rejects_backslash_in_special_skill_archive_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "bundle"
            _write_office_bundle(bundle)
            archive = (
                bundle / "tasks" / SPECIAL_TASK / "environment" / "workspace.tar.gz"
            )
            with tarfile.open(archive, "w:gz") as stream:
                safe = b"---\nname: recruiting_search\n---\n"
                for name, content in (
                    ("agent_pack/skills/recruiting_search/SKILL.md", safe),
                    ("agent_pack/skills/recruiting_search/..\\escape", b"bad"),
                ):
                    info = tarfile.TarInfo(name)
                    info.size = len(content)
                    stream.addfile(info, io.BytesIO(content))
            base = _write_workspace(root, bundle)
            stderr = io.StringIO()
            with (
                patch(
                    "psycheval.harbor.workbuddy.validate_workbuddy_runtime",
                    return_value={"version": "0.1.0"},
                ),
                redirect_stderr(stderr),
            ):
                exit_code = main(
                    [
                        "harbor",
                        "prepare",
                        "-r",
                        str(root),
                        "--dataset",
                        "office",
                        "--config",
                        str(base),
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("archive path is unsafe", stderr.getvalue())

    def test_prepare_rejects_literal_workbuddy_verifier_secret(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "bundle"
            _write_office_bundle(bundle)
            base = _write_workspace(root, bundle)
            base.write_text(
                base.read_text()
                + "verifier:\n"
                + "  env:\n"
                + "    WORKBUDDY_VERIFIER_LLM_API_KEY: literal-sensitive-value\n"
            )
            stderr = io.StringIO()
            with (
                patch(
                    "psycheval.harbor.workbuddy.validate_workbuddy_runtime",
                    return_value={"version": "0.1.0"},
                ),
                patch.dict(
                    "os.environ",
                    {name: "" for name in (*LLM_REQUIRED_ENV, LLM_OPTIONAL_ENV)},
                    clear=False,
                ),
                redirect_stderr(stderr),
            ):
                exit_code = main(
                    [
                        "harbor",
                        "prepare",
                        "-r",
                        str(root),
                        "--dataset",
                        "office",
                        "--config",
                        str(base),
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("environment reference", stderr.getvalue())
            self.assertNotIn("literal-sensitive-value", stderr.getvalue())

    def test_prepare_adapts_explicit_host_environment_for_workbuddy_bootstrap(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "bundle"
            _write_office_bundle(bundle)
            base = _write_workspace(root, bundle)
            base.write_text(
                "job_name: host\n"
                "agents:\n"
                "  - name: opencode\n"
                "    model_name: xiaomi-token-plan-cn/mimo-v2.5-pro\n"
                "environment:\n"
                "  import_path: psycheval.harbor.environment:HostEnvironment\n"
                "  kwargs:\n"
                "    allow_host_execution: true\n"
            )
            with (
                patch(
                    "psycheval.harbor.workbuddy.validate_workbuddy_runtime",
                    return_value={"version": "0.1.0"},
                ),
                patch(
                    "psycheval.harbor.workbuddy.validate_workbuddy_host_dependencies"
                ) as host_preflight,
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(
                    main(
                        [
                            "harbor",
                            "prepare",
                            "-r",
                            str(root),
                            "--dataset",
                            "office",
                            "--config",
                            str(base),
                        ]
                    ),
                    0,
                )
            host_preflight.assert_called_once_with()
            plan_path = next((root / "harbor-plans").glob("*/workbuddy-run-plan.json"))
            plan = json.loads(plan_path.read_text())
            normal, special = [
                yaml.safe_load(Path(item["config"]).read_text())
                for item in plan["jobs"]
            ]
            environment = normal["environment"]
            self.assertFalse(environment["force_build"])
            self.assertEqual(environment["override_cpus"], 0)
            self.assertEqual(environment["override_memory_mb"], 0)
            self.assertEqual(environment["override_storage_mb"], 0)
            self.assertTrue(environment["kwargs"]["bootstrap_workbuddy_workspace"])
            self.assertTrue(plan["host_environment"])
            mcp = special["agents"][0]["mcp_servers"][0]
            self.assertEqual(
                mcp["args"][0],
                "environment/mock_mcp/recruiting_search_lab_server.py",
            )
            self.assertEqual(
                special["agents"][0]["env"]["RECRUITING_SEARCH_LAB_EXPORT_DIR"],
                "input/workspace/exports",
            )

    def test_prepare_rejects_integer_host_execution_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "bundle"
            _write_office_bundle(bundle)
            base = _write_workspace(root, bundle)
            base.write_text(
                "job_name: host\n"
                "agents:\n"
                "  - name: opencode\n"
                "environment:\n"
                "  import_path: psycheval.harbor.environment:HostEnvironment\n"
                "  kwargs:\n"
                "    allow_host_execution: 1\n"
            )
            stderr = io.StringIO()
            with (
                patch(
                    "psycheval.harbor.workbuddy.validate_workbuddy_runtime",
                    return_value={"version": "0.1.0"},
                ),
                redirect_stderr(stderr),
            ):
                exit_code = main(
                    [
                        "harbor",
                        "prepare",
                        "-r",
                        str(root),
                        "--dataset",
                        "office",
                        "--config",
                        str(base),
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("allow_host_execution=true", stderr.getvalue())

    def test_summarize_requires_terminal_jobs_then_delegates_official_metrics(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_id = "office-plan"
            plan_dir = root / "harbor-plans" / plan_id
            jobs_root = root / "harbor-jobs" / plan_id
            plan_dir.mkdir(parents=True)
            jobs_root.mkdir(parents=True)
            (root / "peval.toml").write_text("")
            plan = {
                "schema": "psycheval.workbuddy-run-plan.v1",
                "plan_id": plan_id,
                "dataset_id": "office",
                "runtime": {"version": "0.1.0"},
                "jobs_root": str(jobs_root),
                "expected_tasks": ["one", SPECIAL_TASK],
                "jobs": [
                    {"name": "normal", "config": str(plan_dir / "normal.yaml")},
                    {"name": "special", "config": str(plan_dir / "special.yaml")},
                ],
                "warnings": ["known source defect"],
            }
            (plan_dir / "workbuddy-run-plan.json").write_text(json.dumps(plan))
            (jobs_root / "normal").mkdir()
            stderr = io.StringIO()
            with (
                patch(
                    "psycheval.harbor.workbuddy.validate_workbuddy_runtime",
                    return_value={"version": "0.1.0"},
                ),
                redirect_stderr(stderr),
            ):
                self.assertEqual(
                    main(["harbor", "summarize", "-r", str(root), "--plan", plan_id]),
                    1,
                )
            self.assertIn("not terminal", stderr.getvalue())

            for name in ("normal", "special"):
                job = jobs_root / name
                job.mkdir(exist_ok=True)
                (job / "result.json").write_text(
                    json.dumps({"finished_at": "2026-09-03T00:00:00Z"})
                )
            official = {
                "run_dir": "/private/jobs",
                "reward": 0.5,
                "pass_rate": 0.25,
                "n_tasks": 2,
                "n_trials": 6,
                "missing_tasks": [],
                "per_task": {"one": {"attempts": [{"trial": "private"}]}},
                "attempts_per_task": [3],
                "score_sources": {"reward": 6},
                "per_attempt": [
                    {"attempt": 1, "n_tasks": 2, "reward": 0.5, "pass_rate": 0.25}
                ],
            }
            stdout = io.StringIO()
            with (
                patch(
                    "psycheval.harbor.workbuddy.compute_official_metrics",
                    return_value=official,
                ) as compute,
                patch(
                    "psycheval.harbor.workbuddy.validate_workbuddy_runtime",
                    return_value={"version": "0.1.0"},
                ) as validate_runtime,
                redirect_stdout(stdout),
            ):
                self.assertEqual(
                    main(["harbor", "summarize", "-r", str(root), "--plan", plan_id]),
                    0,
                )
            compute.assert_called_once_with(jobs_root, ["one", SPECIAL_TASK])
            validate_runtime.assert_called_once_with()
            snapshot = json.loads((plan_dir / "workbuddy-summary.json").read_text())
            self.assertEqual(snapshot["metrics"], official)
            self.assertIn("WorkBuddy Benchmark Summary", stdout.getvalue())
            self.assertIn("known source defect", stdout.getvalue())
            summaries = discover_workbuddy_summaries(root, {"office"})
            self.assertEqual(
                summaries,
                [
                    {
                        "plan_id": plan_id,
                        "dataset_id": "office",
                        "generated_at": snapshot["generated_at"],
                        "provisional": False,
                        "pending_jobs": [],
                        "metrics": {
                            "reward": 0.5,
                            "pass_rate": 0.25,
                            "n_tasks": 2,
                            "n_trials": 6,
                            "missing_task_count": 0,
                            "attempts_per_task": [3],
                            "score_sources": {"reward": 6},
                            "per_attempt": [
                                {
                                    "attempt": 1,
                                    "n_tasks": 2,
                                    "reward": 0.5,
                                    "pass_rate": 0.25,
                                }
                            ],
                        },
                        "warnings": ["known source defect"],
                    }
                ],
            )
            self.assertNotIn("/private/jobs", json.dumps(summaries))
            self.assertNotIn("private", json.dumps(summaries))

    @unittest.skipUnless(hasattr(Path, "symlink_to"), "symlinks are unavailable")
    def test_summarize_rejects_a_jobs_root_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_id = "office-plan"
            plan_dir = root / "harbor-plans" / plan_id
            outside = root / "outside"
            plan_dir.mkdir(parents=True)
            outside.mkdir()
            (root / "harbor-jobs").mkdir()
            linked_jobs = root / "harbor-jobs" / plan_id
            linked_jobs.symlink_to(outside, target_is_directory=True)
            (root / "peval.toml").write_text("")
            plan = {
                "schema": "psycheval.workbuddy-run-plan.v1",
                "plan_id": plan_id,
                "dataset_id": "office",
                "jobs_root": str(linked_jobs),
                "expected_tasks": ["one", SPECIAL_TASK],
                "jobs": [
                    {"name": "normal", "config": str(plan_dir / "normal.yaml")},
                    {"name": "special", "config": str(plan_dir / "special.yaml")},
                ],
            }
            (plan_dir / "workbuddy-run-plan.json").write_text(json.dumps(plan))

            stderr = io.StringIO()
            with redirect_stderr(stderr):
                exit_code = main(
                    ["harbor", "summarize", "-r", str(root), "--plan", plan_id]
                )
            self.assertEqual(exit_code, 1)
            self.assertIn("symbolic link", stderr.getvalue())

    def test_summarize_rejects_a_traversing_job_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_id = "office-plan"
            plan_dir = root / "harbor-plans" / plan_id
            jobs_root = root / "harbor-jobs" / plan_id
            plan_dir.mkdir(parents=True)
            jobs_root.mkdir(parents=True)
            (root / "peval.toml").write_text("")
            plan = {
                "schema": "psycheval.workbuddy-run-plan.v1",
                "plan_id": plan_id,
                "dataset_id": "office",
                "jobs_root": str(jobs_root),
                "expected_tasks": ["one", SPECIAL_TASK],
                "jobs": [
                    {"name": "../../outside", "config": "unused"},
                    {"name": "special", "config": "unused"},
                ],
            }
            (plan_dir / "workbuddy-run-plan.json").write_text(json.dumps(plan))

            stderr = io.StringIO()
            with redirect_stderr(stderr):
                exit_code = main(
                    ["harbor", "summarize", "-r", str(root), "--plan", plan_id]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("Job entry is invalid", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
