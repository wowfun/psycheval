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

from psycheval.harbor.documents import inspect_document
from psycheval.harbor.evidence import EvidenceLimitError, EvidenceWriter, SourceSnapshot
from psycheval.harbor.verifier import ObservationIndex

GITHUB_URL = "https://github.com/trending?since=weekly"
HN_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
_LITERAL = r"""(?:"([^"\r\n]+)"|'([^'\r\n]+)'|([^\s;&|<>]+))"""
_READ_TOOLS = [
    "*read*",
    "*exec*",
    "*terminal*",
    "*shell*",
    "bash",
    "pwsh",
]
_EVIDENCE_BYTES = 1024 * 1024


def _source_evidence(observations, max_bytes, *, source_url=GITHUB_URL):
    """Retain complete distinct bodies and every provenance within one budget."""
    prefix = f"Source: {source_url}"
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


def _node_paths(command, cwd, method):
    literal = r"""(?:"([^"\r\n]+)"|'([^'\r\n]+)')"""
    call = rf"\b{re.escape(method)}\s*\(\s*"
    end = r"\s*(?=,|\))"
    paths = {
        _path(_literal(match), cwd)
        for match in re.finditer(call + literal + end, command)
    }
    for match in re.finditer(
        call + rf"process\.env\.([A-Za-z_]\w*)\s*\+\s*{literal}" + end,
        command,
    ):
        suffix = next(value for value in match.groups()[1:] if value is not None)
        paths.add(_path(f"$env:{match[1]}{suffix}", cwd))
    return paths - {None}


def _download_paths(arguments, cwd):
    command = _command(arguments)
    if not cwd:
        return set()
    paths = (
        _node_paths(command, cwd, "fs.writeFileSync")
        if re.search(r"\bfetch\s*\(", command)
        else set()
    )
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
        return paths
    return paths | {
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
        rf"\b(?:cat|Get-Content|type)\s+(?:(?:-LiteralPath|-Path)\s+)?{_LITERAL}",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, command):
            paths.add(_path(_literal(match), cwd))
    paths.update(_node_paths(command, cwd, "readFileSync"))
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


def _argument_url(value, url):
    if isinstance(value, str):
        return _contains_normalized_value(normalize(value), url)
    if isinstance(value, dict):
        return any(_argument_url(item, url) for item in value.values())
    if isinstance(value, list):
        return any(_argument_url(item, url) for item in value)
    return False


