from __future__ import annotations

import json
import math
from html import escape
from importlib import import_module
from typing import Any

from psycheval.html.assets import load_asset_text, render_echarts_script
from psycheval.html.serve_controls import (
    render_harbor_dataset_page,
    render_serve_configuration_page,
    render_serve_header,
    render_serve_home,
    render_serve_overlays,
    render_serve_report_page,
)
from psycheval.i18n import messages_for, normalize_locale


def render_html(
    report: dict[str, Any],
    locale: str = "en",
    mode: str = "report",
    sources: list[dict[str, Any]] | None = None,
    reports: list[dict[str, Any]] | None = None,
    adapter_defaults: dict[str, str] | None = None,
    loading: bool = False,
    load_error: str | None = None,
    workspace_id: str | None = None,
    workspace_description: str | None = None,
    role: str = "admin",
    authentication_enabled: bool = False,
    serve_page: str = "home",
) -> str:
    normalized_mode = normalize_render_mode(mode)
    return _render_html_document(
        report,
        locale=locale,
        mode=normalized_mode,
        sources=sources,
        reports=reports,
        adapter_defaults=adapter_defaults,
        loading=loading,
        load_error=load_error,
        workspace_id=workspace_id,
        workspace_description=workspace_description,
        role=role,
        authentication_enabled=authentication_enabled,
        serve_page=serve_page,
    )


def render_workspace_snapshot_html(
    report: dict[str, Any],
    snapshot: dict[str, Any],
    locale: str,
    echarts_js: str,
) -> str:
    return _render_html_document(
        report,
        locale=locale,
        mode="workspace_snapshot",
        sources=list_value(snapshot.get("catalog_rows")),
        reports=list_value(snapshot.get("reports")),
        snapshot=snapshot,
        echarts_js=echarts_js,
        workspace_description=str(snapshot.get("workspace_description") or ""),
    )


def _render_html_document(
    report: dict[str, Any],
    *,
    locale: str,
    mode: str,
    sources: list[dict[str, Any]] | None = None,
    reports: list[dict[str, Any]] | None = None,
    adapter_defaults: dict[str, str] | None = None,
    loading: bool = False,
    load_error: str | None = None,
    snapshot: dict[str, Any] | None = None,
    echarts_js: str | None = None,
    workspace_id: str | None = None,
    workspace_description: str | None = None,
    role: str = "admin",
    authentication_enabled: bool = False,
    serve_page: str = "home",
) -> str:
    normalized_mode = mode
    normalized_serve_page = normalize_serve_page(serve_page)
    normalized_locale = normalize_locale(locale)
    messages = messages_for(normalized_locale)
    serve_source_payload = (
        list(sources) if sources is not None else serve_sources(report)
    )
    render_options: dict[str, Any] = {
        "mode": normalized_mode,
        "sources": serve_source_payload
        if normalized_mode in {"serve", "workspace_snapshot"}
        else [],
    }
    if normalized_mode == "serve":
        render_options["reports"] = list(reports or [])
        render_options["adapter_defaults"] = adapter_defaults or {}
        render_options["loading"] = bool(loading)
        render_options["workspace_id"] = workspace_id or "default"
        render_options["role"] = role
        render_options["authentication_enabled"] = bool(authentication_enabled)
        render_options["serve_page"] = normalized_serve_page
        if load_error:
            render_options["load_error"] = load_error
    elif normalized_mode == "workspace_snapshot":
        render_options["reports"] = list(reports or [])
    normalized_description = str(workspace_description or "").strip()
    if normalized_mode in {"serve", "workspace_snapshot"} and normalized_description:
        render_options["workspace_description"] = normalized_description
    title_key = (
        "serve_title" if normalized_mode in {"serve", "workspace_snapshot"} else "title"
    )
    payload = load_asset_text("report.html").replace(
        "__LANG__", escape(normalized_locale)
    )
    body_class = (
        "serve-mode workspace-snapshot-mode"
        if normalized_mode == "workspace_snapshot"
        else (
            f"serve-mode serve-page-{normalized_serve_page}"
            if normalized_mode == "serve"
            else f"{normalized_mode}-mode"
        )
    )
    payload = payload.replace("__BODY_CLASS__", escape(body_class))
    if normalized_mode == "serve":
        serve_header = render_serve_header(
            messages,
            normalized_locale,
            page=normalized_serve_page,
            role=role,
            authentication_enabled=authentication_enabled,
        )
        if normalized_serve_page == "home":
            page_content = render_serve_home()
        elif normalized_serve_page == "datasets":
            page_content = render_harbor_dataset_page(messages, role=role)
        elif normalized_serve_page == "reports":
            page_content = render_serve_report_page(messages, role=role)
        else:
            page_content = render_serve_configuration_page(
                messages,
                adapter_defaults or {},
            )
        serve_overlays = render_serve_overlays(
            messages,
            page=normalized_serve_page,
            role=role,
            authentication_enabled=authentication_enabled,
        )
    else:
        serve_header = ""
        page_content = render_report_content(normalized_mode)
        serve_overlays = (
            '<aside class="step-drawer" id="step-drawer" hidden></aside>'
            if normalized_mode == "report"
            else '<aside class="report-reader" id="workspace-report-reader" hidden></aside>'
        )
    payload = payload.replace("__SERVE_HEADER__", serve_header)
    payload = payload.replace("__PAGE_CONTENT__", page_content)
    payload = payload.replace("__SERVE_OVERLAYS__", serve_overlays)
    payload = payload.replace("__TITLE__", escape(messages[title_key]))
    if normalized_mode == "workspace_snapshot":
        inline_echarts = str(echarts_js or "").replace("</script", "<\\/script")
        echarts_script = f"<script>{inline_echarts}</script>"
    elif normalized_mode == "serve" and normalized_serve_page != "home":
        echarts_script = ""
    else:
        echarts_script = render_echarts_script(normalized_mode)
    payload = payload.replace("__ECHARTS_SCRIPT__", echarts_script)
    payload = payload.replace("__CSS__", load_asset_text("report.css"))
    payload = payload.replace("__JS__", load_asset_text("report.js"))
    payload = payload.replace(
        "__DATA__",
        safe_json_for_script(json.dumps(report, ensure_ascii=False)),
    )
    payload = payload.replace(
        "__TOKEN_ESTIMATES__",
        safe_json_for_script(
            json.dumps(step_token_estimates(report), ensure_ascii=False)
        ),
    )
    payload = payload.replace(
        "__I18N__",
        safe_json_for_script(json.dumps(messages, ensure_ascii=False)),
    )
    payload = payload.replace(
        "__WORKSPACE_SNAPSHOT_DATA__",
        (
            '<script type="application/json" id="peval-workspace-snapshot">'
            + safe_json_for_script(json.dumps(snapshot or {}, ensure_ascii=False))
            + "</script>"
        )
        if normalized_mode == "workspace_snapshot"
        else "",
    )
    payload = payload.replace(
        "__RENDER_OPTIONS__",
        safe_json_for_script(json.dumps(render_options, ensure_ascii=False)),
    )
    return payload


