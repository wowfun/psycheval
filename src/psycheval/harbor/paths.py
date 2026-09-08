"""Pure path translation primitives for native Harbor environments."""

from __future__ import annotations

import secrets
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType

from harbor.models.task.config import TaskOS

from . import windows

_SHORTUUID_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_SHORTUUID_LENGTH = 7


def trial_short_uuid(trial_name: str) -> str:
    """Return the valid seven-character trial suffix or a fresh short ID.

    Harbor trial names commonly end in a short UUID after ``__``. Valid suffixes
    are reused so native workspaces are easy to correlate with their Trial;
    malformed or absent suffixes receive a collision-resistant random ID.
    """

    candidate = trial_name.rsplit("__", 1)[-1]
    if len(candidate) == _SHORTUUID_LENGTH and all(
        char in _SHORTUUID_ALPHABET for char in candidate
    ):
        return candidate
    return "".join(
        secrets.choice(_SHORTUUID_ALPHABET) for _ in range(_SHORTUUID_LENGTH)
    )


def split_virtual_path(
    value: str,
    host_os: TaskOS,
    virtual_roots: Sequence[str],
) -> tuple[str, tuple[str, ...]] | None:
    """Split a virtual environment path into its root and safe suffix.

    The longest matching root wins. Windows matching is case-insensitive and
    accepts both ``/root`` and ``C:/root`` aliases. A traversal, embedded drive
    prefix, or alternate-data-stream suffix raises ``ValueError``.
    """

    if host_os == TaskOS.WINDOWS:
        return windows.split_virtual_path(value, virtual_roots)
    for virtual in sorted(set(virtual_roots), key=len, reverse=True):
        if value == virtual:
            return virtual, ()
        if value.startswith(virtual + "/"):
            parts = PurePosixPath(value[len(virtual) + 1 :]).parts
            if ".." in parts:
                raise ValueError(f"unsupported HostEnvironment path: {value}")
            return virtual, tuple(part for part in parts if part != ".")
    return None


@dataclass(frozen=True, slots=True)
class HostPathMapper:
    """Translate explicit Harbor virtual paths to native host paths.

    The mapper has no lifecycle or allocation side effects. Callers provide the
    complete mapping and the virtual task workdir explicitly. Non-virtual
    absolute paths are treated as native host paths; relative paths resolve from
    ``task_workdir``.
    """

    host_os: TaskOS
    mappings: Mapping[str, Path]
    task_workdir: str

    def __post_init__(self) -> None:
        if not isinstance(self.task_workdir, str) or not self.task_workdir:
            raise ValueError("HostPathMapper task_workdir must be non-empty")
        normalized = {str(root): Path(path) for root, path in self.mappings.items()}
        if not normalized:
            raise ValueError("HostPathMapper mappings must not be empty")
        object.__setattr__(self, "mappings", MappingProxyType(normalized))

    @property
    def virtual_roots(self) -> tuple[str, ...]:
        """The virtual roots accepted by this mapper, longest first."""

        return tuple(sorted(self.mappings, key=len, reverse=True))

    def split(self, value: str | Path) -> tuple[str, tuple[str, ...]] | None:
        """Return the matching virtual root and suffix, if *value* is virtual."""

        return split_virtual_path(str(value), self.host_os, self.virtual_roots)

    def translate(self, value: str | Path) -> Path:
        """Translate one virtual, native absolute, or task-relative path."""

        raw = str(value)
        virtual_match = self.split(raw)
        if virtual_match is not None:
            virtual, suffix = virtual_match
            return self.mappings[virtual].joinpath(*suffix)

        if raw.startswith("/") or (
            self.host_os == TaskOS.WINDOWS and windows.is_absolute_path(raw)
        ):
            return Path(raw)

        relative = PurePosixPath(
            raw.replace("\\", "/") if self.host_os == TaskOS.WINDOWS else raw
        )
        if ".." in relative.parts:
            raise ValueError(f"unsupported HostEnvironment path: {raw}")
        task_match = self.split(self.task_workdir)
        if task_match is None:
            raise ValueError(
                "HostPathMapper task_workdir must be covered by its mappings"
            )
        virtual, suffix = task_match
        return self.mappings[virtual].joinpath(
            *suffix, *(part for part in relative.parts if part != ".")
        )

    def translate_literal(self, value: str) -> str | None:
        """Translate a virtual literal, returning ``None`` for native values."""

        match = self.split(value)
        if match is None:
            return None
        virtual, suffix = match
        return str(self.mappings[virtual].joinpath(*suffix))

    def translate_environment(
        self,
        env: Mapping[str, str],
        *,
        path_separator: str = ";",
    ) -> dict[str, str]:
        """Translate environment values while preserving native values."""

        if self.host_os == TaskOS.WINDOWS:
            return windows.translate_environment(
                env, self.mappings, path_separator=path_separator
            )
        return {
            key: self.translate_literal(value) or value for key, value in env.items()
        }
