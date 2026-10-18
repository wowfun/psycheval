from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from ..runtime_config import (
    EffectiveRuntimeConfig,
    RuntimePaths,
    optional_effective_runtime_config,
)
from ._runner import run_verifier


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Grade a Psycheval trajectory")
    parser.add_argument("config", type=Path)
    args = parser.parse_args(argv)
    config_path = args.config.resolve()
    runtime = optional_effective_runtime_config()
    if runtime is None:
        runtime = EffectiveRuntimeConfig(
            paths=RuntimePaths(
                workdir=str(Path.cwd()),
                tests=str(config_path.parent),
                agent_logs="/logs/agent",
                verifier_logs="/logs/verifier",
                artifacts="/logs/artifacts",
            ),
            python=sys.executable,
        )
    asyncio.run(run_verifier(config_path, runtime=runtime))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
