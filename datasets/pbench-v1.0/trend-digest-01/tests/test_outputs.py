"""Fixed deterministic output checks; scoring and publication belong to Harbor."""

from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from itertools import chain
from pathlib import Path
from urllib.parse import urlsplit

from harbor.models.trajectories import Trajectory

from psycheval.harbor.evidence import EvidenceLimitError, EvidenceWriter
from psycheval.harbor.verifier import ObservationIndex

GITHUB_URL = "https://github.com/trending?since=weekly"
HN_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
_LITERAL = r"""(?:"([^"\r\n]+)"|'([^'\r\n]+)'|([^\s;&|<>]+))"""
_READ_TOOLS = ["*read*", "*Read*", "*exec*", "*terminal*", "*shell*", "bash", "Bash"]
_EVIDENCE_BYTES = 1024 * 1024


def _source_evidence(observations, max_bytes):
    """Retain complete distinct bodies and every provenance within one budget."""
    prefix = f"Source: {GITHUB_URL}"
    size = len(prefix.encode("utf-8"))
    bodies = {}
    for provenance, text in observations:
        if len(text) > max_bytes:
            raise EvidenceLimitError(f"Complete sources exceed {max_bytes} byte budget")
        if text not in bodies:
            added = 4 + len(provenance.encode("utf-8")) + len(text.encode("utf-8"))
        elif provenance not in bodies[text]:
            added = 1 + len(provenance.encode("utf-8"))
        else:
            continue
        size += added
        if size > max_bytes:
            raise EvidenceLimitError(f"Complete sources exceed {max_bytes} byte budget")
        bodies.setdefault(text, {})[provenance] = None
    return prefix + "".join(
        "\n\n" + "\n".join(provenance) + "\n\n" + text
        for text, provenance in bodies.items()
    )


def _command(arguments):
    return next(
        (
            arguments[key]
            for key in ("command", "cmd", "code")
            if isinstance(arguments.get(key), str)
        ),
        "",
    )


def _literal(match):
    return next(value for value in match.groups() if value is not None)


def _path(value, cwd):
    """Compare lexical Agent paths without touching or resolving host files."""
    symbolic = re.fullmatch(
        r"\$env:([A-Za-z_]\w*)([/\\].*)?", value or "", re.IGNORECASE
    )
    if symbolic:
        suffix = (symbolic[2] or "").replace("\\", "/").lstrip("/")
        return posixpath.normpath(f"/@env/{symbolic[1]}/{suffix}").casefold()
    if not value or any(char in value for char in "$`%"):
        return None
    value, cwd = value.replace("\\", "/"), cwd.replace("\\", "/")
    result = posixpath.normpath(
        value
        if value.startswith("/") or re.match(r"^[A-Za-z]:/", value)
        else posixpath.join(cwd, value)
    )
    return result.casefold() if re.match(r"^[A-Za-z]:/", result) else result


def _call_cwd(arguments, default):
    cwd = arguments.get("workdir", arguments.get("cwd", default))
    cwd = _path(cwd, default) if isinstance(cwd, str) else None
    change = re.match(
        rf"^\s*(?:cd|Set-Location)\s+(?:(?:-LiteralPath|-Path)\s+)?{_LITERAL}",
        _command(arguments),
        re.IGNORECASE,
    )
    return _path(_literal(change), cwd) if change and cwd else cwd


def _download_paths(arguments, cwd):
    command = _command(arguments)
    if not cwd:
        return set()
    if re.search(r"\bcurl(?:\.exe)?\b", command, re.IGNORECASE):
        option = r"(?:\s-o\s+|\s--output(?:=|\s+))"
    elif re.search(r"\bwget\b", command, re.IGNORECASE):
        option = r"\s-O\s+"
    elif re.search(r"\b(?:Invoke-WebRequest|iwr)\b", command, re.IGNORECASE):
        option = (
            r"(?i:\s-OutFile\s+|\|\s*Out-File\s+"
            r"(?:-Encoding\s+\w+\s+)?(?:-FilePath\s+)?)"
        )
    else:
        return set()
    return {
        path
        for match in re.finditer(option + _LITERAL, command)
        if (path := _path(_literal(match), cwd))
    }


