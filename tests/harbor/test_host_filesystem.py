from __future__ import annotations

import asyncio
import logging
import os
import platform
import stat
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from harbor.models.task.config import ArtifactConfig
from harbor.trial.artifact_handler import ArtifactHandler

from tests.harbor.test_environment import make_environment


def filesystem_host(tmp_path):
    return make_environment(
        tmp_path / "host",
        host_access={"filesystem": True, "process": False},
        environment_kwargs={
            "workspace_baseline": "none",
            "workdir_root": tmp_path / "copies",
        },
    )


def test_mounted_artifact_collection_preserves_source_bytes(tmp_path):
    async def scenario():
        host = filesystem_host(tmp_path)
        await host.start(False)
        try:
            evidence = host.native_path("/logs/artifacts/report.txt")
            evidence.write_bytes(b"retained evidence")
            excluded = evidence.with_suffix(".tmp")
            excluded.write_bytes(b"excluded source")
            handler = ArtifactHandler(artifacts=[], logger=logging.getLogger("test"))
            entry = await handler._download_artifact(
                source_env=host,
                artifacts_dir=host.trial_paths.artifacts_dir,
                artifact=ArtifactConfig(source="/logs/artifacts", exclude=["*.tmp"]),
                convention_source="/logs/artifacts",
            )
            assert entry.status == "ok"
            assert evidence.read_bytes() == b"retained evidence"
            assert excluded.read_bytes() == b"excluded source"
            alias = tmp_path / "hardlink.txt"
            os.link(evidence, alias)
            await host.download_file("/logs/artifacts/report.txt", alias)
            assert evidence.read_bytes() == alias.read_bytes() == b"retained evidence"
        finally:
            await host.stop(True)

    asyncio.run(scenario())


def test_download_preserves_file_mode_and_timestamps(tmp_path):
    async def scenario():
        host = filesystem_host(tmp_path)
        await host.start(False)
        try:
            source = host.work_dir / "run.sh"
            source.write_bytes(b"#!/bin/sh\necho ok\n")
            source.chmod(0o755)
            os.utime(source, ns=(1_000_000_000_000, 2_000_000_000_000))
            for method in ("download_file", "download_dir", "download_dir_filtered"):
                target = tmp_path / method
                if method == "download_file":
                    await host.download_file("run.sh", target / "run.sh")
                elif method == "download_dir":
                    await host.download_dir(".", target)
                else:
                    await host.download_dir_filtered(source_dir=".", target_dir=target)
                copied = target / "run.sh"
                assert copied.read_bytes() == source.read_bytes()
                assert copied.stat().st_mtime_ns == source.stat().st_mtime_ns
                if os.name != "nt":
                    assert stat.S_IMODE(copied.stat().st_mode) == 0o755
        finally:
            await host.stop(True)

    asyncio.run(scenario())


def test_relative_directories_resolve_from_task_workdir(tmp_path):
    async def scenario():
        host = filesystem_host(tmp_path)
        await host.start(False)
        try:
            await host.ensure_dirs(["output/nested"], chmod=False)
            (host.work_dir / "output/nested/value").touch()
            await host.empty_dirs(["output"], chmod=False)
            assert list((host.work_dir / "output").iterdir()) == []
            await host.reset_dirs(remove_dirs=["output"], create_dirs=["next"])
            assert not (host.work_dir / "output").exists()
            assert (host.work_dir / "next").is_dir()
        finally:
            await host.stop(True)

    asyncio.run(scenario())


@pytest.mark.parametrize("filtered", [False, True])
def test_directory_download_rejects_target_nested_in_source(tmp_path, filtered):
    async def scenario():
        host = filesystem_host(tmp_path)
        await host.start(False)
        target = host.work_dir / "nested-download"
        try:
            with pytest.raises(ValueError, match="inside its source"):
                if filtered:
                    await host.download_dir_filtered(source_dir=".", target_dir=target)
                else:
                    await host.download_dir(".", target)
            assert not target.exists()
        finally:
            await host.stop(True)

    asyncio.run(scenario())


@pytest.mark.skipif(platform.system() != "Windows", reason="native Windows junction")
def test_empty_directory_replaces_junction_without_touching_target(tmp_path):
    import _winapi

    async def scenario():
        host = filesystem_host(tmp_path)
        await host.start(False)
        outside = tmp_path / "outside"
        outside.mkdir()
        sentinel = outside / "keep.txt"
        sentinel.write_bytes(b"keep")
        link = host.work_dir / "link"
        _winapi.CreateJunction(str(outside), str(link))
        try:
            await host.empty_dirs(["/app/link"], chmod=False)
            assert sentinel.read_bytes() == b"keep"
            assert link.is_dir() and not link.is_junction()
            assert list(link.iterdir()) == []
        finally:
            if link.is_junction():
                link.rmdir()
            await host.stop(True)

    asyncio.run(scenario())


def test_task_git_pointer_cannot_mutate_external_repository(tmp_path):
    original = tmp_path / "original"
    original.mkdir()
    git_env = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    git_env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)

    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(original), *args], env=git_env, text=True
        ).strip()

    git("init", "-q", "-b", "main")
    git("config", "user.name", "Original Owner")
    git("config", "user.email", "owner@example.test")
    (original / "source.txt").write_text("source", encoding="utf-8")
    git("add", ".")
    git("-c", "commit.gpgSign=false", "commit", "-q", "-m", "original")
    before = git("rev-parse", "HEAD")
    host = make_environment(tmp_path / "host")
    pointer = host.environment_dir / ".git"
    pointer.write_text(f"gitdir: {(original / '.git').as_posix()}\n", encoding="utf-8")
    pointer_bytes = pointer.read_bytes()

    async def scenario():
        await host.start(False)
        try:
            assert git("rev-parse", "HEAD") == before
            assert git("config", "user.name") == "Original Owner"
            assert pointer.read_bytes() == pointer_bytes
            assert (host.work_dir / ".git").is_dir()
        finally:
            await host.stop(True)

    asyncio.run(scenario())


