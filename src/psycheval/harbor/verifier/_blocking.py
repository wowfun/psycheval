"""Keep ownership of blocking work until it settles, including cancellation."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from functools import partial
from typing import Any

# Keep long custom scripts out of the embedding application's default executor.
# Workers are created on demand and shared across verifier calls/event loops.
_EXECUTOR = ThreadPoolExecutor(thread_name_prefix="psycheval-verifier")


async def run_blocking[T](
    function: Callable[..., T], /, *args: Any, **kwargs: Any
) -> T:
    work = partial(function, *args, **kwargs)
    worker = asyncio.get_running_loop().run_in_executor(
        _EXECUTOR, copy_context().run, work
    )
    try:
        return await asyncio.shield(worker)
    except asyncio.CancelledError:
        # Threads cannot be interrupted safely. Drain even repeated cancellation
        # before returning control to callers that may reuse the output paths.
        while not worker.done():
            try:
                await asyncio.shield(worker)
            except BaseException:
                continue
        if not worker.cancelled():
            worker.exception()
        raise
