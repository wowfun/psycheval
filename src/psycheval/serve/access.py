from __future__ import annotations

import math
import os
import secrets
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from http.cookies import CookieError, SimpleCookie
from pathlib import Path
from threading import Lock

from dotenv import dotenv_values

ADMIN_PASSWORD_ENV = "PEVAL_ADMIN_PASSWORD"
ADMIN_ROLE = "admin"
GUEST_ROLE = "guest"
SESSION_COOKIE_NAME = "peval_admin_session"
SESSION_IDLE_SECONDS = 12 * 60 * 60
LOGIN_WINDOW_SECONDS = 60
LOGIN_FAILURE_LIMIT = 5

__all__ = [
    "ADMIN_PASSWORD_ENV",
    "ADMIN_ROLE",
    "GUEST_ROLE",
    "SESSION_COOKIE_NAME",
    "SESSION_IDLE_SECONDS",
    "LOGIN_WINDOW_SECONDS",
    "LOGIN_FAILURE_LIMIT",
    "AuthenticationDisabled",
    "InvalidCredentials",
    "LoginRateLimited",
    "ServeAccess",
    "resolve_admin_password",
]


class InvalidCredentials(ValueError):
    pass


class AuthenticationDisabled(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class LoginRateLimited(ValueError):
    retry_after: int


def resolve_admin_password(
    workspace_root: str | Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> str | None:
    values = os.environ if environ is None else environ
    process_value = values.get(ADMIN_PASSWORD_ENV)
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
    file_value = dotenv.get(ADMIN_PASSWORD_ENV)
    return file_value if isinstance(file_value, str) and file_value else None


class ServeAccess:
    """Own serve authentication, sessions, and login throttling."""

    def __init__(
        self,
        password: str | None,
        *,
        now: Callable[[], float] = time.monotonic,
        token_factory: Callable[[], str] | None = None,
    ) -> None:
        self._password = password or None
        self._now = now
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(32))
        self._sessions: dict[str, float] = {}
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
            now=now,
            token_factory=token_factory,
        )

    @property
    def authentication_enabled(self) -> bool:
        return self._password is not None

    def session_payload(self, cookie_header: str | None) -> dict[str, object]:
        return {
            "authentication_enabled": self.authentication_enabled,
            "role": self.role(cookie_header),
        }

    def role(self, cookie_header: str | None) -> str:
        if not self.authentication_enabled:
            return ADMIN_ROLE
        token = self._session_token(cookie_header)
        now = self._now()
        with self._lock:
            self._prune_expired(now)
            if token is None:
                return GUEST_ROLE
            last_seen = self._sessions.get(token)
            if last_seen is None:
                return GUEST_ROLE
            self._sessions[token] = now
        return ADMIN_ROLE

    def login(self, password: str, client_address: str) -> str:
        if not self.authentication_enabled:
            raise AuthenticationDisabled("administrator authentication is disabled")
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
            assert self._password is not None
            if not secrets.compare_digest(
                password.encode("utf-8"), self._password.encode("utf-8")
            ):
                failures.append(now)
                self._failures[client_address] = failures
                raise InvalidCredentials("invalid administrator password")
            self._failures.pop(client_address, None)
            token = self._token_factory()
            self._sessions[token] = now
            return token

    def logout(self, cookie_header: str | None) -> None:
        token = self._session_token(cookie_header)
        if token is None:
            return
        with self._lock:
            self._sessions.pop(token, None)

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
            token: last_seen
            for token, last_seen in self._sessions.items()
            if last_seen > session_cutoff
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
