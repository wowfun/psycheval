from pathlib import Path
from unittest.mock import patch

import pytest

from psycheval.config import (
    ToolConfig,
    apply_toml_config,
    load_config,
    write_workspace_timezone,
)
from psycheval.html import render_serve_html
from psycheval.timezones import resolve_timezone, validate_timezone


def test_server_local_timezone_and_actionable_failure():
    with patch(
        "psycheval.timezones.get_localzone_name", return_value="America/New_York"
    ):
        assert resolve_timezone(None) == "America/New_York"
        assert resolve_timezone("Asia/Kolkata") == "Asia/Kolkata"
    for failure in (None, "Invalid/Zone"):
        with patch("psycheval.timezones.get_localzone_name", return_value=failure):
            with pytest.raises(ValueError, match="set timezone.*peval.toml"):
                resolve_timezone(None)


@pytest.mark.parametrize(
    "value", ["UTC", "Asia/Shanghai", "Asia/Kolkata", "America/New_York"]
)
def test_timezone_configuration(value):
    assert apply_toml_config(ToolConfig(), {"timezone": value}).timezone == value


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("asia/shanghai", "Asia/Shanghai"),
        ("utc", "UTC"),
        ("aMERICA/nEW_yORK", "America/New_York"),
    ],
)
def test_timezone_spelling_is_normalized_at_every_configuration_entry(
    tmp_path, value, expected
):
    assert validate_timezone(value) == expected
    assert resolve_timezone(value) == expected
    assert apply_toml_config(ToolConfig(), {"timezone": value}).timezone == expected
    with patch("psycheval.timezones.get_localzone_name", return_value=value):
        assert resolve_timezone(None) == expected
    path = tmp_path / "peval.toml"
    path.touch()
    write_workspace_timezone(path, value)
    assert f'timezone = "{expected}"' in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("value", [8, True, {}, [], b"UTC", "Factory", "factory"])
def test_timezone_validator_rejects_wrong_types_and_unknown_timezone_placeholder(value):
    with pytest.raises(ValueError, match="timezone"):
        validate_timezone(value)


@pytest.mark.parametrize("value", ["", "Invalid/Zone", "../UTC", 8, True])
def test_invalid_timezone_configuration(value):
    with pytest.raises(ValueError):
        apply_toml_config(ToolConfig(), {"timezone": value})


def test_timezone_writer_preserves_other_configuration(tmp_path: Path):
    config = tmp_path / "peval.toml"
    original = '# retained comment\nlocale = "en"\n[adapters.claude]\ndefault_session_root = "sessions"\n'
    config.write_text(original, encoding="utf-8")
    write_workspace_timezone(config, "Asia/Shanghai")
    assert load_config(workspace_root=tmp_path).timezone == "Asia/Shanghai"
    write_workspace_timezone(config, "UTC")
    assert load_config(workspace_root=tmp_path).timezone == "UTC"
    write_workspace_timezone(config, None)
    assert config.read_text(encoding="utf-8").split() == original.split()
    assert load_config(workspace_root=tmp_path).timezone is None


def test_guest_bootstrap_contains_only_effective_timezone():
    html = render_serve_html(role="guest", effective_timezone="Asia/Kolkata")
    assert '"effective_timezone": "Asia/Kolkata"' in html
    assert "data-timezone-form" not in html


def test_unresolvable_server_timezone_exits_cleanly(tmp_path, capsys):
    from psycheval.cli.main import main

    (tmp_path / "peval.toml").touch()
    with patch(
        "psycheval.timezones.get_localzone_name", side_effect=OSError("unavailable")
    ):
        assert main(["serve", "-r", str(tmp_path)]) == 1
    output = capsys.readouterr()
    assert "set timezone" in output.err
    assert "Traceback" not in output.err
    assert "peval serve:" not in output.err
