from psycheval.harbor.redaction import redact_value
from psycheval.redaction import sanitize_credentials


def test_current_secret_formats_and_usage_containers():
    secrets = ["sk-proj-" + "aB_12-" * 8, "sk-ant-api03-" + "abc123-" * 8]
    for secret in secrets:
        assert secret not in redact_value({"message": secret})["message"]
        assert secret not in sanitize_credentials(secret)
    usage = {
        "tokens": {"input": 12, "output": 3},
        "prompt_tokens_details": {"cached_tokens": 5},
        "tokenizer": "cl100k_base",
    }
    assert redact_value(usage) == usage
    assert redact_value(
        {"access_token": "sensitive", "token": {"private": "sensitive"}}
    ) == {"access_token": "<redacted>", "token": "<redacted>"}
