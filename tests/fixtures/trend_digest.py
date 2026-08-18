"""Pure source, snapshot, and report fixtures for Trend Digest verifier tests."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

GITHUB_URL = "https://github.com/trending?since=weekly"
HN_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
USERS = [
    ("sama", "Sam Altman"),
    ("karpathy", "Andrej Karpathy"),
    ("gdb", "Greg Brockman"),
    ("JeffDean", "Jeff Dean"),
    ("simonw", "Simon Willison"),
    ("_akhaliq", "AK"),
    ("ylecun", "Yann LeCun"),
    ("kaboroeconomics", "Kaboro"),
    ("fchollet", "Francois Chollet"),
    ("aidan_mclau", "Aidan McLau"),
    ("steipete", "Peter Steinberger"),
]


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def report_path(artifacts: Path, platform: str, now: datetime) -> Path:
    return artifacts / f"{platform}-{now.strftime('%Y%m%dT%H%M%SZ')}.md"


def github(artifacts: Path, now: datetime) -> tuple[dict, str, dict]:
    repositories = [
        f"fixture-org-{index}/fixture-repo-{index}" for index in range(1, 11)
    ]
    lines = [
        "---",
        "platform: github",
        f'generated_at: "{format_utc(now)}"',
        f'source: "{GITHUB_URL}"',
        "window: weekly",
        "---",
        "# GitHub 趋势",
    ]
    for rank, repository in enumerate(repositories, start=1):
        lines.extend(
            [
                f"## {rank}. {repository}",
                f"- url: https://github.com/{repository}",
                "- 摘要：这是当前 GitHub weekly 榜单中的趋势仓库。",
            ]
        )
    report_path(artifacts, "github", now).write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    observation = "\n".join(
        f"https://github.com/{repository}" for repository in repositories
    )
    return {"url": GITHUB_URL}, observation, {"repositories": repositories}


def x(workspace: Path, artifacts: Path, now: datetime) -> tuple[dict, str, dict]:
    start = now - timedelta(hours=24)
    accounts = [
        {
            "handle": handle,
            "name": name,
            "enabled": True,
            "status": "no_updates",
            "source_instance": "https://fixture.nitter",
            "posts": [],
        }
        for handle, name in USERS
    ]
    snapshot = {
        "schema_version": 1,
        "platform": "x",
        "generated_at": format_utc(now),
        "window_start": format_utc(start),
        "window_end": format_utc(now),
        "source": "nitter-rss",
        "accounts": accounts,
    }
    snapshot_path = workspace / ".trend-digest" / "x.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "---",
        "platform: x",
        f'generated_at: "{format_utc(now)}"',
        'source: "nitter-rss"',
        f'window_start: "{format_utc(start)}"',
        f'window_end: "{format_utc(now)}"',
        "---",
        "# X 近 24 小时动态",
    ]
    for handle, name in USERS:
        lines.extend(
            [
                f"## {name} (@{handle})",
                "- 状态：近 24 小时无新推文",
                "- 摘要：当前窗口没有可报告的新内容。",
            ]
        )
    report_path(artifacts, "x", now).write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    arguments = {
        "cmd": [
            "python",
            "/app/skills/x-daily/scripts/fetch.py",
            "--users",
            "/app/input/x-users.xlsx",
            "--output",
            "/app/.trend-digest/x.json",
        ]
    }
    return arguments, "x-daily completed", snapshot


def hacker_news(
    workspace: Path, artifacts: Path, now: datetime
) -> tuple[dict, str, dict]:
    stories = []
    for rank in range(1, 13):
        story_id = 1000 + rank
        stories.append(
            {
                "rank": rank,
                "id": story_id,
                "title": f"Fixture Hacker News story {rank}",
                "url": f"https://example.com/story-{rank}",
                "discussion_url": f"https://news.ycombinator.com/item?id={story_id}",
                "by": f"author-{rank}",
                "score": 100 - rank,
                "comment_count": rank,
                "published_at": format_utc(now - timedelta(minutes=rank)),
            }
        )
    snapshot = {
        "schema_version": 1,
        "platform": "hacker-news",
        "generated_at": format_utc(now),
        "source_url": HN_URL,
        "stories": stories,
    }
    snapshot_path = workspace / ".trend-digest" / "hacker-news.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "---",
        "platform: hacker-news",
        f'generated_at: "{format_utc(now)}"',
        f'source: "{HN_URL}"',
        f'snapshot_at: "{format_utc(now)}"',
        "---",
        "# Hacker News 当前热门",
    ]
    for story in stories:
        lines.extend(
            [
                f"## {story['rank']}. {story['title']}",
                f"- url: {story['url']}",
                f"- hn: {story['discussion_url']}",
                "- 摘要：这是当前 Hacker News 热门列表中的条目。",
            ]
        )
    report_path(artifacts, "hacker-news", now).write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    arguments = {
        "cmd": [
            "python",
            "/app/skills/hackernews-daily/scripts/fetch.py",
            "--output",
            "/app/.trend-digest/hacker-news.json",
        ]
    }
    return arguments, "hackernews-daily completed", snapshot
