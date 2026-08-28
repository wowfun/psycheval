from __future__ import annotations

import json
from html import escape
from typing import Any

from psycheval.html.assets import load_asset_text
from psycheval.html.serve_controls import (
    render_harbor_dataset_page,
    render_serve_configuration_page,
    render_serve_header,
    render_serve_home,
    render_serve_overlays,
    render_serve_report_page,
)
from psycheval.i18n import messages_for, normalize_locale


def render_serve_html(
    locale: str = "en",
    adapter_defaults: dict[str, str] | None = None,
    loading: bool = False,
    load_error: str | None = None,
    workspace_id: str | None = None,
    workspace_description: str | None = None,
    role: str = "admin",
    authentication_enabled: bool = False,
    serve_page: str = "home",
) -> str:
    normalized_page = normalize_serve_page(serve_page)
    normalized_locale = normalize_locale(locale)
    messages = messages_for(normalized_locale)
    render_options: dict[str, Any] = {
        "adapter_defaults": adapter_defaults or {},
        "loading": bool(loading),
        "workspace_id": workspace_id or "default",
        "role": role,
        "authentication_enabled": bool(authentication_enabled),
        "initial_page": normalized_page,
    }
    normalized_description = str(workspace_description or "").strip()
    if normalized_description:
        render_options["workspace_description"] = normalized_description
    if load_error:
        render_options["load_error"] = load_error

    payload = load_asset_text("workspace.html")
    payload = payload.replace("__LANG__", escape(normalized_locale))
    payload = payload.replace(
        "__BODY_CLASS__", escape(f"serve-mode serve-page-{normalized_page}")
    )
    payload = payload.replace(
        "__SERVE_HEADER__",
        render_serve_header(
            messages,
            normalized_locale,
            page=normalized_page,
            role=role,
            authentication_enabled=authentication_enabled,
        ),
    )
    payload = payload.replace(
        "__PAGE_CONTENT__",
        render_serve_pages(
            normalized_page,
            messages,
            role=role,
            adapter_defaults=adapter_defaults or {},
        ),
    )
    payload = payload.replace(
        "__SERVE_OVERLAYS__",
        render_serve_overlays(
            messages,
            role=role,
            authentication_enabled=authentication_enabled,
        ),
    )
    payload = payload.replace("__TITLE__", escape(messages["serve_title"]))
    payload = payload.replace(
        "__I18N__",
        safe_json_for_script(json.dumps(messages, ensure_ascii=False)),
    )
    payload = payload.replace(
        "__RENDER_OPTIONS__",
        safe_json_for_script(json.dumps(render_options, ensure_ascii=False)),
    )
    return payload


def render_serve_pages(
    initial_page: str,
    messages: dict[str, str],
    *,
    role: str,
    adapter_defaults: dict[str, str],
) -> str:
    pages = [
        ("home", render_serve_home()),
        ("datasets", render_harbor_dataset_page(messages, role=role)),
        ("reports", render_serve_report_page(messages, role=role)),
    ]
    if role == "admin":
        pages.append(
            ("config", render_serve_configuration_page(messages, adapter_defaults))
        )
    return "".join(
        f'<section class="workspace-page-slot" data-workspace-page="{page}" '
        f'tabindex="-1"{"" if page == initial_page else " hidden"}>'
        f"{content}</section>"
        for page, content in pages
    )


def normalize_serve_page(value: object) -> str:
    page = str(value or "home").strip().lower()
    if page not in {"home", "datasets", "reports", "config"}:
        raise ValueError(f"unsupported serve page: {page}")
    return page


def safe_json_for_script(value: str) -> str:
    return value.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
