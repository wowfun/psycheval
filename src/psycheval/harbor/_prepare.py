"""Child-process entrypoint for trusted Task input preparation."""

from __future__ import annotations

import importlib.util
import inspect
import json
import sys
from pathlib import Path


def main() -> None:
    script, workdir, state_dir, output = (
        Path(value).resolve() for value in sys.argv[1:]
    )
    sys.path.insert(0, str(script.parent))
    spec = importlib.util.spec_from_file_location("_task_prepare", script)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load preparation script: {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    prepare = getattr(module, "prepare", None)
    if not callable(prepare) or inspect.iscoroutinefunction(prepare):
        raise TypeError(
            "prepare.py must define synchronous prepare(workdir, state_dir)"
        )
    result = prepare(str(workdir), str(state_dir))
    if inspect.iscoroutine(result):
        result.close()
    if not isinstance(result, list) or not all(
        isinstance(path, str) for path in result
    ):
        raise TypeError(
            "prepare(workdir, state_dir) must return a list of relative input paths"
        )
    raw = json.dumps(result, ensure_ascii=False).encode("utf-8")
    if len(raw) > 1024 * 1024:
        raise ValueError("prepared input selection exceeds 1 MiB")
    output.write_bytes(raw)


if __name__ == "__main__":
    main()
