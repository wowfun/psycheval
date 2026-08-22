from __future__ import annotations

from psycheval.i18n import messages_for
from tests.peval.reports_html_support import (
    FIXTURES,
    MessageRecord,
    Path,
    ReportSession,
    ToolConfig,
    build_multi_report,
    build_report,
    compact_css_text,
    convert_records,
    load_asset_text,
    re,
    read_jsonl,
    render_html,
    render_serve_html,
    script_json,
    unittest,
)


class PevalReportHtmlServeLocaleTests(unittest.TestCase):
    def test_frontend_literal_translation_keys_exist_in_every_locale(self) -> None:
        root = Path(__file__).resolve().parents[2]
        frontend_keys: set[str] = set()
        for path in (root / "web" / "src").rglob("*.js"):
            frontend_keys.update(
                re.findall(r'\bt\("([^"]+)"\s*,', path.read_text(encoding="utf-8"))
            )

        for locale in ("en", "zh-CN"):
            with self.subTest(locale=locale):
                self.assertEqual(frontend_keys - messages_for(locale).keys(), set())

    def test_workspace_description_is_public_escaped_markdown_chrome(self) -> None:
        report = {
            "schema_version": 19,
            "trajectory": [],
            "trajectory_meta": [],
        }
        description = "**Nightly** <script>alert(1)</script>"

        static_html = render_html(report)
        admin_html = render_serve_html(
            report, workspace_description=description, role="admin"
        )
        guest_html = render_serve_html(
            report, workspace_description=description, role="guest"
        )
        blank_html = render_serve_html(report, workspace_description="   ")

        for html in (admin_html, guest_html):
            self.assertEqual(
                script_json(html, "peval-render-options")["workspace_description"],
                description,
            )
            self.assertIn(
                'class="workspace-description note-body" '
                "data-workspace-description hidden",
                html,
            )
            self.assertIn("Nightly** \\u003cscript", html)
            self.assertNotIn("<script>alert(1)</script>", html)

        self.assertNotIn(
            "workspace_description", script_json(static_html, "peval-render-options")
        )
        self.assertNotIn(
            "workspace_description", script_json(blank_html, "peval-render-options")
        )

    def test_category_labels_are_localized_for_tables_and_summary_counts(self) -> None:
        self.assertEqual(messages_for("en")["category"], "Category")
        self.assertEqual(messages_for("en")["summary_categories"], "categories")
        self.assertEqual(messages_for("zh-CN")["category"], "分类")
        self.assertEqual(messages_for("zh-CN")["summary_categories"], "个分类")
        self.assertEqual(
            messages_for("zh-CN")["metric_coverage"], "{covered}/{matched} 个试次"
        )

    def test_retired_source_manager_messages_are_not_shipped(self) -> None:
        retired = {
            "double_click_to_edit",
            "select_source",
            "select_visible_sources",
            "serve_activate",
            "serve_archive",
            "serve_delete",
            "serve_delete_confirm",
            "serve_no_sources",
            "serve_source_count",
            "serve_sources",
            "serve_sources_count",
        }
        for locale in ("en", "zh-CN"):
            self.assertTrue(retired.isdisjoint(messages_for(locale)))

    def test_leaderboard_scrolls_with_the_main_analysis_content(self) -> None:
        html = render_serve_html(
            {
                "schema_version": 19,
                "trajectory": [],
                "trajectory_meta": [],
            },
        )
        workspace_main = re.search(
            r'<main class="workspace-main">(.*?)</main>',
            html,
            re.DOTALL,
        )

        self.assertIsNotNone(workspace_main)
        main_scroll = re.search(
            r'<div class="workspace-main-scroll" data-workspace-main-scroll>'
            r"(.*)</div>\s*$",
            workspace_main.group(1),
            re.DOTALL,
        )
        self.assertIsNotNone(main_scroll)
        self.assertIn('id="leaderboard-region"', main_scroll.group(1))

    def test_saved_view_cards_keep_intrinsic_height_inside_scrolling_rail(self) -> None:
        css = load_asset_text("report.css")
        rule = re.search(r"\.workspace-view-list\s*\{([^}]*)\}", css)

        self.assertIsNotNone(rule)
        declarations = {
            name.strip(): value.strip()
            for declaration in rule.group(1).split(";")
            if ":" in declaration
            for name, value in [declaration.split(":", 1)]
        }
        self.assertEqual(declarations.get("align-content"), "start")
        self.assertEqual(declarations.get("grid-auto-rows"), "max-content")

    def test_action_buttons_shrink_and_action_groups_wrap_inside_panels(self) -> None:
        css = load_asset_text("report.css")

        action_rule = re.search(r"\.action-button\s*\{([^}]*)\}", css)
        self.assertIsNotNone(action_rule)
        action_declarations = {
            name.strip(): value.strip()
            for declaration in action_rule.group(1).split(";")
            if ":" in declaration
            for name, value in [declaration.split(":", 1)]
        }
        self.assertEqual(action_declarations.get("min-width"), "0")
        self.assertEqual(action_declarations.get("max-width"), "100%")
        self.assertEqual(action_declarations.get("display"), "inline-flex")
        self.assertEqual(action_declarations.get("white-space"), "normal")

        for selector in (".leaderboard-action-row", ".workspace-view-index-actions"):
            rule = re.search(rf"{re.escape(selector)}\s*\{{([^}}]*)\}}", css)
            self.assertIsNotNone(rule)
            declarations = {
                name.strip(): value.strip()
                for declaration in rule.group(1).split(";")
                if ":" in declaration
                for name, value in [declaration.split(":", 1)]
            }
            self.assertEqual(declarations.get("flex-wrap"), "wrap")

    def test_source_configuration_sections_are_full_width_and_scrollable(self) -> None:
        css = load_asset_text("report.css")
        sections_rule = re.search(r"\.configuration-sections\s*\{([^}]*)\}", css)

        self.assertIsNotNone(sections_rule)
        declarations = {
            name.strip(): value.strip()
            for declaration in sections_rule.group(1).split(";")
            if ":" in declaration
            for name, value in [declaration.split(":", 1)]
        }
        self.assertEqual(declarations.get("overflow"), "auto")
        self.assertNotIn(".source-manager-list", css)
        self.assertNotIn(".source-table", css)

    def test_harbor_registries_use_shared_data_table_column_widths(self) -> None:
        css = load_asset_text("report.css")

        self.assertNotIn(".harbor-dataset-registry-table", css)
        self.assertNotIn(".harbor-mount-registry-table", css)
        self.assertIn("table-layout:auto", css)
        path_width_rules = re.findall(
            r'([^{}]*\[data-value-type="path"\][^{}]*)\{([^{}]*)\}',
            css,
        )
        self.assertTrue(
            any(
                "--table-column-max:40ch" in declarations
                for _, declarations in path_width_rules
            )
        )
        self.assertIn(
            "max-width:var(--table-column-max)",
            css,
        )

    def test_configuration_puts_sqlite_db_import_first(self) -> None:
        html = render_serve_html(
            {
                "schema_version": 19,
                "trajectory": [],
                "trajectory_meta": [],
            },
            serve_page="config",
        )
        forms_panel = re.search(
            r'<div class="trajectory-ingestion-forms"[^>]*>(.*?)</div>\s*</section>',
            html,
            re.DOTALL,
        )

        self.assertIsNotNone(forms_panel)
        form_tags = re.findall(r"<form\b[^>]*>", forms_panel.group(1))
        self.assertIn('data-source-kind="db"', form_tags[0])
        self.assertEqual(
            re.findall(r'data-source-kind="([^"]+)"', forms_panel.group(1)),
            ["db", "path"],
        )
        self.assertEqual(len(form_tags), 2)

    def test_desktop_saved_views_grid_bounds_wide_index_content(self) -> None:
        css = load_asset_text("report.css")
        desktop_css = css.split("@media (min-width:1181px)", 1)[1].split(
            "@media (max-width:1180px)", 1
        )[0]
        rail_rule = re.search(
            r"\.workspace-views\s*\{([^}]*)\}",
            desktop_css,
        )
        self.assertIsNotNone(rail_rule)
        declarations = {
            name.strip(): value.strip()
            for declaration in rail_rule.group(1).split(";")
            if ":" in declaration
            for name, value in [declaration.split(":", 1)]
        }
        self.assertEqual(
            declarations,
            {
                "display": "grid",
                "grid-template-columns": "minmax(0,1fr)",
                "grid-template-rows": "auto auto minmax(0,1fr)",
                "overflow": "hidden",
            },
        )

    def test_desktop_step_drawer_keeps_inline_steps_within_the_main_column(
        self,
    ) -> None:
        css = load_asset_text("report.css")
        desktop_css = css.split("@media (min-width:1181px)", 1)[1].split(
            "@media (max-width:1180px)", 1
        )[0]
        summary_rule = re.search(
            r"\.serve-mode\.step-drawer-open #trace \.step>summary\s*\{([^}]*)\}",
            desktop_css,
        )
        rail_rule = re.search(
            r"\.serve-mode\.step-drawer-open #trace \.rail\s*\{([^}]*)\}",
            desktop_css,
        )

        self.assertIsNotNone(summary_rule)
        self.assertIsNotNone(rail_rule)
        summary_declarations = {
            name.strip(): value.strip()
            for declaration in summary_rule.group(1).split(";")
            if ":" in declaration
            for name, value in [declaration.split(":", 1)]
        }
        rail_declarations = {
            name.strip(): value.strip()
            for declaration in rail_rule.group(1).split(";")
            if ":" in declaration
            for name, value in [declaration.split(":", 1)]
        }
        self.assertEqual(
            summary_declarations.get("grid-template-columns"),
            "minmax(0,1fr)",
        )
        self.assertEqual(rail_declarations.get("justify-items"), "stretch")

    def test_desktop_step_drawer_preserves_the_document_scroll_owner(self) -> None:
        css = load_asset_text("report.css")
        desktop_css = css.split("@media (min-width:1181px)", 1)[1].split(
            "@media (max-width:1180px)", 1
        )[0]

        self.assertNotIn(
            ".serve-mode.step-drawer-open {\n    overflow:hidden",
            desktop_css,
        )
        self.assertNotIn(
            ".serve-mode.step-drawer-open .workspace-main-scroll",
            desktop_css,
        )

    def test_desktop_saved_views_assign_only_remaining_height_to_workspace_content(
        self,
    ) -> None:
        css = load_asset_text("report.css")
        desktop_css = css.split("@media (min-width:1181px)", 1)[1].split(
            "@media (max-width:1180px)", 1
        )[0]
        workspace_rule = re.search(
            r"\.serve-mode\.workspace-views-open \.workspace\s*\{([^}]*)\}",
            desktop_css,
        )
        content_rule = re.search(
            r"\.serve-mode\.workspace-views-open \.workspace-content\s*\{([^}]*)\}",
            desktop_css,
        )

        self.assertIsNotNone(workspace_rule)
        self.assertIsNotNone(content_rule)
        workspace_declarations = {
            name.strip(): value.strip()
            for declaration in workspace_rule.group(1).split(";")
            if ":" in declaration
            for name, value in [declaration.split(":", 1)]
        }
        content_declarations = {
            name.strip(): value.strip()
            for declaration in content_rule.group(1).split(";")
            if ":" in declaration
            for name, value in [declaration.split(":", 1)]
        }
        self.assertEqual(workspace_declarations.get("display"), "flex")
        self.assertEqual(workspace_declarations.get("flex-direction"), "column")
        self.assertEqual(content_declarations.get("height"), "auto")
        self.assertEqual(content_declarations.get("flex"), "1 1 auto")

    def test_workspace_report_chrome_and_catalog_are_serve_only(self) -> None:
        report = {
            "schema_version": 19,
            "includes": ["core"],
            "trajectory": [],
            "trajectory_meta": [],
        }
        catalog = [
            {
                "report_id": "20260710-143012-123456",
                "filename": "cross-session-report.md",
                "format": "markdown",
                "source_keys": ["cell-a", "cell-b"],
            }
        ]

        static_html = render_html(report)
        serve_html = render_serve_html(report, reports=catalog)
        reports_html = render_serve_html(report, reports=catalog, serve_page="reports")
        serve_markup = re.sub(
            r"<script(?:\s[^>]*)?>.*?</script>", "", serve_html, flags=re.DOTALL
        )
        reports_markup = re.sub(
            r"<script(?:\s[^>]*)?>.*?</script>", "", reports_html, flags=re.DOTALL
        )

        self.assertEqual(
            script_json(static_html, "peval-render-options"),
            {"mode": "report", "sources": []},
        )
        self.assertNotIn('<div class="report-manager-backdrop"', static_html)
        self.assertNotIn('<aside class="report-reader"', static_html)
        self.assertNotIn('<aside class="workspace-views"', static_html)
        serve_options = script_json(reports_html, "peval-render-options")
        self.assertEqual(serve_options["reports"], catalog)
        self.assertIn('href="/reports"', serve_html)
        self.assertNotIn("data-report-manager", serve_markup)
        self.assertIn("data-report-manager", reports_markup)
        self.assertNotIn('<div class="report-manager-backdrop"', reports_html)
        self.assertIn('<aside class="report-reader"', serve_html)
        self.assertIn(
            '<div class="workspace-side-region" id="workspace-side-region">', serve_html
        )
        self.assertIn(
            '<aside class="workspace-views" id="workspace-views" hidden data-serve-only>',
            serve_html,
        )
        self.assertIn("data-report-inventory", reports_html)
        self.assertIn("data-report-bindings", reports_html)
        self.assertIn('sandbox="allow-scripts"', serve_html)
        self.assertNotIn("allow-same-origin", serve_html)
        self.assertIn("data-report-reader-open-tab", serve_html)
        self.assertIn('target="_blank"', serve_html)
        self.assertIn('rel="noopener"', serve_html)
        self.assertIn("data-report-reader-resize", serve_html)
        self.assertIn('aria-orientation="vertical"', serve_html)

    def test_serve_html_mode_reuses_report_body_with_export_selection_controls(
        self,
    ) -> None:
        config = ToolConfig(adapter="opencode")
        first = convert_records(
            read_jsonl(str(FIXTURES / "common_session.jsonl")), config
        )
        second = convert_records(
            read_jsonl(str(FIXTURES / "psychevo_session.jsonl")), config
        )
        report = build_multi_report(
            [
                ReportSession(
                    conversion=first,
                    input_label="common_session.jsonl",
                    input_path=str(FIXTURES / "common_session.jsonl"),
                    session_hint="common_session",
                    source_alias="Readable source",
                ),
                ReportSession(
                    conversion=second,
                    input_label="psychevo_session.jsonl",
                    input_path=str(FIXTURES / "psychevo_session.jsonl"),
                    session_hint="psychevo_session",
                ),
            ],
            config,
            [],
        )
        self.assertNotIn("comparison", report)
        self.assertEqual(report["trajectory"][0]["session_id"], "common_session")
        self.assertEqual(
            report["trajectory_meta"][0]["source_alias"], "Readable source"
        )
        self.assertEqual(report["trajectory_meta"][0]["finished_at_ms"], 1500)

        static_html = render_html(report)
        home_html = render_serve_html(
            report,
            adapter_defaults={"opencode": "/tmp/opencode.db"},
        )
        sources_html = render_serve_html(
            report,
            adapter_defaults={"opencode": "/tmp/opencode.db"},
            serve_page="config",
        )
        datasets_html = render_serve_html(report, serve_page="datasets")
        reports_html = render_serve_html(report, serve_page="reports")
        serve_html = home_html + sources_html + datasets_html + reports_html
        zh_serve_html = (
            render_serve_html(report, locale="zh-CN")
            + render_serve_html(report, locale="zh-CN", serve_page="config")
            + render_serve_html(report, locale="zh-CN", serve_page="datasets")
        )
        compact_serve_html = compact_css_text(serve_html)

        self.assertIn('<body class="report-mode">', static_html)
        self.assertIn("<title>Agent Trajectory Report</title>", static_html)
        self.assertIn("<h1>Agent Trajectory Report</h1>", static_html)
        self.assertNotIn('class="serve-import-panel"', static_html)
        self.assertNotIn('class="source-manager-modal"', static_html)
        self.assertNotIn('<form class="source-form"', static_html)
        self.assertNotIn('type="button" data-db-inspect', static_html)
        self.assertIn("Timeline Waterfall", static_html)
        self.assertIn("Timeline Detail Table", static_html)
        self.assertIn('id="leaderboard-summary"', static_html)
        self.assertIn(
            "function renderLeaderboardSummary(rows = leaderboardRows())", static_html
        )
        self.assertIn(
            '<script src="https://cdn.jsdelivr.net/npm/echarts@6.0.0/dist/echarts.min.js"></script>',
            static_html,
        )
        self.assertNotIn("/assets/echarts/6.0.0/echarts.min.js", static_html)
        self.assertEqual(
            script_json(static_html, "peval-render-options"),
            {"mode": "report", "sources": []},
        )

        serve_options = script_json(home_html, "peval-render-options")
        self.assertEqual(serve_options["mode"], "serve")
        self.assertEqual(len(serve_options["sources"]), 2)
        self.assertEqual(
            serve_options["adapter_defaults"],
            {"opencode": "/tmp/opencode.db"},
        )
        self.assertIn('<body class="serve-mode serve-page-home">', home_html)
        self.assertIn("<title>Eval Workspace</title>", serve_html)
        self.assertNotIn("<h1>Home</h1>", home_html)
        self.assertNotIn('class="serve-source-heading"', home_html)
        self.assertNotRegex(home_html, r"<[^>]+\sdata-source-count(?:\s|>)")
        self.assertNotRegex(home_html, r"<[^>]+\sdata-source-status(?:\s|>)")
        self.assertNotRegex(home_html, r"<[^>]+\sdata-refresh-all(?:\s|>)")
        self.assertNotIn(
            '<section class="topline"><h1>Eval Workspace</h1></section>',
            serve_html,
        )
        self.assertIn("<title>评测工作台</title>", zh_serve_html)
        self.assertNotIn("<h1>主页</h1>", zh_serve_html)
        self.assertNotIn('<h1 id="harbor-workbench-title">数据集</h1>', zh_serve_html)
        self.assertNotIn('class="workspace-page-head', serve_html)
        self.assertIn('aria-label="Datasets"', datasets_html)
        self.assertIn('aria-label="Reports"', reports_html)
        self.assertIn('aria-label="Configuration"', sources_html)
        self.assertIn(">新建文件</button>", zh_serve_html)
        self.assertIn(">新建文件夹</button>", zh_serve_html)
        self.assertIn(">上传</button>", zh_serve_html)
        self.assertIn(">下载</button>", zh_serve_html)
        self.assertIn(
            ".serve-page-home .workspace,\n"
            ".serve-page-datasets .workspace,\n"
            ".serve-page-reports .workspace,\n"
            ".serve-page-config .workspace {\n"
            "  max-width:1500px",
            serve_html,
        )
        self.assertIn(
            compact_css_text(
                ".serve-page-home .workspace,"
                ".serve-page-datasets .workspace,"
                ".serve-page-reports .workspace,"
                ".serve-page-config .workspace{"
                "max-width:1500px}"
            ),
            compact_serve_html,
        )
        self.assertIn(
            compact_css_text(
                ".serve-page-datasets .workspace,"
                ".serve-page-reports .workspace,"
                ".serve-page-config .workspace{"
                "min-height:100vh;min-height:100dvh;"
                "display:flex;flex-direction:column}"
            ),
            compact_serve_html,
        )
        self.assertIn(
            compact_css_text(
                ".serve-page-datasets .harbor-workbench{"
                "width:100%;height:auto;min-height:0;display:flex"
            ),
            compact_serve_html,
        )
        self.assertIn(
            compact_css_text(".harbor-task-detail{flex:1 1 auto"),
            compact_serve_html,
        )
        self.assertIn(
            compact_css_text(
                ".serve-page-home .workspace-description{"
                "margin:0 0 14px auto;text-align:right}"
            ),
            compact_serve_html,
        )
        self.assertIn(
            compact_css_text(
                ".serve-page-reports .report-manager-page{"
                "min-height:0;display:flex;flex-direction:column}"
            ),
            compact_serve_html,
        )
        self.assertIn(
            compact_css_text(
                ".serve-page-reports .report-manager-body{"
                "flex:1 1 auto;min-height:620px}"
            ),
            compact_serve_html,
        )
        self.assertIn("--step-drawer-width:clamp(620px,44vw,760px)", serve_html)
        self.assertIn("width:100%;\n  max-width:none", serve_html)
        self.assertIn(".workspace {\n  max-width:1180px", serve_html)
        self.assertIn("grid-template-columns:repeat(2,minmax(0,1fr))", serve_html)
        self.assertIn(".serve-mode .workspace-side-region .step-drawer", serve_html)
        self.assertIn("position:absolute", serve_html)
        self.assertIn("@media (min-width:1181px)", serve_html)
        self.assertIn("height:100dvh", serve_html)
        self.assertIn("max-height:min(calc(45px + (48px * 10)),42dvh)", serve_html)
        self.assertIn("max-height:min(260px,32dvh)", serve_html)
        self.assertIn("@media (max-width:1180px)", serve_html)
        self.assertIn("@media (max-width:720px)", serve_html)
        self.assertIn("inset:auto 0 0", serve_html)
        self.assertIn('id="leaderboard-region"', serve_html)
        self.assertIn("data-workspace-main-scroll", serve_html)
        self.assertIn("data-catalog-clear-conditions", serve_html)
        self.assertNotIn("data-catalog-clear-selection", serve_html)
        self.assertNotIn("data-view-cancel-application", serve_html)
        self.assertNotIn('data-view-apply="', serve_html)
        self.assertIn("/assets/echarts/6.0.0/echarts.min.js", serve_html)
        self.assertIn(
            "this.onerror=null;this.src='https://cdn.jsdelivr.net/npm/echarts@6.0.0/dist/echarts.min.js'",
            serve_html,
        )
        self.assertNotIn('class="serve-import-panel"', serve_html)
        self.assertIn('class="workspace-header"', serve_html)
        self.assertIn("data-locale-select", serve_html)
        self.assertIn(
            'class="workspace-page configuration-page"',
            sources_html,
        )
        self.assertNotIn('class="adapter-default-db-panel"', serve_html)
        self.assertNotIn("data-adapter-default-db-form", serve_html)
        self.assertIn("configuration-sections", serve_html)
        self.assertIn("data-adapter-default-db-save", serve_html)
        self.assertIn("data-adapter-default-db-clear", serve_html)
        self.assertIn("Save as default", serve_html)
        self.assertIn("保存为默认", zh_serve_html)
        self.assertIn("LOCAL PROCESS", sources_html)
        self.assertIn("本地进程", zh_serve_html)
        self.assertNotIn("LOCAL PROCESS", zh_serve_html)
        self.assertNotIn("Upload snapshot", serve_html)
        self.assertNotIn("report JSON uploads", serve_html)
        self.assertIn("Session / ATIF / runs Path", serve_html)
        self.assertNotIn("<strong>Session / ATIF / runs Path</strong>", serve_html)
        self.assertIn('<textarea name="path"', serve_html)
        self.assertIn('aria-describedby="source-path-auto-help"', serve_html)
        self.assertIn('aria-describedby="source-db-auto-help"', serve_html)
        self.assertNotIn('data-source-kind="input_table"', serve_html)
        self.assertNotIn("data-harbor-mount-form", serve_html)
        self.assertIn("data-harbor-add-mount", serve_html)
        self.assertIn("data-harbor-remove-mounts", serve_html)
        self.assertIn("data-harbor-mount-count", serve_html)
        self.assertIn('href="/datasets"', home_html)
        self.assertIn("data-harbor-workbench", serve_html)
        self.assertIn("Jobs 路径", zh_serve_html)
        self.assertIn(
            "Auto infers the adapter only when the source path contains an adapter name.",
            serve_html,
        )
        self.assertIn("auto 仅在来源路径包含 adapter 名称时推断。", zh_serve_html)
        self.assertIn("data-path-picker-target", serve_html)
        self.assertIn("data-path-picker", serve_html)
        self.assertIn("Choose files", serve_html)
        self.assertIn('<textarea name="db"', serve_html)
        self.assertIn("Inspect DB", serve_html)
        self.assertIn("data-db-inspect", serve_html)
        self.assertIn("data-db-session-picker", serve_html)
        self.assertIn("data-db-add-selected", serve_html)
        self.assertIn("data-table-select-visible", serve_html)
        self.assertEqual(serve_html.count('class="source-adapter-select"'), 2)
        self.assertEqual(
            len(re.findall(r'class="[^"]*\bsource-add-actions\b', serve_html)), 2
        )
        db_path_control = re.search(
            r'<span class="db-path-control">\s*<textarea name="db".*?</textarea>'
            r'\s*<span class="db-default-actions">(.*?)</span>\s*</span>',
            serve_html,
            re.DOTALL,
        )
        self.assertIsNotNone(db_path_control)
        default_actions = db_path_control.group(1)
        self.assertLess(
            default_actions.index("data-adapter-default-db-save"),
            default_actions.index("data-adapter-default-db-clear"),
        )
        self.assertNotIn("db-source-add-actions", serve_html)
        self.assertIn('name="adapter" aria-label="Adapter"', serve_html)
        self.assertIn('<option value="auto" selected>Auto</option>', serve_html)
        self.assertIn(
            '<option value="opencode"  data-default-db="/tmp/opencode.db">opencode</option>',
            serve_html,
        )
        self.assertNotIn('name="alias"', serve_html)
        self.assertNotIn("data-source-alias-save", serve_html)
        self.assertNotIn("data-source-alias-input", serve_html)
        self.assertIn('data-table-column-key="${esc(column.key)}"', serve_html)
        self.assertIn(
            compact_css_text(
                ".configuration-sections{min-height:0;display:grid;"
                "gap:0;padding:16px;overflow:auto}"
            ),
            compact_serve_html,
        )
        self.assertNotIn("source-manager-list", serve_html)
        self.assertIn(
            compact_css_text(
                ".db-path-control{display:grid;"
                "grid-template-columns:minmax(0,1fr) max-content;"
                "align-items:stretch;gap:8px;min-width:0}"
            ),
            compact_serve_html,
        )
        self.assertNotIn("adapter-choice-group", serve_html)
        self.assertNotIn('type="radio" name="adapter"', serve_html)
        self.assertNotIn('data-source-action="refresh"', serve_html)
        self.assertNotIn(
            '{ key: "actions", label: t("serve_refresh", "Refresh")', serve_html
        )
        self.assertIn("data-source-config-rescan", sources_html)
        self.assertNotIn('data-source-action="delete"', serve_html)
        self.assertNotIn("data-source-bulk-state", serve_html)
        self.assertNotIn("data-source-bulk-delete", serve_html)
        self.assertIn("data-source-state-action", serve_html)
        self.assertIn("data-source-delete-action", serve_html)
        self.assertIn("Delete selected", serve_html)
        self.assertIn("删除所选", zh_serve_html)
        self.assertIn("Permanently delete selected sources?", serve_html)
        self.assertIn("永久删除所选来源？", zh_serve_html)
        self.assertIn("data-table-row-select", serve_html)
        self.assertIn("data-table-select-visible", serve_html)
        self.assertNotIn("function renderSourceSelectionHeader(rows)", serve_html)
        self.assertIn("function deleteVisibleServeSources()", serve_html)
        self.assertNotIn("2 sources", home_html)
        self.assertIn("common_session.jsonl", serve_html)
        self.assertIn("Timeline Waterfall", serve_html)
        self.assertIn("Timeline Detail Table", serve_html)
        self.assertIn('id="leaderboard-summary"', serve_html)

        self.assertIn(
            "function renderLeaderboard(rows = leaderboardRows())", serve_html
        )
        self.assertIn(
            "function renderLeaderboardSummary(rows = leaderboardRows())", serve_html
        )
        self.assertIn(
            "function renderTrajectoryOverview(rows = leaderboardRows())", serve_html
        )
        self.assertIn("function renderTrace()", serve_html)
        self.assertIn("function renderStepDrawer()", serve_html)
        self.assertIn(
            "function displayLeaderboardColumns(rows = leaderboardRows())",
            serve_html,
        )
        self.assertIn('t("task_alias", "Task / Alias")', serve_html)
        self.assertIn('t("last_turn_end", "Last Turn End")', serve_html)
        self.assertIn('key: "finished_at_ms"', serve_html)
        self.assertNotIn("function sourceColumns()", serve_html)
        self.assertIn("last_turn_finished_at_ms", serve_html)
        self.assertIn(
            '{ key: "source_tags", label: t("tags", "Tags"), valueType: "list"',
            serve_html,
        )
        self.assertIn(
            'commit: (row, value) => commitSourceCellEdit(row, "tags", value)',
            serve_html,
        )
        self.assertNotIn("source-table", serve_html)
        self.assertNotIn("sourceSelection:", serve_html)
        self.assertNotIn("function pruneSourceSelection()", serve_html)
        self.assertIn("new Set()", serve_html)
        self.assertIn('tableId: "harbor-dataset-registry"', serve_html)
        self.assertIn(
            "serveMode() ? [selectionColumn(), ...displayed] : displayed",
            serve_html,
        )
        self.assertIn("data-table-select-visible", serve_html)
        self.assertIn("data-table-row-select", serve_html)
        self.assertIn("leaderboard-export", serve_html)
        self.assertIn("function bindServeSourceControls()", serve_html)
        self.assertIn("function choosePathSourceFiles(button)", serve_html)
        self.assertIn(
            'const firstError = String(failures[0]?.error || "").trim();', serve_html
        )
        self.assertIn('serveApi("/api/config/locale"', serve_html)
        self.assertIn('serveApi("/api/config/adapter-default-db"', serve_html)
        self.assertIn('serveApi("/api/path-picker"', serve_html)
        self.assertIn("adapterDefaults: initialAdapterDefaults()", serve_html)
        self.assertIn("function saveAdapterDefaultDb(form, defaultDbPath)", serve_html)
        self.assertIn("function updateAdapterDefaultOptions()", serve_html)
        self.assertIn("function bindAdapterDefaultDbControls()", serve_html)
        self.assertNotIn("function renderServeSourceAliasCell(source)", serve_html)
        self.assertIn("function commitSourceCellEdit(row, field, value)", serve_html)
        self.assertIn(
            "function beginTableCellEdit(cell, { tableId, column, row, onChange = null })",
            serve_html,
        )
        self.assertNotIn("function saveInlineSourceEdit", serve_html)
        self.assertIn('serveApi("/api/db-sessions"', serve_html)
        self.assertIn("function inspectDbSessions(form)", serve_html)
        self.assertIn("function addSelectedDbSessions(form)", serve_html)
        self.assertIn("session_ids: sessionIds", serve_html)
        self.assertNotIn('serveApi("/api/upload"', serve_html)
        self.assertIn('serveApi("/api/config/harbor/mounts"', serve_html)
        self.assertIn('serveApi("/api/sources"', serve_html)
        self.assertIn('serveApi("/api/sources/reload"', serve_html)
        self.assertIn('href="/config"', home_html)
        self.assertNotIn("data-source-list", serve_html)
        self.assertIn("data-harbor-dataset-registry", serve_html)
        self.assertIn("data-harbor-mount-config", serve_html)
        self.assertNotIn("surface=sources", serve_html)
        self.assertNotIn("data-source-upload-form", serve_html)
        self.assertIn('t("export", "Export")', serve_html)
        self.assertIn('t("export_excel", "Export Excel")', serve_html)
        self.assertIn("data-summary-export-xlsx", serve_html)
        self.assertIn("data-view-export-selected", serve_html)
        self.assertIn("function exportLeaderboardSummary()", serve_html)
        self.assertIn("function exportSelectedWorkspaceViews()", serve_html)
        self.assertIn('t("export_xlsx_table", "Table (.xlsx)")', serve_html)
        self.assertIn('data-export-kind="xlsx"', serve_html)
        self.assertNotIn('data-export-kind="csv"', serve_html)
        self.assertIn('data-export-kind="json"', serve_html)
        self.assertIn('data-export-kind="workspace_html"', serve_html)
        self.assertNotIn('data-export-kind="html"', serve_html)
        self.assertIn("Workspace snapshot (.html)", serve_html)
        self.assertIn("工作台快照 (.html)", zh_serve_html)
        self.assertIn("function exportScopeRows()", serve_html)
        self.assertIn(
            "const selected = rows.filter((row) => state.rowSelection.has(row.trial_key));",
            serve_html,
        )
        self.assertIn("return selected.length ? selected : rows;", serve_html)
        self.assertIn("state.rowSelection.delete(key)", serve_html)
        self.assertIn("renderComparisonPanels({ trace: false })", serve_html)
        self.assertIn("event.stopPropagation();", serve_html)
        self.assertIn("function reportSubset(rows)", serve_html)
        self.assertIn("function renderAnalysisPaths(analysis)", serve_html)
        self.assertIn("analysis.md_report", serve_html)
        self.assertIn("analysis.relative_paths", serve_html)
        self.assertIn("analysis.markdown_reports", serve_html)
        self.assertIn("renderMarkdown(report.markdown)", serve_html)
        self.assertIn("Harbor Trial analysis", serve_html)
        self.assertIn("Harbor Trial 分析", zh_serve_html)
        self.assertIn("Workspace analysis", serve_html)
        self.assertIn("工作台分析", zh_serve_html)
        self.assertIn("function editableNotesSource(trialKey)", serve_html)
        self.assertIn("function saveSelectedNotes(button)", serve_html)
        self.assertIn("data-notes-edit", serve_html)
        self.assertIn("data-notes-save", serve_html)
        self.assertIn("/notes", serve_html)
        self.assertIn(
            "analysis: (original.annotations.analysis || []).filter((item) => selectedKeys.has(item.trial_key))",
            serve_html,
        )
        self.assertIn('"peval-report-v19.json"', serve_html)
        self.assertIn('"peval-workspace-snapshot.html"', serve_html)
        self.assertIn("peval-leaderboard.xlsx", serve_html)
        self.assertIn(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            serve_html,
        )
        self.assertIn("function xlsxBytesForRows(rows, columns)", serve_html)
        self.assertNotIn("peval-leaderboard-visible.csv", serve_html)

    def test_html_render_mode_rejects_unknown_mode(self) -> None:
        report = {
            "schema_version": 19,
            "includes": ["core"],
            "trajectory": [{"trajectory_id": "trial:mode", "steps": []}],
            "trajectory_meta": [
                {"trial_key": "trial:mode", "status": "passed", "steps": []}
            ],
        }

        with self.assertRaisesRegex(ValueError, "unsupported HTML render mode"):
            render_html(report, mode="dashboard")

    def test_html_report_locale_localizes_report_chrome_except_steps(self) -> None:
        config = ToolConfig(adapter="opencode")
        first = convert_records(
            read_jsonl(str(FIXTURES / "common_session.jsonl")), config
        )
        second = convert_records(
            read_jsonl(str(FIXTURES / "psychevo_session.jsonl")), config
        )
        report = build_multi_report(
            [
                ReportSession(
                    conversion=first,
                    input_label="common_session.jsonl",
                    input_path=str(FIXTURES / "common_session.jsonl"),
                    session_hint="common_session",
                ),
                ReportSession(
                    conversion=second,
                    input_label="psychevo_session.jsonl",
                    input_path=str(FIXTURES / "psychevo_session.jsonl"),
                    session_hint="psychevo_session",
                ),
            ],
            config,
            [],
        )

        english_html = render_html(report)
        zh_html = render_html(report, locale="zh-CN")

        self.assertIn('<html lang="en">', english_html)
        self.assertIn("<title>Agent Trajectory Report</title>", english_html)
        self.assertIn("<h1>Agent Trajectory Report</h1>", english_html)
        self.assertIn("Leaderboard", english_html)
        self.assertIn("Leaderboard Summary", english_html)
        self.assertIn("Trajectory Overview", english_html)
        self.assertIn('"leaderboard_summary": "Leaderboard Summary"', english_html)
        self.assertIn(
            '"leaderboard_summary_hint": "Compare one statistic at a time; '
            'expand the table for the full distribution."',
            english_html,
        )
        self.assertIn('"model_call_duration": "Model call duration"', english_html)
        self.assertIn('"summary_statistic": "Statistic"', english_html)
        self.assertIn('"summary_group_by": "Group by"', english_html)
        self.assertIn('"summary_show_table": "Show summary table"', english_html)
        self.assertNotIn('"summary_missing"', english_html)
        self.assertNotIn('"summary_total"', english_html)
        self.assertIn('"show_archived": "Show archived"', english_html)
        self.assertIn('"archive_selected": "Archive selected"', english_html)
        self.assertIn('"activate_selected": "Activate selected"', english_html)
        self.assertIn('"serve_archived_snapshots": "Archived snapshots"', english_html)
        self.assertIn(
            '"archived_view_unavailable": "No sessions are available in that view. Change the filters or turn off Show archived."',
            english_html,
        )
        self.assertNotIn("Not enough archived sessions", english_html)
        self.assertIn('"agent": "Agent"', english_html)
        self.assertIn('"filter": "Filter"', english_html)
        self.assertIn('"clear": "Clear"', english_html)
        self.assertIn('"apply": "Apply"', english_html)
        self.assertIn('"selected_count": "selected"', english_html)
        self.assertIn('"step_details": "Step details"', english_html)
        self.assertIn('"open_step_details": "Open step details"', english_html)
        self.assertIn('"close": "Close"', english_html)
        self.assertNotIn("Agent 轨迹报告", english_html)
        self.assertNotIn("可见热力图", english_html)
        self.assertNotIn("visible_heatmap", english_html)

        self.assertIn('<html lang="zh-CN">', zh_html)
        self.assertIn("<title>Agent 轨迹报告</title>", zh_html)
        self.assertIn("<h1>Agent 轨迹报告</h1>", zh_html)
        self.assertIn('"leaderboard": "Leaderboard"', zh_html)
        self.assertIn('"leaderboard_summary": "Leaderboard 汇总"', zh_html)
        self.assertIn(
            '"leaderboard_summary_hint": "一次比较一个统计值；需要完整分布时再展开表格。"',
            zh_html,
        )
        self.assertIn('"model_call_duration": "模型调用耗时"', zh_html)
        self.assertIn('"summary_statistic": "统计项"', zh_html)
        self.assertIn('"summary_group_by": "分组方式"', zh_html)
        self.assertIn('"summary_show_table": "展开汇总表"', zh_html)
        self.assertNotIn('"summary_missing"', zh_html)
        self.assertNotIn('"summary_total"', zh_html)
        self.assertIn('"show_archived": "显示已归档"', zh_html)
        self.assertIn('"archive_selected": "归档所选"', zh_html)
        self.assertIn('"activate_selected": "启用所选"', zh_html)
        self.assertIn('"serve_archived_snapshots": "已归档快照"', zh_html)
        self.assertIn(
            '"archived_view_unavailable": "该视图没有可显示的会话。请调整筛选条件或关闭“显示已归档”。"',
            zh_html,
        )
        self.assertNotIn("不足两条", zh_html)
        self.assertIn('"agent": "Agent"', zh_html)
        self.assertIn('"trajectory_overview": "轨迹概览"', zh_html)
        self.assertIn('"filter": "筛选"', zh_html)
        self.assertIn('"clear": "清除"', zh_html)
        self.assertIn('"apply": "应用"', zh_html)
        self.assertIn('"selected_count": "已选"', zh_html)
        self.assertIn('"step_details": "Step 详情"', zh_html)
        self.assertIn('"open_step_details": "打开 Step 详情"', zh_html)
        self.assertIn('"close": "关闭"', zh_html)
        self.assertNotIn('"visible_heatmap"', zh_html)
        self.assertNotIn("visible_heatmap_eyebrow", zh_html)
        self.assertNotIn("leaderboard_eyebrow", zh_html)
        self.assertIn('"duration": "活跃耗时"', zh_html)
        self.assertIn('"status.passed": "通过"', zh_html)
        self.assertIn('"session": "Session"', zh_html)
        self.assertIn('"result": "Result"', zh_html)
        self.assertIn('"notes": "Notes"', zh_html)
        self.assertNotIn('"agent": "代理"', zh_html)
        self.assertIn(
            '"selected_trial_trajectory": "selected trial trajectory"', zh_html
        )
        self.assertIn('"run": "Run"', zh_html)
        self.assertIn('"variant": "variant"', zh_html)
        self.assertIn('"evaluator": "evaluator"', zh_html)
        self.assertIn('"reasoning": "reasoning"', zh_html)
        self.assertIn('"reasoning_exposed": "reasoning exposed"', zh_html)
        self.assertIn('"steps_events": "steps/events"', zh_html)
        self.assertIn('"turns": "Turns"', zh_html)
        self.assertIn('"tool_calls": "Tool Calls"', zh_html)
        self.assertIn('"tool_success_total": "tool success / total"', zh_html)
        self.assertIn('"evidence": "Evidence"', zh_html)
        self.assertIn('"cache_read": "cache read"', zh_html)
        self.assertIn('"cache_write": "cache write"', zh_html)
        self.assertIn('"usage_breakdown": "用量明细"', zh_html)
        self.assertNotIn('"session": "会话"', zh_html)
        self.assertNotIn('"result": "结果"', zh_html)
        self.assertNotIn('"notes": "备注"', zh_html)
        self.assertNotIn('"trajectory_overview": "Trajectory Overview"', zh_html)
        self.assertNotIn('"selected_trial_trajectory": "选中的 Trial 轨迹"', zh_html)
        self.assertNotIn('"run": "运行"', zh_html)
        self.assertNotIn('"variant": "变体"', zh_html)
        self.assertNotIn('"evaluator": "评估器"', zh_html)
        self.assertNotIn('"reasoning": "推理"', zh_html)
        self.assertNotIn('"reasoning_exposed": "包含推理"', zh_html)
        self.assertNotIn('"steps_events": "步骤/事件"', zh_html)
        self.assertNotIn('"turns": "轮次"', zh_html)
        self.assertNotIn('"tool_calls": "工具调用"', zh_html)
        self.assertNotIn('"tool_success_total": "工具成功 / 总数"', zh_html)
        self.assertNotIn('"evidence": "证据"', zh_html)
        self.assertNotIn('"cache_read": "缓存读取"', zh_html)
        self.assertNotIn('"cache_write": "缓存写入"', zh_html)
        self.assertNotIn('"leaderboard": "排行榜"', zh_html)
        self.assertNotIn(">排行榜<", zh_html)
        self.assertIn("<h3>Steps (${count})</h3>", zh_html)
        self.assertIn("<h4>Tool Calls</h4>", zh_html)

    def test_html_renders_tool_names_timing_and_nested_observations(self) -> None:
        records = [
            MessageRecord(
                message={
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_call",
                            "id": "call-exec",
                            "name": "exec_command",
                            "arguments": {"cmd": "true"},
                        }
                    ],
                    "timestamp_ms": 1000,
                },
                usage={"prompt_tokens": 21460},
            ),
            MessageRecord(
                message={
                    "role": "tool_result",
                    "tool_call_id": "call-exec",
                    "tool_name": "exec_command",
                    "content": {"exit_code": 0},
                    "timestamp_ms": 1110,
                },
                metadata={"elapsed_ms": 101},
            ),
        ]
        config = ToolConfig(adapter="psychevo")
        result = convert_records(records, config)
        report = build_report(result, config, "inline")
        html = render_html(report)

        self.assertEqual(len(report["trajectory"][0]["steps"]), 1)
        self.assertIn("exec_command", html)
        self.assertIn("tool exec", html)
        self.assertIn("rail-summary", html)
        self.assertIn("rail-tool-row", html)
        self.assertIn("function stepTimingStats", html)
        self.assertIn("maxStepDurationMs", html)
        self.assertIn("maxToolExecutionMs", html)
        self.assertIn("elapsedMaxMs", html)
        self.assertIn("timeGradientStyle", html)
        self.assertIn("time-gradient", html)
        self.assertIn("--time-pct", html)
        self.assertIn("slowest step", html)
        self.assertIn("slowest tool", html)
        self.assertIn(
            'timeTitle("elapsed", meta?.elapsed_ms, elapsedRatio, "trajectory")', html
        )
        self.assertIn("function fmtRailTokens", html)
        self.assertIn("fmtRailTokens(tokenInfo.tokens)", html)
        self.assertIn("fmtNum(tokenInfo.tokens)", html)
        self.assertIn("Tool Calls", html)
        self.assertIn("Observations", html)
        self.assertEqual(
            report["trajectory_meta"][0]["steps"][0]["tool_calls"][0][
                "execution_duration_ms"
            ],
            101,
        )
