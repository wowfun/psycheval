import os
from types import SimpleNamespace

import pytest

from psycheval.serve import api
from psycheval.serve.api_models import ConfigPatchRequest
from psycheval.serve.harbor_workspace import _atomic_write, config_revision


@pytest.mark.parametrize("target", ["task", "config"])
def test_atomic_writes_close_descriptor_when_stream_creation_fails(
    tmp_path, monkeypatch, target
):
    path = tmp_path / "peval.toml"
    original = b'locale = "en"\n'
    path.write_bytes(original)
    runtime = SimpleNamespace(
        store=SimpleNamespace(paths=SimpleNamespace(config_path=path))
    )
    descriptors = []
    failure = OSError("fixture fdopen failure")

    fdopen = os.fdopen

    def fail_open(descriptor, mode, *args, **kwargs):
        if mode == "wb":
            descriptors.append(descriptor)
            raise failure
        return fdopen(descriptor, mode, *args, **kwargs)

    monkeypatch.setattr(os, "fdopen", fail_open)
    caught = None
    try:
        if target == "task":
            _atomic_write(path, b"replacement")
        else:
            api._patch_workspace_config(
                runtime, ConfigPatchRequest(locale="zh-CN"), config_revision(path)
            )
    except BaseException as exc:
        caught = exc
    leaked = []
    temporary = list(tmp_path.glob(".peval.toml.*"))
    for descriptor in descriptors:
        try:
            os.fstat(descriptor)
        except OSError:
            continue
        leaked.append(descriptor)
        os.close(descriptor)
    for entry in temporary:
        entry.unlink()
    assert descriptors
    assert caught is failure
    assert leaked == []
    assert temporary == []
    assert path.read_bytes() == original
