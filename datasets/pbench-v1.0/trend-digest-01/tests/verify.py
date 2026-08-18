#!/usr/bin/env python3
"""Programmatic verifier for the PBench trend digest task."""

from __future__ import annotations

import json
import os
import re
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from harbor.models.trajectories import Trajectory

from psycheval.harbor.runtime_config import optional_effective_runtime_config
from psycheval.harbor.verifier import evaluate

WEIGHTS = {
    "source_evidence": 0.30,
    "freshness": 0.25,
    "coverage": 0.30,
    "format": 0.15,
}
_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_REPOSITORY_URL = re.compile(
    r"https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", re.IGNORECASE
)


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().strip('"').replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize(value: object) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def contains_value(content: str, value: object) -> bool:
    normalized_value = normalize(value)
    if not normalized_value:
        return False
    return (
        re.search(
            re.escape(normalized_value)
            + r"(?=$|[\s<>)\]\}\"'，。；：！？]|[.,;:!?](?=$|\s))",
            normalize(content),
        )
        is not None
    )


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def parse_front_matter(content: str) -> dict[str, str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    metadata: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return metadata
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return {}


def _cell_value(cell: ElementTree.Element, shared: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(f".//{{{_MAIN_NS}}}t"))
    value = cell.find(f"{{{_MAIN_NS}}}v")
    raw = value.text if value is not None and value.text is not None else ""
    if cell_type == "s" and raw:
        return shared[int(raw)]
    if cell_type == "b":
        return "true" if raw == "1" else "false"
    return raw


def read_enabled_users(path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        try:
            shared_root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = [
                "".join(node.text or "" for node in item.findall(f".//{{{_MAIN_NS}}}t"))
                for item in shared_root.findall(f"{{{_MAIN_NS}}}si")
            ]
        except KeyError:
            shared = []
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        sheet = next(
            item
            for item in workbook.findall(f".//{{{_MAIN_NS}}}sheet")
            if item.attrib.get("name", "").casefold() == "users"
        )
        relation_id = sheet.attrib[f"{{{_REL_NS}}}id"]
        relationships = ElementTree.fromstring(
            archive.read("xl/_rels/workbook.xml.rels")
        )
        target = next(
            item.attrib["Target"]
            for item in relationships.findall(f"{{{_PKG_REL_NS}}}Relationship")
            if item.attrib.get("Id") == relation_id
        )
        sheet_path = "xl/" + target.lstrip("/").removeprefix("xl/")
        root = ElementTree.fromstring(archive.read(sheet_path))
    rows = [
        [_cell_value(cell, shared).strip() for cell in row.findall(f"{{{_MAIN_NS}}}c")]
        for row in root.findall(f".//{{{_MAIN_NS}}}row")
    ]
    headers = [value.casefold() for value in rows[0]]
    positions = {name: headers.index(name) for name in ("handle", "name", "enabled")}
    users: list[dict[str, str]] = []
    for row in rows[1:]:
        padded = row + [""] * (len(headers) - len(row))
        if padded[positions["enabled"]].casefold() not in {
            "1",
            "true",
            "yes",
            "on",
        }:
            continue
        handle = padded[positions["handle"]].lstrip("@").strip()
        if handle:
            users.append({"handle": handle, "name": padded[positions["name"]].strip()})
    return users


def _successful_calls(trajectory: dict[str, Any]) -> list[dict[str, str]]:
    calls: list[dict[str, str]] = []
    steps = trajectory.get("steps")
    if not isinstance(steps, list):
        return calls
    for step in steps:
        if not isinstance(step, dict):
            continue
        observations: dict[str, dict[str, Any]] = {}
        observation = step.get("observation")
        if isinstance(observation, dict):
            for result in observation.get("results") or []:
                if isinstance(result, dict) and result.get("source_call_id"):
                    observations[str(result["source_call_id"])] = result
        for call in step.get("tool_calls") or []:
            if not isinstance(call, dict):
                continue
            result = observations.get(str(call.get("tool_call_id", "")))
            if not result:
                continue
            extra = result.get("extra") if isinstance(result.get("extra"), dict) else {}
            if extra.get("is_error") is True:
                continue
            if str(extra.get("status", "")).casefold() in {"error", "failed"}:
                continue
            if extra.get("exit_code") not in {None, 0, "0"}:
                continue
            calls.append(
                {
                    "name": str(call.get("function_name") or ""),
                    "arguments": json.dumps(
                        call.get("arguments"), ensure_ascii=False, sort_keys=True
                    ),
                    "observation": str(result.get("content") or ""),
                }
            )
    return calls


def _report(
    artifacts_dir: Path, platform: str
) -> tuple[Path | None, str, dict[str, str], list[bool]]:
    entries = (
        [path for path in artifacts_dir.iterdir()] if artifacts_dir.is_dir() else []
    )
    files = [path for path in entries if path.is_file() and not path.is_symlink()]
    one_file = len(entries) == 1 and len(files) == 1
    if not one_file:
        return None, "", {}, [False, False, False, False, False]
    path = files[0]
    content = path.read_text(encoding="utf-8")
    metadata = parse_front_matter(content)
    match = re.fullmatch(rf"{re.escape(platform)}-(\d{{8}}T\d{{6}}Z)\.md", path.name)
    filename_valid = match is not None
    timestamp_valid = False
    if match and metadata.get("generated_at"):
        try:
            timestamp_valid = parse_utc(metadata["generated_at"]).strftime(
                "%Y%m%dT%H%M%SZ"
            ) == match.group(1)
        except ValueError:
            timestamp_valid = False
    platform_valid = metadata.get("platform") == platform
    source_valid = bool(metadata.get("source"))
    chinese_summary = (
        "摘要" in content and len(re.findall(r"[\u4e00-\u9fff]", content)) >= 8
    )
    return (
        path,
        content,
        metadata,
        [
            one_file,
            filename_valid,
            timestamp_valid and platform_valid,
            source_valid,
            chinese_summary,
        ],
    )


def _is_current(value: datetime, now: datetime, max_age_seconds: int) -> bool:
    return (
        now - timedelta(seconds=max_age_seconds) <= value <= now + timedelta(minutes=5)
    )


def _github_dimensions(
    config: dict[str, Any],
    calls: list[dict[str, str]],
    content: str,
    metadata: dict[str, str],
    now: datetime,
) -> tuple[dict[str, float], dict[str, Any]]:
    source_url = str(config["source_url"])
    required_count = int(config["required_count"])
    repositories: list[str] = []
    for call in calls:
        if source_url not in call["arguments"]:
            continue
        seen: set[str] = set()
        candidate: list[str] = []
        for owner, repository in _REPOSITORY_URL.findall(call["observation"]):
            url = f"https://github.com/{owner}/{repository.rstrip('.,)')}"
            key = url.casefold()
            if key not in seen:
                seen.add(key)
                candidate.append(url)
        if len(candidate) >= required_count:
            repositories = candidate[:required_count]
            break
    source_evidence = float(len(repositories) == required_count)
    try:
        report_time = parse_utc(metadata["generated_at"])
        freshness = float(
            metadata.get("source") == source_url
            and metadata.get("window") == "weekly"
            and _is_current(report_time, now, int(config["max_age_seconds"]))
        )
    except (KeyError, ValueError):
        freshness = 0.0
    represented = sum(contains_value(content, url) for url in repositories)
    coverage = represented / required_count if required_count else 0.0
    return (
        {
            "source_evidence": source_evidence,
            "freshness": freshness,
            "coverage": coverage,
        },
        {"repositories": repositories, "represented": represented},
    )


def _x_dimensions(
    config: dict[str, Any],
    skill_call_valid: bool,
    content: str,
    metadata: dict[str, str],
    workspace: Path,
    now: datetime,
) -> tuple[dict[str, float], dict[str, Any]]:
    snapshot = load_json(workspace / str(config["snapshot"]))
    users = read_enabled_users(workspace / str(config["users"]))
    expected_handles = [user["handle"].casefold() for user in users]
    accounts = (
        snapshot.get("accounts") if isinstance(snapshot.get("accounts"), list) else []
    )
    account_by_handle = {
        str(account.get("handle", "")).casefold(): account
        for account in accounts
        if isinstance(account, dict)
    }
    valid_statuses = {"success", "no_updates", "fetch_failed"}
    statuses_valid = set(account_by_handle) == set(expected_handles) and all(
        account_by_handle[handle].get("status") in valid_statuses
        for handle in expected_handles
    )
    statuses_valid = statuses_valid and all(
        (
            account_by_handle[handle].get("status") == "success"
            and bool(account_by_handle[handle].get("posts"))
        )
        or (
            account_by_handle[handle].get("status") in {"no_updates", "fetch_failed"}
            and not account_by_handle[handle].get("posts")
        )
        for handle in expected_handles
    )
    successful_handles = [
        handle
        for handle in expected_handles
        if account_by_handle.get(handle, {}).get("status") in {"success", "no_updates"}
    ]
    source_evidence = float(
        skill_call_valid
        and snapshot.get("platform") == "x"
        and snapshot.get("source") == "nitter-rss"
        and statuses_valid
        and bool(successful_handles)
    )
    try:
        generated = parse_utc(str(snapshot["generated_at"]))
        window_start = parse_utc(str(snapshot["window_start"]))
        window_end = parse_utc(str(snapshot["window_end"]))
        report_time = parse_utc(metadata["generated_at"])
        freshness = float(
            window_end == generated
            and window_end - window_start == timedelta(hours=24)
            and _is_current(generated, now, int(config["max_age_seconds"]))
            and generated <= report_time <= generated + timedelta(minutes=15)
            and metadata.get("source") == "nitter-rss"
            and metadata.get("window_start") == format_utc(window_start)
            and metadata.get("window_end") == format_utc(window_end)
        )
    except (KeyError, ValueError):
        freshness = 0.0
    classified = 0
    for handle in expected_handles:
        account = account_by_handle.get(handle, {})
        section_match = re.search(
            rf"##[^\n]*@{re.escape(handle)}[^\n]*\n(.*?)(?=\n##|\Z)",
            content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        section = normalize(section_match.group(1)) if section_match else ""
        expected_status = account.get("status")
        if expected_status == "success":
            correct_status = "状态：成功" in section
        elif expected_status == "no_updates":
            correct_status = "无新推文" in section
        else:
            correct_status = "抓取失败" in section
        classified += bool(section_match and correct_status)
    source_coverage = (
        len(successful_handles) / len(expected_handles) if expected_handles else 0
    )
    account_coverage = classified / len(expected_handles) if expected_handles else 0
    posts = [
        post
        for account in accounts
        if isinstance(account, dict)
        for post in account.get("posts", [])
        if isinstance(post, dict)
    ]
    represented_posts = sum(
        contains_value(content, post.get("url", ""))
        and (
            not normalize(post.get("text", ""))
            or normalize(post.get("text", ""))[:40] in normalize(content)
        )
        for post in posts
    )
    post_coverage = represented_posts / len(posts) if posts else 1.0
    coverage = mean([source_coverage, account_coverage, post_coverage])
    return (
        {
            "source_evidence": source_evidence,
            "freshness": freshness,
            "coverage": coverage,
        },
        {
            "expected_accounts": len(expected_handles),
            "successful_accounts": len(successful_handles),
            "classified_accounts": classified,
            "posts": len(posts),
            "represented_posts": represented_posts,
        },
    )


def _hacker_news_dimensions(
    config: dict[str, Any],
    skill_call_valid: bool,
    content: str,
    metadata: dict[str, str],
    workspace: Path,
    now: datetime,
) -> tuple[dict[str, float], dict[str, Any]]:
    snapshot = load_json(workspace / str(config["snapshot"]))
    stories = (
        snapshot.get("stories") if isinstance(snapshot.get("stories"), list) else []
    )
    required_count = int(config["required_count"])
    ranks = [story.get("rank") for story in stories if isinstance(story, dict)]
    source_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    source_evidence = float(
        skill_call_valid
        and snapshot.get("platform") == "hacker-news"
        and snapshot.get("source_url") == source_url
        and len(stories) == required_count
        and ranks == list(range(1, required_count + 1))
    )
    try:
        generated = parse_utc(str(snapshot["generated_at"]))
        report_time = parse_utc(metadata["generated_at"])
        freshness = float(
            _is_current(generated, now, int(config["max_age_seconds"]))
            and generated <= report_time <= generated + timedelta(minutes=15)
            and metadata.get("source") == source_url
            and metadata.get("snapshot_at") == format_utc(generated)
        )
    except (KeyError, ValueError):
        freshness = 0.0
    represented = 0
    for story in stories:
        if not isinstance(story, dict):
            continue
        required_values = {
            normalize(story.get("title", "")),
            normalize(story.get("url", "")),
            normalize(story.get("discussion_url", "")),
        }
        if all(contains_value(content, value) for value in required_values):
            represented += 1
    coverage = represented / required_count if required_count else 0.0
    return (
        {
            "source_evidence": source_evidence,
            "freshness": freshness,
            "coverage": coverage,
        },
        {"stories": len(stories), "represented": represented},
    )


def grade(
    config: dict[str, Any],
    *,
    workspace: Path,
    agent_logs: Path,
    artifacts_dir: Path,
    now: datetime,
) -> tuple[dict[str, float], dict[str, Any]]:
    platform = str(config["platform"])
    trajectory_data = load_json(agent_logs / "trajectory.json")
    trajectory = Trajectory(**trajectory_data)
    calls = _successful_calls(trajectory_data)
    generic_config = {
        field: config[field]
        for field in (
            "required_calls",
            "forbidden_tool_names",
            "final_terms",
            "required_artifacts",
        )
        if field in config
    }
    common_checks = evaluate(trajectory, generic_config, artifacts_dir)
    required_call_checks = [
        check
        for check in common_checks
        if str(check.get("id", "")).startswith("required_call_")
    ]
    skill_call_valid = bool(required_call_checks) and all(
        check["passed"] for check in required_call_checks
    )
    _, content, metadata, format_checks = _report(artifacts_dir, platform)
    if platform == "github":
        dimensions, evidence = _github_dimensions(config, calls, content, metadata, now)
    elif platform == "x":
        dimensions, evidence = _x_dimensions(
            config, skill_call_valid, content, metadata, workspace, now
        )
    elif platform == "hacker-news":
        dimensions, evidence = _hacker_news_dimensions(
            config, skill_call_valid, content, metadata, workspace, now
        )
    else:
        raise ValueError(f"unsupported platform: {platform}")
    final_answer_check = next(
        check for check in common_checks if check["id"] == "final_answer"
    )
    dimensions["format"] = mean([float(value) for value in format_checks])
    dimensions["final_answer"] = float(final_answer_check["passed"])
    quality_reward = sum(dimensions[name] * weight for name, weight in WEIGHTS.items())
    dimensions["reward"] = quality_reward * dimensions["final_answer"]
    rewards = {name: round(value, 6) for name, value in dimensions.items()}
    details = {
        "platform": platform,
        "rewards": rewards,
        "checks": common_checks,
        "format_checks": format_checks,
        "source": evidence,
    }
    return rewards, details


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        raise SystemExit("usage: verify.py /tests/grader.json")
    runtime = optional_effective_runtime_config()
    workspace = Path(runtime.paths.workdir) if runtime else Path("/app")
    agent_logs = Path(runtime.paths.agent_logs) if runtime else Path("/logs/agent")
    artifacts_dir = (
        Path(runtime.paths.artifacts) if runtime else Path("/logs/artifacts")
    )
    verifier_logs = (
        Path(runtime.paths.verifier_logs) if runtime else Path("/logs/verifier")
    )
    verifier_logs.mkdir(parents=True, exist_ok=True)
    try:
        now_value = os.environ.get("PBENCH_TREND_NOW")
        now = parse_utc(now_value) if now_value else datetime.now(timezone.utc)
        rewards, details = grade(
            load_json(Path(arguments[0])),
            workspace=workspace,
            agent_logs=agent_logs,
            artifacts_dir=artifacts_dir,
            now=now,
        )
    except Exception as error:
        rewards = {name: 0.0 for name in (*WEIGHTS, "final_answer", "reward")}
        details = {
            "error": f"{type(error).__name__}: {error}",
            "rewards": rewards,
            "checks": [],
        }
    (verifier_logs / "checks.json").write_text(
        json.dumps({"checks": details["checks"]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (verifier_logs / "reward.json").write_text(
        json.dumps(rewards, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (verifier_logs / "reward-details.json").write_text(
        json.dumps(details, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(details, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
