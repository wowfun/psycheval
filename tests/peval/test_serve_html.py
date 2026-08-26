from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from psycheval.html import render_serve_html
from psycheval.i18n import messages_for


def literal_translation_keys(source: str) -> set[str]:
    return set(re.findall(r'\bt\(\s*"([^"]+)"\s*(?:,|\))', source))


def script_json(html: str, element_id: str) -> dict:
    match = re.search(
        rf'<script type="application/json" id="{re.escape(element_id)}">(.*?)</script>',
        html,
        re.S,
    )
    if not match:
        raise AssertionError(f"missing script JSON: {element_id}")
    return json.loads(match.group(1))


class PevalServeHtmlTests(unittest.TestCase):
    def test_literal_translation_key_scan_includes_calls_without_fallback(
        self,
    ) -> None:
        self.assertEqual(
            literal_translation_keys(
                't("with_fallback", "Fallback"); t("without_fallback");'
            ),
            {"with_fallback", "without_fallback"},
        )

    def test_frontend_literal_translation_keys_exist_in_every_locale(self) -> None:
        asset_root = Path(__file__).resolve().parents[2] / "src/psycheval/assets/web"
        frontend_keys: set[str] = set()
        for path in asset_root.rglob("*.js"):
            frontend_keys.update(
                literal_translation_keys(path.read_text(encoding="utf-8"))
            )

        for locale in ("en", "zh-CN"):
            with self.subTest(locale=locale):
                self.assertEqual(frontend_keys - messages_for(locale).keys(), set())

    def test_live_shell_uses_external_esm_without_embedded_report_payload(self) -> None:
        html = render_serve_html(workspace_id="workspace-one", role="guest")

        self.assertIn(
            '<script type="module" src="/assets/peval/main.js"></script>', html
        )
        self.assertNotIn('id="peval-data"', html)
        self.assertNotIn('id="peval-token-estimates"', html)
        self.assertNotIn('id="peval-workspace-snapshot"', html)
        self.assertNotIn("peval-entrypoint", html)
        self.assertNotIn('data-export-kind="workspace_html"', html)
        self.assertEqual(
            script_json(html, "peval-render-options"),
            {
                "adapter_defaults": {},
                "loading": False,
                "workspace_id": "workspace-one",
                "role": "guest",
                "authentication_enabled": False,
                "serve_page": "home",
            },
        )

    def test_all_live_pages_render_their_owned_shell(self) -> None:
        expected = {
            "home": 'id="leaderboard-region"',
            "datasets": "data-harbor-workbench",
            "reports": "data-report-manager",
            "config": "data-config-page",
        }
        for page, marker in expected.items():
            with self.subTest(page=page):
                html = render_serve_html(serve_page=page)
                self.assertIn(marker, html)
                self.assertEqual(
                    script_json(html, "peval-render-options")["serve_page"], page
                )

    def test_workspace_description_is_json_escaped_and_blank_is_omitted(self) -> None:
        description = "**Nightly** <script>alert(1)</script>"
        html = render_serve_html(workspace_description=description)

        self.assertEqual(
            script_json(html, "peval-render-options")["workspace_description"],
            description,
        )
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertNotIn(
            "workspace_description",
            script_json(
                render_serve_html(workspace_description="   "),
                "peval-render-options",
            ),
        )

    def test_locale_and_page_validation_are_deterministic(self) -> None:
        zh_html = render_serve_html(locale="zh-CN", serve_page="datasets")
        self.assertIn('<html lang="zh-CN">', zh_html)
        self.assertIn("数据集", zh_html)
        with self.assertRaisesRegex(ValueError, "unsupported serve page"):
            render_serve_html(serve_page="snapshot")


if __name__ == "__main__":
    unittest.main()
