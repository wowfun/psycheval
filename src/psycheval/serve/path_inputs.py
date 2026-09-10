"""Literal tokens pasted into browser filesystem-path inputs."""

from __future__ import annotations


def unquote_path_token(raw: object) -> str:
    _reject_path_controls(str(raw))
    text = str(raw).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1].strip()
    return text


def required_path_token(value: str) -> str:
    return validate_path_token(unquote_path_token(value))


def source_path_lines(raw: str) -> list[str]:
    """Split a path batch, retaining quotes until each item's parsing boundary."""
    return [
        line.strip()
        for line in raw.replace("\r\n", "\n").split("\n")
        if unquote_path_token(line)
    ]


def validate_path_token(text: str) -> str:
    """Validate a decoded token without removing a second pair of quotes."""
    if not text.strip():
        raise ValueError("path must not be empty")
    _reject_path_controls(text)
    return text


def _reject_path_controls(text: str) -> None:
    if any(
        ord(character) < 32
        or 127 <= ord(character) <= 159
        or character in {"\u2028", "\u2029"}
        for character in text
    ):
        raise ValueError("path contains control characters")
