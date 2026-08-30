from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from psycheval.html import render_serve_html
from psycheval.html.assets import WORKSPACE_STYLESHEET_PARTS, load_workspace_stylesheet
from psycheval.i18n import messages_for
from psycheval.serve.assets import workspace_stylesheet_asset


def literal_translation_keys(source: str) -> set[str]:
    return set(re.findall(r'\bt\(\s*"([^"]+)"\s*(?:,|\))', source))


def script_json(html: str, element_id: str) -> dict:
    match = re.search(
        rf'<script type="application/json" id="{re.escape(element_id)}"[^>]*>(.*?)</script>',
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
            if path.is_relative_to(asset_root / "vendor"):
                continue
            frontend_keys.update(
                literal_translation_keys(path.read_text(encoding="utf-8"))
            )

        for locale in ("en", "zh-CN"):
            with self.subTest(locale=locale):
                self.assertEqual(frontend_keys - messages_for(locale).keys(), set())

    def test_live_shell_uses_external_esm_without_embedded_report_payload(self) -> None:
        html = render_serve_html(workspace_id="workspace-one", role="guest")

        self.assertIn(
            '<link rel="stylesheet" href="/assets/peval/workspace.css">', html
        )
        self.assertNotIn("<style", html)
        self.assertNotIn("__CSS__", html)
        self.assertIn(
            '<script type="module" src="/assets/peval/main.js" nonce="static-render"></script>',
            html,
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
                "initial_page": "home",
                "csp_nonce": "static-render",
            },
        )
        self.assertEqual(html.count('nonce="static-render"'), 3)

    def test_workspace_stylesheet_preserves_fragment_order(self) -> None:
        asset_root = Path(__file__).resolve().parents[2] / "src/psycheval/assets"
        expected = "\n".join(
            (asset_root / path).read_text(encoding="utf-8")
            for path in WORKSPACE_STYLESHEET_PARTS
        )

        self.assertEqual(load_workspace_stylesheet(), expected)
        self.assertFalse((asset_root / "report.css").exists())
        self.assertFalse((asset_root / "report.html").exists())
        self.assertFalse((asset_root / "report_css").exists())

    def test_workspace_stylesheet_asset_is_composed_only_once(self) -> None:
        cache_clear = getattr(workspace_stylesheet_asset, "cache_clear", lambda: None)
        cache_clear()
        try:
            with patch(
                "psycheval.serve.assets.load_workspace_stylesheet",
                return_value="body { color: black; }",
            ) as load:
                first = workspace_stylesheet_asset()
                second = workspace_stylesheet_asset()

            self.assertEqual(first, second)
            load.assert_called_once_with()
        finally:
            cache_clear()

    def test_all_live_routes_render_one_persistent_role_allowed_shell(self) -> None:
        expected = {
            "home": 'id="leaderboard-region"',
            "datasets": "data-harbor-workbench aria-label",
            "reports": "data-report-manager aria-label",
            "config": "data-config-page aria-label",
        }
        for page, marker in expected.items():
            with self.subTest(page=page):
                html = render_serve_html(serve_page=page)
                for shell_page, shell_marker in expected.items():
                    self.assertEqual(html.count(shell_marker), 1, shell_page)
                self.assertEqual(
                    script_json(html, "peval-render-options")["initial_page"], page
                )
                self.assertRegex(
                    html,
                    rf'data-workspace-page="{page}"(?![^>]*\shidden(?:\s|>))',
                )

        guest_html = render_serve_html(role="guest")
        self.assertIn('data-workspace-page="home"', guest_html)
        self.assertIn('data-workspace-page="datasets"', guest_html)
        self.assertIn('data-workspace-page="reports"', guest_html)
        self.assertNotIn('data-workspace-page="config"', guest_html)
        self.assertNotIn("data-config-page aria-label", guest_html)

    def test_admin_acp_drawer_starts_with_compact_agent_controls(self) -> None:
        html = render_serve_html(role="admin")

        drawer = html[html.index('<aside class="acp-drawer"') :]
        self.assertIn('aria-label="Copilot"', drawer[:300])
        self.assertNotIn('aria-labelledby="acp-drawer-title"', drawer[:300])
        self.assertNotIn('class="acp-drawer-head"', drawer)
        self.assertNotIn("Psycheval Copilot</h2>", drawer)
        self.assertNotIn('class="acp-context-bar"', drawer)
        self.assertNotIn("data-acp-context-capture", drawer)
        self.assertNotIn("data-acp-protocol", drawer)
        self.assertNotIn('class="acp-notice"', drawer)
        self.assertNotIn("data-acp-notice", drawer)
        self.assertLess(
            drawer.index('class="acp-controls"'),
            drawer.index('class="acp-chat-frame"'),
        )
        controls = drawer[
            drawer.index('class="acp-controls"') : drawer.index("</section>")
        ]
        self.assertIn("data-acp-agent", controls)
        self.assertIn("data-acp-close", controls)

    def test_chinese_acp_prompt_preset_uses_compact_copy(self) -> None:
        html = render_serve_html(role="admin", locale="zh-CN")
        drawer = html[html.index('<aside class="acp-drawer"') :]
        prompt_assets = drawer[
            drawer.index('<section class="acp-prompt-assets"') : drawer.index(
                "</section>", drawer.index('<section class="acp-prompt-assets"')
            )
        ]

        self.assertIn("<span>预设</span>", prompt_assets)
        self.assertIn(">使用</button>", prompt_assets)
        self.assertNotIn("提示词资产", prompt_assets)
        self.assertNotIn("使用提示词", prompt_assets)

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
