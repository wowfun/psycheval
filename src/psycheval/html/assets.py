from __future__ import annotations

from html import escape
from importlib.resources import files

ASSET_PACKAGE = "psycheval.assets"
ECHARTS_VERSION = "6.0.0"
ECHARTS_LOCAL_SRC = f"/assets/echarts/{ECHARTS_VERSION}/echarts.min.js"
ECHARTS_CDN_SRC = (
    f"https://cdn.jsdelivr.net/npm/echarts@{ECHARTS_VERSION}/dist/echarts.min.js"
)
WORKSPACE_STYLESHEET_PARTS = (
    "css/00-base.css",
    "css/05-data-table.css",
    "css/06-leaderboard-summary.css",
    "css/08-trajectory.css",
    "css/10-trace.css",
    "css/12-steps.css",
    "css/14-analysis.css",
    "css/16-timeline.css",
    "css/20-serve-toolbar.css",
    "css/22-source-forms.css",
    "css/23-harbor-workbench.css",
    "css/24-source-list-export.css",
    "css/26-detail-sidebar.css",
    "css/28-workspace-reports.css",
    "css/30-workspace-views.css",
    "css/32-acp-client.css",
)


def render_echarts_script() -> str:
    cdn = escape(ECHARTS_CDN_SRC)
    local = escape(ECHARTS_LOCAL_SRC)
    return (
        f'<script src="{local}" '
        f"onerror=\"this.onerror=null;this.src='{cdn}'\"></script>"
    )


def load_asset_text(name: str) -> str:
    return files(ASSET_PACKAGE).joinpath(name).read_text(encoding="utf-8")


def load_workspace_stylesheet() -> str:
    return "\n".join(load_asset_text(part) for part in WORKSPACE_STYLESHEET_PARTS)


def replace_template_tokens(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"__{key}__", value)
    return rendered