def _read_paths(call, cwd):
    if not cwd:
        return set()
    arguments, paths = call.arguments, set()
    if "read" in call.function_name.casefold():
        for key in ("file_path", "path", "filePath"):
            if isinstance(arguments.get(key), str):
                paths.add(_path(arguments[key], cwd))
    command = _command(arguments)
    patterns = [
        rf"""\bopen\s*\(\s*{_LITERAL}(?=\s*(?:\)|,\s*(?:encoding\s*=|(?:mode\s*=\s*)?['"]r[bt]?['"])))""",
        rf"\bPath\s*\(\s*{_LITERAL}\s*\)\.read_(?:text|bytes)\s*\(",
        rf"\breadFileSync\s*\(\s*{_LITERAL}",
        rf"\b(?:cat|Get-Content|type)\s+(?:(?:-LiteralPath|-Path)\s+)?{_LITERAL}",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, command):
            paths.add(_path(_literal(match), cwd))
    for match in re.finditer(
        rf"\breadFileSync\s*\(\s*process\.env\.([A-Za-z_]\w*)\s*\+\s*{_LITERAL}",
        command,
    ):
        suffix = next(value for value in match.groups()[1:] if value is not None)
        paths.add(_path(f"$env:{match[1]}{suffix}", cwd))
    return paths - {None}


def _observation_body(text):
    # WorkBuddy's shell observation includes an echoed command before stdout.
    if text.startswith("Command: "):
        if "\nStdout: " not in text:
            return ""
        return text.split("\nStdout: ", 1)[1].split("\nStderr:", 1)[0].rstrip("\r\n")
    return text


def github_sources(index, rule, workdir, *, fetch_ids=None):
    """Yield direct fetches or later linked reads, with call provenance."""
    ids = Counter(call.tool_call_id for call in index.calls)
    fetches = {
        call.tool_call_id: observations
        for call, observations in index.matching(rule)
        if fetch_ids is None or call.tool_call_id in fetch_ids
    }
    reads = {
        call.tool_call_id: observations
        for call, observations in index.matching({"any": [{"tool_names": _READ_TOOLS}]})
    }
    downloaded = {}
    for call in index.calls:
        if ids[call.tool_call_id] != 1:
            continue
        direct = fetches.get(call.tool_call_id, ())
        if not direct and (not downloaded or call.tool_call_id not in reads):
            continue
        cwd = _call_cwd(call.arguments, str(workdir))
        if direct:
            for observation in direct:
                yield (
                    call.tool_call_id,
                    call.tool_call_id,
                    _observation_body(observation),
                )
            for path in _download_paths(call.arguments, cwd):
                downloaded[path] = call.tool_call_id
        else:
            linked = _read_paths(call, cwd) & downloaded.keys()
            if linked:
                fetch_id = ", ".join(sorted({downloaded[path] for path in linked}))
                for observation in reads[call.tool_call_id]:
                    yield fetch_id, call.tool_call_id, _observation_body(observation)


def github_supporting_sources(index, rule, workdir, repositories):
    seen = set()
    selected = {
        repository.removeprefix("https://github.com/").casefold(): repository
        for repository in repositories
    }
    by_fetch = {}
    for call in index.calls:
        identities = {
            match[1].casefold()
            for match in re.finditer(
                r"https://(?:github\.com|raw\.githubusercontent\.com)/"
                r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)",
                json.dumps(call.arguments, ensure_ascii=False),
            )
        } & selected.keys()
        if identities:
            by_fetch[call.tool_call_id] = identities
    prefixes = []
    for repository in repositories:
        identity = repository.removeprefix("https://github.com/")
        prefixes.extend(
            [
                f"https://github.com/{identity}",
                f"https://raw.githubusercontent.com/{identity}",
            ]
        )
    supporting_rule = {
        "any": [
            {"tool_names": branch["tool_names"], "argument_terms": [prefix]}
            for branch in rule["any"]
            for prefix in prefixes
        ]
    }
    if not by_fetch:
        return
    for fetch_id, read_id, text in github_sources(
        index, supporting_rule, workdir, fetch_ids=by_fetch
    ):
        if (fetch_id, read_id, text) not in seen:
            seen.add((fetch_id, read_id, text))
            identities = set().union(
                *(by_fetch.get(item, set()) for item in fetch_id.split(", "))
            )
            names = ", ".join(selected[item] for item in selected if item in identities)
            yield (
                f"Repository: {names}\nFetch call: {fetch_id}\n"
                f"Evidence call: {read_id}",
                text,
            )


