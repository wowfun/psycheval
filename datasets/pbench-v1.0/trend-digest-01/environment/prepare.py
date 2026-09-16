"""Stage static inputs and diagnostic preparation metadata; never fetch sources."""

import hashlib
import importlib.util
import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path


def prepare(workdir: str) -> None:
    data = Path(__file__).parent / "data"
    spec = importlib.util.spec_from_file_location(
        "trend_watchlist", data / "skills/x-daily/scripts/fetch.py"
    )
    if spec is None or spec.loader is None:
        raise ValueError("cannot load the watchlist reader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    users = module.read_users_xlsx(data / "input/x-users.xlsx")
    handles = [user["handle"].casefold() for user in users]
    if len(handles) != 11 or len(set(handles)) != len(handles):
        raise ValueError("watchlist must contain eleven distinct enabled accounts")
    target = Path(workdir)
    prepared_at = (
        datetime.fromisoformat(os.environ["PBENCH_TREND_NOW"].replace("Z", "+00:00"))
        if "PBENCH_TREND_NOW" in os.environ
        else datetime.now(timezone.utc)
    )
    if prepared_at.tzinfo is None or prepared_at.utcoffset() != timedelta(0):
        raise ValueError("PBENCH_TREND_NOW must have an explicit UTC offset")
    hashes = {}
    for path in sorted(data.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            with path.open("rb") as stream:
                hashes[path.relative_to(data).as_posix()] = hashlib.file_digest(
                    stream, "sha256"
                ).hexdigest()
    for name in ("input", "skills"):
        shutil.copytree(
            data / name,
            target / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    snapshots = target / ".trend-digest"
    snapshots.mkdir()
    (snapshots / "preparation.json").write_text(
        json.dumps(
            {
                "prepared_at": prepared_at.isoformat(),
                "watchlist": users,
                "sha256": hashes,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
