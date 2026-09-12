import io
import subprocess
import sys
import zipfile

import pytest

from psycheval.redaction import (
    protect_retained_bytes,
    redact_credentials,
    redact_retained_text,
)


def test_metadata_with_python_containers_still_filters_credentials():
    value = {1: ("sk-abcdefghijklmnop1234", {"api_key": "private"})}
    protected = redact_credentials(value)
    assert protected == {1: ["[redacted]", {"api_key": "[redacted]"}]}


@pytest.mark.parametrize("suffix", ['"}', '"', ""])
def test_partial_json_credential_values_remain_redacted(suffix):
    value = '{"api_key": "private-literal' + suffix
    assert "private-literal" not in redact_retained_text(value)
    assert "[redacted]" in redact_retained_text(value)


def test_invalid_json_escape_stays_readable():
    value = r'{"bad\x": "retained"}'
    assert redact_retained_text(value) == value


def test_malformed_text_filters_multiple_fields_and_preserves_references():
    text = 'prefix {"api_key":"alpha", "password":"${PASSWORD}", "secret":"beta'
    assert (
        redact_retained_text(text)
        == 'prefix {"api_key":"[redacted]", "password":"${PASSWORD}", "secret":"[redacted]"'
    )


def test_escaped_unterminated_text_is_read_with_bounded_work():
    source = """
from psycheval.redaction import redact_retained_text
value = '"' + '\\\\"' * 100000 + '\\\\'
assert redact_retained_text(value) == value
"""
    subprocess.run(
        [sys.executable, "-c", source], check=True, timeout=10, capture_output=True
    )


def test_binary_artifact_credentials_are_rejected_including_zip_members():
    secret = b"sk-abcdefghijklmnop1234"
    with pytest.raises(ValueError, match="credential"):
        protect_retained_bytes(b"\x00" + secret, text=False, limit=10000)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/sharedStrings.xml", b"<value>" + secret + b"</value>")
    with pytest.raises(ValueError, match="credential"):
        protect_retained_bytes(buffer.getvalue(), text=False, limit=10000)


def test_archive_expansion_is_bounded():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/data.xml", b"x" * 10000)
    with pytest.raises(ValueError, match="inspection limit"):
        protect_retained_bytes(buffer.getvalue(), text=False, limit=100)


def test_corrupt_deflate_is_a_controlled_validation_error():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("content", b"plain text" * 100)
    data = bytearray(buffer.getvalue())
    data[30 + len("content")] = 7  # Invalid DEFLATE block type in the first member.
    with pytest.raises(ValueError, match="cannot be inspected"):
        protect_retained_bytes(bytes(data), text=False, limit=10000)