def _ranked_repositories(text):
    try:
        rows = json.loads(text)
    except ValueError:
        try:
            rows = [
                json.loads(line)
                for line in text.splitlines()
                if line.lstrip().startswith("{")
            ]
        except ValueError:
            return []
    if not isinstance(rows, list) or not rows:
        return []
    names, seen = [], set()
    for rank, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            return []
        identities = set()
        name = None
        for field in ("path", "url", "html_url", "full_name", "repo", "name"):
            value = row.get(field)
            match = (
                re.fullmatch(
                    r"(?:https://github\.com/|/)?([A-Za-z0-9_.-]+)\s*/\s*([A-Za-z0-9_.-]+)/?",
                    value.strip(),
                )
                if isinstance(value, str)
                else None
            )
            if match:
                name = f"{match[1]}/{match[2]}"
                identities.add(name.casefold())
        if (
            type(row.get("rank")) is not int
            or row["rank"] != rank
            or len(identities) != 1
            or name.casefold() in seen
        ):
            return []
        names.append("/" + name)
        seen.add(name.casefold())
    return names


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
    if headings:
        links = headings
    elif re.search(r'"rank"\s*:', observation):
        links = _ranked_repositories(observation)
    else:
        links = re.findall(
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
    sources = sources_problem = None
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
        index = ObservationIndex(
            trajectory.model_copy(
                update={
                    "steps": [
                        step
                        for step in trajectory.steps
                        if step.source == "agent" and not step.is_copied_context
                    ]
                }
            )
        )
        repositories = []
        observations = list(
            github_sources(index, config["required_calls"][0], paths["workdir"])
        )
        for _fetch_id, _read_id, observation in observations:
            candidates = github_repositories(observation)
            if len(candidates) >= 10:
                repositories = candidates[:10]
                break
        if repositories:
            report_bytes = len(content.encode("utf-8")) if report is not None else 0
            available = _EVIDENCE_BYTES - (
                report_bytes if report_bytes <= _EVIDENCE_BYTES else 0
            )
            try:
                sources = _source_evidence(
                    chain(
                        (
                            (f"Fetch call: {fetch_id}\nEvidence call: {read_id}", text)
                            for fetch_id, read_id, text in observations
                        ),
                        github_supporting_sources(
                            index,
                            config["required_calls"][0],
                            paths["workdir"],
                            repositories,
                        ),
                    ),
                    available,
                )
            except EvidenceLimitError as error:
                sources_problem = str(error)
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
    if len(checks) != len(declared) or {check["id"] for check in checks} != set(
        declared
    ):
        raise ValueError("Trend Digest check declarations do not match implementation")
    remaining = _EVIDENCE_BYTES
    with EvidenceWriter(
        paths["verifier_logs"], max_text_bytes=_EVIDENCE_BYTES
    ) as evidence:
        for name, text in (
            ("report", content if report is not None else None),
            ("sources", sources),
        ):
            if name == "sources" and sources_problem:
                evidence.unavailable(name, sources_problem, status="error")
            elif text is None:
                evidence.unavailable(name, "No validated current-step evidence")
            elif len(text.encode("utf-8")) > remaining:
                evidence.unavailable(
                    name,
                    f"Complete {name} exceeds remaining {remaining} byte evidence budget",
                    status="error",
                )
            else:
                evidence.add_text(name, text)
                remaining -= len(text.encode("utf-8"))
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
