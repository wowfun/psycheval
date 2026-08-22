from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
PAIR_MANIFEST = ROOT / "docs/i18n/pairs.json"
REQUIRED_DOCS = {
    "docs/architecture.md",
    "docs/development.md",
    "docs/testing.md",
    "docs/reference/evaluation.md",
    "docs/reference/state-and-data.md",
    "docs/reference/harbor.md",
    "docs/reference/pbench.md",
    "docs/reference/cli.md",
    "docs/reference/workspace.md",
    "docs/user/peval/index.md",
    "docs/user/peval/inputs-and-adapters.md",
    "docs/user/peval/reports.md",
    "docs/user/peval/workspace.md",
    "docs/user/pbench/index.md",
    "docs/user/pbench/authoring.md",
    "docs/user/pbench/scoring.md",
}
PAIRED_SOURCES = {
    "docs/user/peval/index.md",
    "docs/user/peval/inputs-and-adapters.md",
    "docs/user/peval/reports.md",
    "docs/user/peval/workspace.md",
}
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
MARKDOWN = MarkdownIt()


def active_markdown() -> list[Path]:
    roots = [ROOT / "AGENTS.md", ROOT / "README.md"]
    roots.extend((ROOT / "docs").rglob("*.md"))
    roots.extend((ROOT / "skills/peval").rglob("*.md"))
    return sorted({path.resolve() for path in roots if path.is_file()})


def prose_lines(text: str) -> list[str]:
    lines: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        match = FENCE_RE.match(line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker
            elif marker == fence:
                fence = None
            continue
        if fence is None:
            lines.append(line)
    return lines


def heading_slug(value: str) -> str:
    value = re.sub(r"\[(.*?)\]\([^)]+\)", r"\1", value).strip().lower()
    value = value.replace("`", "")
    chars = [
        char
        for char in value
        if char in {" ", "-", "_"}
        or not unicodedata.category(char).startswith(("P", "S"))
    ]
    return re.sub(r"[\s-]+", "-", "".join(chars)).strip("-")


def anchors(path: Path) -> set[str]:
    found: set[str] = set()
    seen: dict[str, int] = {}
    for line in prose_lines(path.read_text(encoding="utf-8")):
        match = HEADING_RE.match(line)
        if not match:
            continue
        base = heading_slug(match.group(1))
        count = seen.get(base, 0)
        seen[base] = count + 1
        found.add(base if count == 0 else f"{base}-{count}")
    return found


def link_failures(paths: list[Path]) -> list[str]:
    failures: list[str] = []
    anchor_cache: dict[Path, set[str]] = {}
    for path in paths:
        tokens = MARKDOWN.parse(path.read_text(encoding="utf-8"))
        raw_targets = [
            href
            for token in tokens
            if token.type == "inline"
            for child in token.children or []
            if child.type == "link_open"
            if (href := child.attrGet("href")) is not None
        ]
        for raw_target in raw_targets:
            target = raw_target.strip().strip("<>")
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            relative, _, fragment = target.partition("#")
            if not relative:
                resolved = path
            else:
                resolved = (path.parent / unquote(relative)).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                failures.append(
                    f"{path.relative_to(ROOT)}: link escapes repository: {target}"
                )
                continue
            if not resolved.is_file():
                failures.append(
                    f"{path.relative_to(ROOT)}: missing link target: {target}"
                )
                continue
            if fragment and resolved.suffix.lower() == ".md":
                available = anchor_cache.setdefault(resolved, anchors(resolved))
                if unquote(fragment).lower() not in available:
                    failures.append(
                        f"{path.relative_to(ROOT)}: missing anchor in {target}"
                    )
    return failures


def load_pairs() -> list[dict[str, str]]:
    payload = json.loads(PAIR_MANIFEST.read_text(encoding="utf-8"))
    pairs = payload.get("pairs")
    if not isinstance(pairs, list) or not all(isinstance(item, dict) for item in pairs):
        raise ValueError("docs/i18n/pairs.json must contain a pairs array")
    return pairs


def source_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_pairs() -> None:
    pairs = load_pairs()
    for pair in pairs:
        source = ROOT / pair["source"]
        pair["source_sha256"] = source_hash(source)
    PAIR_MANIFEST.write_text(
        json.dumps({"pairs": pairs}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def pair_failures() -> list[str]:
    failures: list[str] = []
    try:
        pairs = load_pairs()
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"translation manifest: {exc}"]
    sources = {item.get("source") for item in pairs}
    if sources != PAIRED_SOURCES:
        failures.append(
            "translation manifest does not list exactly the four peval guides"
        )
    translations: set[str] = set()
    for item in pairs:
        source_name = item.get("source")
        translation_name = item.get("translation")
        recorded = item.get("source_sha256")
        if not all(
            isinstance(value, str)
            for value in (source_name, translation_name, recorded)
        ):
            failures.append("translation manifest entry has invalid fields")
            continue
        source = ROOT / source_name
        translation = ROOT / translation_name
        if not source.is_file():
            failures.append(f"missing paired source: {source_name}")
            continue
        if not translation.is_file():
            failures.append(f"missing paired translation: {translation_name}")
            continue
        if translation_name in translations:
            failures.append(f"duplicate paired translation: {translation_name}")
        translations.add(translation_name)
        actual = source_hash(source)
        if recorded != actual:
            failures.append(
                f"stale translation pair: {translation_name}; review it and record hashes"
            )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate active documentation.")
    parser.add_argument(
        "--record-pairs",
        action="store_true",
        help="Record current English source hashes after paired review.",
    )
    args = parser.parse_args()
    if args.record_pairs:
        record_pairs()

    paths = active_markdown()
    failures = [
        f"missing required document: {name}"
        for name in sorted(REQUIRED_DOCS)
        if not (ROOT / name).is_file()
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if "specs/" in text:
            failures.append(
                f"{path.relative_to(ROOT)}: active documentation references specs/"
            )
    failures.extend(link_failures(paths))
    failures.extend(pair_failures())
    if failures:
        for failure in failures:
            print(f"documentation check: {failure}")
        return 1
    print(f"documentation check passed for {len(paths)} Markdown files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
