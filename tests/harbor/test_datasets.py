from __future__ import annotations

from pathlib import Path

import pytest

from psycheval.harbor.datasets import HarborDatasetError, resolve_harbor_dataset


def test_dataset_resolution_uses_explicit_paths_and_normalized_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "suite/task").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    result = resolve_harbor_dataset(dataset_id=" suite ", path="suite")
    assert result.id == "suite"
    assert result.source_root == tmp_path / "suite"
    assert result.task_root == result.source_root
    assert result.task_names == ("task",)
    assert not result.read_only


@pytest.mark.parametrize(
    "arguments, message",
    [
        ({"dataset_id": "../invalid", "path": "."}, "path-safe identifier"),
        ({"dataset_id": "suite", "path": ""}, "non-empty string"),
        ({"dataset_id": "suite", "path": ".", "format": "unknown"}, "unsupported"),
    ],
)
def test_dataset_inputs_raise_domain_errors(arguments: dict, message: str) -> None:
    with pytest.raises(HarborDatasetError, match=message):
        resolve_harbor_dataset(**arguments)


@pytest.mark.parametrize("path", [".", Path("."), Path("")])
def test_dataset_accepts_an_explicit_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, path: str | Path
) -> None:
    monkeypatch.chdir(tmp_path)
    result = resolve_harbor_dataset(dataset_id="suite", path=path)
    assert result.source_root == tmp_path


@pytest.mark.parametrize("identifier", [None, False, 0, 1, [], {}])
def test_dataset_ids_must_be_strings(tmp_path: Path, identifier: object) -> None:
    with pytest.raises(HarborDatasetError, match="must be a string"):
        resolve_harbor_dataset(dataset_id=identifier, path=tmp_path)
