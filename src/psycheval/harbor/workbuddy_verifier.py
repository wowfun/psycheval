"""WorkBuddy plugin execution and native Python/pytest format adaptation.

Windows mechanics live in windows. Optional WorkBuddy imports occur only during
verification, preserving the relocatable module's import-time independence.
"""

from __future__ import annotations

import ast
import asyncio
import hashlib
import importlib.machinery
import json
import logging
import os
import re
import shlex
import shutil
import stat
import sys
import tempfile
import time
import tomllib
from collections.abc import Mapping
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path
from types import ModuleType
from typing import Any

from harbor.models.task.config import TaskOS
from harbor.models.task.paths import TaskPaths
from harbor.models.verifier.result import VerifierResult
from harbor.utils.env import (
    is_sensitive_env_key,
    resolve_env_vars,
    templatize_sensitive_env,
)
from harbor.verifier.base import BaseVerifier

from . import windows
from .datasets import (
    TASK_TEXT_LIMIT,
    _read_regular_bytes,
    _walk_regular_tree,
    read_workbuddy_manifest,
)

logger = logging.getLogger(__name__)

_PATH_LITERAL = re.compile(r"^/(workspace|tests|logs)(?:/|$)")
_PYTHONPATHS = {
    "PYTHONPATH=/workspace:${PYTHONPATH:-}": ("/workspace",),
    "PYTHONPATH=/workspace:/tests/grading:${PYTHONPATH:-}": (
        "/workspace",
        "/tests/grading",
    ),
}


class OfficeProfileError(ValueError):
    """The Dataset cannot be executed under the supported native profile."""


@dataclass(frozen=True)
class OfficeCommand:
    command: str
    pytest_target: str
    pythonpath: tuple[str, ...]
    env: dict[str, str]


@dataclass(frozen=True)
class OfficeRule:
    template: str
    score_python: str
    reward_python: str
    source_sha256: str
    prepare_command: str


@dataclass(frozen=True)
class NativeExecutionResult:
    command: str
    return_code: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    error: str | None = None
    duration_sec: float = 0.0


def _read_source(root: Path, path: Path) -> str:
    return _read_regular_bytes(root, path, max_bytes=TASK_TEXT_LIMIT).decode(
        "utf-8-sig"
    )


def _parse_python(source: str) -> ast.Module:
    try:
        tree = ast.parse(source)
        compile(tree, "<Office profile>", "exec")
    except SyntaxError as exc:
        raise OfficeProfileError(
            f"invalid Python in Office profile at line {exc.lineno}: {exc.msg}"
        ) from exc
    return tree


def _load_rule(root: Path) -> OfficeRule:
    source = _read_regular_bytes(
        root, root / "shared/verifier/rule.py", max_bytes=TASK_TEXT_LIMIT
    )
    tree = _parse_python(source.decode("utf-8-sig"))
    template = next(
        (
            node.value.strip()
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and "__PYTEST_COMMAND__" in node.value
            and "PY_SCORE" in node.value
        ),
        None,
    )
    if template is None:
        raise OfficeProfileError("Office rule execution template is unavailable")
    preparation = next(
        (
            value.value.strip()
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "prepare_command"
            for statement in node.body
            if isinstance(statement, ast.Return)
            for value in ast.walk(statement)
            if isinstance(value, ast.Constant) and isinstance(value.value, str)
        ),
        "",
    )
    if preparation.replace("--cached", "--staged").splitlines() != [
        "set -euo pipefail",
        "mkdir -p /logs/verifier",
        "cd /workspace",
        "git add -A 2>/dev/null || true",
        "git diff --staged > /logs/verifier/agent.patch 2>/dev/null || true",
        "git reset >/dev/null 2>&1 || true",
    ]:
        raise OfficeProfileError("unsupported native Python preparation command")

    # Reuse the source profile's Python score/reward code verbatim except for
    # file-access paths. Scoring conditions have no second implementation.
    def embedded(marker: str) -> str:
        match = re.search(
            rf"<<'{marker}'\r?\n(.*?)\r?\n{marker}(?:\r?\n|$)",
            template,
            re.DOTALL,
        )
        if match is None:
            raise OfficeProfileError(
                f"Office rule execution template is missing {marker}"
            )
        return match.group(1)

    return OfficeRule(
        template,
        embedded("PY_SCORE"),
        embedded("PY_REWARD"),
        hashlib.sha256(source).hexdigest(),
        preparation,
    )


