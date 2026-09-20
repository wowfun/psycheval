from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from psycheval.serve.path_picker import tkinter_file_paths


@pytest.mark.parametrize("multiple", [False, True])
@pytest.mark.parametrize("outcome", ["selected", "cancelled", "failed"])
def test_native_chooser_is_visible_and_disposes_its_owner(
    monkeypatch: pytest.MonkeyPatch, tmp_path, multiple: bool, outcome: str
) -> None:
    root = Mock()
    paths = [str(tmp_path / "中文 report.md"), str(tmp_path / "second.html")]

    def choose(*, parent):
        assert parent is root
        root.attributes.assert_any_call("-topmost", True)
        root.withdraw.assert_called_once()
        root.destroy.assert_not_called()
        if outcome == "failed":
            raise RuntimeError("picker unavailable")
        if outcome == "cancelled":
            return () if multiple else ""
        return tuple(paths) if multiple else paths[0]

    dialogs = SimpleNamespace(askopenfilename=choose, askopenfilenames=choose)
    monkeypatch.setitem(
        sys.modules, "tkinter", SimpleNamespace(Tk=lambda: root, filedialog=dialogs)
    )
    if outcome == "failed":
        with pytest.raises(RuntimeError, match="picker unavailable"):
            tkinter_file_paths(multiple=multiple)
    else:
        expected = [] if outcome == "cancelled" else paths if multiple else paths[:1]
        assert tkinter_file_paths(multiple=multiple) == expected
    root.destroy.assert_called_once()
