"""Runtime-owned, single-flight Task discovery; readers use atomic generations."""

from __future__ import annotations

import json
from threading import RLock, Thread

from psycheval.state.task_catalog import TaskCatalog

from .harbor_workspace import HarborNotFoundError, HarborWorkspace, config_revision


class TaskInventory:
    def __init__(self, config_path, config):
        self.config_path, self.config = config_path, config
        self.cache = TaskCatalog(
            config_path.parent / ".cache" / "peval" / "task-catalog.sqlite3"
        )
        self._lock = RLock()
        self._thread = None
        self._epoch = 0
        self._pending = False
        self._closed = False
        self._error = None
        self._mutations = 0
        self._configs = self._config_keys(config)

    @staticmethod
    def _config_keys(config):
        return {
            item.id: json.dumps(item.model_dump(mode="json"), sort_keys=True)
            for item in config.harbor_datasets
        }

    def status(self):
        with self._lock:
            generation = self.cache.generation(self._configs)
            checking = self._thread is not None or bool(self._mutations)
            return {
                "generation": generation,
                "checking": checking,
                "stale": bool(generation and (checking or self._error)),
                "error": self._error,
            }

    def snapshot(self, dataset_id=None):
        with self._lock:
            if dataset_id is not None and dataset_id not in self._configs:
                raise HarborNotFoundError(f"Dataset not found: {dataset_id}")
            value = self.cache.snapshot(self._configs, dataset_id=dataset_id)
            value.update(self.status())
            return value

    def conflict(self, dataset_id, task, revision):
        with self._lock:
            return self.cache.conflict(
                dataset_id, task, self._configs.get(dataset_id), revision
            )

    def configure(self, config):
        with self._lock:
            changed = config.harbor_datasets != self.config.harbor_datasets
            self.config = config
            if changed:
                self._configs = self._config_keys(config)
                self.invalidate()
                self.refresh()

    def invalidate(self):
        with self._lock:
            self._epoch += 1
            self._pending = True

    def begin_mutation(self):
        with self._lock:
            self._mutations += 1
            self.invalidate()

    def end_mutation(self):
        with self._lock:
            self._mutations -= 1
            self.invalidate()
            if not self._mutations:
                self.refresh()

    def refresh(self):
        with self._lock:
            if self._closed:
                return self.status()
            if self._thread is not None or self._mutations:
                return self.status()
            self._pending = False
            self._error = None
            self._thread = Thread(target=self._run, daemon=True, name="task-inventory")
            self._thread.start()
            return self.status()

    def reconcile(self):
        with self._lock:
            if self._mutations or self._closed:
                return
            config, key, epoch = self.config, self._configs, self._epoch
        service = HarborWorkspace(self.config_path, config, task_catalog=self.cache)
        previous = {item["id"]: item for item in self.cache.snapshot(key)["datasets"]}
        datasets = []
        for dataset in config.harbor_datasets:
            try:
                value = service.task_inventory(dataset.id)["datasets"][0]
            except (OSError, ValueError) as exc:
                value = previous.get(
                    dataset.id,
                    {
                        "id": dataset.id,
                        "path": dataset.path,
                        "format": dataset.format,
                        "tasks": [],
                        "trash": [],
                        "task_count": None,
                    },
                )
                value = {**value, "error": str(exc)}
            value = {
                **value,
                "tasks": [
                    {name: item for name, item in task.items() if name != "resources"}
                    for task in value["tasks"]
                ],
            }
            datasets.append(value)
        with self._lock:
            if (
                not self._closed
                and not self._mutations
                and epoch == self._epoch
                and key == self._configs
            ):
                self.cache.publish(
                    key,
                    {
                        "revision": config_revision(self.config_path),
                        "datasets": datasets,
                    },
                )
                self._error = next(
                    (item["error"] for item in datasets if item.get("error")), None
                )

    def _run(self):
        while True:
            try:
                self.reconcile()
            except Exception as exc:  # noqa: BLE001 - retain the last good generation.
                with self._lock:
                    self._error = str(exc)
            with self._lock:
                if self._pending and not self._closed and not self._mutations:
                    self._pending = False
                    continue
                self._thread = None
                return

    def close(self):
        with self._lock:
            self._closed = True
            thread = self._thread
        if thread is not None:
            thread.join()
        self.cache.close()
