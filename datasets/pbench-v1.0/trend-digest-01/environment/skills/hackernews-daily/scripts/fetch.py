#!/usr/bin/env python3
"""Fetch current Hacker News top stories into one ordered JSON snapshot."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_BASE = "https://hacker-news.firebaseio.com/v0"
SOURCE_URL = f"{API_BASE}/topstories.json"
REQUEST_TIMEOUT_SECONDS = 15
USER_AGENT = "psycheval-trend-digest-hn/1.0"


def parse_utc(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc).replace(microsecond=0)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _http_json(url: str) -> object | None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(
            request, timeout=REQUEST_TIMEOUT_SECONDS
        ) as response:
            return json.loads(response.read())
    except Exception:
        return None


def _fixture_json(fixture_dir: Path, name: str) -> object | None:
    path = fixture_dir / name
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_topstories(fixture_dir: Path | None) -> object | None:
    if fixture_dir is not None:
        return _fixture_json(fixture_dir, "topstories.json")
    return _http_json(SOURCE_URL)


def _load_item(story_id: int, fixture_dir: Path | None) -> object | None:
    if fixture_dir is not None:
        return _fixture_json(fixture_dir, f"item-{story_id}.json")
    return _http_json(f"{API_BASE}/item/{story_id}.json")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def fetch(
    output_path: Path,
    *,
    limit: int,
    now: datetime,
    fixture_dir: Path | None = None,
) -> dict[str, object]:
    ids = _load_topstories(fixture_dir)
    if not isinstance(ids, list):
        raise RuntimeError("unable to fetch Hacker News topstories")
    stories: list[dict[str, object]] = []
    for story_id in ids:
        if len(stories) >= limit:
            break
        if not isinstance(story_id, int):
            continue
        item = _load_item(story_id, fixture_dir)
        if not isinstance(item, dict):
            continue
        if (
            item.get("type") != "story"
            or item.get("deleted")
            or item.get("dead")
            or not item.get("title")
        ):
            continue
        discussion_url = f"https://news.ycombinator.com/item?id={story_id}"
        stories.append(
            {
                "rank": len(stories) + 1,
                "id": story_id,
                "title": str(item["title"]),
                "url": str(item.get("url") or discussion_url),
                "discussion_url": discussion_url,
                "by": str(item.get("by") or ""),
                "score": int(item.get("score") or 0),
                "comment_count": int(item.get("descendants") or 0),
                "published_at": format_utc(
                    datetime.fromtimestamp(int(item.get("time") or 0), timezone.utc)
                ),
            }
        )
    snapshot: dict[str, object] = {
        "schema_version": 1,
        "platform": "hacker-news",
        "generated_at": format_utc(now),
        "source_url": SOURCE_URL,
        "stories": stories,
    }
    write_json(output_path, snapshot)
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/app/.trend-digest/hacker-news.json"),
    )
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--now", help=argparse.SUPPRESS)
    parser.add_argument("--fixture-dir", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        snapshot = fetch(
            args.output,
            limit=args.limit,
            now=parse_utc(args.now),
            fixture_dir=args.fixture_dir,
        )
    except RuntimeError as error:
        print(f"[hackernews-daily] {error}", file=sys.stderr)
        return 1
    count = len(snapshot["stories"])
    print(f"[hackernews-daily] captured {count}/{args.limit} stories")
    return 0 if count == args.limit else 1


if __name__ == "__main__":
    raise SystemExit(main())
