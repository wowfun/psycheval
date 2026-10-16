"""Owned native ACP subprocess, strict SDK transport and descendant settlement."""

from __future__ import annotations

import asyncio
import ctypes
import json
import os
import shutil
import signal
import sys
from pathlib import Path

from .acp_protocol import (
    FORCED_CLEANUP_RESERVE_SEC,
    KILL_REAP_RESERVE_SEC,
    MAX_FRAME,
    EvidenceBudget,
    EvidenceWriter,
    ProtocolError,
    StrictTransport,
    config_option_choices,
    evidence_manifest,
)


def _subreaper():
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "cannot own ACP descendants")


def _save(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


class Client:
    def __init__(self, summary, directory, policy, stopping, evidence):
        self.evidence = evidence
        self.summary, self.directory, self.policy, self.stopping = (
            summary,
            directory,
            policy,
            stopping,
        )

    async def session_update(self, **kwargs):
        pass  # Authoritative evidence was already recorded at the byte boundary.

    async def request_permission(self, session_id, tool_call, options, **kwargs):
        from acp.schema import RequestPermissionResponse

        preferred = (
            ["allow_once", "allow_always"]
            if self.policy == "allow"
            else ["reject_once", "reject_always"]
        )
        selected = None
        if not self.stopping.is_set():
            for kind in preferred:
                selected = next(
                    (option for option in options if option.kind == kind), None
                )
                if selected is not None:
                    break
        outcome = (
            {"outcome": "selected", "optionId": selected.option_id}
            if selected
            else {"outcome": "cancelled"}
        )
        record = {
            "session_id": session_id,
            "tool_call_id": tool_call.tool_call_id,
            "policy": self.policy,
            "outcome": outcome,
        }
        try:
            self.evidence.retain(record)
        except ProtocolError:
            self.stopping.set()
            raise
        self.summary.setdefault("permissions", []).append(record)
        if selected is None and not self.stopping.is_set():
            self.summary["permission_policy_unsupported"] = True
            self.stopping.set()
        return RequestPermissionResponse.model_validate({"outcome": outcome})


async def _wait_cleanup(work, stopping, deadline):
    task = asyncio.ensure_future(work)
    interrupt = asyncio.create_task(stopping.wait())
    try:
        done, _ = await asyncio.wait(
            [task, interrupt],
            timeout=max(0, deadline - asyncio.get_running_loop().time()),
            return_when=asyncio.FIRST_COMPLETED,
        )
        if task in done:
            return task.result()
    finally:
        interrupt.cancel()
        if not task.done():
            task.cancel()
        await asyncio.gather(task, interrupt, return_exceptions=True)


async def _settle(process, connection, prompt, stopping, budget, summary, adapter=None):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + budget
    forced_at = deadline - FORCED_CLEANUP_RESERVE_SEC
    if (
        prompt is not None
        and not prompt.done()
        and connection is not None
        and summary.get("session_id")
    ):
        try:
            await _wait_cleanup(
                connection.cancel(session_id=summary["session_id"]), stopping, forced_at
            )
            await _wait_cleanup(
                asyncio.shield(prompt), stopping, min(loop.time() + 30, forced_at)
            )
        except Exception:
            pass
    if process.stdin and not process.stdin.is_closing():
        process.stdin.close()
    await _wait_cleanup(process.wait(), stopping, forced_at)
    if adapter is not None:
        await adapter.settle(process, max(0.01, deadline - loop.time()))
        summary["cleanup_complete"] = True
        summary["agent_exit_code"] = process.returncode
        return
    import psutil

    parent = psutil.Process()
    signaled = set()
    delay = 0.02
    while loop.time() < deadline:
        children = await asyncio.to_thread(parent.children, recursive=True)
        if process.returncode is not None and not children:
            summary["cleanup_complete"] = True
            summary["agent_exit_code"] = process.returncode
            return
        for child in children:
            try:
                forced = loop.time() >= deadline - KILL_REAP_RESERVE_SEC
                # psutil's Process identity uses kernel start time on Linux;
                # its public wall-clock create_time can change after NTP updates.
                identity = (child, forced)
                if identity not in signaled:
                    child.kill() if forced else child.terminate()
                    signaled.add(identity)
            except psutil.NoSuchProcess:
                pass
        # asyncio owns the direct ACP child; only reap adopted direct children.
        for child in children:
            try:
                if child.pid != process.pid and child.ppid() == parent.pid:
                    os.waitpid(child.pid, os.WNOHANG)
            except (ChildProcessError, ProcessLookupError, psutil.NoSuchProcess):
                pass
        await asyncio.sleep(min(delay, max(0, deadline - loop.time())))
        delay = min(delay * 2, 0.25)
    summary["cleanup_complete"] = False
    summary["surviving_descendants"] = [
        child.pid for child in await asyncio.to_thread(parent.children, recursive=True)
    ]


async def run(config_path: Path):
    from acp import connect_to_agent

    config = json.loads(config_path.read_text(encoding="utf-8"))
    directory, state = config_path.parent, Path(config["state"])
    summary = {
        "invocation_id": config["invocation_id"],
        "prompt_submitted": False,
        "protocol_complete": True,
        "cleanup_complete": False,
        "stage": "launch",
    }
    stopping = asyncio.Event()
    loop = asyncio.get_running_loop()
    if sys.platform == "win32":
        from .windows import WindowsProcessAdapter

        adapter = WindowsProcessAdapter()
        for signum in (signal.SIGTERM, signal.SIGINT):
            signal.signal(signum, lambda *_: loop.call_soon_threadsafe(stopping.set))
    else:
        adapter = None
        for signum in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(signum, stopping.set)
        _subreaper()
    excluded = ("PEVAL_",) + (
        ("CODEBUDDY_", "WORKBUDDY_", "ACC_PRODUCT_")
        if config.get("tool_result_format") == "codebuddy"
        else ()
    )
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith(excluded)
    }
    environment.update(config["child_env"])
    evidence = EvidenceBudget(
        summary, config["max_evidence_bytes"], config.get("max_decoded_evidence_bytes")
    )
    stderr = None
    process = connection = transport = prompt = None
    stderr_task = None
    setup_deadline = loop.time() + config["handshake_timeout_sec"]

    async def drain_stderr(reader):
        discarded = False
        while chunk := await reader.read(64 * 1024):
            if not discarded:
                try:
                    stderr.write(chunk)
                except ProtocolError:
                    discarded = True
                    stopping.set()
                except OSError:
                    summary.update(protocol_complete=False, error_type="OSError")
                    discarded = True
                    stopping.set()

    async def request(stage, work):
        summary["stage"] = stage
        task = asyncio.create_task(work)
        interrupt = asyncio.create_task(stopping.wait())
        try:
            done, _ = await asyncio.wait(
                [task, interrupt],
                timeout=max(0, setup_deadline - loop.time()),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if task in done:
                return task.result()
            if interrupt in done:
                raise RuntimeError("ACP handshake cancelled")
            raise TimeoutError("ACP handshake deadline exceeded")
        finally:
            interrupt.cancel()
            if not task.done():
                task.cancel()
            await asyncio.gather(task, interrupt, return_exceptions=True)

    try:
        # Reserve every gzip trailer before launching a child.
        stderr = EvidenceWriter(directory / "acp.stderr.log.gz", evidence)
        transport = StrictTransport(
            None,
            None,
            directory,
            summary,
            evidence,
            result_format=config.get("tool_result_format", "acp"),
        )
        kwargs = dict(
            cwd=config["cwd"],
            env=environment,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=MAX_FRAME + 1,
        )
        if adapter is not None:
            process = await adapter.spawn(config["argv"], **kwargs)
        else:
            process = await asyncio.create_subprocess_exec(
                *config["argv"], start_new_session=True, **kwargs
            )
        stderr_task = asyncio.create_task(drain_stderr(process.stderr))
        transport.reader, transport.writer = process.stdout, process.stdin
        if config.get("tool_result_format") == "codebuddy":
            transport.expected_model = config["config_options"].get("model")
        connection = connect_to_agent(
            Client(summary, directory, config["permission_mode"], stopping, evidence),
            transport,
        )
        initialization = await request(
            "initialize",
            connection.initialize(
                protocol_version=1,
                client_capabilities={"session": {"configOptions": {"boolean": {}}}},
            ),
        )
        init = initialization.model_dump(mode="json", by_alias=True, exclude_none=True)
        if init["protocolVersion"] != 1:
            raise ProtocolError("ACP version negotiation failed")
        evidence.retain(init.get("agentInfo"))
        summary["agent_info"] = init.get("agentInfo")
        capabilities = init.get("agentCapabilities", {})
        method = config.get("authenticate_method_id")
        if method is not None:
            if not any(item["id"] == method for item in init.get("authMethods", [])):
                raise ValueError("requested authentication method is unavailable")
            await request("authenticate", connection.authenticate(method_id=method))
        servers = []
        for server in config["mcp_servers"]:
            kind = server.get("transport", "stdio")
            if kind == "streamable-http":
                kind = "http"
            if kind == "stdio":
                command = shutil.which(server["command"])
                if command is None:
                    raise ValueError("MCP executable is unavailable")
                servers.append(
                    {
                        "type": "stdio",
                        "name": server["name"],
                        "command": command,
                        "args": server.get("args", []),
                        "env": [
                            {"name": key, "value": value}
                            for key, value in server.get("env", {}).items()
                        ],
                    }
                )
            else:
                if not capabilities.get("mcpCapabilities", {}).get(kind):
                    raise ValueError("MCP transport is not supported by Agent")
                servers.append(
                    {
                        "type": kind,
                        "name": server["name"],
                        "url": server["url"],
                        "headers": [],
                    }
                )
        setup = {"cwd": config["cwd"], "mcp_servers": servers}
        session_path = state / "session.json"
        if config["action"] in {"run", "inspect"}:
            response = await request("session/new", connection.new_session(**setup))
            summary["session_id"] = response.session_id
            evidence.retain(response.session_id)
            _save(
                session_path,
                {
                    "session_id": response.session_id,
                    "cwd": config["cwd"],
                    "mcp_servers": servers,
                },
            )
        else:
            saved = json.loads(session_path.read_text(encoding="utf-8"))
            if saved["cwd"] != config["cwd"] or saved["mcp_servers"] != servers:
                raise ValueError("ACP restore setup changed")
            summary["session_id"] = saved["session_id"]
            evidence.retain(saved["session_id"])
            if "resume" in capabilities.get("sessionCapabilities", {}):
                response = await request(
                    "session/resume",
                    connection.resume_session(session_id=saved["session_id"], **setup),
                )
            elif capabilities.get("loadSession"):
                response = await request(
                    "session/load",
                    connection.load_session(session_id=saved["session_id"], **setup),
                )
            else:
                raise ValueError("Agent cannot restore this Session")
        summary["models"] = response.model_dump(
            mode="json", by_alias=True, exclude_none=True
        ).get("models", {})
        evidence.retain(summary["models"])
        options = response.model_dump(
            mode="json", by_alias=True, exclude_none=True
        ).get("configOptions", [])
        for identity, value in config["config_options"].items():
            option = next((item for item in options if item["id"] == identity), None)
            if (
                option is None
                or (option["type"] == "boolean" and type(value) is not bool)
                or (
                    option["type"] == "select"
                    and (
                        not isinstance(value, str)
                        or not any(
                            choice["value"] == value
                            for choice in config_option_choices(option)
                        )
                    )
                )
            ):
                raise ValueError("requested configuration is not advertised")
            response = await request(
                "session/set_config_option",
                connection.set_config_option(
                    session_id=summary["session_id"], config_id=identity, value=value
                ),
            )
            options = response.model_dump(
                mode="json", by_alias=True, exclude_none=True
            )["configOptions"]
        current = {option["id"]: option["currentValue"] for option in options}
        if any(
            current.get(identity) != value
            for identity, value in config["config_options"].items()
        ):
            raise ValueError("Agent did not confirm requested configuration")
        evidence.retain(options)
        summary["config_options"] = options
        if config["action"] == "inspect":
            summary["inspection_complete"] = True
            return 0
        if loop.time() >= setup_deadline:
            raise TimeoutError("ACP setup deadline exceeded")
        summary["stage"] = "prompt"
        instruction = (directory / "instruction.txt").read_text(encoding="utf-8")
        prompt = asyncio.create_task(
            connection.prompt(
                session_id=summary["session_id"],
                prompt=[{"type": "text", "text": instruction}],
            )
        )
        interrupt = asyncio.create_task(stopping.wait())
        try:
            done, _ = await asyncio.wait(
                [prompt, interrupt], return_when=asyncio.FIRST_COMPLETED
            )
            if prompt in done:
                result = prompt.result()
                summary["stop_reason"] = result.stop_reason
                metadata = result.model_dump(
                    mode="json", by_alias=True, exclude_none=True
                ).get("_meta", {})
                if config.get("tool_result_format") == "codebuddy" and metadata.get(
                    "codebuddy.ai/errorMessage"
                ):
                    summary["error_type"] = "WorkBuddyPromptError"
            else:
                summary["cancel_requested"] = True
        finally:
            interrupt.cancel()
            await asyncio.gather(interrupt, return_exceptions=True)
    except Exception as exc:
        summary["error_type"] = type(exc).__name__
        # The raw protocol and stderr carry evidence; do not echo payload-bearing exceptions.
    finally:
        cleanup_deadline = loop.time() + config["shutdown_timeout_sec"]

        def cleanup_error(exc):
            summary.update(
                protocol_complete=False, cleanup_error_type=type(exc).__name__
            )
            summary.setdefault("error_type", type(exc).__name__)

        if process is not None:
            try:
                await _settle(
                    process,
                    connection,
                    prompt,
                    stopping,
                    config["shutdown_timeout_sec"],
                    summary,
                    adapter,
                )
            except Exception as exc:
                cleanup_error(exc)
        else:
            summary["cleanup_complete"] = True
        if connection is not None:
            try:
                await asyncio.wait_for(
                    connection.close(), max(0.01, cleanup_deadline - loop.time())
                )
            except Exception as exc:
                cleanup_error(exc)
        if prompt is not None:
            if not prompt.done():
                prompt.cancel()
            try:
                await asyncio.wait_for(
                    asyncio.gather(prompt, return_exceptions=True),
                    max(0.01, cleanup_deadline - loop.time()),
                )
            except Exception as exc:
                cleanup_error(exc)
        if transport is not None:
            try:
                transport.finish()
            except OSError as exc:
                cleanup_error(exc)
        if stderr_task is not None:
            if not stderr_task.done():
                stderr_task.cancel()
            await asyncio.gather(stderr_task, return_exceptions=True)
        try:
            evidence.close()
        except OSError as exc:
            cleanup_error(exc)
        if summary.get("evidence_limit_exceeded"):
            summary["error_type"] = "ProtocolError"
        summary["evidence_bytes"] = evidence.bytes
        summary["decoded_evidence_bytes"] = evidence.decoded_bytes
        summary["evidence_frames"] = evidence.frames
        try:
            summary["evidence_files"] = evidence_manifest(
                directory, evidence.maximum, evidence.decoded_maximum
            )
        except (OSError, ProtocolError) as exc:
            cleanup_error(exc)
        _save(directory / "acp.summary.json", summary)
    return (
        0
        if summary.get("stop_reason") == "end_turn"
        and summary["cleanup_complete"]
        and not summary.get("error_type")
        else 1
    )


def main():
    return asyncio.run(run(Path(sys.argv[1])))


if __name__ == "__main__":
    raise SystemExit(main())
