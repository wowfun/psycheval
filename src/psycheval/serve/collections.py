"""Role-aware Dataset/Job tables and workspace collection mutations."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from psycheval.jobs.storage import read_object, safe_path
from psycheval.serve.api_access import (
    ADMIN_ACCESS,
    GUEST_ACCESS,
    access,
    mutation_guard,
    require_admin,
    role_for,
)
from psycheval.serve.api_http import ProblemException, json_response, operation_response
from psycheval.serve.api_support import harbor_workspace, writable_runtime
from psycheval.serve.visibility import project_harbor_inventory
from psycheval.state.collections import (
    CollectionConflict,
    CollectionStore,
    directory_identity,
)
from psycheval.state.jobs import managed_config

TERMINAL = {"completed", "failed", "cancelled", "interrupted"}


class NoteWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    note: str
    revision: str


class CollectionRevision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str
    revision: str


class ArchiveWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    archived: StrictBool
    items: list[CollectionRevision] = Field(min_length=1, max_length=1000)


class WorkspaceCollections:
    def __init__(self, runtime):
        self.runtime = runtime
        self.workspace = runtime.store.paths.root
        self.store = CollectionStore(self.workspace)

    def datasets(self, role):
        service = harbor_workspace(self.runtime.store, self.runtime)
        counts = self.runtime.report_library.association_counts()
        items = []
        for dataset in self.runtime.config.harbor_datasets:
            try:
                value = service.task_inventory(dataset.id)["datasets"][0]
                count = len(value["tasks"])
                error = None
            except (ValueError, OSError) as exc:
                value = {
                    "id": dataset.id,
                    "path": dataset.path,
                    "tasks": [],
                    "trash": [],
                }
                count, error = (
                    None,
                    str(exc) if role == "admin" else "Dataset unavailable",
                )
            projected = project_harbor_inventory({"datasets": [value]}, role)[
                "datasets"
            ][0]
            overlay = self.store.read("dataset", Path(dataset.path))
            projected.update(
                note=overlay["note"], collection_revision=overlay["revision"]
            )
            projected.update(
                {
                    "task_count": count,
                    "error": error,
                    "report_count": counts.get(("dataset", dataset.id), 0),
                }
            )
            if role == "admin":
                projected["mount_ids"] = [
                    m.id
                    for m in self.runtime.config.harbor_mounts
                    if dataset.id in m.dataset_ids
                ]
            else:
                for field in ("collection_revision",):
                    projected.pop(field, None)
            items.append(projected)
        return {"datasets": items}

    def _jobs(self, *, runs=None):
        result = {}
        for run in self.runtime.jobs.list() if runs is None else runs:
            name = run.get("job_name")
            path = safe_path(self.workspace, "jobs", name) if name else None
            result[directory_identity(path) if path else run["id"]] = {
                "id": self.store.key(path) if path else "managed:" + run["id"],
                "name": name or run["id"],
                "path": str(path) if path else None,
                "run_id": run["id"],
                "report_ref": "managed:" + run["id"],
                "harness": run.get("harness", "harbor"),
                "state": run["state"],
                "mount_ids": [],
                "job_refs": [],
                "ended": path is not None and run["state"] in TERMINAL,
            }
        effective = managed_config(self.runtime.config, self.workspace)
        for mount in effective.harbor_mounts:
            root = safe_path(Path(mount.path))
            if not root.is_dir():
                continue
            for path in sorted(root.iterdir()):
                # Do not follow linked entries, even merely to count their Trials.
                try:
                    safe_path(root, path.name)
                except ValueError:
                    continue
                if not path.is_dir():
                    continue
                key = directory_identity(path)
                value = result.setdefault(
                    key,
                    {
                        "id": self.store.key(path),
                        "name": path.name,
                        "path": str(path),
                        "run_id": None,
                        "report_ref": f"harbor:{mount.id}/{path.name}",
                        "harness": "harbor",
                        "state": "unknown",
                        "ended": False,
                        "mount_ids": [],
                        "job_refs": [],
                    },
                )
                value["mount_ids"].append(mount.id)
                value["job_refs"].append(f"harbor/{mount.id}/{path.name}/")
                if value["run_id"] is None:
                    try:
                        native = read_object(path / "result.json", {})
                        finished = native.get("finished_at")
                        if isinstance(finished, str):
                            datetime.fromisoformat(finished.replace("Z", "+00:00"))
                            value.update(state="completed", ended=True)
                        elif native.get("started_at"):
                            value["state"] = "unfinished"
                    except (ValueError, OSError):
                        pass
        return list(result.values())

    def resolve(self, kind, identity):
        if kind == "dataset":
            for dataset in self.runtime.config.harbor_datasets:
                if dataset.id == identity:
                    return Path(dataset.path), None
        elif kind == "job":
            for job in self._jobs():
                if job["id"] == identity and job["path"]:
                    return Path(job["path"]), job
        raise ProblemException(404, "Collection not found")

    @staticmethod
    def _trial_groups(rows):
        groups = {}
        for row in rows:
            parts = row["source_ref"].split("/")
            if parts[0] == "harbor" and len(parts) >= 4:
                prefix = "/".join(parts[:3]) + "/"
            elif parts[:2] == ["runs", "jobs"] and len(parts) >= 5:
                prefix = "/".join(parts[:4]) + "/"
            else:
                continue
            groups.setdefault(prefix, []).append(row)
        return groups

    def _trials(self, job, groups):
        found = {}
        prefixes = job["job_refs"]
        if job["run_id"]:
            prefixes = [*prefixes, f"runs/jobs/{job['harness']}/{job['run_id']}/"]
        for prefix in prefixes:
            for row in groups.get(prefix, ()):
                parts = row["source_ref"].split("/")
                key = parts[3] if parts[0] == "harbor" else row["source_ref"]
                is_root = parts[0] != "harbor" or len(parts) == 4
                if key not in found or is_root:
                    found[key] = row
        return list(found.values())

    def jobs(self, role, state="active", *, runs=None):
        rows = self.runtime.catalog.collection_rows()
        counts = self.runtime.report_library.association_counts(rows)
        groups = self._trial_groups(rows)
        items = []
        for job in self._jobs(runs=runs):
            overlay = (
                self.store.read("job", Path(job["path"]))
                if job["path"]
                else {
                    "archived": False,
                    "trial_count": 0,
                    "note": "",
                    "revision": None,
                }
            )
            archived = overlay["archived"]
            if (
                role != "admin"
                and archived
                or state == "active"
                and archived
                or state == "archived"
                and not archived
            ):
                continue
            count = (
                overlay["trial_count"] if archived else len(self._trials(job, groups))
            )
            if not archived and job["path"] and not Path(job["path"]).is_dir():
                count = None
            value = {
                **job,
                **overlay,
                "trial_count": count,
                "count_retained": archived,
                "report_count": counts.get(("job", job["report_ref"]), 0),
                "can_archive": job["ended"],
            }
            value["collection_revision"] = value.pop("revision")
            value.pop("job_refs")
            value.pop("ended")
            if role != "admin":
                for field in (
                    "path",
                    "mount_ids",
                    "collection_revision",
                    "archived",
                    "can_archive",
                ):
                    value.pop(field, None)
            items.append(value)
        return {"items": sorted(items, key=lambda row: row["name"], reverse=True)}

    def detail(self, identity, role, offset):
        _path, job = self.resolve("job", identity)
        if self.store.archived(_path) and role != "admin":
            raise ProblemException(404, "Collection not found")
        trials = self._trials(
            job, self._trial_groups(self.runtime.catalog.collection_rows())
        )
        return {
            "name": job["name"],
            "state": job["state"],
            "run_id": job["run_id"],
            "results": [
                {k: v for k, v in row.items() if k != "source_ref"}
                for row in trials[offset : offset + 50]
            ],
            "result_count": len(trials),
            "result_offset": offset,
        }


def register_collection_routes(app: FastAPI):
    def call(action):
        try:
            return action()
        except CollectionConflict as exc:
            raise ProblemException(409, str(exc)) from exc
        except (ValueError, OSError) as exc:
            raise ProblemException(422, str(exc)) from exc

    @app.get("/api/collections/datasets")
    @access(GUEST_ACCESS)
    def datasets(request: Request):
        return call(
            lambda: json_response(
                WorkspaceCollections(request.app.state.runtime).datasets(
                    role_for(request)
                )
            )
        )

    @app.get("/api/collections/jobs")
    @access(GUEST_ACCESS)
    def jobs(
        request: Request,
        state: str = Query("active", pattern="^(active|archived|all)$"),
    ):
        runtime = request.app.state.runtime
        return call(
            lambda: json_response(
                WorkspaceCollections(runtime).jobs(
                    role_for(request), state, runs=runtime.jobs_list()
                )
            )
        )

    @app.get("/api/collections/jobs/{identity}")
    @access(GUEST_ACCESS)
    def detail(request: Request, identity: str, offset: int = Query(0, ge=0)):
        return call(
            lambda: json_response(
                WorkspaceCollections(request.app.state.runtime).detail(
                    identity, role_for(request), offset
                )
            )
        )

    @app.put(
        "/api/collections/{kind}/{identity}/note",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def note(request: Request, kind: str, identity: str, body: NoteWrite):
        def save():
            service = WorkspaceCollections(request.app.state.runtime)
            path, _job = service.resolve(kind, identity)
            return json_response(
                service.store.save_note(kind, path, body.note, body.revision),
                headers={"X-Peval-Invalidations": "collections"},
            )

        return call(save)

    @app.post(
        "/api/collections/job-state-operations",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def archive(request: Request, body: ArchiveWrite):
        def save():
            runtime = writable_runtime(request)
            service = WorkspaceCollections(runtime)
            snapshot = None

            def action(item):
                nonlocal snapshot
                # Load once inside the operation's catalog writer lease.
                if snapshot is None:
                    snapshot = (
                        {job["id"]: job for job in service._jobs()},
                        service._trial_groups(runtime.catalog.collection_rows()),
                    )
                jobs, groups = snapshot
                job = jobs.get(item["id"])
                if job is None:
                    raise ValueError("Collection not found")
                if body.archived and not job["ended"]:
                    raise CollectionConflict(
                        "Only a Job with verified terminal state can be archived"
                    )
                if job["path"] is None:
                    raise ValueError("Job has no result directory")
                path = Path(job["path"])
                count = (
                    len(service._trials(job, groups))
                    if body.archived and path.is_dir()
                    else None
                )
                return service.store.set_archived(
                    path, body.archived, count, item["revision"]
                )

            operation = runtime.start_operation(
                "job-archive", [item.model_dump() for item in body.items], action
            )
            return operation_response(operation)

        return call(save)