def _load_command(task_dir: Path) -> OfficeCommand:
    value = tomllib.loads(_read_source(task_dir, task_dir / "tests/verifier.toml"))
    run = value.get("run", {})
    if (
        value.get("schema_version") != "workbuddy.office.verifier.v1"
        or not isinstance(run, dict)
        or run.get("cwd", "/workspace") != "/workspace"
    ):
        raise OfficeProfileError(
            f"unsupported Office verifier manifest: {task_dir.name}"
        )
    command = run.get("command")
    if not isinstance(command, str):
        raise OfficeProfileError("Office verifier run.command must be a string")
    tokens = shlex.split(command.replace("\\\n", " "))
    prefix = tokens[0] if tokens else ""
    target = tokens[4] if len(tokens) > 4 else ""
    expected = [
        prefix,
        "python",
        "-m",
        "pytest",
        target,
        "-p",
        "no:cacheprovider",
        "-v",
        "--tb=short",
        "--junitxml=/logs/verifier/results.xml",
        ">",
        "/logs/verifier/test_output.txt",
        "2>&1",
    ]
    if (
        prefix not in _PYTHONPATHS
        or target not in {"/tests/grading", "/tests/grading/test_verify.py"}
        or tokens != expected
    ):
        raise OfficeProfileError(f"unsupported Office pytest command: {task_dir.name}")
    env = value.get("env", {})
    if not isinstance(env, dict) or any(
        not isinstance(k, str) or not isinstance(v, str) for k, v in env.items()
    ):
        raise OfficeProfileError("Office verifier env must contain string values")
    return OfficeCommand(command.strip(), target, _PYTHONPATHS[prefix], env)