def render_serve_html(
    report: dict[str, Any],
    locale: str = "en",
    sources: list[dict[str, Any]] | None = None,
    reports: list[dict[str, Any]] | None = None,
    adapter_defaults: dict[str, str] | None = None,
    loading: bool = False,
    load_error: str | None = None,
    workspace_id: str | None = None,
    workspace_description: str | None = None,
    role: str = "admin",
    authentication_enabled: bool = False,
    serve_page: str = "home",
) -> str:
    return render_html(
        report,
        locale=locale,
        mode="serve",
        sources=sources,
        reports=reports,
        adapter_defaults=adapter_defaults,
        loading=loading,
        load_error=load_error,
        workspace_id=workspace_id,
        workspace_description=workspace_description,
        role=role,
        authentication_enabled=authentication_enabled,
        serve_page=serve_page,
    )


def normalize_serve_page(value: object) -> str:
    page = str(value or "home").strip().lower()
    if page not in {"home", "datasets", "reports", "config"}:
        raise ValueError(f"unsupported serve page: {page}")
    return page


def render_report_content(mode: str) -> str:
    if mode == "workspace_snapshot":
        title = (
            '<section class="topline workspace-snapshot-header">'
            "<h1>__TITLE__</h1>"
            '<div class="workspace-description note-body" '
            "data-workspace-description hidden></div>"
            "</section>"
        )
        side = (
            '<div class="workspace-side-region" id="workspace-side-region">'
            '<aside class="workspace-views" id="workspace-views" hidden data-serve-only></aside>'
            '<aside class="step-drawer" id="step-drawer" hidden></aside>'
            "</div>"
        )
    else:
        title = '<section class="topline"><h1>__TITLE__</h1></section>'
        side = ""
    return f"""
  <div class="workspace-content">
    <main class="workspace-main">
      {title}
      <section id="report-notes"></section>
      <div class="workspace-main-scroll" data-workspace-main-scroll>
        <section class="panel-stack workspace-leaderboard-region" id="leaderboard-region"></section>
        <section class="panel-stack" id="comparison"></section>
        <section class="trace-panel" id="trace"></section>
      </div>
    </main>
    {side}
  </div>"""


