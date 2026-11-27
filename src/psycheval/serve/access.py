from __future__ import annotations

import math
import os
import secrets
import time
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from http.cookies import CookieError, SimpleCookie
from pathlib import Path
from threading import Lock

from dotenv import dotenv_values

ADMIN_PASSWORD_ENV = "PEVAL_ADMIN_PASSWORD"
ANNOTATOR_PASSWORD_ENV = "PEVAL_ANNOTATOR_PASSWORD"
ADMIN_ROLE = "admin"
ANNOTATOR_ROLE = "annotator"
GUEST_ROLE = "guest"
SESSION_COOKIE_NAME = "peval_session"
SESSION_IDLE_SECONDS = 12 * 60 * 60
LOGIN_WINDOW_SECONDS = 60
LOGIN_FAILURE_LIMIT = 5
MAX_USER_ID_BYTES = 64

__all__ = [
    "ADMIN_PASSWORD_ENV",
    "ANNOTATOR_PASSWORD_ENV",
    "ADMIN_ROLE",
    "ANNOTATOR_ROLE",
    "GUEST_ROLE",
    "SESSION_COOKIE_NAME",
    "SESSION_IDLE_SECONDS",
    "LOGIN_WINDOW_SECONDS",
    "LOGIN_FAILURE_LIMIT",
    "MAX_USER_ID_BYTES",
    "AuthenticationDisabled",
    "InvalidCredentials",
    "LoginRateLimited",
    "ServeAccess",
    "SessionIdentity",
    "resolve_admin_password",
    "resolve_annotator_password",
    "validate_user_id",
]


class InvalidCredentials(ValueError):
    pass


