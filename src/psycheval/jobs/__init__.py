"""Workspace evaluation harness registration."""

import re
from functools import lru_cache
from importlib.metadata import entry_points

from .protocol import Harness, HarnessContext, RunControl, RunRequest, Variant


class UnavailableHarness:
    def __init__(self, name, error):
        self.name, self.error = name, error

    def describe(self, context):
        return {"label": self.name, "available": False, "error": self.error}

    def catalog(self, context):
        return [{"id": self.name, "label": self.name, "tasks": [], "error": self.error}]

    def prepare(self, request, context):
        raise ValueError(self.error)

    async def execute(self, prepared, control):
        raise ValueError(self.error)

    def read_results(self, output_dir):
        raise ValueError(self.error)


@lru_cache(maxsize=1)
def _registered_harnesses() -> dict[str, Harness]:
    from .harbor import HarborHarness

    result: dict[str, Harness] = {"harbor": HarborHarness()}
    for entry in entry_points(group="psycheval.harnesses"):
        if (
            not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", entry.name)
            or entry.name == "harbor"
        ):
            continue
        try:
            if entry.name in result:
                raise ValueError(f"duplicate harness: {entry.name}")
            value = entry.load()
            instance = value() if callable(value) else value
            for method in ("describe", "catalog", "prepare", "execute", "read_results"):
                if not callable(getattr(instance, method, None)):
                    raise ValueError(f"harness {entry.name} requires {method}")
            result[entry.name] = instance
        except Exception as exc:  # noqa: BLE001 - isolate installed plugin loading.
            result[entry.name] = UnavailableHarness(entry.name, str(exc))
    return result


def harnesses() -> dict[str, Harness]:
    return dict(_registered_harnesses())


__all__ = [
    "Harness",
    "HarnessContext",
    "RunControl",
    "RunRequest",
    "Variant",
    "harnesses",
]
