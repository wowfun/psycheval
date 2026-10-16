from __future__ import annotations

import asyncio
import gzip
import json
import random
import sys
from pathlib import Path

import pytest

from psycheval.harbor import acp_protocol as protocol


def test_stored_limit_keeps_a_valid_compressed_prefix(tmp_path):
    summary = {}
    budget = protocol.EvidenceBudget(summary, 512, 10_000)
    path = tmp_path / "wire.gz"
    writer = protocol.EvidenceWriter(path, budget)
    prefix = b"retained\n"
    writer.write(prefix)
    try:
        with pytest.raises(protocol.ProtocolError):
            writer.write(random.Random(0).randbytes(1024))
    finally:
        writer.close()
    assert summary["evidence_limit_kind"] == "stored_bytes"
    assert gzip.decompress(path.read_bytes()) == prefix
    assert path.stat().st_size <= 512


def test_write_error_closes_handles_without_sealing_false_evidence(
    tmp_path, monkeypatch
):
    budget = protocol.EvidenceBudget({}, 1024)
    path = tmp_path / "wire.gz"
    writer = protocol.EvidenceWriter(path, budget)
    primary = OSError("fixture write failure")

    def fail(*args):
        raise primary

    monkeypatch.setattr(budget, "write", fail)
    with pytest.raises(OSError) as caught:
        writer.write(b"record\n")
    assert caught.value is primary
    budget.close()
    path.unlink()


@pytest.mark.parametrize(
    "error_type", [OSError, protocol.ProtocolError, RuntimeError, KeyboardInterrupt]
)
def test_budget_close_attempts_every_writer_and_preserves_first_error(
    tmp_path, monkeypatch, error_type
):
    budget = protocol.EvidenceBudget({}, 1024)
    writers = [
        protocol.EvidenceWriter(tmp_path / f"{index}.gz", budget) for index in range(3)
    ]
    primary = error_type("first close failure")
    attempted = []
    write = budget.write

    def fail_first_two(stream, *args):
        attempted.append(stream)
        if len(attempted) == 1:
            raise primary
        if len(attempted) == 2:
            raise OSError("later close failure")
        return write(stream, *args)

    monkeypatch.setattr(budget, "write", fail_first_two)
    try:
        with pytest.raises(error_type) as caught:
            budget.close()
        assert caught.value is primary
        assert attempted == [writer.stream for writer in writers]
        assert all(writer.stream.closed for writer in writers)
        assert budget.reserved == 0
        budget.close()
        assert len(attempted) == 3
    finally:
        for writer in writers:
            writer.stream.close()


def test_compressible_peer_can_exceed_stored_budget_in_decoded_bytes(tmp_path):
    from harbor.models.agent.context import AgentContext

    from psycheval.harbor.acp_agent import HostACPAgent
    from tests.harbor.environment_support import make_environment

    async def scenario():
        host = make_environment(
            tmp_path,
            environment_kwargs={
                "workdir_root": tmp_path / "work",
                "workspace_baseline": "none",
            },
        )
        await host.start(False)
        agent = HostACPAgent(
            logs_dir=host.trial_paths.agent_dir,
            argv=[
                sys.executable,
                str(Path(__file__).parents[1] / "fixtures/acp_peer.py"),
                "stdout-flood",
            ],
            max_evidence_bytes=32 * 1024,
            max_decoded_evidence_bytes=8 * 1024 * 1024,
        )
        try:
            await agent.setup(host)
            context = AgentContext()
            await agent.run("compressible evidence", host, context)
            agent.populate_context_post_run(context)
            summary = json.loads((agent.logs_dir / "acp.summary.json").read_text())
            assert summary["protocol_complete"] and summary["cleanup_complete"]
            assert summary["decoded_evidence_bytes"] > 1024 * 1024
            assert summary["evidence_bytes"] <= 32 * 1024
            protocol.verify_evidence(agent.logs_dir, summary)
        finally:
            await host.stop(True)

    asyncio.run(scenario())


def test_compressed_evidence_preserves_live_bytes_and_closes_after_limit(tmp_path):
    summary = {}
    budget = protocol.EvidenceBudget(summary, 1024, 100_000)
    path = tmp_path / "wire.gz"
    writer = protocol.EvidenceWriter(path, budget)
    reader = protocol.EvidenceReader(path, 1024, 100_000)
    data = ("中文🙂" * 3000 + "\n").encode()
    try:
        writer.write(data)
        assert b"".join(iter(reader.read, b"")) == data
        with pytest.raises(protocol.ProtocolError):
            writer.write(b"x" * 100_001)
    finally:
        writer.close()
    assert gzip.decompress(path.read_bytes()) == data
    assert path.stat().st_size <= 1024
    assert summary["evidence_limit_kind"] == "decoded_bytes"
    assert b"".join(iter(reader.read, b"")) == b""
    reader.finish()
    reader.close()
    path.unlink()


@pytest.mark.parametrize("damage", ["truncated", "trailing", "crc", "expansion"])
def test_evidence_reader_rejects_corruption_and_expansion(tmp_path, damage):
    path = tmp_path / "wire.gz"
    blob = gzip.compress(b"x" * 200_000)
    if damage == "truncated":
        blob = blob[:-1]
    elif damage == "trailing":
        blob += b"extra"
    elif damage == "crc":
        blob = blob[:-8] + bytes([blob[-8] ^ 1]) + blob[-7:]
    path.write_bytes(blob)
    reader = protocol.EvidenceReader(
        path, 1000, 100 if damage == "expansion" else 300_000
    )
    try:
        with pytest.raises(protocol.ProtocolError):
            while reader.read():
                pass
            reader.finish()
    finally:
        reader.close()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Job pipe settlement")
def test_failed_protocol_drains_paused_stdout_before_job_settlement(monkeypatch):
    from psycheval.harbor import acp_harness
    from psycheval.harbor.windows import WindowsProcessAdapter

    monkeypatch.setattr(acp_harness, "FORCED_CLEANUP_RESERVE_SEC", 0.3)

    async def scenario():
        adapter = WindowsProcessAdapter()
        process = await adapter.spawn(
            [
                sys.executable,
                "-I",
                "-S",
                "-c",
                "import os\nwhile True: os.write(1,b'x'*65536)",
            ],
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            limit=1024,
        )
        try:
            async with asyncio.timeout(5):
                while not process.stdout._paused:
                    await asyncio.sleep(0.01)
            summary = {"protocol_complete": False}
            await acp_harness._settle(
                process, None, None, asyncio.Event(), 0.6, summary, adapter
            )
            assert summary["cleanup_complete"]
            assert process.stdout.at_eof()
            assert not adapter._jobs
        finally:

            async def drain():
                while await process.stdout.read(65536):
                    pass

            draining = asyncio.create_task(drain())
            if process in adapter._jobs:
                await adapter.settle(process, 3)
            await asyncio.wait_for(draining, 3)

    asyncio.run(scenario())
