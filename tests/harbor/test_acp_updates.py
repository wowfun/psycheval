from __future__ import annotations

import asyncio
import gzip
import json
import logging
import sys
import threading
import zlib
from pathlib import Path

import pytest
from harbor.models.agent.context import AgentContext

from psycheval.harbor.acp_agent import HostACPAgent
from tests.harbor.environment_support import make_environment

PEER = Path(__file__).resolve().parents[1] / "fixtures/acp_peer.py"


@pytest.mark.parametrize("callback", [False, 1, "callback", [], {}])
def test_session_update_callback_requires_callable(tmp_path, callback):
    with pytest.raises(ValueError, match="on_session_update"):
        HostACPAgent(
            logs_dir=tmp_path, argv=[sys.executable], on_session_update=callback
        )


def _update_record(
    update, *, phase="prompt", direction="receive", method="session/update"
):
    return (
        json.dumps(
            {
                "direction": direction,
                "phase": phase,
                "message": {
                    "method": method,
                    "params": {"sessionId": "fixture-session", "update": update},
                },
            },
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def test_update_relay_reads_incrementally_and_drains_complete_records(
    tmp_path, monkeypatch, caplog
):
    from psycheval.harbor import acp_agent

    monkeypatch.setattr(acp_agent, "_UPDATE_READ_BYTES", 3)

    async def scenario():
        path = tmp_path / "events.ndjson"
        received = asyncio.Queue()
        relay = acp_agent._SessionUpdateRelay(
            path, received.put_nowait, logging.getLogger("test.updates")
        )
        first = {
            "sessionUpdate": "agent_message_chunk",
            "content": {"type": "text", "text": "中文🙂"},
        }
        final = {
            "sessionUpdate": "tool_call",
            "toolCallId": "call",
            "name": "original",
            "_meta": {"vendor/toolName": "原始🙂"},
        }
        writer = None
        try:
            await asyncio.sleep(0)  # The observer starts before the file exists.
            writer = gzip.open(path, "wb")
            writer.write(_update_record(first))
            writer.flush()
            assert await asyncio.wait_for(received.get(), 2) == first
            writer.write(_update_record(final, phase="setup"))
            writer.write(_update_record(final, phase="replay"))
            writer.write(_update_record(final, direction="send"))
            writer.write(_update_record(final, method="_vendor/notice"))
            writer.write(_update_record(final))
            writer.close()
            await relay.finish()
            assert received.get_nowait() == final
            assert received.empty()
            assert relay.task.done()
            path.unlink()  # Windows also requires the reader to be closed.
            assert not caplog.records
        finally:
            if writer is not None:
                writer.close()
            await relay.finish()

    asyncio.run(scenario())


def test_update_relay_waits_for_a_partial_utf8_record(tmp_path, caplog):
    from psycheval.harbor import acp_agent

    async def scenario():
        path = tmp_path / "events.ndjson"
        update = {
            "sessionUpdate": "agent_message_chunk",
            "content": {"type": "text", "text": "中文🙂"},
        }
        data = _update_record(update)
        split = data.index("🙂".encode()) + 2
        compressor = zlib.compressobj(wbits=31)
        initial = compressor.compress(data[:split]) + compressor.flush(
            zlib.Z_SYNC_FLUSH
        )
        final = compressor.compress(data[split:]) + compressor.flush()
        path.write_bytes(initial)
        partial_read = asyncio.Event()
        received = []

        class Reader:
            def __init__(self):
                self.stream = path.open("rb")

            def read(self, maximum):
                chunk = self.stream.read(maximum)
                if not chunk:
                    partial_read.set()
                return chunk

            def close(self):
                self.stream.close()

        class ObservedPath:
            def open(self, mode):
                return Reader()

        relay = acp_agent._SessionUpdateRelay(
            ObservedPath(), received.append, logging.getLogger("test.updates")
        )
        try:
            await asyncio.wait_for(partial_read.wait(), 2)
            assert received == []
            with path.open("ab") as writer:
                writer.write(final)
            await relay.finish()
            assert received == [update]
            path.unlink()
        finally:
            await relay.finish()

    asyncio.run(scenario())
    assert not caplog.records


def test_update_callback_self_cancellation_is_confined_to_observer(tmp_path, caplog):
    from psycheval.harbor import acp_agent

    path = tmp_path / "events.ndjson"
    path.write_bytes(
        gzip.compress(_update_record({"sessionUpdate": "agent_message_chunk"}), mtime=0)
    )

    async def scenario():
        async def observe(update):
            asyncio.current_task().cancel("PRIVATE_CANCELLATION")
            await asyncio.sleep(0)

        relay = acp_agent._SessionUpdateRelay(
            path, observe, logging.getLogger("test.updates")
        )
        await relay.finish()
        assert relay.task.done()
        path.unlink()

    asyncio.run(scenario())
    assert len(caplog.records) == 1
    assert "CancelledError" in caplog.text
    assert "PRIVATE_CANCELLATION" not in caplog.text


@pytest.mark.parametrize("damage", ["json", "partial", "oversized", "read"])
def test_update_observer_read_failure_is_categorical(
    tmp_path, monkeypatch, caplog, damage
):
    from psycheval.harbor import acp_agent

    path = tmp_path / "events.ndjson"
    if damage == "read":
        path.mkdir()
    else:
        monkeypatch.setattr(acp_agent, "MAX_EVENT_FRAME", 64)
        path.write_bytes(
            gzip.compress(
                {
                    "json": b"PRIVATE_PAYLOAD\n",
                    "partial": b"PRIVATE_PAYLOAD",
                    "oversized": b"x" * 65,
                }[damage]
            )
        )

    async def scenario():
        received = []
        relay = acp_agent._SessionUpdateRelay(
            path, received.append, logging.getLogger("test.updates")
        )
        await relay.finish()
        assert relay.task.done()
        assert received == []

    asyncio.run(scenario())
    assert len(caplog.records) == 1
    assert "observer disabled" in caplog.text
    assert "PRIVATE_PAYLOAD" not in caplog.text


def test_update_final_drain_has_its_own_deadline(tmp_path, monkeypatch, caplog):
    from psycheval.harbor import acp_agent

    monkeypatch.setattr(acp_agent, "_UPDATE_CALLBACK_TIMEOUT_SEC", 10)
    monkeypatch.setattr(acp_agent, "_UPDATE_DRAIN_TIMEOUT_SEC", 0.03)
    path = tmp_path / "events.ndjson"
    path.write_bytes(
        gzip.compress(_update_record({"sessionUpdate": "agent_message_chunk"}), mtime=0)
    )

    async def scenario():
        entered, cancelled = asyncio.Event(), asyncio.Event()

        async def observe(update):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        relay = acp_agent._SessionUpdateRelay(
            path, observe, logging.getLogger("test.updates")
        )
        try:
            await asyncio.wait_for(entered.wait(), 2)
            await asyncio.wait_for(relay.finish(), 1)
            assert cancelled.is_set()
            assert relay.task.done()
            path.unlink()
        finally:
            await relay.finish()

    asyncio.run(scenario())
    assert len([r for r in caplog.records if "observer disabled" in r.message]) == 1
    assert "TimeoutError" in caplog.text


@pytest.mark.parametrize("failure", ["sync", "async", "cancelled", "timeout"])
def test_session_update_failure_does_not_fail_evaluation(
    tmp_path, monkeypatch, caplog, failure
):
    from psycheval.harbor import acp_agent

    monkeypatch.setattr(acp_agent, "_UPDATE_CALLBACK_TIMEOUT_SEC", 0.03)

    async def scenario():
        host = make_environment(
            tmp_path,
            environment_kwargs={
                "workdir_root": tmp_path / "work",
                "workspace_baseline": "none",
            },
        )
        await host.start(False)
        received = []

        def observe(update):
            received.append(update)
            raise RuntimeError("PRIVATE_EXCEPTION")

        async def observe_async(update):
            received.append(update)
            if failure == "timeout":
                await asyncio.Event().wait()
            if failure == "cancelled":
                raise asyncio.CancelledError("PRIVATE_EXCEPTION")
            raise RuntimeError("PRIVATE_EXCEPTION")

        agent = HostACPAgent(
            logs_dir=host.trial_paths.agent_dir,
            argv=[sys.executable, str(PEER)],
            on_session_update=observe if failure == "sync" else observe_async,
        )
        try:
            await agent.setup(host)
            for action in (agent.run, agent.resume):
                received.clear()
                await action("display failure", host, AgentContext())
                assert len(received) == 1
                context = AgentContext()
                agent.populate_context_post_run(context)
                assert context.metadata["acp_stop_reason"] == "end_turn"
                assert (agent.logs_dir / "trajectory.json").exists()
        finally:
            await host.stop(True)

    asyncio.run(scenario())
    warnings = [r for r in caplog.records if "observer disabled" in r.message]
    assert len(warnings) == 2
    assert "PRIVATE_EXCEPTION" not in caplog.text


def _stub_update_agent(tmp_path, monkeypatch, execute, observe):
    from harbor.models.task.config import TaskOS

    staging = tmp_path / "invocation"
    staging.mkdir()

    class Host:
        os = TaskOS.LINUX
        work_dir = tmp_path
        exec_argv = staticmethod(execute)

        def runtime_directory(self, name):
            return staging

    host = Host()
    agent = HostACPAgent(
        logs_dir=tmp_path / "logs",
        argv=[sys.executable],
        on_session_update=observe,
    )
    agent._setup_host, agent._state, agent._child_env = host, tmp_path, {}
    monkeypatch.setattr(agent, "_host", lambda environment: environment)
    monkeypatch.setattr(agent, "_check_runtime", lambda environment: None)
    return agent, host, staging


def test_publication_failure_after_successful_execution_is_not_hidden(
    tmp_path, monkeypatch
):
    async def scenario():
        async def execute(*args, **kwargs):
            return object()

        agent, host, staging = _stub_update_agent(
            tmp_path, monkeypatch, execute, lambda update: None
        )
        failure = OSError("publication failed")

        def publish(*args):
            raise failure

        monkeypatch.setattr(agent, "_publish_call", publish)
        before = asyncio.all_tasks()
        with pytest.raises(OSError) as caught:
            await agent.run("success", host, AgentContext())
        assert caught.value is failure
        assert not agent._invoking
        assert asyncio.all_tasks() == before
        (staging / "acp.events.ndjson.gz").write_bytes(b"")
        (staging / "acp.events.ndjson.gz").unlink()

    asyncio.run(scenario())


def test_relay_cancelled_before_it_starts_can_still_finish(tmp_path, caplog):
    from psycheval.harbor import acp_agent

    async def scenario():
        relay = acp_agent._SessionUpdateRelay(
            tmp_path / "events", lambda update: None, logging.getLogger("test.relay")
        )
        relay.task.cancel()
        await asyncio.gather(relay.task, return_exceptions=True)
        await relay.finish()
        await relay.finish()

    asyncio.run(scenario())
    assert len(caplog.records) == 1


@pytest.mark.parametrize("failure", ["launch", "observer", "publication"])
def test_update_cleanup_preserves_primary_execution_error(
    tmp_path, monkeypatch, caplog, failure
):
    async def scenario():
        primary = OSError("original execution error")
        received = []

        async def execute(argv, **kwargs):
            if failure == "observer":
                (Path(argv[-1]).parent / "acp.events.ndjson.gz").write_bytes(
                    gzip.compress(
                        _update_record({"sessionUpdate": "agent_message_chunk"}),
                        mtime=0,
                    )
                )
            raise primary

        def observe(update):
            received.append(update)
            raise RuntimeError("PRIVATE_EXCEPTION")

        agent, host, staging = _stub_update_agent(
            tmp_path, monkeypatch, execute, observe
        )
        if failure == "publication":

            def publish(invocation):
                raise ValueError("PRIVATE_PUBLICATION_EXCEPTION")

            monkeypatch.setattr(agent, "_publish_call", publish)
        before = asyncio.all_tasks()
        with pytest.raises(OSError) as caught:
            await agent.run("failed launch", host, AgentContext())
        assert caught.value is primary
        assert asyncio.all_tasks() == before
        assert not agent._invoking
        assert len(received) == (1 if failure == "observer" else 0)
        if failure == "publication":
            assert primary.__notes__ == ["ACP publication cleanup failed: ValueError"]
        else:
            assert not (staging / "request.json").exists()

    asyncio.run(scenario())
    assert len([r for r in caplog.records if "observer disabled" in r.message]) == (
        1 if failure == "observer" else 0
    )
    assert "PRIVATE_EXCEPTION" not in caplog.text


def test_repeated_cancellation_finishes_update_observer_before_publication(
    tmp_path, monkeypatch, caplog
):
    from psycheval.harbor import acp_agent

    monkeypatch.setattr(acp_agent, "_UPDATE_CALLBACK_TIMEOUT_SEC", 10)
    monkeypatch.setattr(acp_agent, "_UPDATE_DRAIN_TIMEOUT_SEC", 0.1)

    async def scenario():
        entered, draining, cancelled = (
            asyncio.Event(),
            asyncio.Event(),
            asyncio.Event(),
        )
        original_finish = acp_agent._SessionUpdateRelay.finish

        async def finish(relay):
            draining.set()
            await original_finish(relay)

        monkeypatch.setattr(acp_agent._SessionUpdateRelay, "finish", finish)

        async def execute(argv, **kwargs):
            (Path(argv[-1]).parent / "acp.events.ndjson.gz").write_bytes(
                gzip.compress(
                    _update_record({"sessionUpdate": "agent_message_chunk"}), mtime=0
                )
            )
            await asyncio.Event().wait()

        async def observe(update):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        agent, host, staging = _stub_update_agent(
            tmp_path, monkeypatch, execute, observe
        )
        before = asyncio.all_tasks()
        running = asyncio.create_task(agent.run("cancelled", host, AgentContext()))
        try:
            await asyncio.wait_for(entered.wait(), 2)
            running.cancel("initial cancellation")
            await asyncio.wait_for(draining.wait(), 2)
            running.cancel("repeated cancellation")
            with pytest.raises(asyncio.CancelledError, match="initial cancellation"):
                await asyncio.wait_for(running, 2)
            assert cancelled.is_set()
            assert asyncio.all_tasks() == before
            assert not agent._invoking
            assert not (staging / "acp.events.ndjson.gz").exists()
            (agent.logs_dir / "acp.events.ndjson.gz").unlink()
        finally:
            running.cancel()
            await asyncio.gather(running, return_exceptions=True)

    asyncio.run(scenario())
    assert len([r for r in caplog.records if "observer disabled" in r.message]) == 1
    assert "TimeoutError" in caplog.text


@pytest.mark.parametrize("asynchronous", [False, True])
def test_session_updates_arrive_before_prompt_completion(tmp_path, asynchronous):
    async def scenario():
        host = make_environment(
            tmp_path,
            environment_kwargs={
                "workdir_root": tmp_path / "work",
                "workspace_baseline": "none",
            },
        )
        await host.start(False)
        received = []
        loop_thread = threading.get_ident()

        def observe(update):
            assert threading.get_ident() == loop_thread
            received.append(json.loads(json.dumps(update)))
            if update["sessionUpdate"] == "tool_call":
                assert update["name"] == "bash"
                (host.work_dir / "live-update-ack").touch()
                update["name"] = "callback mutation"

        async def observe_async(update):
            await asyncio.sleep(0)
            observe(update)

        agent = HostACPAgent(
            logs_dir=host.trial_paths.agent_dir,
            argv=[
                sys.executable,
                str(PEER),
                "live",
                str(host.work_dir / "live-update-ack"),
            ],
            on_session_update=observe_async if asynchronous else observe,
        )
        try:
            await agent.setup(host)
            for action in (agent.run, agent.resume):
                received.clear()
                await asyncio.wait_for(action("live 中文🙂", host, AgentContext()), 45)
                assert [update["sessionUpdate"] for update in received] == [
                    "agent_message_chunk",
                    "tool_call",
                    "tool_call_update",
                    "agent_message_chunk",
                ]
                assert received[0]["content"]["text"] == "中文🙂"
                assert received[-1]["content"]["text"] == "完成中文🙂"
                context = AgentContext()
                agent.populate_context_post_run(context)
                data = json.loads(
                    (agent.logs_dir / "trajectory.json").read_text(encoding="utf-8")
                )
                calls = [c for s in data["steps"] for c in s.get("tool_calls", [])]
                assert [c["function_name"] for c in calls] == ["bash"]
                assert not (agent.logs_dir / "acp.updates.ndjson").exists()
        finally:
            await host.stop(True)

    asyncio.run(scenario())
