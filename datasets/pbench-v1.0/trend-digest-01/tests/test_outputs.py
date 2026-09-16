"""Fixed deterministic output checks; scoring and publication belong to Harbor."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from harbor.models.trajectories import Trajectory

from psycheval.harbor.verifier import matching_observations

GITHUB_URL = "https://github.com/trending?since=weekly"
HN_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"


def github_repositories(observation: str) -> list[str]:
    """Read ranked repository headings before considering plain-text URLs."""

    class Headings(HTMLParser):
        def __init__(self):
            super().__init__()
            self.heading = False
            self.links = []

        def handle_starttag(self, tag, attrs):
            if tag == "h2":
                self.heading = True
            if tag == "a" and self.heading:
                self.links.append(dict(attrs).get("href", ""))

        def handle_endtag(self, tag):
            if tag == "h2":
                self.heading = False

    parser = Headings()
    parser.feed(observation)
    headings = parser.links or re.findall(
        r"(?m)^#{1,3}\s+.*?\[[^\]]+\]\(([^)]+)\)", observation
    )
    links = headings or re.findall(
        r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", observation
    )
    repositories = []
    seen = set()
    for link in links:
        match = re.fullmatch(
            r"(?:https://github\.com)?/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/?",
            link.rstrip(".,)"),
        )
        if match is None or match[1].casefold() in {
            "features",
            "topics",
            "collections",
            "sponsors",
            "orgs",
            "settings",
            "solutions",
            "enterprise",
            "security",
            "pricing",
            "readme",
            "customer-stories",
            "trending",
            "marketplace",
        }:
            continue
        url = f"https://github.com/{match[1]}/{match[2]}"
        if url.casefold() not in seen:
            repositories.append(url)
            seen.add(url.casefold())
    return repositories


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be UTC with an explicit offset")
    return parsed


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def contains_value(content: str, value: str) -> bool:
    return _contains_normalized_value(normalize(content), value)


def _contains_normalized_value(content: str, value: str) -> bool:
    return bool(
        value
        and re.search(
            re.escape(normalize(value))
            + r"(?=$|[\s<>)\]\}\"'，。；：！？]|[.,;:!?](?=$|\s))",
            content,
        )
    )


def _read(path: Path, root: Path, *, limit_mib: int = 4) -> str:
    if not path.is_relative_to(root):
        raise ValueError("input escaped its root")
    for part in (
        root,
        *[
            root.joinpath(*path.relative_to(root).parts[:n])
            for n in range(1, len(path.relative_to(root).parts) + 1)
        ],
    ):
        if part.is_symlink() or part.is_junction():
            raise ValueError("linked input is not supported")
    with path.open("rb") as stream:
        raw = stream.read(limit_mib * 1024 * 1024 + 1)
    if len(raw) > limit_mib * 1024 * 1024:
        raise ValueError(f"input exceeds {limit_mib} MiB")
    return raw.decode("utf-8")


def _parse_report(content: str) -> tuple[dict, str]:
    lines = content.removeprefix("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, content
    result = {}
    valid = True
    for index, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            return (result if valid else {}), "\n".join(lines[index + 1 :])
        if ":" in line:
            key, value = line.split(":", 1)
            if key.strip() in result:
                valid = False
            result[key.strip()] = value.strip().strip("\"'")
    return {}, ""


def _time(value) -> datetime | None:
    try:
        return parse_utc(value)
    except (ValueError, TypeError, AttributeError):
        return None


def _current(value: datetime | None, now: datetime) -> bool:
    return value is not None and now - timedelta(hours=1) <= value <= now + timedelta(
        minutes=5
    )


def _url(value) -> bool:
    try:
        return (
            isinstance(value, str)
            and urlsplit(value).scheme in {"http", "https"}
            and bool(urlsplit(value).netloc)
        )
    except ValueError:
        return False


def check_outputs(context: dict, config: dict, *, now: datetime) -> list[dict]:
    platform = context["harbor"]["verifier"]["step_name"]
    if platform not in {"github", "x", "hacker-news"}:
        raise ValueError("Trend Digest requires a known current step_name")
    paths = {name: Path(path) for name, path in context["paths"].items()}
    declared = config["custom_checks"]
    checks = []

    def check(name, passed, evidence):
        checks.append({"id": name, "passed": bool(passed), "evidence": evidence})

    entries = list(paths["artifacts"].iterdir()) if paths["artifacts"].is_dir() else []
    content = ""
    report = entries[0] if len(entries) == 1 else None
    if report is not None:
        try:
            content = _read(report, paths["artifacts"])
        except (OSError, ValueError):
            report = None
    meta, body = _parse_report(content)
    normalized_report = normalize(content)
    match = (
        re.fullmatch(rf"{platform}-(\d{{8}}T\d{{6}}Z)\.md", report.name)
        if report
        else None
    )
    report_time = _time(meta.get("generated_at"))
    check("report_unique", report is not None, "exactly one regular UTF-8 report")
    check("report_filename", match is not None, "platform-YYYYMMDDTHHMMSSZ.md")
    check(
        "report_timestamp",
        match and report_time and report_time.strftime("%Y%m%dT%H%M%SZ") == match[1],
        "filename matches UTC generated_at",
    )
    check(
        "report_platform",
        meta.get("platform") == platform,
        "front matter platform matches step",
    )
    check("report_source", bool(meta.get("source")), "source is present")
    check(
        "report_chinese",
        len(re.findall(r"[\u4e00-\u9fff]", body)) >= 8,
        "basic Chinese summary is present",
    )
    check(
        "report_current",
        _current(report_time, now),
        "report time within one hour, with five-minute future tolerance",
    )
    sources = None
    if platform == "github":
        trajectory = Trajectory(
            **json.loads(
                _read(
                    paths["agent_logs"] / "trajectory.json",
                    paths["agent_logs"],
                    limit_mib=128,
                )
            )
        )
        observations = matching_observations(trajectory, config["required_calls"][0])
        repositories = []
        for observation in observations:
            candidates = github_repositories(observation)
            if len(candidates) >= 10:
                repositories = candidates[:10]
                sources = observation
                break
        check(
            "github_weekly",
            meta.get("source") == GITHUB_URL and meta.get("window") == "weekly",
            "report identifies the weekly source",
        )
        for index in range(10):
            url = repositories[index] if index < len(repositories) else ""
            check(
                f"github_repository_{index + 1:02}",
                _contains_normalized_value(normalized_report, url),
                url or "source repository slot missing",
            )
    else:
        try:
            snapshot = json.loads(
                _read(
                    paths["workdir"] / f".trend-digest/{platform}.json",
                    paths["workdir"],
                )
            )
            if not isinstance(snapshot, dict):
                snapshot = {}
        except (OSError, ValueError):
            snapshot = {}
        generated = _time(snapshot.get("generated_at"))
        check(
            "snapshot_current",
            _current(generated, now)
            and report_time
            and generated <= report_time <= generated + timedelta(minutes=15),
            "snapshot is current and report follows it within fifteen minutes",
        )
        if platform == "x":
            handles = [
                name.removeprefix("x_fetched_")
                for name in declared
                if name.startswith("x_fetched_")
            ]
            accounts = snapshot.get("accounts", [])
            accounts = accounts if isinstance(accounts, list) else []
            by_handle = {
                str(account.get("handle", "")).casefold(): account
                for account in accounts
                if isinstance(account, dict)
            }
            start, end = (
                _time(snapshot.get("window_start")),
                _time(snapshot.get("window_end")),
            )
            window = (
                start
                and end
                and end == generated
                and end - start == timedelta(hours=24)
            )
            valid = (
                snapshot.get("schema_version") == 1
                and snapshot.get("platform") == "x"
                and snapshot.get("source") == "nitter-rss"
                and len(accounts) == len(handles)
                and set(by_handle) == set(handles)
            )
            validated = []
            for handle in handles:
                account = by_handle.get(handle, {})
                posts = account.get("posts")
                status = account.get("status")
                if not isinstance(status, str):
                    status = None
                posts_valid = isinstance(posts, list) and all(
                    isinstance(post, dict)
                    and isinstance(post.get("text"), str)
                    and bool(post["text"].strip())
                    and _url(post.get("url"))
                    and _time(post.get("published_at"))
                    and window
                    and start <= _time(post["published_at"]) <= end
                    for post in posts
                )
                account_valid = posts_valid and (
                    (status == "success" and bool(posts))
                    or (status in {"no_updates", "fetch_failed"} and not posts)
                )
                valid = bool(valid and account_valid)
                section_match = re.search(
                    rf"^##[^\n]*@{re.escape(handle)}(?![A-Za-z0-9_])[^\n]*\n(.*?)(?=\n##|\Z)",
                    content,
                    flags=re.IGNORECASE | re.DOTALL | re.MULTILINE,
                )
                section = section_match[1] if section_match else ""
                normalized_section = normalize(section)
                status_text = {
                    "success": "状态：成功",
                    "no_updates": "无新推文",
                    "fetch_failed": "抓取失败",
                }.get(status, "")
                check(
                    f"x_fetched_{handle}",
                    account_valid and status in {"success", "no_updates"},
                    f"@{handle}: {status}",
                )
                check(
                    f"x_status_{handle}",
                    account_valid and status_text and status_text in section,
                    f"@{handle}: report explains {status}",
                )
                check(
                    f"x_posts_{handle}",
                    account_valid
                    and all(
                        _contains_normalized_value(normalized_section, post["url"])
                        and normalize(post["text"]) in normalized_section
                        for post in posts
                    ),
                    f"@{handle}: complete in-window posts",
                )
                if account_valid:
                    validated.append(account)
            check(
                "x_snapshot",
                valid,
                "schema, source, fixed watchlist, statuses and posts are valid",
            )
            check(
                "x_window",
                window
                and meta.get("source") == "nitter-rss"
                and _time(meta.get("window_start")) == start
                and _time(meta.get("window_end")) == end,
                "24-hour window follows actual fetch time and matches front matter",
            )
            if valid and window:
                sources = json.dumps(
                    {**snapshot, "accounts": validated}, ensure_ascii=False, indent=2
                )
        else:
            stories = snapshot.get("stories", [])
            stories = stories if isinstance(stories, list) else []
            valid = (
                snapshot.get("schema_version") == 1
                and snapshot.get("platform") == platform
                and snapshot.get("source_url") == HN_URL
                and len(stories) == 12
            )
            valid = valid and all(
                isinstance(story, dict)
                and type(story.get("rank")) is int
                and story["rank"] == index
                and isinstance(story.get("title"), str)
                and bool(story["title"].strip())
                and type(story.get("id")) is int
                and _url(story.get("url"))
                and story.get("discussion_url")
                == f"https://news.ycombinator.com/item?id={story['id']}"
                for index, story in enumerate(stories, 1)
            )
            check(
                "hn_snapshot",
                valid,
                "twelve ordered stories with original and discussion URLs",
            )
            check(
                "hn_source",
                meta.get("source") == HN_URL
                and generated
                and _time(meta.get("snapshot_at")) == generated,
                "report source and snapshot timestamp match",
            )
            for index in range(12):
                story = (
                    stories[index]
                    if index < len(stories) and isinstance(stories[index], dict)
                    else {}
                )
                check(
                    f"hn_story_{index + 1:02}",
                    all(
                        isinstance(story.get(key), str)
                        and _contains_normalized_value(normalized_report, story[key])
                        for key in ("title", "url", "discussion_url")
                    ),
                    f"story slot {index + 1}: title, original and discussion links",
                )
            if valid:
                sources = json.dumps(snapshot, ensure_ascii=False, indent=2)
    evidence = paths["verifier_logs"] / "judge-evidence"
    evidence.mkdir(exist_ok=True)
    if report is not None:
        (evidence / "report.md").write_bytes(content.encode("utf-8"))
    if sources is not None:
        (evidence / "sources.md").write_text(sources, encoding="utf-8")
    if len(checks) != len(declared) or {check["id"] for check in checks} != set(
        declared
    ):
        raise ValueError("Trend Digest check declarations do not match implementation")
    return checks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    context = json.loads(args.context.read_text(encoding="utf-8"))
    config = json.loads(
        (Path(__file__).parent / "grader.json").read_text(encoding="utf-8")
    )
    now = (
        parse_utc(os.environ["PBENCH_TREND_NOW"])
        if "PBENCH_TREND_NOW" in os.environ
        else datetime.now(timezone.utc)
    )
    args.output.write_text(
        json.dumps(
            {"checks": check_outputs(context, config, now=now)}, ensure_ascii=True
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
