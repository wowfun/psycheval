from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar

from psycheval.harbor.verifier._blocking import run_blocking


def test_verifier_work_does_not_starve_application_default_executor():
    started, release = threading.Event(), threading.Event()

    def slow_check():
        started.set()
        assert release.wait(timeout=5)

    async def scenario():
        loop = asyncio.get_running_loop()
        loop.set_default_executor(ThreadPoolExecutor(max_workers=1))
        verifier = asyncio.create_task(run_blocking(slow_check))
        unrelated = None
        try:
            async with asyncio.timeout(3):
                while not started.is_set():
                    await asyncio.sleep(0.01)
            unrelated = asyncio.create_task(asyncio.to_thread(lambda: "ready"))
            assert await asyncio.wait_for(asyncio.shield(unrelated), 0.5) == "ready"
            assert not verifier.done()
        finally:
            release.set()
            await verifier
            if unrelated is not None:
                await unrelated

    asyncio.run(scenario())


def test_verifier_workers_keep_each_callers_context():
    identity = ContextVar("verifier_test_identity", default="outside")

    async def invocation(value):
        token = identity.set(value)
        try:
            return await run_blocking(identity.get)
        finally:
            identity.reset(token)

    async def scenario():
        assert await asyncio.gather(invocation("first"), invocation("second")) == [
            "first",
            "second",
        ]
        assert identity.get() == "outside"

    asyncio.run(scenario())