def normalize_render_mode(mode: object) -> str:
    text = str(mode or "report").strip().lower()
    if text in {"report", "serve"}:
        return text
    raise ValueError(
        f"unsupported HTML render mode: {mode}; supported modes: report, serve"
    )


def serve_sources(report: dict[str, Any]) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    for index, meta in enumerate(list_value(report.get("trajectory_meta"))):
        if not isinstance(meta, dict):
            continue
        data_ref = as_dict(meta.get("data_ref"))
        label = (
            data_ref.get("relative_path")
            or data_ref.get("path")
            or meta.get("trial_key")
            or f"source-{index + 1}"
        )
        kind = meta.get("adapter") or "source"
        sources.append({"label": str(label), "kind": str(kind)})
    return sources


def step_token_estimates(
    report: dict[str, Any],
) -> dict[str, dict[str, dict[str, Any]]]:
    estimates: dict[str, dict[str, dict[str, Any]]] = {}
    trajectories = list_value(report.get("trajectory"))
    metas = list_value(report.get("trajectory_meta"))
    for index, trajectory in enumerate(trajectories):
        if not isinstance(trajectory, dict):
            continue
        meta = (
            metas[index]
            if index < len(metas) and isinstance(metas[index], dict)
            else {}
        )
        trial_key = str(
            meta.get("trial_key")
            or trajectory.get("trajectory_id")
            or trajectory.get("session_id")
            or f"input-{index + 1}"
        )
        model = as_dict(trajectory.get("agent")).get("model_name")
        counter, method = token_counter_for_model(model)
        step_estimates: dict[str, dict[str, Any]] = {}
        for step in list_value(trajectory.get("steps")):
            if not isinstance(step, dict):
                continue
            step_id = step.get("step_id")
            if step_id is None or exact_step_token_total(step) is not None:
                continue
            text = visible_step_text(step)
            if not text:
                continue
            tokens = counter(text) if counter else byte_length_token_estimate(text)
            step_estimates[str(step_id)] = {
                "tokens": max(0, int(tokens)),
                "estimated": True,
                "method": method,
                "source": "visible_step_text",
            }
        if step_estimates:
            estimates[trial_key] = step_estimates
    return estimates


def token_counter_for_model(model: object) -> tuple[Any | None, str]:
    importer = import_module
    try:
        from psycheval import html as html_facade

        importer = getattr(html_facade, "import_module", import_module)
    except Exception:  # noqa: BLE001 - optional patch compatibility only.
        pass
    try:
        tiktoken = importer("tiktoken")
    except Exception:  # noqa: BLE001 - optional renderer capability.
        return None, "byte_length_div_4"
    try:
        encoding = tiktoken.encoding_for_model(str(model)) if model else None
    except Exception:  # noqa: BLE001 - model may be unknown to tiktoken.
        encoding = None
    if encoding is None:
        try:
            encoding = tiktoken.get_encoding("o200k_base")
        except Exception:  # noqa: BLE001 - optional renderer capability.
            return None, "byte_length_div_4"
    name = str(getattr(encoding, "name", "") or model or "o200k_base")
    return lambda text: len(encoding.encode(text)), f"tiktoken:{name}"


def byte_length_token_estimate(text: str) -> int:
    return int(math.ceil(len(text.encode("utf-8")) / 4))


def visible_step_text(step: dict[str, Any]) -> str:
    parts: list[str] = []
    append_visible(parts, step.get("reasoning_content"))
    append_visible(parts, step.get("message"))
    for tool in list_value(step.get("tool_calls")):
        if not isinstance(tool, dict):
            continue
        append_visible(parts, tool.get("function_name"))
        append_visible(parts, tool.get("arguments"))
    for observation in list_value(as_dict(step.get("observation")).get("results")):
        if not isinstance(observation, dict):
            continue
        append_visible(parts, observation.get("content"))
    return "\n".join(part for part in parts if part)


def append_visible(parts: list[str], value: Any) -> None:
    text = visible_value(value)
    if text:
        parts.append(text)


def visible_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def exact_step_token_total(step: dict[str, Any]) -> int | None:
    metrics = as_dict(step.get("metrics"))
    prompt = numeric_value(metrics.get("prompt_tokens"))
    completion = numeric_value(metrics.get("completion_tokens"))
    if prompt is not None or completion is not None:
        return int((prompt or 0) + (completion or 0))
    usage_total = numeric_value(as_dict(metrics.get("usage")).get("total_tokens"))
    return int(usage_total) if usage_total is not None else None


def numeric_value(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return number


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def safe_json_for_script(value: str) -> str:
    return value.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
