"""Child-process entrypoint for trusted Task input preparation."""

from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path


def main() -> None:
    script, workdir = (Path(value).resolve() for value in sys.argv[1:])
    sys.path.insert(0, str(script.parent))
    spec = importlib.util.spec_from_file_location("_task_prepare", script)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load preparation script: {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    prepare = getattr(module, "prepare", None)
    if not callable(prepare) or inspect.iscoroutinefunction(prepare):
        raise TypeError("prepare.py must define synchronous prepare(workdir: str)")
    result = prepare(str(workdir))
    if inspect.iscoroutine(result):
        result.close()
    if result is not None:
        raise TypeError("prepare(workdir) must return None")


if __name__ == "__main__":
    main()
