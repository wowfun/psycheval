"""Workspace-owned display metadata for Agent-owned Copilot sessions."""

import os
import stat
import tempfile
from pathlib import Path

from pydantic import Field, TypeAdapter, ValidationError

from psycheval.file_access import blocking_file_lease, open_read_descriptor
from psycheval.harbor.atif import iso_timestamp_ms
from psycheval.serve.api_http import ProblemException
from psycheval.serve.api_models import StrictRequest


class SessionDecoration(StrictRequest):
    sessionId: str = Field(min_length=1, max_length=16384)
    title: str = Field(default="", max_length=16384)
    updatedAt: str = Field(default="", max_length=128)
    alias: str = Field(default="", max_length=256)
    pinned: bool = False
    archived: bool = False


_ROWS = TypeAdapter(list[SessionDecoration])
_MAX_BYTES = 8 * 1024 * 1024


def read_organization(path: Path) -> list[SessionDecoration]:
    try:
        with open(
            path, "rb", opener=lambda name, _: open_read_descriptor(name)
        ) as source:
            info = os.fstat(source.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or getattr(info, "st_file_attributes", 0)
                & stat.FILE_ATTRIBUTE_REPARSE_POINT
            ):
                raise ProblemException(
                    409, f"Copilot organization file {path.name} must be a regular file"
                )
            if info.st_size > _MAX_BYTES:
                raise ProblemException(
                    409, f"Copilot organization file {path.name} exceeds its size limit"
                )
            return _ROWS.validate_json(source.read(info.st_size + 1))
    except FileNotFoundError:
        return []
    except OSError as exc:
        raise ProblemException(
            409, f"Cannot read Copilot organization file {path.name}"
        ) from exc
    except ValidationError as exc:
        raise ProblemException(
            409, f"Invalid Copilot organization data in {path.name}"
        ) from exc


def patch_organization(
    path: Path, patch: SessionDecoration
) -> SessionDecoration | None:
    with blocking_file_lease(
        path.with_suffix(".lock"), label="Copilot session metadata"
    ):
        rows = {row.sessionId: row for row in read_organization(path)}
        previous = rows.get(patch.sessionId)
        row = patch
        if previous:
            changes = patch.payload()
            if "title" in changes or "updatedAt" in changes:
                current_time = iso_timestamp_ms(previous.updatedAt)
                incoming_time = iso_timestamp_ms(patch.updatedAt)
                if current_time is not None and (
                    incoming_time is None or incoming_time < current_time
                ):
                    changes.pop("updatedAt", None)
                    changes.pop("title", None)
            row = previous.model_copy(update=changes)
        if row.alias or row.archived or row.pinned:
            rows[row.sessionId] = row
        else:
            rows.pop(row.sessionId, None)
        result = rows.get(row.sessionId)
        if previous == result:
            return result
        content = _ROWS.dump_json(list(rows.values()), exclude_defaults=True)
        if len(content) > _MAX_BYTES:
            raise ProblemException(
                422, "Copilot organization update exceeds the file size limit"
            )
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f"{path.name}.", dir=path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        return result
