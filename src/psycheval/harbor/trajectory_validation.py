"""UTF-8 trajectory files with Harbor's schema and image-reference validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harbor.utils.trajectory_validator import TrajectoryValidator


def load_validated_trajectory(path: Path) -> dict[str, Any]:
    """Read without rewriting; raise ValueError for invalid UTF-8, JSON, or ATIF."""
    trajectory = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(trajectory, dict):
        raise ValueError("ATIF trajectory must be an object")
    validator = TrajectoryValidator()
    valid = validator.validate(trajectory, validate_images=False)
    if valid:
        # Harbor 0.21 exposes image-file context only through these private hooks.
        # Preserve its original-directory checks without its locale-based reader.
        validator._trajectory_dir = path.parent
        validator._validate_image_paths(trajectory)
    if not valid or validator.errors:
        raise ValueError("; ".join(validator.errors))
    return trajectory
