from __future__ import annotations

import re
from pathlib import Path

DEFAULT_PORT_START = 58010
DEFAULT_PORT_END = 58029
LOCALHOSTS = {"127.0.0.1", "localhost", "::1"}
MAX_JSON_BODY_BYTES = 22 * 1024 * 1024
WINDOWS_DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
WINDOWS_DRIVE_MOUNT_ROOT = Path("/mnt")
