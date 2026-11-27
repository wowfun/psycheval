from __future__ import annotations

from typing import Any

from .en import EN_MESSAGES
from .zh_cn import ZH_CN_MESSAGES

SUPPORTED_LOCALES = ("en", "zh-CN")

_ALIASES = {
    "en": "en",
    "en-us": "en",
    "zh": "zh-CN",
    "zh-cn": "zh-CN",
}


def normalize_locale(value: Any) -> str:
    if value is None:
        return "en"
    text = str(value).strip()
    if not text:
        return "en"
    normalized = _ALIASES.get(text.lower())
    if normalized:
        return normalized
    supported = ", ".join(SUPPORTED_LOCALES)
    raise ValueError(f"unsupported locale: {text}; supported locales: {supported}")


def messages_for(locale: str) -> dict[str, str]:
    return dict(MESSAGES[normalize_locale(locale)])


MESSAGES: dict[str, dict[str, str]] = {
    "en": EN_MESSAGES,
    "zh-CN": ZH_CN_MESSAGES,
}