def hn_supporting_sources(index, workdir, stories):
    tools = [
        "*fetch*",
        "*browse*",
        "*web*",
        "*crawl*",
        "*http*",
        "*exec*",
        "*terminal*",
        "*shell*",
        "bash",
        "pwsh",
    ]
    for story in stories:
        for kind, key in (("original", "url"), ("discussion", "discussion_url")):
            url = story[key]
            rule = {"any": [{"tool_names": tools, "argument_terms": [url]}]}
            fetch_ids = {
                call.tool_call_id
                for call in index.calls
                if _argument_url(call.arguments, url)
            }
            observations = list(
                github_sources(index, rule, workdir, fetch_ids=fetch_ids)
            )
            provenance = (
                f"Story rank: {story['rank']}\nStory ID: {story['id']}\n"
                f"Source kind: {kind}\nSource URL: {url}"
            )
            if not observations:
                yield (
                    provenance,
                    "No retained successful source observation. Only snapshot metadata is available for this source.",
                )
            for fetch_id, read_id, text in observations:
                yield (
                    f"{provenance}\nFetch call: {fetch_id}\nEvidence call: {read_id}",
                    text,
                )
        repository = re.fullmatch(
            r"https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/?",
            story["url"],
            flags=re.IGNORECASE,
        )
        if repository:
            for provenance, text in github_supporting_sources(
                index,
                {"any": [{"tool_names": tools}]},
                workdir,
                [f"https://github.com/{repository[1]}"],
            ):
                yield (
                    f"Story rank: {story['rank']}\nStory ID: {story['id']}\n"
                    f"Source kind: repository_support\nStory URL: {story['url']}\n{provenance}",
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
    if isinstance(rows, dict):
        arrays = [value for value in rows.values() if isinstance(value, list)]
        if len(arrays) != 1 or any(isinstance(value, dict) for value in rows.values()):
            return []
        if "total" in rows and (
            type(rows["total"]) is not int or rows["total"] < len(arrays[0])
        ):
            return []
        rows = arrays[0]
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


def _snapshot(path: Path, root: Path, *, limit_mib: int = 4) -> SourceSnapshot:
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
    return SourceSnapshot.read(path, max_bytes=limit_mib * 1024 * 1024)


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


def _item_units(body, identity):
    """Read independent Markdown sections/list entries/table rows, not global hits."""
    report = inspect_document(
        SourceSnapshot(Path("report.md"), body.encode()), format="md"
    )
    lines = report.text.splitlines()
    units = []
    headings = []
    for block in report.blocks:
        if block.kind == "heading":
            match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", lines[block.start_line])
            if match:
                headings.append((block.start_line, len(match[1]), match[2]))
    for position, (start, level, label) in enumerate(headings):
        if level == 1:
            continue
        end = next(
            (n for n, depth, _ in headings[position + 1 :] if depth <= level),
            len(lines),
        )
        text = "\n".join(lines[start:end])
        ranked = re.match(r"\s*(?:第\s*)?\d{1,2}\s*(?:[.)、：:]|名|位|\s)", label)
        if ranked or len(identity(text)) == 1:
            if not any(left <= start and end <= right for left, right, _ in units):
                units.append((start, end, text))
    for block in report.blocks:
        if any(left <= block.start_line < right for left, right, _ in units):
            continue
        if block.table is not None:
            rows = {}
            for cell in block.table.cells:
                if cell.row_span != 1 or cell.column_span != 1:
                    rows = {}
                    break
                rows.setdefault(cell.row, {})[cell.column] = " ".join(
                    p.text for p in cell.blocks if hasattr(p, "text")
                )
            ordered = [row for _, row in sorted(rows.items())]
            if len(ordered) < 2:
                continue
            headers = ordered[0]
            entries = [
                "\n".join(
                    f"{headers.get(column, '')}: {value}"
                    for column, value in sorted(row.items())
                )
                for row in ordered[1:]
            ]
            if any(identity(text) for text in entries):
                units.extend(
                    (block.start_line, block.end_line, text) for text in entries
                )
        elif block.kind == "ordered_list":
            starts = [
                index
                for index in range(block.start_line, block.end_line)
                if re.match(r"^ {0,3}\d+[.)]\s+", lines[index])
            ]
            entries = [
                (
                    start,
                    starts[index + 1] if index + 1 < len(starts) else block.end_line,
                )
                for index, start in enumerate(starts)
            ]
            if any(identity("\n".join(lines[start:end])) for start, end in entries):
                units.extend(
                    (start, end, "\n".join(lines[start:end])) for start, end in entries
                )
    return sorted(units, key=lambda item: item[0])


def _github_identities(text):
    return {
        url.rstrip(".,").casefold()
        for url in re.findall(
            r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", text, re.IGNORECASE
        )
    }


def _hn_identities(text):
    return set(re.findall(r"https://news\.ycombinator\.com/item\?id=\d+", text))


def _metric_in_item(text, value, labels):
    if type(value) is not int or value < 0:
        return False
    number = rf"(?<![\d]){value:,}(?![\d])|(?<![\d]){value}(?![\d])"
    emphasis = r"(?:\*\*|__|`)?"
    after_label = rf"\s*[)）]?\s*{emphasis}\s*[：:=]?\s*{emphasis}\s*"
    return bool(
        re.search(
            rf"(?:{labels}){after_label}(?:{number})|(?:{number})\s*{emphasis}\s*(?:{labels})",
            text,
            flags=re.IGNORECASE,
        )
    )


def check_outputs(context: dict, config: dict, *, now: datetime) -> list[dict]:
    platform = context["harbor"]["verifier"]["step_name"]
    if platform not in {"github", "x", "hacker-news"}:
        raise ValueError("Trend Digest requires a known current step_name")
    paths = {
        name: Path(path) for name, path in context["paths"].items() if path is not None
    }
    declared = config["custom_checks"]
    checks = []

    def check(name, passed, evidence):
        checks.append({"id": name, "passed": bool(passed), "evidence": evidence})

    entries = list(paths["artifacts"].iterdir()) if paths["artifacts"].is_dir() else []
    content = ""
    report_snapshot = source_snapshot = trajectory_snapshot = None
    report = entries[0] if len(entries) == 1 else None
    if report is not None:
        try:
            report_snapshot = _snapshot(report, paths["artifacts"])
            content = report_snapshot.content.decode("utf-8")
        except (OSError, ValueError):
            report = None
    meta, body = _parse_report(content)
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
        bool(re.search(r"[\u4e00-\u9fff]", body)),
        "Chinese body text is present; semantic quality is Judge-owned",
    )
    check(
        "report_current",
        _current(report_time, now),
        "report time within one hour, with five-minute future tolerance",
    )
    sources = sources_problem = None
    supporting = supporting_problem = None
    successful_sources = None
    if platform == "github":
        trajectory_snapshot = _snapshot(
            paths["agent_logs"] / "trajectory.json", paths["agent_logs"], limit_mib=128
        )
        trajectory = Trajectory(**json.loads(trajectory_snapshot.content))
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
        units = _item_units(body, _github_identities)
        identity_counts = Counter(
            url for _, _, text in units for url in _github_identities(text)
        )
        for index in range(10):
            url = repositories[index] if index < len(repositories) else ""
            unit = units[index][2] if index < len(units) else ""
            check(
                f"github_repository_{index + 1:02}",
                bool(url)
                and len(units) == 10
                and _github_identities(unit) == {url.casefold()}
                and identity_counts[url.casefold()] == 1,
                f"source rank {index + 1}: {url or 'missing'}; independent report units={len(units)}",
            )
    else:
        try:
            source_snapshot = _snapshot(
                paths["workdir"] / f".trend-digest/{platform}.json", paths["workdir"]
            )
            snapshot = json.loads(source_snapshot.content)
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
            account_counts = Counter(
                str(account.get("handle", "")).casefold()
                for account in accounts
                if isinstance(account, dict)
            )
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
                posts_valid = (
                    isinstance(posts, list)
                    and len(
                        {
                            post.get("url")
                            for post in posts
                            if isinstance(post, dict)
                            and isinstance(post.get("url"), str)
                        }
                    )
                    == len(posts)
                    and all(
                        isinstance(post, dict)
                        and isinstance(post.get("text"), str)
                        and bool(post["text"].strip())
                        and _url(post.get("url"))
                        and _time(post.get("published_at"))
                        and window
                        and start <= _time(post["published_at"]) <= end
                        for post in posts
                    )
                )
                account_valid = (
                    account_counts[handle] == 1
                    and posts_valid
                    and (
                        (status == "success" and bool(posts))
                        or (status in {"no_updates", "fetch_failed"} and not posts)
                    )
                )
                valid = bool(valid and account_valid)
                section_matches = list(
                    re.finditer(
                        rf"^##[^\n]*@{re.escape(handle)}(?![A-Za-z0-9_])[^\n]*\n(.*?)(?=\n##|\Z)",
                        content,
                        flags=re.IGNORECASE | re.DOTALL | re.MULTILINE,
                    )
                )
                section = section_matches[0][1] if len(section_matches) == 1 else ""
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
                    account_valid
                    and status_text
                    and status_text in section
                    and len(section_matches) == 1,
                    f"@{handle}: report explains {status}",
                )
                check(
                    f"x_posts_{handle}",
                    account_valid
                    and status != "fetch_failed"
                    and len(section_matches) == 1
                    and set(
                        re.findall(
                            r"https://(?:x|twitter)\.com/[A-Za-z0-9_]+/status/\d+",
                            section,
                        )
                    )
                    == {post["url"] for post in posts}
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
                successful = [
                    account
                    for account in validated
                    if account["status"] in {"success", "no_updates"}
                ]
                if successful:
                    successful_sources = json.dumps(
                        {**snapshot, "accounts": successful},
                        ensure_ascii=False,
                        indent=2,
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
            valid = (
                valid
                and len(
                    {
                        story.get("id")
                        for story in stories
                        if isinstance(story, dict) and type(story.get("id")) is int
                    }
                )
                == len(stories)
                and all(
                    isinstance(story, dict)
                    and type(story.get("rank")) is int
                    and story["rank"] == index
                    and isinstance(story.get("title"), str)
                    and bool(story["title"].strip())
                    and type(story.get("id")) is int
                    and all(
                        type(story.get(field)) is int and story[field] >= 0
                        for field in ("score", "comment_count")
                    )
                    and _url(story.get("url"))
                    and story.get("discussion_url")
                    == f"https://news.ycombinator.com/item?id={story['id']}"
                    for index, story in enumerate(stories, 1)
                )
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
            units = _item_units(body, _hn_identities)
            identity_counts = Counter(
                url for _, _, text in units for url in _hn_identities(text)
            )
            for index in range(12):
                story = (
                    stories[index]
                    if index < len(stories) and isinstance(stories[index], dict)
                    else {}
                )
                check(
                    f"hn_story_{index + 1:02}",
                    bool(valid)
                    and len(units) == 12
                    and index < len(units)
                    and _hn_identities(units[index][2]) == {story.get("discussion_url")}
                    and identity_counts[story.get("discussion_url")] == 1
                    and _metric_in_item(
                        units[index][2],
                        story.get("score"),
                        r"score|points?|得分|积分|分数|赞",
                    )
                    and _metric_in_item(
                        units[index][2],
                        story.get("comment_count"),
                        r"comment_count|comments?|评论数?|讨论数?",
                    )
                    and all(
                        isinstance(story.get(key), str)
                        and _contains_normalized_value(
                            normalize(units[index][2]), story[key]
                        )
                        for key in ("title", "url", "discussion_url")
                    ),
                    f"story slot {index + 1}: title, original and discussion links",
                )
            if valid:
                sources = json.dumps(snapshot, ensure_ascii=False, indent=2)
                try:
                    trajectory_snapshot = _snapshot(
                        paths["agent_logs"] / "trajectory.json",
                        paths["agent_logs"],
                        limit_mib=128,
                    )
                    trajectory = Trajectory(**json.loads(trajectory_snapshot.content))
                    index = ObservationIndex(
                        trajectory.model_copy(
                            update={
                                "steps": [
                                    step
                                    for step in trajectory.steps
                                    if step.source == "agent"
                                    and not step.is_copied_context
                                ]
                            }
                        )
                    )
                    supporting = _source_evidence(
                        hn_supporting_sources(index, paths["workdir"], stories),
                        _EVIDENCE_BYTES,
                        source_url=HN_URL,
                    )
                except EvidenceLimitError as error:
                    supporting_problem = str(error)
                except (OSError, ValueError) as error:
                    supporting = f"No usable retained trajectory for supporting observations: {error}"
            else:
                supporting = (
                    "No valid story snapshot for associating supporting observations."
                )
    if len(checks) != len(declared) or {check["id"] for check in checks} != set(
        declared
    ):
        raise ValueError("Trend Digest check declarations do not match implementation")
    remaining = _EVIDENCE_BYTES
    with EvidenceWriter(
        paths["verifier_logs"], max_text_bytes=_EVIDENCE_BYTES
    ) as evidence:
        if report_snapshot is not None:
            evidence.capture("report_file", report_snapshot, max_bytes=4 * 1024 * 1024)
        if trajectory_snapshot is not None:
            evidence.capture(
                "retained_trajectory", trajectory_snapshot, max_bytes=128 * 1024 * 1024
            )
        if source_snapshot is not None:
            evidence.capture(
                "fetch_snapshot", source_snapshot, max_bytes=4 * 1024 * 1024
            )
        texts = [
            ("report", content if report is not None else None),
            ("sources", sources),
        ]
        if platform == "hacker-news":
            texts.append(("supporting_sources", supporting))
        elif platform == "x":
            texts.append(("successful_sources", successful_sources))
        for name, text in texts:
            problem = (
                sources_problem
                if name == "sources"
                else supporting_problem
                if name == "supporting_sources"
                else None
            )
            if problem:
                evidence.unavailable(name, problem, status="error")
            elif text is None:
                evidence.unavailable(
                    name,
                    "No validated successfully fetched X account; substantive-summary evidence is unavailable"
                    if name == "successful_sources"
                    else "No validated current-step evidence",
                )
            elif len(text.encode("utf-8")) > remaining:
                evidence.unavailable(
                    name,
                    f"Complete {name} exceeds remaining {remaining} byte evidence budget",
                    status="error",
                )
            else:
                source_id = (
                    "report_file"
                    if name == "report"
                    else "retained_trajectory"
                    if platform == "github"
                    else "fetch_snapshot"
                )
                if name == "supporting_sources":
                    source_id = (
                        "retained_trajectory"
                        if trajectory_snapshot is not None
                        else None
                    )
                evidence.add_text(name, text, source_id=source_id)
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
