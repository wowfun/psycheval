"""Disposable Task observations, independent of filesystem and serve policy."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from time import time_ns


def _encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


class TaskCatalog:
    def __init__(
        self,
        path: Path | None = None,
        *,
        max_entries=40000,
        max_bytes=128 * 1024 * 1024,
    ):
        self._lock = RLock()
        self.path = path
        self.max_entries, self.max_bytes = max_entries, max_bytes
        self._db = None
        self._sessions = 0
        self._closed = False
        if path is not None:
            self._validate_path()
            path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._initialize()
        except sqlite3.DatabaseError:
            if path is None:
                raise
            path.unlink(missing_ok=True)
            self._initialize()

    def _validate_path(self):
        if self.path is not None:
            for path in (self.path, *self.path.parents):
                if path.is_symlink() or path.is_junction():
                    raise ValueError("Task cache path must not contain links")

    @contextmanager
    def session(self):
        """Reuse a guarded connection during a scan; release idle file handles."""
        with self._lock:
            if self._closed:
                raise RuntimeError("Task catalog is closed")
            if self._db is None:
                self._validate_path()
                db = sqlite3.connect(self.path or ":memory:", check_same_thread=False)
                try:
                    if self.path is not None:
                        db.execute("PRAGMA journal_mode=WAL")
                        db.execute("PRAGMA synchronous=NORMAL")
                except Exception:
                    db.close()
                    raise
                self._db = db
            self._sessions += 1
        try:
            yield
        finally:
            with self._lock:
                self._sessions -= 1
                if not self._sessions and (self.path is not None or self._closed):
                    self._db.close()
                    self._db = None

    @contextmanager
    def _connection(self):
        with self.session(), self._lock, self._db as db:
            yield db

    def _initialize(self):
        with self._connection() as db:
            if db.execute("PRAGMA user_version").fetchone()[0] != 4:
                db.executescript("""
                    DROP TABLE IF EXISTS projections;
                    DROP TABLE IF EXISTS inventory;
                    DROP TABLE IF EXISTS dataset_inventory;
                    DROP TABLE IF EXISTS task_conflicts;
                    PRAGMA user_version=4;
                """)
            db.executescript("""
                CREATE TABLE IF NOT EXISTS projections (
                    key TEXT PRIMARY KEY, signature TEXT NOT NULL,
                    value TEXT NOT NULL, created INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY CHECK(id=1), generation INTEGER NOT NULL,
                    config TEXT NOT NULL, metadata TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS dataset_inventory (
                    id TEXT PRIMARY KEY, config TEXT NOT NULL, value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS task_conflicts (
                    dataset TEXT NOT NULL, task TEXT NOT NULL, config TEXT NOT NULL,
                    revision TEXT NOT NULL, value TEXT NOT NULL,
                    PRIMARY KEY(dataset, task)
                );
            """)

    def generation(self, config):
        with self._connection() as db:
            row = db.execute(
                "SELECT generation, config FROM inventory WHERE id=1"
            ).fetchone()
        if row:
            previous = json.loads(row[1])
            if previous == config or any(
                previous.get(key) == value for key, value in config.items()
            ):
                return row[0]
        return 0

    def project(self, key, *, signature, load):
        """Recheck caller-owned safe paths even on hits; never retain unstable reads."""
        with self.session():
            key, before = _encode(key), _encode(signature())
            with self._connection() as db:
                row = db.execute(
                    "SELECT signature, value FROM projections WHERE key=?", (key,)
                ).fetchone()
            if row and row[0] == before:
                return json.loads(row[1])
            value = load()
            if before != _encode(signature()):
                raise ValueError("Task changed while its inventory was being inspected")
            encoded = _encode(value)
            if self.max_entries > 0 and len(encoded.encode("utf-8")) <= min(
                4 * 1024 * 1024, self.max_bytes
            ):
                with self._connection() as db:
                    db.execute(
                        "INSERT OR REPLACE INTO projections VALUES (?, ?, ?, ?)",
                        (key, before, encoded, time_ns()),
                    )
            return json.loads(encoded)

    def snapshot(self, config: dict[str, str], dataset_id=None):
        with self._connection() as db:
            row = db.execute("SELECT metadata FROM inventory WHERE id=1").fetchone()
            rows = db.execute(
                "SELECT id, config, value FROM dataset_inventory"
                + (" WHERE id=?" if dataset_id is not None else ""),
                (dataset_id,) if dataset_id is not None else (),
            ).fetchall()
            datasets = {
                key: json.loads(value)
                for key, signature, value in rows
                if config.get(key) == signature
            }
            return {
                **(json.loads(row[0]) if row else {}),
                "datasets": [datasets[key] for key in config if key in datasets],
                "generation": self.generation(config),
            }

    def conflict(self, dataset_id, task, config, revision):
        with self._connection() as db:
            row = db.execute(
                "SELECT value FROM task_conflicts WHERE dataset=? AND task=? AND config=? AND revision=?",
                (dataset_id, task, config, revision),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def publish(self, config: dict[str, str], value: dict):
        encoded_config = _encode(config)
        metadata = _encode(
            {key: item for key, item in value.items() if key != "datasets"}
        )
        datasets = {item["id"]: _encode(item) for item in value["datasets"]}
        with self._connection() as db:
            row = db.execute(
                "SELECT generation, config, metadata FROM inventory WHERE id=1"
            ).fetchone()
            previous = dict(db.execute("SELECT id, value FROM dataset_inventory"))
            if not row or row[1:] != (encoded_config, metadata) or previous != datasets:
                db.execute(
                    "INSERT OR REPLACE INTO inventory VALUES (1, ?, ?, ?)",
                    (row[0] + 1 if row else 1, encoded_config, metadata),
                )
                db.execute("DELETE FROM dataset_inventory")
                db.execute("DELETE FROM task_conflicts")
                db.executemany(
                    "INSERT INTO dataset_inventory VALUES (?, ?, ?)",
                    [(key, config[key], item) for key, item in datasets.items()],
                )
                db.executemany(
                    "INSERT INTO task_conflicts VALUES (?, ?, ?, ?, ?)",
                    [
                        (
                            dataset["id"],
                            task["directory"],
                            config[dataset["id"]],
                            task["revision"],
                            _encode(
                                {
                                    "status": "conflict",
                                    "diagnostics": task["diagnostics"],
                                }
                            ),
                        )
                        for dataset in value["datasets"]
                        for task in dataset.get("tasks", [])
                        if task.get("status") == "conflict"
                    ],
                )
            # Insert-time eviction avoids turning warm reads into write transactions.
            db.execute(
                """DELETE FROM projections WHERE key IN (
                SELECT key FROM (SELECT key, ROW_NUMBER() OVER (ORDER BY created DESC) AS n,
                    SUM(LENGTH(CAST(value AS BLOB))) OVER (ORDER BY created DESC) AS bytes FROM projections)
                WHERE n > ? OR bytes > ?
            )""",
                (self.max_entries, self.max_bytes),
            )

    def close(self):
        with self._lock:
            self._closed = True
            if self._db is not None and not self._sessions:
                self._db.close()
                self._db = None
