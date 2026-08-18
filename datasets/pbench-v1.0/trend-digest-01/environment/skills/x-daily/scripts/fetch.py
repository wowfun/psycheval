#!/usr/bin/env python3
"""Fetch rolling 24-hour X posts through Nitter RSS into one JSON snapshot."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree

NITTER_INSTANCES = (
    "https://nitter.net",
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
)
REQUEST_TIMEOUT_SECONDS = 15
USER_AGENT = "psycheval-trend-digest-x/1.0"
_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def parse_utc(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc).replace(microsecond=0)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return [
        "".join(node.text or "" for node in item.findall(f".//{{{_MAIN_NS}}}t"))
        for item in root.findall(f"{{{_MAIN_NS}}}si")
    ]


def _users_sheet_path(archive: zipfile.ZipFile) -> str:
    workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    sheet = next(
        (
            item
            for item in workbook.findall(f".//{{{_MAIN_NS}}}sheet")
            if item.attrib.get("name", "").casefold() == "users"
        ),
        None,
    )
    if sheet is None:
        raise ValueError("workbook must contain a 'users' sheet")
    relation_id = sheet.attrib.get(f"{{{_REL_NS}}}id")
    relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    target = next(
        (
            item.attrib["Target"]
            for item in relationships.findall(f"{{{_PKG_REL_NS}}}Relationship")
            if item.attrib.get("Id") == relation_id
        ),
        None,
    )
    if target is None:
        raise ValueError("users sheet relationship is missing")
    return "xl/" + target.lstrip("/").removeprefix("xl/")


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


def read_users_xlsx(path: Path) -> list[dict[str, str | bool]]:
    with zipfile.ZipFile(path) as archive:
        shared = _shared_strings(archive)
        root = ElementTree.fromstring(archive.read(_users_sheet_path(archive)))
    rows = [
        [_cell_value(cell, shared).strip() for cell in row.findall(f"{{{_MAIN_NS}}}c")]
        for row in root.findall(f".//{{{_MAIN_NS}}}row")
    ]
    if not rows:
        raise ValueError("users sheet is empty")
    headers = [value.casefold() for value in rows[0]]
    required = {"handle", "name", "enabled"}
    if not required.issubset(headers):
        raise ValueError("users sheet must contain handle, name, and enabled columns")
    positions = {name: headers.index(name) for name in required}
    users: list[dict[str, str | bool]] = []
    for row in rows[1:]:
        padded = row + [""] * (len(headers) - len(row))
        handle = padded[positions["handle"]].lstrip("@").strip()
        if not handle:
            continue
        enabled = padded[positions["enabled"]].casefold() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if enabled:
            users.append(
                {
                    "handle": handle,
                    "name": padded[positions["name"]].strip() or handle,
                    "enabled": True,
                }
            )
    if not users:
        raise ValueError("users sheet has no enabled accounts")
    return users


def _http_get(url: str) -> str | None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(
            request, timeout=REQUEST_TIMEOUT_SECONDS
        ) as response:
            return response.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def _strip_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    return re.sub(r"[ \t]+", " ", value).strip()


def parse_rss(value: str, handle: str) -> list[dict[str, str]]:
    root = ElementTree.fromstring(value.lstrip("\ufeff \t\r\n"))
    posts: list[dict[str, str]] = []
    for item in root.findall(".//item"):
        link = (item.findtext("link") or "").strip()
        guid = (item.findtext("guid") or "").strip()
        match = re.search(r"/status/(\d+)", link or guid)
        published = (item.findtext("pubDate") or "").strip()
        if match is None or not published:
            continue
        parsed = parsedate_to_datetime(published)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        post_id = match.group(1)
        posts.append(
            {
                "id": post_id,
                "text": _strip_html(item.findtext("description") or ""),
                "published_at": format_utc(parsed),
                "url": f"https://x.com/{handle}/status/{post_id}",
            }
        )
    return posts


def _fixture_rss(fixture_dir: Path, handle: str, index: int) -> str | None:
    path = fixture_dir / f"{handle}-{index}.xml"
    return path.read_text(encoding="utf-8") if path.is_file() else None


def fetch_account(
    handle: str,
    *,
    fixture_dir: Path | None,
) -> tuple[list[dict[str, str]] | None, str | None]:
    for index, instance in enumerate(NITTER_INSTANCES, start=1):
        value = (
            _fixture_rss(fixture_dir, handle, index)
            if fixture_dir is not None
            else _http_get(f"{instance}/{handle}/rss")
        )
        if value is None:
            continue
        try:
            return parse_rss(value, handle), instance
        except (ElementTree.ParseError, ValueError):
            continue
    return None, None


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def fetch(
    users_path: Path,
    output_path: Path,
    *,
    now: datetime,
    fixture_dir: Path | None = None,
) -> dict[str, object]:
    users = read_users_xlsx(users_path)
    window_start = now - timedelta(hours=24)
    accounts: list[dict[str, object]] = []
    successful_fetches = 0
    for user in users:
        handle = str(user["handle"])
        posts, instance = fetch_account(handle, fixture_dir=fixture_dir)
        if posts is None:
            accounts.append(
                {
                    **user,
                    "status": "fetch_failed",
                    "source_instance": None,
                    "posts": [],
                }
            )
            print(f"[x-daily] @{handle}: fetch_failed", file=sys.stderr)
            continue
        successful_fetches += 1
        filtered = []
        seen: set[str] = set()
        for post in posts:
            published = parse_utc(post["published_at"])
            if window_start <= published <= now and post["id"] not in seen:
                seen.add(post["id"])
                filtered.append(post)
        filtered.sort(key=lambda item: item["published_at"])
        status = "success" if filtered else "no_updates"
        accounts.append(
            {
                **user,
                "status": status,
                "source_instance": instance,
                "posts": filtered,
            }
        )
        print(f"[x-daily] @{handle}: {status} ({len(filtered)} posts)")
    snapshot: dict[str, object] = {
        "schema_version": 1,
        "platform": "x",
        "generated_at": format_utc(now),
        "window_start": format_utc(window_start),
        "window_end": format_utc(now),
        "source": "nitter-rss",
        "accounts": accounts,
    }
    write_json(output_path, snapshot)
    return snapshot | {"successful_fetches": successful_fetches}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--users", type=Path, default=Path("/app/input/x-users.xlsx"))
    parser.add_argument(
        "--output", type=Path, default=Path("/app/.trend-digest/x.json")
    )
    parser.add_argument("--now", help=argparse.SUPPRESS)
    parser.add_argument("--fixture-dir", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    result = fetch(
        args.users,
        args.output,
        now=parse_utc(args.now),
        fixture_dir=args.fixture_dir,
    )
    return 0 if int(result["successful_fetches"]) > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
