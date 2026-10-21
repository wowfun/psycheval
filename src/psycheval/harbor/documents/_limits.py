"""Input, inspection-work and output budgets, independent of parser backends."""

from dataclasses import dataclass, fields


class DocumentParseError(ValueError):
    """The selected document cannot be inspected."""


class DocumentLimitError(DocumentParseError):
    """Document content exceeds an explicit inspection budget."""


@dataclass(frozen=True)
class DocumentLimits:
    source_bytes: int = 64 * 1024 * 1024
    archive_entries: int = 10000
    expanded_bytes: int = 256 * 1024 * 1024
    pages: int = 1000
    facts: int = 100000
    text_bytes: int = 4 * 1024 * 1024
    color_operations: int = 100000

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{field.name} must be a positive integer")


def _text_size(text, remaining, message):
    # Character count is a lower bound on UTF-8 bytes, so reject obvious excess
    # before allocating an encoded copy. Acceptance always uses the byte count.
    if len(text) > remaining:
        raise DocumentLimitError(message)
    size = len(text.encode("utf-8"))
    if size > remaining:
        raise DocumentLimitError(message)
    return size


class InspectionBudget:
    def __init__(self, limits):
        self.limits = limits
        self.facts = 0
        self.text_bytes = 0
        self.color_operations = 0

    def pages(self, count):
        if count > self.limits.pages:
            raise DocumentLimitError(
                f"Document exceeds {self.limits.pages} pages/sheets"
            )

    def fact(self, count=1):
        self.facts += count
        if self.facts > self.limits.facts:
            raise DocumentLimitError(f"Document exceeds {self.limits.facts} facts")

    def text(self, value):
        if value is None:
            return
        self.text_bytes += _text_size(
            str(value),
            self.limits.text_bytes - self.text_bytes,
            "Document exceeds extracted text byte limit",
        )

    def color(self):
        if self.color_operations >= self.limits.color_operations:
            raise DocumentLimitError(
                f"Document exceeds {self.limits.color_operations} color operations"
            )
        self.color_operations += 1


def bounded_markdown(parts, max_bytes):
    """Account for framing as well as body text before joining the result."""
    retained, size = [], 0
    for part in parts:
        size += 2 if retained else 0
        size += _text_size(part, max_bytes - size, "Markdown exceeds text byte limit")
        retained.append(part)
    return "\n\n".join(retained)