def _adapt_python(
    source: str, mappings: Mapping[str, Path]
) -> tuple[str, list[dict[str, Any]]]:
    tree = _parse_python(source)
    parents = {
        child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)
    }
    edits = []
    audit = []

    def skipped(node: ast.AST, reason: str) -> None:
        audit.append(
            {
                "line": node.lineno,
                "column": node.col_offset,
                "kind": "skipped",
                "reason": reason,
                "before": ast.get_source_segment(source, node) or ast.unparse(node),
            }
        )

    for node in ast.walk(tree):
        if (
            not isinstance(node, ast.Constant)
            or not isinstance(node.value, str)
            or not _PATH_LITERAL.match(node.value)
        ):
            continue
        parent = parents.get(node)
        if isinstance(parent, ast.JoinedStr):
            skipped(parent, "unrecognized interpolated path")
            continue
        ancestors = []
        cursor = parent
        while cursor is not None:
            ancestors.append(cursor)
            cursor = parents.get(cursor)
        # These strings describe the logical Task contract, not native I/O.
        if isinstance(parent, ast.Compare) or (
            isinstance(parent, ast.Call)
            and isinstance(parent.func, ast.Attribute)
            and parent.func.attr in {"startswith", "removeprefix"}
        ):
            continue
        calls = [item for item in ancestors if isinstance(item, ast.Call)]
        allowed = any(
            ast.unparse(call.func) in {"Path", "sys.path.insert", "os.environ.get"}
            for call in calls
        )
        direct_call = parents.get(parent) if isinstance(parent, ast.keyword) else parent
        if isinstance(direct_call, ast.Call):
            opener = ast.unparse(direct_call.func)
            if opener in {"open", "builtins.open", "io.open", "os.open"}:
                path_keyword = "path" if opener == "os.open" else "file"
                allowed |= bool(direct_call.args and direct_call.args[0] is node) or (
                    isinstance(parent, ast.keyword) and parent.arg == path_keyword
                )
        allowed |= (
            isinstance(parent, ast.keyword)
            and parent.arg == "default"
            and any(
                isinstance(call.func, ast.Attribute)
                and call.func.attr == "add_argument"
                for call in calls
            )
        )
        allowed |= isinstance(parent, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "DEFAULT_OUTPUT_PATH"
            for target in parent.targets
        )
        allowed |= any(
            isinstance(item, ast.FunctionDef) and item.name == "_default_output_path"
            for item in ancestors
        ) and isinstance(parent, (ast.Return, ast.BoolOp))
        if not allowed:
            skipped(node, "unrecognized path expression")
            continue
        try:
            mapped = windows.translate_literal(node.value, mappings)
        except ValueError as exc:
            raise OfficeProfileError(
                f"invalid Office path at line {node.lineno}: {node.value}"
            ) from exc
        if mapped is None:
            skipped(node, "no native path mapping")
            continue
        edits.append((node, repr(mapped)))
        audit.append(
            {
                "line": node.lineno,
                "column": node.col_offset,
                "kind": "file_path",
                "before": node.value,
                "after": mapped,
            }
        )
    # WindowsPath sorts without case sensitivity. Preserve the source POSIX
    # traversal order used by snapshot hashes, without changing any hash inputs.
    snapshot_roots = {
        "_compute_snapshot": "root",
        "_compute_workspace_snapshot": "workspace_root",
        "_protected_root_rollup": "base",
    }
    for function in tree.body:
        if not isinstance(function, ast.FunctionDef):
            continue
        root = snapshot_roots.get(function.name)
        if root is None:
            continue
        calls = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "sorted"
        ]
        expected = f"sorted((p for p in {root}.rglob('*') if p.is_file()))"
        if len(calls) != 1 or ast.unparse(calls[0]) != expected:
            skipped(function, "unrecognized snapshot traversal")
            continue
        node = calls[0]
        expression = (
            f"sorted((p for p in {root}.rglob('*') if p.is_file()), "
            "key=lambda p: p.parts)"
        )
        edits.append((node, expression))
        audit.append(
            {
                "line": node.lineno,
                "column": node.col_offset,
                "kind": "path_order",
                "before": expected,
                "after": expression,
            }
        )
    # The MCP probe validates the source config's literal "python3" contract.
    # Adapt only its launch expression, leaving that validation and config intact.
    for function in tree.body:
        if (
            not isinstance(function, ast.FunctionDef)
            or function.name != "load_mcp_process_config"
        ):
            continue
        returns = [n for n in ast.walk(function) if isinstance(n, ast.Return)]
        if len(returns) != 1:
            skipped(function, "unrecognized MCP probe launch")
            continue
        value = returns[0].value
        if (
            not isinstance(value, ast.Tuple)
            or not value.elts
            or not isinstance(value.elts[0], ast.List)
            or not value.elts[0].elts
            or ast.unparse(value.elts[0].elts[0]) != "command"
        ):
            skipped(returns[0], "unrecognized MCP probe launch")
            continue
        node = value.elts[0].elts[0]
        expression = f"({sys.executable!r} if command == 'python3' else command)"
        edits.append((node, expression))
        audit.append(
            {
                "line": node.lineno,
                "column": node.col_offset,
                "kind": "python_launch",
                "before": "command",
                "after": expression,
            }
        )
    try:
        return windows.rewrite_python(source, edits), audit
    except (ValueError, SyntaxError) as exc:
        raise OfficeProfileError(f"invalid Office Python adaptation: {exc}") from exc