class AuthenticationDisabled(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class LoginRateLimited(ValueError):
    retry_after: int


@dataclass(frozen=True, slots=True)
class SessionIdentity:
    role: str
    user_id: str | None = None


@dataclass(slots=True)
class _SessionRecord:
    role: str
    user_id: str | None
    last_seen: float


def validate_user_id(value: str | None) -> str:
    if not isinstance(value, str):
        raise ValueError("user_id is required")
    normalized = value.strip()
    if not normalized:
        raise ValueError("user_id must not be empty")
    if len(normalized.encode("utf-8")) > MAX_USER_ID_BYTES:
        raise ValueError(f"user_id must be at most {MAX_USER_ID_BYTES} UTF-8 bytes")
    if any(
        ch in {"\n", "\r", "\t"} or unicodedata.category(ch) == "Cc"
        for ch in normalized
    ):
        raise ValueError("user_id must be a single line without control characters")
    if normalized.casefold() == ADMIN_ROLE:
        raise ValueError("user_id 'admin' is reserved")
    return normalized


def _resolve_env_password(
    workspace_root: str | Path,
    env_name: str,
    *,
    environ: Mapping[str, str] | None = None,
) -> str | None:
    values = os.environ if environ is None else environ
    process_value = values.get(env_name)
    if process_value:
        return process_value

    env_path = Path(workspace_root).expanduser() / ".env"
    if not env_path.exists():
        return None
    if env_path.is_symlink() or not env_path.is_file():
        raise ValueError(f"workspace dotenv must be a regular file: {env_path}")
    try:
        dotenv = dotenv_values(env_path, encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"failed to read workspace dotenv: {env_path}") from exc
    file_value = dotenv.get(env_name)
    return file_value if isinstance(file_value, str) and file_value else None


def resolve_admin_password(
    workspace_root: str | Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> str | None:
    return _resolve_env_password(workspace_root, ADMIN_PASSWORD_ENV, environ=environ)


def resolve_annotator_password(
    workspace_root: str | Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> str | None:
    return _resolve_env_password(
        workspace_root, ANNOTATOR_PASSWORD_ENV, environ=environ
    )


class ServeAccess:
    """Own serve authentication, sessions, and login throttling."""

    def __init__(
        self,
        password: str | None,
        *,
        annotator_password: str | None = None,
        now: Callable[[], float] = time.monotonic,
        token_factory: Callable[[], str] | None = None,
    ) -> None:
        self._password = password or None
        self._annotator_password = annotator_password or None
        self._now = now
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(32))
        self._sessions: dict[str, _SessionRecord] = {}
        self._failures: dict[str, list[float]] = {}
        self._lock = Lock()

    @classmethod
    def from_workspace(
        cls,
        workspace_root: str | Path,
        *,
        environ: Mapping[str, str] | None = None,
        now: Callable[[], float] = time.monotonic,
        token_factory: Callable[[], str] | None = None,
    ) -> ServeAccess:
        return cls(
            resolve_admin_password(workspace_root, environ=environ),
            annotator_password=resolve_annotator_password(
                workspace_root, environ=environ
            ),
            now=now,
            token_factory=token_factory,
        )

    @property
    def admin_login_enabled(self) -> bool:
        return self._password is not None

    @property
    def annotator_login_enabled(self) -> bool:
        return self._annotator_password is not None

    @property
    def authentication_enabled(self) -> bool:
        return self.admin_login_enabled or self.annotator_login_enabled

    def session_payload(self, cookie_header: str | None) -> dict[str, object]:
        current = self.identity(cookie_header)
        return {
            "authentication_enabled": self.authentication_enabled,
            "admin_login_enabled": self.admin_login_enabled,
            "annotator_login_enabled": self.annotator_login_enabled,
            "role": current.role,
            "user_id": current.user_id,
        }

    def identity(self, cookie_header: str | None) -> SessionIdentity:
        if not self.authentication_enabled:
            return SessionIdentity(ADMIN_ROLE, "admin")
        token = self._session_token(cookie_header)
        now = self._now()
        with self._lock:
            self._prune_expired(now)
            if token is None:
                return SessionIdentity(GUEST_ROLE, None)
            record = self._sessions.get(token)
            if record is None:
                return SessionIdentity(GUEST_ROLE, None)
            record.last_seen = now
            return SessionIdentity(record.role, record.user_id)

    def role(self, cookie_header: str | None) -> str:
        return self.identity(cookie_header).role

    def login_session(
        self,
        password: str,
        client_address: str,
        *,
        role: str = ADMIN_ROLE,
        user_id: str | None = None,
    ) -> tuple[str, SessionIdentity]:
        if role not in {ADMIN_ROLE, ANNOTATOR_ROLE}:
            raise ValueError(f"unsupported login role: {role}")
        expected_password = (
            self._password if role == ADMIN_ROLE else self._annotator_password
        )
        if expected_password is None:
            label = "administrator" if role == ADMIN_ROLE else "annotator"
            raise AuthenticationDisabled(f"{label} authentication is disabled")
        resolved_user_id: str | None
        if role == ANNOTATOR_ROLE:
            resolved_user_id = validate_user_id(user_id)
        else:
            if user_id is not None and user_id.strip():
                raise ValueError("user_id is only accepted for annotator login")
            resolved_user_id = "admin"

        now = self._now()
        with self._lock:
            self._prune_expired(now)
            failures = self._recent_failures(client_address, now)
            if len(failures) >= LOGIN_FAILURE_LIMIT:
                retry_after = max(
                    1,
                    math.ceil(LOGIN_WINDOW_SECONDS - (now - failures[0])),
                )
                raise LoginRateLimited(retry_after)
            if not secrets.compare_digest(
                password.encode("utf-8"), expected_password.encode("utf-8")
            ):
                failures.append(now)
                self._failures[client_address] = failures
                label = "administrator" if role == ADMIN_ROLE else "annotator"
                raise InvalidCredentials(f"invalid {label} password")
            self._failures.pop(client_address, None)
            token = self._token_factory()
            self._sessions[token] = _SessionRecord(
                role=role, user_id=resolved_user_id, last_seen=now
            )
            return token, SessionIdentity(role, resolved_user_id)

    def login(
        self,
        password: str,
        client_address: str,
        *,
        role: str = ADMIN_ROLE,
        user_id: str | None = None,
    ) -> str:
        token, _identity = self.login_session(
            password, client_address, role=role, user_id=user_id
        )
        return token

    def active_session_token(self, cookie_header: str | None) -> str | None:
        if not self.authentication_enabled:
            return None
        token = self._session_token(cookie_header)
        if token is None:
            return None
        now = self._now()
        with self._lock:
            self._prune_expired(now)
            record = self._sessions.get(token)
            if record is None or record.role != ADMIN_ROLE:
                return None
            record.last_seen = now
            return token

    def logout(self, cookie_header: str | None) -> str | None:
        token = self._session_token(cookie_header)
        if token is None:
            return None
        with self._lock:
            return token if self._sessions.pop(token, None) is not None else None

    @staticmethod
    def session_cookie(token: str) -> str:
        cookie = SimpleCookie()
        cookie[SESSION_COOKIE_NAME] = token
        morsel = cookie[SESSION_COOKIE_NAME]
        morsel["httponly"] = True
        morsel["samesite"] = "Strict"
        morsel["path"] = "/"
        return morsel.OutputString()

    @staticmethod
    def expired_session_cookie() -> str:
        cookie = SimpleCookie()
        cookie[SESSION_COOKIE_NAME] = ""
        morsel = cookie[SESSION_COOKIE_NAME]
        morsel["expires"] = "Thu, 01 Jan 1970 00:00:00 GMT"
        morsel["httponly"] = True
        morsel["max-age"] = 0
        morsel["samesite"] = "Strict"
        morsel["path"] = "/"
        return morsel.OutputString()

    def _recent_failures(self, client_address: str, now: float) -> list[float]:
        cutoff = now - LOGIN_WINDOW_SECONDS
        return [
            timestamp
            for timestamp in self._failures.get(client_address, [])
            if timestamp > cutoff
        ]

    def _prune_expired(self, now: float) -> None:
        session_cutoff = now - SESSION_IDLE_SECONDS
        self._sessions = {
            token: record
            for token, record in self._sessions.items()
            if record.last_seen > session_cutoff
        }
        failure_cutoff = now - LOGIN_WINDOW_SECONDS
        self._failures = {
            client_address: recent
            for client_address, timestamps in self._failures.items()
            if (
                recent := [
                    timestamp for timestamp in timestamps if timestamp > failure_cutoff
                ]
            )
        }

    @staticmethod
    def _session_token(cookie_header: str | None) -> str | None:
        if not cookie_header or len(cookie_header) > 16 * 1024:
            return None
        cookie = SimpleCookie()
        try:
            cookie.load(cookie_header)
        except CookieError:
            return None
        morsel = cookie.get(SESSION_COOKIE_NAME)
        return morsel.value if morsel is not None and morsel.value else None
