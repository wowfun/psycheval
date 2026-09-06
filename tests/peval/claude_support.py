"""Owned Claude Code transcripts; no dependence on installed Agent state."""

import json
from pathlib import Path


def event(kind, *, content=None, message_id=None, agent=None, seq=1, **extra):
    value = {
        "type": kind,
        "sessionId": "root-session",
        "uuid": f"{agent or 'main'}-{seq}",
        "timestamp": f"2026-01-01T00:00:{seq % 60:02d}.000Z",
        "version": "2.1.0",
    }
    if agent:
        value.update(agentId=agent, isSidechain=True)
    if kind in {"assistant", "user"}:
        value["message"] = {"role": kind, "content": content}
        if kind == "assistant":
            value["message"].update(
                id=message_id or f"msg-{agent or 'main'}-{seq}",
                model="claude-test",
                usage={
                    "input_tokens": 3,
                    "cache_read_input_tokens": 4,
                    "cache_creation_input_tokens": 5,
                    "output_tokens": 6,
                },
            )
    elif content is not None:
        value["content"] = content
    value.update(extra)
    return value


def write_events(path: Path, events):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events),
        encoding="utf-8",
    )
    return path


def family(project: Path) -> Path:
    def transcript(agent, children):
        calls = [
            {
                "type": "tool_use",
                "id": f"call-{child}",
                "name": "Agent",
                "input": {"prompt": "Inspect fixture"},
            }
            for child in children
        ]
        records = [
            event("user", content="Start fixture", agent=agent),
            event(
                "assistant",
                content=[{"type": "text", "text": "Working"}, *calls],
                agent=agent,
                seq=2,
            ),
        ]
        records.extend(
            event(
                "user",
                agent=agent,
                seq=3 + i,
                content=[
                    {
                        "type": "tool_result",
                        "tool_use_id": f"call-{child}",
                        "content": "",
                    }
                ],
                toolUseResult={"agentId": child, "outputFile": "/must/not/read"},
            )
            for i, child in enumerate(children)
        )
        return records

    root = write_events(
        project / "root-session.jsonl",
        transcript(None, [f"child-{i}" for i in range(6)]),
    )
    directory = project / "root-session" / "subagents"
    for i in range(6):
        agent = f"child-{i}"
        write_events(
            directory / f"agent-{agent}.jsonl",
            transcript(agent, ["grand-0", "grand-1"] if i == 0 else []),
        )
    for i in range(2):
        agent = f"grand-{i}"
        write_events(directory / f"agent-{agent}.jsonl", transcript(agent, []))
    return root
