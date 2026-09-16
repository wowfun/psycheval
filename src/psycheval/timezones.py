"""Workspace display timezone validation and server-local resolution."""

from functools import cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from tzlocal import get_localzone_name


@cache
def _timezone_names() -> dict[str, str]:
    # Factory is tzdb's unknown-timezone placeholder, not a display timezone.
    return {
        name.casefold(): name for name in available_timezones() if name != "Factory"
    }


def validate_timezone(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("timezone must be an IANA timezone name string or null")
    try:
        normalized = _timezone_names().get(value.casefold())
        if normalized is None:
            raise ValueError("unknown timezone name")
        ZoneInfo(normalized)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise ValueError(
            f"Invalid timezone {value!r}; set timezone in peval.toml to an IANA "
            'name such as "Asia/Shanghai" or "UTC"'
        ) from exc
    return normalized


def resolve_timezone(value: str | None) -> str:
    normalized = validate_timezone(value)
    if normalized is not None:
        return normalized
    try:
        local = validate_timezone(get_localzone_name())
        if not local:
            raise ValueError("system timezone has no IANA name")
        return local
    except (ValueError, OSError, KeyError, ZoneInfoNotFoundError) as exc:
        raise ValueError(
            'Cannot resolve server local timezone; set timezone = "UTC" or an '
            f"IANA timezone name in peval.toml: {exc}"
        ) from exc
