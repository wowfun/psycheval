"""Static Task input facts; never materialize a workspace or execute Task code."""

from __future__ import annotations

import gzip
import io
import tarfile
from pathlib import Path, PurePosixPath

from .host_files import (
    _WORKBUDDY_ARCHIVE_ENTRY_LIMIT,
    _WORKBUDDY_ARCHIVE_FILE_LIMIT,
    _WORKBUDDY_ARCHIVE_TOTAL_LIMIT,
)
from .tasks import load_harbor_task_config


def _archive_files(content: bytes) -> list[dict]:
    files, seen, total = [], set(), 0

    class BoundedArchive:
        def __init__(self, stream):
            self.stream, self.remaining = stream, _WORKBUDDY_ARCHIVE_TOTAL_LIMIT

        def read(self, size=-1):
            value = self.stream.read(
                min(size, self.remaining + 1) if size >= 0 else self.remaining + 1
            )
            self.remaining -= len(value)
            if self.remaining < 0:
                raise ValueError("Workspace archive exceeds input inspection limits")
            return value

    with (
        gzip.GzipFile(fileobj=io.BytesIO(content)) as stream,
        tarfile.open(fileobj=BoundedArchive(stream), mode="r|") as archive,
    ):
        for index, member in enumerate(archive, 1):
            if index > _WORKBUDDY_ARCHIVE_ENTRY_LIMIT:
                raise ValueError("Workspace archive has too many entries")
            if member.isdir() and member.name in {".", "./"}:
                continue
            path = PurePosixPath(member.name)
            if (
                path.is_absolute()
                or not path.parts
                or "\\" in member.name
                or ":" in member.name
                or any(
                    part in {"..", ".git"} or part.endswith((" ", "."))
                    for part in path.parts
                )
                or not (member.isdir() or member.isfile())
            ):
                raise ValueError("Workspace archive has unsafe entries")
            if member.isdir():
                continue
            if path in seen:
                raise ValueError("Workspace archive has duplicate file paths")
            seen.add(path)
            total += member.size
            if (
                member.size < 0
                or member.size > _WORKBUDDY_ARCHIVE_FILE_LIMIT
                or total > _WORKBUDDY_ARCHIVE_TOTAL_LIMIT
            ):
                raise ValueError("Workspace archive exceeds input inspection limits")
            files.append({"name": path.as_posix(), "size": member.size})
    return files


def task_resource_inventory(
    task_dir: Path, *, read_bytes, tree, format="harbor", layout=None
) -> dict:
    result = {
        "skill_count": None,
        "input_file_count": None,
        "has_prepare": None,
        "resources": {"skills": [], "files": [], "prepare": []},
        "resource_diagnostics": [],
    }
    try:
        config = load_harbor_task_config(
            task_dir, read_bytes=lambda path: read_bytes(path, 2 * 1024 * 1024)
        ).config
        skills_dir = config.environment.skills_dir
        if not skills_dir:
            result["skill_count"] = 0
        files = [item for item in tree if item["kind"] == "file"]
        paths = {item["path"] for item in files}
        prepare = "environment/prepare.py"
        result["has_prepare"] = format != "workbuddy.v1" and prepare in paths
        if result["has_prepare"]:
            result["resources"]["prepare"] = [{"name": prepare, "path": prepare}]
        archive_path = (
            (layout or {}).get("workspace_archive")
            if format == "workbuddy.v1"
            else None
        )
        if (
            not archive_path
            and format == "workbuddy.v1"
            and "environment/workspace.tar.gz" in paths
        ):
            archive_path = "environment/workspace.tar.gz"
        if archive_path:
            archive_path = str(archive_path)
            if archive_path not in paths:
                raise ValueError("Declared workspace archive is unavailable")
            entries = [
                {**item, "archive": archive_path}
                for item in _archive_files(
                    read_bytes(task_dir / archive_path, _WORKBUDDY_ARCHIVE_TOTAL_LIMIT)
                )
            ]
        elif format == "workbuddy.v1":
            raise ValueError(
                "Workspace inputs cannot be determined without a declared archive"
            )
        else:
            entries = [
                {
                    "name": item["path"][len("environment/data/") :],
                    "path": item["path"],
                    "size": item["size"],
                }
                for item in files
                if item["path"].startswith("environment/data/")
            ]
        skills_relative = None
        if skills_dir:
            workdir = PurePosixPath(
                config.environment.workdir
                or ("/workspace" if format == "workbuddy.v1" else "/app")
            )
            skills = PurePosixPath(skills_dir)
            if not skills.is_absolute():
                skills = workdir / skills
            try:
                skills_relative = skills.relative_to(workdir)
                if ".." in skills_relative.parts:
                    raise ValueError
            except ValueError:
                skills_relative = None
                result["resource_diagnostics"].append(
                    "Skills directory is outside the statically available Task inputs"
                )
        skill_entries, input_entries = [], []
        for item in entries:
            path = PurePosixPath(item["name"])
            is_skill = skills_relative is not None and path.is_relative_to(
                skills_relative
            )
            if is_skill:
                if path.name == "SKILL.md":
                    skill_entries.append({**item, "name": path.parent.as_posix()})
            else:
                input_entries.append(item)
        result["resources"]["skills"] = skill_entries
        result["resources"]["files"] = input_entries
        result["skill_count"] = (
            len(skill_entries)
            if not skills_dir or skills_relative is not None
            else None
        )
        if skills_dir and not skill_entries and result["has_prepare"]:
            result["skill_count"] = None
            result["resource_diagnostics"].append(
                "Skills may be created by preparation; no static Skill packages are available"
            )
        result["input_file_count"] = len(input_entries)
    except (OSError, EOFError, ValueError, tarfile.TarError) as exc:
        result["resource_diagnostics"].append(str(exc).replace(str(task_dir), "<task>"))
    return result


def task_totals(tasks: list[dict]) -> dict:
    result = {"task_count": len(tasks)}
    for field in ("rule_count", "rubric_count", "scoring_item_count"):
        missing = sum(task.get(field) is None for task in tasks)
        result[field] = None if missing else sum(task[field] for task in tasks)
        result[f"missing_{field}"] = missing
    return result
