import builtins
import json
from pathlib import Path

import pytest
from harbor.utils.trajectory_validator import TrajectoryValidator

from psycheval.harbor.trajectory_validation import load_validated_trajectory


def trajectory():
    return {
        "schema_version": "ATIF-v1.7",
        "session_id": "fixture",
        "agent": {"name": "fixture", "version": "1"},
        "steps": [{"step_id": 1, "source": "user", "message": "中文任务 🎉"}],
    }


@pytest.mark.parametrize("default_encoding", ["cp936", "utf-8"])
def test_trajectory_decoding_preserves_unicode_without_changing_bytes(
    tmp_path,
    monkeypatch,
    default_encoding,
):
    payload = trajectory()
    path = tmp_path / "trajectory.json"
    original = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    path.write_bytes(original)
    read_text, open_file = Path.read_text, builtins.open

    def locale_read_text(self, encoding=None, **kwargs):
        return read_text(self, encoding=encoding or default_encoding, **kwargs)

    def locale_open(file, mode="r", buffering=-1, encoding=None, **kwargs):
        if "b" not in mode and encoding is None:
            encoding = default_encoding
        return open_file(file, mode, buffering=buffering, encoding=encoding, **kwargs)

    monkeypatch.setattr(Path, "read_text", locale_read_text)
    monkeypatch.setattr(builtins, "open", locale_open)
    assert load_validated_trajectory(path) == payload
    assert path.read_bytes() == original
    assert list(tmp_path.glob("*.json")) == [path]


@pytest.mark.parametrize("content", [b"[]", b"null", b"42", b'"{}"'])
def test_trajectory_file_requires_a_json_object(tmp_path, content):
    path = tmp_path / "trajectory.json"
    path.write_bytes(content)
    with pytest.raises(ValueError, match="must be an object"):
        load_validated_trajectory(path)
    assert path.read_bytes() == content


@pytest.mark.parametrize("content", [b"\xff", b"{", b"{}", b'{"steps": [42]}'])
def test_invalid_encoding_json_and_schema_remain_rejected(tmp_path, content):
    path = tmp_path / "trajectory.json"
    path.write_bytes(content)
    with pytest.raises(ValueError):
        load_validated_trajectory(path)
    assert path.read_bytes() == content


def test_missing_trajectory_file_is_not_created(tmp_path):
    path = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        load_validated_trajectory(path)
    assert not path.exists()


@pytest.mark.parametrize("location", ["message", "observation"])
@pytest.mark.parametrize(
    "kind,exists",
    [
        ("relative", True),
        ("relative", False),
        ("absolute", True),
        ("absolute", False),
        ("url", False),
    ],
)
def test_image_references_keep_harbor_rules_and_original_directory(
    tmp_path,
    monkeypatch,
    location,
    kind,
    exists,
):
    logs = tmp_path / "logs"
    logs.mkdir()
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    relative = Path("assets/截图.png")
    # A same-named image in cwd must not satisfy a trajectory-relative reference.
    (cwd / relative).parent.mkdir()
    (cwd / relative).write_bytes(b"unrelated image")
    target = logs / relative
    if exists:
        target.parent.mkdir()
        target.write_bytes(b"image fixture")
    image_path = {
        "relative": relative.as_posix(),
        "absolute": str(target),
        "url": "https://example.invalid/image.png",
    }[kind]
    content = [
        {"type": "image", "source": {"media_type": "image/png", "path": image_path}}
    ]
    payload = trajectory()
    if location == "message":
        payload["steps"][0]["message"] = content
    else:
        payload["steps"].append(
            {
                "step_id": 2,
                "source": "agent",
                "message": "截图",
                "tool_calls": [
                    {
                        "tool_call_id": "capture",
                        "function_name": "capture",
                        "arguments": {},
                    }
                ],
                "observation": {
                    "results": [{"source_call_id": "capture", "content": content}]
                },
            }
        )
    path = logs / "trajectory.json"
    original = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    path.write_bytes(original)
    reference = logs / "reference.json"
    reference.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    upstream = TrajectoryValidator()
    valid = upstream.validate(reference)
    assert valid == (exists or kind == "url")
    if valid:
        assert load_validated_trajectory(path) == payload
    else:
        with pytest.raises(ValueError) as caught:
            load_validated_trajectory(path)
        assert str(caught.value) == "; ".join(upstream.errors)
    assert path.read_bytes() == original