class NativeOfficeExecutor:
    """Execute the known Office pipeline through HostEnvironment.exec_argv."""

    def __init__(
        self, environment: Any, task_dir: Path, rule: OfficeRule, command: OfficeCommand
    ):
        self.environment = environment
        self.task_dir = task_dir
        self.rule = rule
        self.command = command
        self.mappings = {
            "/workspace": environment.native_path("/workspace"),
            "/tests": task_dir / "tests",
            "/logs": environment.native_path("/logs"),
            "/logs/verifier": environment.native_path("/logs/verifier"),
        }
        self.logs = self.mappings["/logs/verifier"]
        self.logs.mkdir(parents=True, exist_ok=True)
        self.prepared = False
        self.preparation_error: Exception | None = None

    @property
    def capabilities(self):
        return self.environment.capabilities

    async def exec(self, command: str, *, env=None, cwd=None, **kwargs):
        """Adapt the profile's prepare hook through its runtime Environment handle."""
        try:
            if command.strip() != self.rule.prepare_command or cwd != "/workspace":
                raise OfficeProfileError(
                    "unsupported native Python preparation command"
                )
            await self.prepare(env or {})
            return NativeExecutionResult(command=command, return_code=0)
        except Exception as exc:
            # Upstream HarborCommandExecutor returns exceptions as CommandResult;
            # a prepare hook can ignore that result, so retain the failure here.
            self.preparation_error = exc
            raise

    def path(self, value: str) -> str:
        return windows.translate_literal(value, self.mappings) or value

    def env(
        self, values: Mapping[str, str] | None = None, *, grading: bool = False
    ) -> dict[str, str]:
        env = windows.translate_environment(
            values or {}, self.mappings, path_separator=os.pathsep
        )
        prefix = (
            ("/workspace", "/tests/grading") if grading else self.command.pythonpath
        )
        inherited = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join(
            [
                *(self.path(p) for p in prefix),
                *(p for p in inherited.split(os.pathsep) if p),
            ]
        )
        # Several Office graders derive this default from logical gold data.
        # Override the I/O location without rewriting the gold contract.
        if "WB_BENCH_OUTPUT_PATH" not in env:
            gold = self.task_dir / "tests/gold/gold_answer.json"
            if gold.is_file():
                value = json.loads(_read_source(self.task_dir, gold))
                output = (
                    value.get("output_contract", {}).get("path")
                    if isinstance(value, dict)
                    else None
                )
                if isinstance(output, str) and _PATH_LITERAL.match(output):
                    env["WB_BENCH_OUTPUT_PATH"] = self.path(output)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return env

    async def prepare(self, values: Mapping[str, str]) -> None:
        patch_path = self.logs / "agent.patch"
        patch_path.unlink(missing_ok=True)
        patch = ""
        workspace = self.mappings["/workspace"]
        for args in (["add", "-A"], ["diff", "--staged"], ["reset"]):
            result = await self.environment.exec_argv(
                [
                    "git",
                    "-c",
                    "core.hooksPath=" + os.devnull,
                    f"--git-dir={workspace / '.git'}",
                    f"--work-tree={workspace}",
                    *args,
                ],
                cwd="/workspace",
                env=self.env(values),
                timeout_sec=120,
            )
            if result.return_code != 0:
                diagnostic = (result.stderr or result.stdout or "no diagnostic").strip()
                raise RuntimeError(
                    f"Office preparation failed: git {' '.join(args)} "
                    f"(exit {result.return_code}): {diagnostic[:4096]}"
                )
            if args[0] == "diff":
                patch = result.stdout or ""
        patch_path.write_text(patch, encoding="utf-8")
        self.prepared = True

    async def run(
        self,
        command: Any,
        *,
        cwd: Any = None,
        env: Mapping[str, str] | None = None,
        timeout_sec: float | None = None,
        shell: bool | None = None,
    ):
        expected = self.rule.template.replace(
            "__PYTEST_COMMAND__", self.command.command
        )
        if (
            (shell is not None and shell is not True)
            or command != expected
            or Path(str(cwd)) not in {Path("/workspace"), self.mappings["/workspace"]}
        ):
            raise OfficeProfileError(
                "native Office executor received an unsupported command"
            )
        started = time.monotonic()
        try:
            async with asyncio.timeout(timeout_sec):
                code = await self._run_pipeline(env or {})
            return NativeExecutionResult(
                command=command,
                return_code=code,
                duration_sec=time.monotonic() - started,
            )
        except TimeoutError:
            return NativeExecutionResult(
                command=command,
                return_code=124,
                timed_out=True,
                error="Office verifier timed out",
                duration_sec=time.monotonic() - started,
            )
        except OSError as exc:
            return NativeExecutionResult(
                command=command,
                return_code=1,
                error=str(exc),
                duration_sec=time.monotonic() - started,
            )

    async def _python(
        self,
        args: list[str],
        env: Mapping[str, str],
        *,
        capture: bool = False,
        grading: bool = True,
    ):
        result = await self.environment.exec_argv(
            [sys.executable, *args],
            cwd="/workspace",
            env=self.env(env, grading=grading),
        )
        if not capture:
            with (self.logs / "test_output.txt").open("a", encoding="utf-8") as stream:
                stream.write(result.stdout or "")
                stream.write(result.stderr or "")
        return result

    async def _run_pipeline(self, env: Mapping[str, str]) -> int:
        start = int(time.time())
        output = self.logs / "test_output.txt"
        output.write_text("", encoding="utf-8")
        result = await self._python(
            [
                "-m",
                "pytest",
                self.path(self.command.pytest_target),
                f"--rootdir={self.task_dir / 'tests'}",
                f"--confcutdir={self.task_dir / 'tests'}",
                "-p",
                "no:cacheprovider",
                "-v",
                "--tb=short",
                f"--junitxml={self.logs / 'results.xml'}",
            ],
            env,
            grading=False,
        )
        pytest_exit = result.return_code
        if not (self.logs / "results.xml").is_file():
            (self.logs / "results.xml").write_text(
                '<testsuite name="verifier_startup" tests="1" failures="1" errors="0" skipped="0"><testcase classname="verifier" name="pytest_results_missing"><failure message="pytest did not create results.xml">See /logs/verifier/test_output.txt</failure></testcase></testsuite>\n',
                encoding="utf-8",
            )
        if (self.logs / "artifact_manifest.json").is_file():
            shutil.copy2(
                self.logs / "artifact_manifest.json",
                self.logs / "evaluator_artifact_manifest.json",
            )
        tests = self.task_dir / "tests"
        judge_yaml = tests / "judge.yaml"
        early = tests / "grading/wb_judge_manifest_postprocess.py"
        if judge_yaml.is_file() and early.is_file():
            with output.open("a", encoding="utf-8") as stream:
                stream.write("=== Building WB Judge evidence manifest ===\n")
            result = await self._python(
                [str(early), "--judge-yaml", str(judge_yaml), "--logs", str(self.logs)],
                env,
            )
            if result.return_code:
                return result.return_code
        wall = int(time.time()) - start
        score_env = {**env, "PYTEST_EXIT": str(pytest_exit), "WALL_TIME": str(wall)}
        scorer = tests / "grading/scorer.py"
        if scorer.is_file():
            help_result = await self._python(
                [str(scorer), "--help"], env, capture=True, grading=False
            )
            help_text = (help_result.stdout or "") + (help_result.stderr or "")
            args = [str(scorer), "--results-xml", str(self.logs / "results.xml")]
            for flag, value in (
                ("--log-dir", str(self.logs)),
                ("--pytest-exit", str(pytest_exit)),
                ("--wall-time", str(wall)),
                ("--workspace", self.path("/workspace")),
                ("--gold-path", self.path("/tests/gold/gold_answer.json")),
                ("--start-time", str(start)),
            ):
                if flag in help_text:
                    args.extend([flag, value])
            result = await self._python(
                args,
                {
                    **score_env,
                    "WB_BENCH_WORKSPACE": "/workspace",
                    "WB_BENCH_GOLD_PATH": "/tests/gold/gold_answer.json",
                    "WB_BENCH_VERIFIER_START_TIME": str(start),
                },
            )
        else:
            source, _ = _adapt_python(self.rule.score_python, self.mappings)
            result = await self._python(["-c", source], score_env, grading=False)
        if result.return_code:
            return result.return_code
        for filename, args, optional in (
            (
                "evidence_builder.py",
                ["--workspace", self.path("/workspace"), "--logs", str(self.logs)],
                (),
            ),
            (
                "manifest_postprocess.py",
                ["--judge-yaml", str(judge_yaml), "--logs", str(self.logs)],
                (
                    ("--workspace", self.path("/workspace")),
                    ("--verifier-output", str(self.logs)),
                ),
            ),
            (
                "extract_declared_artifacts.py",
                [
                    "--judge-yaml",
                    str(judge_yaml),
                    "--workspace",
                    self.path("/workspace"),
                    "--logs",
                    str(self.logs),
                ],
                (),
            ),
        ):
            script = tests / "grading/judge" / filename
            if not judge_yaml.is_file() or not script.is_file():
                continue
            if optional:
                result = await self._python(
                    [str(script), "--help"], env, capture=True, grading=False
                )
                help_text = (result.stdout or "") + (result.stderr or "")
                for flag, value in optional:
                    if flag in help_text:
                        args.extend([flag, value])
            result = await self._python([str(script), *args], env)
            if result.return_code:
                return result.return_code
        source, _ = _adapt_python(self.rule.reward_python, self.mappings)
        result = await self._python(["-c", source], env, grading=False)
        if result.return_code:
            return result.return_code
        return (
            0
            if all(
                (self.logs / name).is_file()
                for name in (
                    "results.xml",
                    "test_output.txt",
                    "agent.patch",
                    "score.json",
                    "reward.json",
                    "reward.txt",
                )
            )
            else 1
        )


