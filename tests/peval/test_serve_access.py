from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from psycheval.serve.access import (
    ADMIN_PASSWORD_ENV,
    ADMIN_ROLE,
    GUEST_ROLE,
    LOGIN_FAILURE_LIMIT,
    SESSION_COOKIE_NAME,
    SESSION_IDLE_SECONDS,
    AuthenticationDisabled,
    InvalidCredentials,
    LoginRateLimited,
    ServeAccess,
    resolve_admin_password,
)
from psycheval.serve.lifecycle import validate_bind_host


class ServePasswordDiscoveryTests(unittest.TestCase):
    def test_non_empty_process_value_wins_and_empty_value_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                f'export {ADMIN_PASSWORD_ENV}="dotenv password"\nIGNORED=value\n',
                encoding="utf-8",
            )

            self.assertEqual(
                resolve_admin_password(
                    root, environ={ADMIN_PASSWORD_ENV: "process password"}
                ),
                "process password",
            )
            self.assertEqual(
                resolve_admin_password(root, environ={ADMIN_PASSWORD_ENV: ""}),
                "dotenv password",
            )

    def test_missing_empty_and_invalid_dotenv_disable_authentication(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(resolve_admin_password(root, environ={}))
            (root / ".env").write_text(f"{ADMIN_PASSWORD_ENV}=\n", encoding="utf-8")
            self.assertIsNone(resolve_admin_password(root, environ={}))

        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.mkdir()
            with self.assertRaisesRegex(ValueError, "regular file"):
                resolve_admin_password(Path(tmp), environ={})

    def test_legacy_admin_password_variable_is_not_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(
                resolve_admin_password(
                    Path(tmp), environ={"PEVAL_PY_ADMIN_PASSWORD": "legacy"}
                )
            )

    def test_dotenv_symlink_is_rejected_without_reading_its_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "outside.env"
            target.write_text(
                f"{ADMIN_PASSWORD_ENV}=must-not-be-read\n", encoding="utf-8"
            )
            try:
                (root / ".env").symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")

            with self.assertRaisesRegex(ValueError, "regular file"):
                resolve_admin_password(root, environ={})

    def test_bind_policy_allows_local_admin_and_requires_remote_password(self) -> None:
        self.assertEqual(validate_bind_host("127.0.0.1", False), "127.0.0.1")
        self.assertEqual(validate_bind_host("[::1]", False), "::1")
        self.assertEqual(validate_bind_host("0.0.0.0", True), "0.0.0.0")
        self.assertEqual(validate_bind_host("192.168.1.25", True), "192.168.1.25")
        with self.assertRaisesRegex(ValueError, "non-local serve requires"):
            validate_bind_host("0.0.0.0", False)


class ServeSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = [100.0]
        self.access = ServeAccess(
            "管理密码",
            now=lambda: self.now[0],
            token_factory=lambda: "session-token",
        )

    def login_cookie(self) -> str:
        token = self.access.login("管理密码", "192.0.2.10")
        return f"{SESSION_COOKIE_NAME}={token}"

    def test_login_uses_constant_time_comparison_and_session_cookie_attributes(
        self,
    ) -> None:
        with patch(
            "psycheval.serve.access.secrets.compare_digest", return_value=True
        ) as compare:
            token = self.access.login("管理密码", "192.0.2.10")

        compare.assert_called_once_with("管理密码".encode(), "管理密码".encode())
        cookie = self.access.session_cookie(token)
        self.assertIn(f"{SESSION_COOKIE_NAME}=session-token", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)
        self.assertIn("Path=/", cookie)
        self.assertNotIn("Secure", cookie)
        self.assertNotIn("Max-Age", cookie)
        self.assertNotIn("expires=", cookie.lower())
        self.assertNotIn("domain=", cookie.lower())

    def test_session_is_touched_expires_after_idle_and_logout_revokes_it(self) -> None:
        cookie = self.login_cookie()
        self.assertEqual(self.access.role(cookie), ADMIN_ROLE)
        self.now[0] += SESSION_IDLE_SECONDS - 1
        self.assertEqual(self.access.role(cookie), ADMIN_ROLE)
        self.now[0] += SESSION_IDLE_SECONDS - 1
        self.assertEqual(self.access.role(cookie), ADMIN_ROLE)
        self.now[0] += SESSION_IDLE_SECONDS
        self.assertEqual(self.access.role(cookie), GUEST_ROLE)

        cookie = self.login_cookie()
        self.access.logout(cookie)
        self.access.logout(cookie)
        self.assertEqual(self.access.role(cookie), GUEST_ROLE)
        expired = self.access.expired_session_cookie()
        self.assertIn("Max-Age=0", expired)
        self.assertIn("HttpOnly", expired)
        self.assertIn("SameSite=Strict", expired)

    def test_failed_logins_are_limited_per_client_for_a_rolling_minute(self) -> None:
        for _ in range(LOGIN_FAILURE_LIMIT):
            with self.assertRaises(InvalidCredentials):
                self.access.login("wrong", "192.0.2.10")
        with self.assertRaises(LoginRateLimited) as limited:
            self.access.login("管理密码", "192.0.2.10")
        self.assertEqual(limited.exception.retry_after, 60)

        self.assertEqual(self.access.login("管理密码", "192.0.2.11"), "session-token")
        self.now[0] += 61
        self.assertEqual(self.access.login("管理密码", "192.0.2.10"), "session-token")

    def test_successful_login_clears_the_client_failure_bucket(self) -> None:
        client = "192.0.2.10"
        for _ in range(LOGIN_FAILURE_LIMIT - 1):
            with self.assertRaises(InvalidCredentials):
                self.access.login("wrong", client)
        self.assertEqual(self.access.login("管理密码", client), "session-token")

        for _ in range(LOGIN_FAILURE_LIMIT):
            with self.assertRaises(InvalidCredentials):
                self.access.login("wrong again", client)
        with self.assertRaises(LoginRateLimited):
            self.access.login("管理密码", client)

    def test_later_login_reclaims_expired_sessions_and_failure_buckets(self) -> None:
        tokens = iter(("old-session", "new-session"))
        access = ServeAccess(
            "password",
            now=lambda: self.now[0],
            token_factory=lambda: next(tokens),
        )
        access.login("password", "192.0.2.1")
        with self.assertRaises(InvalidCredentials):
            access.login("wrong", "192.0.2.2")

        self.now[0] += SESSION_IDLE_SECONDS + 1
        access.login("password", "192.0.2.3")

        self.assertEqual(access._sessions, {"new-session": self.now[0]})
        self.assertEqual(access._failures, {})

    def test_disabled_authentication_is_automatic_admin(self) -> None:
        access = ServeAccess(None)
        self.assertEqual(
            access.session_payload(None),
            {
                "authentication_enabled": False,
                "role": ADMIN_ROLE,
            },
        )
        with self.assertRaises(AuthenticationDisabled):
            access.login("anything", "127.0.0.1")

    def test_default_token_contains_32_random_bytes(self) -> None:
        token = ServeAccess("password").login("password", "127.0.0.1")
        padding = "=" * (-len(token) % 4)
        self.assertEqual(len(base64.urlsafe_b64decode(token + padding)), 32)

    def test_guest_route_policy_is_fail_closed(self) -> None:
        self.assertTrue(self.access.permits("GET", "/api/catalog", GUEST_ROLE))
        self.assertTrue(self.access.permits("POST", "/api/exports", GUEST_ROLE))
        self.assertTrue(
            self.access.permits(
                "GET", "/api/reports/20260101-000000-000001/preview", GUEST_ROLE
            )
        )
        self.assertFalse(self.access.permits("GET", "/api/sources", GUEST_ROLE))
        self.assertFalse(self.access.permits("GET", "/api/config/harbor", GUEST_ROLE))
        self.assertFalse(self.access.permits("POST", "/api/views", GUEST_ROLE))
        self.assertFalse(self.access.permits("GET", "/api/future", GUEST_ROLE))
        self.assertTrue(self.access.permits("GET", "/api/future", ADMIN_ROLE))


if __name__ == "__main__":
    unittest.main()
