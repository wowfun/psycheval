from __future__ import annotations

import hashlib
import os
import stat
import tempfile
import threading
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

PROMPT_ASSET_FILENAMES = (
    "evaluation-review.md",
    "evaluation-review-zh-cn.md",
    "failure-diagnosis.md",
    "failure-diagnosis-zh-cn.md",
    "task-audit.md",
    "task-audit-zh-cn.md",
    "report-review.md",
    "report-review-zh-cn.md",
)
PROMPT_ASSET_LIMIT = 256 * 1024


@dataclass(frozen=True)
class PromptAsset:
    filename: str
    title: str
    content: str
    customized: bool
    revision: str

    @property
    def id(self) -> str:
        return self.filename.removesuffix(".md")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "filename": self.filename,
            "title": self.title,
            "content": self.content,
            "customized": self.customized,
            "revision": self.revision,
        }


class PromptAssetConflict(ValueError):
    pass


class PromptAssetLibrary:
    """Own repository defaults and same-name workspace prompt overrides."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).expanduser().resolve()
        self.overrides_root = self.workspace_root / "prompts"
        self._mutation_lock = threading.RLock()

    def catalog(self) -> dict[str, object]:
        return {
            "prompts": [
                self.read(filename).to_dict() for filename in PROMPT_ASSET_FILENAMES
            ]
        }

    def read(self, prompt_id_or_filename: str) -> PromptAsset:
        filename = self._filename(prompt_id_or_filename)
        override = self.overrides_root / filename
        if override.is_symlink():
            raise ValueError(f"prompt override must be a regular file: {filename}")
        customized = override.exists()
        if customized:
            content = self._read_override(override)
        else:
            content = self._default_content(filename)
        return PromptAsset(
            filename=filename,
            title=_prompt_title(content, filename),
            content=content,
            customized=customized,
            revision=_content_revision(content),
        )

    def save(
        self,
        prompt_id_or_filename: str,
        content: str,
        *,
        expected_revision: str,
    ) -> PromptAsset:
        if not isinstance(content, str) or not content.strip():
            raise ValueError("prompt content must be a non-empty string")
        encoded = content.encode("utf-8")
        if len(encoded) > PROMPT_ASSET_LIMIT:
            raise ValueError("prompt content exceeds the 256 KiB limit")
        filename = self._filename(prompt_id_or_filename)
        with self._mutation_lock:
            self._expect_revision(filename, expected_revision)
            self._ensure_overrides_root()
            _atomic_write(self.overrides_root / filename, encoded)
            return self.read(filename)

    def reset(
        self,
        prompt_id_or_filename: str,
        *,
        expected_revision: str,
    ) -> PromptAsset:
        filename = self._filename(prompt_id_or_filename)
        with self._mutation_lock:
            self._expect_revision(filename, expected_revision)
            target = self.overrides_root / filename
            if target.is_symlink() or target.exists():
                if target.is_symlink() or not target.is_file():
                    raise ValueError(
                        f"prompt override must be a regular file: {filename}"
                    )
                target.unlink()
            return self.read(filename)

    def _expect_revision(self, filename: str, expected_revision: str) -> None:
        if not isinstance(expected_revision, str) or not expected_revision:
            raise ValueError("expected_revision is required")
        if self.read(filename).revision != expected_revision:
            raise PromptAssetConflict("Prompt changed; reload before saving")

    def _filename(self, value: str) -> str:
        text = str(value or "").strip()
        candidate = text if text.endswith(".md") else f"{text}.md"
        if candidate not in PROMPT_ASSET_FILENAMES:
            raise ValueError(f"unknown prompt asset: {text}")
        return candidate

    def _read_override(self, path: Path) -> str:
        try:
            before = path.stat(follow_symlinks=False)
            if not stat.S_ISREG(before.st_mode):
                raise ValueError(f"prompt override must be a regular file: {path.name}")
            descriptor = os.open(
                path,
                os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0),
            )
        except (OSError, ValueError):
            raise ValueError(
                f"prompt override must be a regular file: {path.name}"
            ) from None
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode) or (before.st_dev, before.st_ino) != (
                opened.st_dev,
                opened.st_ino,
            ):
                raise ValueError(f"prompt override must be a regular file: {path.name}")
            with os.fdopen(descriptor, "rb") as handle:
                descriptor = -1
                encoded = handle.read(PROMPT_ASSET_LIMIT + 1)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        if len(encoded) > PROMPT_ASSET_LIMIT:
            raise ValueError(f"prompt override exceeds the 256 KiB limit: {path.name}")
        try:
            return encoded.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError(
                f"prompt override must be UTF-8 text: {path.name}"
            ) from None

    def _default_content(self, filename: str) -> str:
        return (
            files("psycheval.assets")
            .joinpath("prompt_assets", filename)
            .read_text(encoding="utf-8")
        )

    def _ensure_overrides_root(self) -> None:
        if self.overrides_root.is_symlink():
            raise ValueError("workspace prompts path must be a directory")
        try:
            self.overrides_root.mkdir(parents=True)
        except FileExistsError:
            if self.overrides_root.is_symlink() or not self.overrides_root.is_dir():
                raise ValueError("workspace prompts path must be a directory") from None


def _prompt_title(content: str, filename: str) -> str:
    for line in content.splitlines():
        if line.startswith("# ") and line[2:].strip():
            return line[2:].strip()
    return filename.removesuffix(".md").replace("-", " ").title()


def _content_revision(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _atomic_write(path: Path, content: bytes) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"prompt override must be a regular file: {path.name}")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
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