class NativePythonVerifier(BaseVerifier):
    """Native host execution with the external WorkBuddy scoring engine."""

    async def verify(self) -> VerifierResult:
        from workbuddy_bench.judge.registry import (
            RegistryBuildContext,
            build_default_context,
            load_verifier_registry,
            maybe_await,
        )
        from workbuddy_bench.judge.runners.rule import HarborScriptRuleJudgeRunner

        from .environment import HostEnvironment
        from .workbuddy import validate_workbuddy_runtime

        if not isinstance(self.environment, HostEnvironment):
            raise OfficeProfileError("NativePythonVerifier requires HostEnvironment")
        validate_workbuddy_runtime()
        with _staged_verifier_task(self) as root:
            task = self.task.paths.task_dir
            executor = NativeOfficeExecutor(
                self.environment, task, _load_rule(root), _load_command(task)
            )
            audit = []
            for path in sorted((task / "tests/grading").rglob("*.py")):
                original_bytes = _read_regular_bytes(
                    task, path, max_bytes=TASK_TEXT_LIMIT
                )
                source = original_bytes.decode("utf-8-sig")
                adapted, edits = _adapt_python(source, executor.mappings)
                adapted_bytes = original_bytes
                if adapted != source:
                    adapted_bytes = adapted.encode("utf-8")
                    path.chmod(path.stat().st_mode | stat.S_IWUSR)
                    path.write_bytes(adapted_bytes)
                if edits:
                    audit.append(
                        {
                            "path": path.relative_to(task).as_posix(),
                            "source_sha256": hashlib.sha256(original_bytes).hexdigest(),
                            "adapted_sha256": hashlib.sha256(adapted_bytes).hexdigest(),
                            "edits": edits,
                        }
                    )
            (executor.logs / "office-adaptation.json").write_text(
                json.dumps(
                    {
                        "schema": "psycheval.workbuddy-office-adaptation.v1",
                        "rule_source_sha256": executor.rule.source_sha256,
                        "files": audit,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            skipped_count = sum(
                edit["kind"] == "skipped" for entry in audit for edit in entry["edits"]
            )
            if skipped_count:
                logger.warning(
                    "Native Office adaptation skipped %d source expressions; "
                    "grading is best effort. See office-adaptation.json.",
                    skipped_count,
                )
            contract = _staged_contract(task)
            runtime = _workbuddy_runtime_type()(
                verifier=self,
                environment=executor,
                tests_dir=str(task / "tests"),
                workspace=executor.path("/workspace"),
                container_verifier_dir=str(executor.logs),
                host_verifier_dir=executor.logs,
            )
            registry = load_verifier_registry(
                RegistryBuildContext(contract=contract, runtime=runtime, verifier=self)
            )
            if registry.custom_verify is not None:
                return await maybe_await(registry.custom_verify(self))
            if "rule_script" not in registry.judge_runners:
                raise OfficeProfileError("unsupported native Python registry execution")
            context = build_default_context(contract, runtime)
            if registry.prepare is not None:
                await maybe_await(registry.prepare(context))
            if executor.preparation_error is not None:
                raise executor.preparation_error
            if not executor.prepared:
                await executor.prepare({**context.env, **executor.command.env})
            plan = await maybe_await(registry.plan_builder(context))
            judges = []
            for judge in plan.judges:
                if judge.type == "rule_script":
                    config = dict(judge.config)
                    config["score_json"] = str(executor.logs / "score.json")
                    config["reward_json"] = str(executor.logs / "reward.json")
                    judge = replace(judge, config=config)
                judges.append(judge)
            plan = replace(plan, judges=judges)
            registry = replace(
                registry,
                judge_runners={
                    **registry.judge_runners,
                    "rule_script": HarborScriptRuleJudgeRunner(
                        runtime, executor=executor
                    ),
                },
            )
            score = await registry.engine().run(context, plan)
            if registry.finalize_score is not None:
                score = await maybe_await(registry.finalize_score(score, context, plan))
            if skipped_count:
                score = replace(
                    score,
                    diagnostics={
                        **score.diagnostics,
                        "native_adaptation": {"skipped": skipped_count},
                    },
                )
            runtime.write_score(score)
            return VerifierResult(rewards=score.reward_payload())


@contextmanager
def _staged_verifier_task(verifier):
    """Keep plugin imports, caches, and rewrites in an invocation-owned copy."""
    from workbuddy_bench.judge.runtime import merged_verifier_env

    original = verifier.task
    original_override = verifier.override_env
    task_dir = original.paths.task_dir
    dataset_root, _ = read_workbuddy_manifest(task_dir)
    with tempfile.TemporaryDirectory(prefix="session-") as directory:
        root = Path(directory)
        # Dataset-level plugin assets may have arbitrary names. Other Tasks need
        # not be copied merely to execute this Task's verifier.
        for child in dataset_root.iterdir():
            if child.name in {".git", "__pycache__"}:
                continue
            if child == task_dir or child in task_dir.parents:
                continue
            if child.is_dir() and (child / "task.toml").is_file():
                continue
            if child.is_dir():
                _walk_regular_tree(child)
                shutil.copytree(
                    child,
                    root / child.name,
                    ignore=shutil.ignore_patterns("__pycache__", ".git"),
                )
            else:
                content = _read_regular_bytes(
                    dataset_root, child, max_bytes=TASK_TEXT_LIMIT
                )
                (root / child.name).write_bytes(content)
        target = root / task_dir.relative_to(dataset_root)
        _walk_regular_tree(task_dir)
        shutil.copytree(
            task_dir,
            target,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", ".git"),
        )
        verifier.task = deepcopy(original)
        verifier.task.paths = TaskPaths(target)
        verifier.task._task_dir = target
        try:
            verifier.override_env = resolve_env_vars(merged_verifier_env(verifier))
            yield root
        finally:
            verifier.task = original
            verifier.override_env = original_override
            namespace = _plugin_namespace(root)
            for name in tuple(sys.modules):
                if name == namespace or name.startswith(namespace + "."):
                    del sys.modules[name]


def _retained_score_diagnostics(diagnostics: dict[str, Any]) -> dict[str, Any]:
    """Redact context credentials without changing the plugin's score object."""
    if not isinstance(diagnostics, dict):
        return diagnostics
    context = diagnostics.get("context")
    if not isinstance(context, dict) or not isinstance(context.get("env"), dict):
        return diagnostics
    env = context["env"]
    retained = {
        **env,
        **templatize_sensitive_env(
            {
                key: str(value)
                for key, value in env.items()
                if isinstance(value, str) or is_sensitive_env_key(key)
            }
        ),
    }
    return {**diagnostics, "context": {**context, "env": retained}}


def _workbuddy_runtime_type():
    # Optional imports stay at execution time. Extend the writer seam so custom
    # hooks using either artifact_writer() or write_score() get the same policy.
    from workbuddy_bench.judge.core import ArtifactWriter
    from workbuddy_bench.judge.runtime import HarborAttemptRuntime

    class RetainedArtifactWriter(ArtifactWriter):
        def write(self, score):
            super().write(
                replace(
                    score,
                    diagnostics=_retained_score_diagnostics(
                        score.score_payload()["diagnostics"]
                    ),
                )
            )

    class WorkBuddyRuntime(HarborAttemptRuntime):
        def artifact_writer(self):
            return RetainedArtifactWriter(
                reward_json_path=self.verifier.trial_paths.reward_json_path,
                score_json_path=self.host_verifier_dir / "score.json",
            )

    return WorkBuddyRuntime


def _plugin_namespace(root: Path) -> str:
    return "_workbuddy_" + hashlib.sha256(str(root).encode()).hexdigest()[:16]


def _staged_contract(task: Path):
    from workbuddy_bench.judge.registry import load_verifier_contract

    contract = load_verifier_contract(task)
    if not contract.plugin:
        return contract
    module, _, function = contract.plugin.partition(":")
    path = contract.dataset_root.joinpath(*module.split("."))
    if not (path.with_suffix(".py").is_file() or (path / "__init__.py").is_file()):
        return contract
    namespace = _plugin_namespace(contract.dataset_root)
    package = ModuleType(namespace)
    package.__path__ = [str(contract.dataset_root)]
    package.__spec__ = importlib.machinery.ModuleSpec(
        namespace, loader=None, is_package=True
    )
    sys.modules[namespace] = package
    return replace(contract, plugin=f"{namespace}.{module}:{function}")


class WorkBuddyVerifier(NativePythonVerifier):
    """Run the upstream plugin lifecycle, with native execution-format adaptation."""

    async def verify(self) -> VerifierResult:
        from workbuddy_bench.judge.registry import (
            RegistryBuildContext,
            build_default_context,
            load_verifier_registry,
            maybe_await,
        )

        from .environment import HostEnvironment
        from .workbuddy import validate_workbuddy_runtime

        validate_workbuddy_runtime()
        manifest = self.task.paths.task_dir / "tests/verifier.toml"
        if (
            isinstance(self.environment, HostEnvironment)
            and self.environment.os == TaskOS.WINDOWS
            and manifest.is_file()
        ):
            declaration = tomllib.loads(_read_source(manifest.parent, manifest))
            if declaration.get("schema_version") == "workbuddy.office.verifier.v1":
                return await super().verify()
        with _staged_verifier_task(self):
            contract = _staged_contract(self.task.paths.task_dir)
            runtime = _workbuddy_runtime_type().from_verifier(self)
            if isinstance(self.environment, HostEnvironment):
                runtime.workspace = str(
                    self.environment.native_path(
                        self.environment.task_env_config.workdir or "/app"
                    )
                )
                runtime.tests_dir = str(self.environment.native_path("/tests"))
                runtime.container_verifier_dir = str(
                    self.environment.native_path("/logs/verifier")
                )
            registry = load_verifier_registry(
                RegistryBuildContext(
                    contract=contract,
                    runtime=runtime,
                    verifier=self,
                )
            )
            if registry.custom_verify is not None:
                return await maybe_await(registry.custom_verify(self))
            await runtime.upload_tests()
            context = build_default_context(contract, runtime)
            if registry.prepare is not None:
                await maybe_await(registry.prepare(context))
            plan = await maybe_await(registry.plan_builder(context))
            score = await registry.engine().run(context, plan)
            if registry.finalize_score is not None:
                score = await maybe_await(registry.finalize_score(score, context, plan))
            runtime.write_score(score)
            return VerifierResult(rewards=score.reward_payload())
