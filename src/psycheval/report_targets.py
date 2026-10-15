"""Resolve report associations against complete workspace metadata, without bodies."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from psycheval.state.jobs import managed_config, records


class ReportTargets:
    def __init__(
        self,
        workspace: Path,
        config: Any,
        rows: list[dict[str, Any]],
        *,
        job_refs: Iterable[str] = (),
    ) -> None:
        self.items: dict[tuple[str, str], dict[str, Any]] = {}
        self.session_refs: dict[str, str] = {}
        self.ref_keys: dict[str, str] = {}
        self.owners: dict[str, list[tuple[str, str]]] = {}
        self.job_aliases: dict[str, str] = {}
        for dataset in config.harbor_datasets:
            self.add("dataset", dataset.id, dataset.id)
        managed_paths: dict[Path, str] = {}
        for _, state in records(workspace):
            key = "managed:" + state["id"]
            self.add("job", key, f"{state['job_name']} · {state['id'][:8]}")
            if state["harness"] == "harbor":
                managed_paths[(workspace / "jobs" / state["job_name"]).resolve()] = key
        mounts = {
            mount.id: Path(mount.path).resolve()
            for mount in managed_config(config, workspace).harbor_mounts
        }
        for mount_id, root in mounts.items():
            for path, key in managed_paths.items():
                if path.parent == root:
                    self.job_aliases[f"harbor:{mount_id}/{path.name}"] = key

        def external_job(mount_id: str, job_name: str) -> str:
            external_key = f"harbor:{mount_id}/{job_name}"
            key = self.job_aliases.get(external_key, external_key)
            self.job_aliases[external_key] = key
            if key == external_key:
                root = mounts.get(mount_id)
                safe_name = (
                    bool(job_name)
                    and job_name not in {".", ".."}
                    and Path(job_name).name == job_name
                    and not any(char in job_name for char in "/\\\0")
                )
                self.add(
                    "job",
                    key,
                    f"{job_name} · {mount_id}",
                    available=safe_name
                    and root is not None
                    and (root / job_name).is_dir()
                    and not (root / job_name).is_symlink(),
                )
            return key

        for ref in job_refs:
            if ref.startswith("harbor:") and "/" in ref:
                external_job(*ref.removeprefix("harbor:").split("/", 1))
        for row in rows:
            key = str(row.get("source_key") or "")
            source_ref = str(row.get("source_ref") or row.get("artifact_dir") or "")
            if not key or not source_ref:
                continue
            available = bool(row.get("readable", row.get("last_status") != "missing"))
            label = str(
                row.get("source_alias")
                or row.get("display_alias")
                or row.get("task_name")
                or row.get("trial_session_id")
                or key
            )
            self.add("session", key, label, available=available)
            self.session_refs[key] = source_ref
            self.ref_keys[source_ref] = key
            owners: list[tuple[str, str]] = []
            dataset_id = str(row.get("dataset_id") or "")
            if dataset_id:
                owners.append(("dataset", dataset_id))
            parts = source_ref.split("/")
            job_key = ""
            if parts[0] == "harbor" and len(parts) >= 4:
                mount_id, job_name = parts[1:3]
                job_key = external_job(mount_id, job_name)
            elif len(parts) == 5 and parts[:2] == ["runs", "jobs"]:
                job_key = "managed:" + parts[3]
            if job_key:
                owners.append(("job", job_key))
            self.owners[key] = owners

    def add(self, kind: str, key: str, label: str, *, available: bool = True) -> None:
        self.items[kind, key] = {
            "kind": kind,
            "key": key,
            "label": label,
            "available": available,
        }

    def resolve(self, kind: str, key: str) -> dict[str, Any]:
        if kind == "job":
            key = self.job_aliases.get(key, key)
        return dict(
            self.items.get(
                (kind, key),
                {"kind": kind, "key": key, "label": key, "available": False},
            )
        )

    def session_key(self, source_ref: str) -> str:
        key = self.ref_keys.get(source_ref)
        if key is None:
            key = "missing:" + hashlib.sha256(source_ref.encode("utf-8")).hexdigest()
            self.session_refs[key] = source_ref
            self.add("session", key, source_ref.rsplit("/", 1)[-1], available=False)
        return key

    def bindings(self, state: dict[str, list[str]]) -> list[dict[str, Any]]:
        refs = [("session", self.session_key(ref)) for ref in state["source_refs"]]
        refs += [("dataset", key) for key in state["dataset_ids"]]
        refs += [("job", key) for key in state["job_refs"]]
        result = {
            (item["kind"], item["key"]): item
            for kind, key in refs
            for item in [self.resolve(kind, key)]
        }
        return list(result.values())

    def associations(
        self, source_keys: list[str], bindings: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        result: dict[tuple[str, str], dict[str, Any]] = {}

        def append(target: dict[str, Any], origin: str) -> None:
            item = result.setdefault(
                (target["kind"], target["key"]), {**target, "origins": []}
            )
            if origin not in item["origins"]:
                item["origins"].append(origin)

        for key in source_keys:
            append(self.resolve("session", key), "source")
        for target in bindings:
            append(target, "manual")
        for item in list(result.values()):
            if item["kind"] == "session":
                for kind, key in self.owners.get(item["key"], []):
                    append(self.resolve(kind, key), "inherited")
        return list(result.values())
