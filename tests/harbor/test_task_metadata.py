from __future__ import annotations

import datetime

import pytest

from psycheval.harbor.task_metadata import (
    MAX_CUSTOM_METADATA_KEYS,
    custom_column_id,
    custom_metadata_group_keys,
    extract_custom_metadata,
    is_custom_column_id,
    parse_custom_column_id,
    validate_custom_metadata_key,
    validate_custom_metadata_value,
)


@pytest.mark.parametrize("key", ["category", "difficulty", "source_case"])
def test_reserved_metadata_keys_are_rejected(key):
    with pytest.raises(ValueError, match="reserved"):
        validate_custom_metadata_key(key)


@pytest.mark.parametrize(
    "bad_key",
    ["", "   ", " lead", "trail ", "bad\nkey", "bad\x00key", "a" * 129, 123],
)
def test_invalid_custom_metadata_keys_are_rejected(bad_key):
    with pytest.raises(ValueError):
        validate_custom_metadata_key(bad_key)


@pytest.mark.parametrize(
    ("raw_key", "expected_id"),
    [
        ("qa_status", "meta:qa_status"),
        ("qa-v1.0_~", "meta:qa-v1.0_~"),
        ("qa status", "meta:qa%20status"),
        ("质检状态", "meta:%E8%B4%A8%E6%A3%80%E7%8A%B6%E6%80%81"),
        ("a!b(c)'d*", "meta:a%21b%28c%29%27d%2A"),
    ],
)
def test_custom_column_id_roundtrip_is_canonical(raw_key, expected_id):
    encoded = custom_column_id(raw_key)
    assert encoded == expected_id
    assert is_custom_column_id(encoded)
    assert parse_custom_column_id(encoded) == raw_key


@pytest.mark.parametrize(
    "bad_id",
    [
        "qa_status",
        "meta:",
        "meta:category",
        "meta:difficulty",
        "meta:source_case",
        "meta:%61",
        "meta:%ZZ",
    ],
)
def test_invalid_or_non_canonical_custom_column_ids_fail(bad_id):
    assert not is_custom_column_id(bad_id)
    with pytest.raises(ValueError):
        parse_custom_column_id(bad_id)


def test_validate_custom_metadata_value_handles_supported_types():
    assert validate_custom_metadata_value(None) is None
    assert validate_custom_metadata_value(True) is True
    assert validate_custom_metadata_value(False) is False
    assert validate_custom_metadata_value(0) == 0
    assert type(validate_custom_metadata_value(0)) is int
    assert validate_custom_metadata_value(-3.5) == -3.5
    assert validate_custom_metadata_value("OK") == "OK"
    assert validate_custom_metadata_value([" a ", "b", "a"]) == ["a", "b"]


@pytest.mark.parametrize(
    "bad_value",
    [
        "",
        "   ",
        "bad\x00text",
        "x" * (16 * 1024 + 1),
        float("nan"),
        float("inf"),
        1 << 63,
        [],
        [""],
        [1, 2],
        {"nested": True},
    ],
)
def test_validate_custom_metadata_value_rejects_invalid_values(bad_value):
    with pytest.raises(ValueError):
        validate_custom_metadata_value(bad_value)


def test_extract_custom_metadata_excludes_reserved_and_normalizes_toml_values():
    raw = {
        "category": "coding",
        "difficulty": "hard",
        "source_case": "office-01",
        "reviewer": "alice",
        "priority": 1,
        "verified": False,
        "issues": ["leak", "missing"],
        "reviewed_on": datetime.date(2026, 11, 26),
        "nested": {"a": 1, "ts": datetime.datetime(2026, 11, 26, 12, 0)},
        "bad_float": float("nan"),
    }
    projected, diagnostics = extract_custom_metadata(raw)
    assert projected == {
        "reviewer": "alice",
        "priority": 1,
        "verified": False,
        "issues": ["leak", "missing"],
        "reviewed_on": "2026-11-26",
        "nested": {"a": 1, "ts": "2026-11-26T12:00:00"},
    }
    assert len(diagnostics) == 1
    assert "bad_float" in diagnostics[0]


def test_extract_custom_metadata_enforces_key_and_byte_limits():
    many = {f"k{i:03d}": "v" for i in range(MAX_CUSTOM_METADATA_KEYS + 5)}
    projected, diagnostics = extract_custom_metadata(many)
    assert len(projected) == MAX_CUSTOM_METADATA_KEYS
    assert any("exceeds" in msg for msg in diagnostics)

    huge = {"small": "ok", "giant": "x" * (70 * 1024)}
    projected, diagnostics = extract_custom_metadata(huge)
    assert projected == {"small": "ok"}
    assert any("giant" in msg for msg in diagnostics)


def test_validate_custom_metadata_allows_unicode_format_chars_and_rejects_cc():
    # Unicode Cf format characters (ZWJ emoji, soft hyphen, RTL mark) are allowed.
    for text in ("👨‍👩‍👧‍👦", "soft\u00adhyphen", "rtl\u200ftext"):
        assert validate_custom_metadata_key(text) == text
        assert validate_custom_metadata_value(text) == text
        assert validate_custom_metadata_value([text]) == [text]
    # True C0/C1 control characters (Cc) are still rejected.
    for bad in ("bad\x00val", "bad\x07val", "bad\x1bval", "bad\x7fval"):
        with pytest.raises(ValueError, match="control"):
            validate_custom_metadata_key(bad)
        with pytest.raises(ValueError, match="control"):
            validate_custom_metadata_value(bad)


def test_custom_metadata_group_keys_covers_scalars_booleans_and_lists():
    assert custom_metadata_group_keys(None) == [None]
    assert custom_metadata_group_keys("  ") == [None]
    assert custom_metadata_group_keys("OK") == ["OK"]
    assert custom_metadata_group_keys(True) == ["true"]
    assert custom_metadata_group_keys(False) == ["false"]
    assert custom_metadata_group_keys(0) == ["0"]
    assert custom_metadata_group_keys(2.0) == ["2"]
    assert custom_metadata_group_keys(2.5) == ["2.5"]
    assert custom_metadata_group_keys(["b", "a", "b", ""]) == ["b", "a"]
    assert custom_metadata_group_keys([]) == [None]


def test_task_scoring_inventory_files_metadata_diagnostics_separately(tmp_path):
    from psycheval.harbor.task_scoring import task_scoring_inventory

    task_dir = tmp_path / "demo"
    task_dir.mkdir()
    (task_dir / "instruction.md").write_text("Check metadata", encoding="utf-8")
    (task_dir / "task.toml").write_text(
        'schema_version = "1.4"\n'
        "[task]\n"
        'name = "local/demo"\n'
        "[metadata]\n"
        "bad_nan = nan\n",
        encoding="utf-8",
    )
    inventory = task_scoring_inventory(
        task_dir, read_bytes=lambda path: path.read_bytes()
    )
    assert inventory["scoring_diagnostics"] == []
    assert len(inventory["metadata_diagnostics"]) == 1
    assert "bad_nan" in inventory["metadata_diagnostics"][0]
