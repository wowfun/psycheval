"""Diagnostic-only trajectory publication and bounded cleanup warnings."""

import json
from pathlib import Path

PARTIAL_TRAJECTORY = "trajectory.partial.json"


def write_partial(directory, trajectory, source):
    if trajectory is None:
        return
    data = trajectory.to_json_dict()
    data["extra"] = {
        **(data.get("extra") or {}),
        "diagnostic_only": True,
        "incomplete": True,
        "diagnostic_source": source,
    }
    path = Path(directory) / PARTIAL_TRAJECTORY
    temporary = path.with_suffix(".tmp")
    try:
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def cleanup_warning(stage, error, paths, **state):
    return {
        "stage": stage,
        "error_type": type(error).__name__,
        "paths": [str(Path(path).absolute()) for path in paths if path is not None],
        **state,
    }


def warning_text(warning):
    return (
        f"Windows cleanup warning ({warning['stage']}: {warning['error_type']}); "
        f"paths: {', '.join(warning['paths'])}"
    )