@pytest.mark.parametrize("cancel", [False, True])
def test_stop_and_cancellation_drain_filesystem_workers(tmp_path, monkeypatch, cancel):
    from psycheval.harbor import environment

    async def scenario():
        host = filesystem_host(tmp_path)
        await host.start(False)
        workspace = host.work_dir
        (workspace / "file").write_bytes(b"source")
        entered, release = threading.Event(), threading.Event()
        original = environment._copy_native_file

        def held_copy(source, target, **kwargs):
            entered.set()
            assert release.wait(5), "filesystem worker was not released"
            assert workspace.is_dir()
            original(source, target, **kwargs)

        monkeypatch.setattr(environment, "_copy_native_file", held_copy)
        transfer = asyncio.create_task(host.download_file("file", tmp_path / "result"))
        stopper = None
        try:
            assert await asyncio.to_thread(entered.wait, 2)
            assert not transfer.done(), "filesystem work blocked the event loop"
            if cancel:
                transfer.cancel()
            stopper = asyncio.create_task(host.stop(True))
            await asyncio.sleep(0.02)
            assert not stopper.done()
            assert not transfer.done()
            assert workspace.exists()
        finally:
            release.set()
            results = await asyncio.gather(transfer, return_exceptions=True)
            if stopper is not None:
                await stopper
            await host.stop(True)
        assert isinstance(results[0], asyncio.CancelledError)
        assert not (tmp_path / "result").exists()
        assert not workspace.exists()

    asyncio.run(scenario())


def test_download_cancellation_discards_partial_file(tmp_path, monkeypatch):
    from psycheval.harbor import environment

    source, target = tmp_path / "source", tmp_path / "target"
    source.write_bytes(b"a" * (3 * 1024 * 1024))
    target.write_bytes(b"keep previous destination")
    cancel = threading.Event()
    fdopen = os.fdopen
    reads = []

    class CancellingReader:
        def __init__(self, handle):
            self.handle = handle

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.handle.close()

        def read(self, size):
            chunk = self.handle.read(size)
            reads.append(len(chunk))
            cancel.set()
            return chunk

    def cancelling_fdopen(descriptor, mode, *args, **kwargs):
        handle = fdopen(descriptor, mode, *args, **kwargs)
        return CancellingReader(handle) if mode == "rb" else handle

    monkeypatch.setattr(environment.os, "fdopen", cancelling_fdopen)
    with pytest.raises(asyncio.CancelledError):
        environment._copy_native_file(source, target, cancel=cancel)
    assert 0 < sum(reads) <= 1024 * 1024
    assert target.read_bytes() == b"keep previous destination"
    assert not list(tmp_path.glob(".peval-copy-*"))


@pytest.mark.parametrize("filtered", [False, True])
def test_directory_download_cancels_before_copying_remaining_files(
    tmp_path, monkeypatch, filtered
):
    from psycheval.harbor import environment

    async def scenario():
        host = filesystem_host(tmp_path)
        await host.start(False)
        source = host.work_dir / "source"
        source.mkdir()
        for index in range(20):
            (source / f"{index}.txt").write_bytes(b"content")
        target = tmp_path / "download"
        entered, release = threading.Event(), threading.Event()
        original = environment._copy_native_file

        def held_copy(source, target, **kwargs):
            original(source, target, **kwargs)
            entered.set()
            assert release.wait(5)

        monkeypatch.setattr(environment, "_copy_native_file", held_copy)
        transfer = asyncio.create_task(
            host.download_dir_filtered(source_dir="source", target_dir=target)
            if filtered
            else host.download_dir("source", target)
        )
        try:
            assert await asyncio.to_thread(entered.wait, 2)
            transfer.cancel()
            await asyncio.sleep(0)
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await transfer
            assert len(list(target.glob("*.txt"))) == 1
        finally:
            release.set()
            await asyncio.gather(transfer, return_exceptions=True)
            await host.stop(True)

    asyncio.run(scenario())


def test_filesystem_workers_leave_executor_capacity_for_other_work(
    tmp_path, monkeypatch
):
    from psycheval.harbor import environment

    async def scenario():
        loop = asyncio.get_running_loop()
        loop.set_default_executor(ThreadPoolExecutor(max_workers=8))
        host = filesystem_host(tmp_path)
        await host.start(False)
        (host.work_dir / "file").write_bytes(b"content")
        entered = asyncio.Event()
        release = threading.Event()
        original = environment._copy_native_file

        def held_copy(source, target, **kwargs):
            loop.call_soon_threadsafe(entered.set)
            assert release.wait(5)
            original(source, target, **kwargs)

        monkeypatch.setattr(environment, "_copy_native_file", held_copy)
        transfers = [
            asyncio.create_task(host.download_file("file", tmp_path / str(index)))
            for index in range(16)
        ]
        try:
            await asyncio.wait_for(entered.wait(), 2)
            assert await asyncio.wait_for(asyncio.to_thread(lambda: True), 1)
        finally:
            release.set()
            await asyncio.gather(*transfers, return_exceptions=True)
            await host.stop(True)

    asyncio.run(scenario())
