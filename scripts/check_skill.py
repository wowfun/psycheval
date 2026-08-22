from __future__ import annotations

import argparse
import re
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESOURCE_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])"
    r"((?:references|scripts)/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+)"
)
OLD_BRAND_RE = re.compile(r"peval[_-]py", re.IGNORECASE)


def frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("SKILL.md must start with YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("SKILL.md frontmatter is not closed") from exc
    values: dict[str, str] = {}
    for line in lines[1:end]:
        key, separator, value = line.partition(":")
        if not separator:
            raise ValueError(f"invalid frontmatter line: {line}")
        values[key.strip()] = value.strip().strip('"')
    return values


def validate(skill_dir: Path) -> list[str]:
    failures: list[str] = []
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        return [f"missing {skill_file}"]
    try:
        values = frontmatter(skill_file)
    except ValueError as exc:
        return [str(exc)]
    name = values.get("name", "")
    description = values.get("description", "")
    if name != skill_dir.name or not NAME_RE.fullmatch(name):
        failures.append("frontmatter name must equal the kebab-case directory name")
    if not description or "<" in description or ">" in description:
        failures.append(
            "frontmatter description must be non-empty and contain no angle brackets"
        )

    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file():
            continue
        if OLD_BRAND_RE.search(path.read_text(encoding="utf-8", errors="replace")):
            failures.append(f"legacy brand in {path.relative_to(skill_dir)}")
        if path.suffix == ".py":
            try:
                compile(path.read_text(encoding="utf-8"), str(path), "exec")
            except SyntaxError as exc:
                failures.append(
                    f"invalid Python in {path.relative_to(skill_dir)}: {exc}"
                )

    skill_text = skill_file.read_text(encoding="utf-8")
    for resource_path in sorted(set(RESOURCE_RE.findall(skill_text))):
        if not (skill_dir / resource_path).is_file():
            failures.append(f"missing referenced skill resource: {resource_path}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a local Agent Skill.")
    parser.add_argument("skill", type=Path)
    args = parser.parse_args()
    failures = validate(args.skill.resolve())
    if failures:
        for failure in failures:
            print(f"skill check: {failure}")
        return 1
    print(f"skill check passed: {args.skill}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
