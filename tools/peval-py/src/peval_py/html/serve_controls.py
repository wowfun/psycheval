from __future__ import annotations

from html import escape
from typing import Any

from peval_py.adapters import available_adapter_ids
from peval_py.html.assets import load_asset_text, replace_template_tokens

def render_serve_source_manager(
    sources: list[dict[str, Any]],
    messages: dict[str, str],
    locale: str,
    adapter_defaults: dict[str, str],
    *,
    loading: bool = False,
) -> str:
    count = len(sources)
    source_word = messages["serve_source_count"]
    if count != 1:
        source_word = messages["serve_sources_count"]
    source_summary = (
        messages["serve_loading_sources"]
        if loading
        else f"{count} {source_word}"
    )
    source_status = (
        messages["serve_scanning_runs"]
        if loading
        else messages["serve_latest_snapshots"]
    )
    return replace_template_tokens(
        load_asset_text("serve_source_manager.html"),
        {
            "SOURCE_SUMMARY": escape(source_summary),
            "SOURCE_STATUS": escape(source_status),
            "SOURCE_STATUS_CLASS": "loading" if loading else "",
            "REFRESH": escape(messages["serve_refresh"]),
            "SOURCE_MANAGER": escape(messages["serve_source_manager"]),
            "REPORTS": escape(messages["workspace_reports"]),
            "LANGUAGE_CONTROL": render_language_control(messages, locale),
            "DROP_COPY": escape(messages["serve_drop_copy"]),
            "CLOSE": escape(messages["close"]),
            "ADD_SOURCE": escape(messages["serve_add_source"]),
            "SOURCE_FORMS": "".join(
                [
                    render_source_add_form("path", messages, adapter_defaults),
                    render_source_add_form("db", messages, adapter_defaults),
                    render_source_add_form("input_table", messages, adapter_defaults),
                    render_upload_form(messages, adapter_defaults),
                ]
            ),
            "SOURCES": escape(messages["serve_sources"]),
            "RELOAD": escape(messages["serve_reload"]),
            "ARCHIVE_SELECTED": escape(messages["archive_selected"]),
            "DELETE_SELECTED": escape(messages["delete_selected"]),
            "SOURCE_LIST_ITEMS": render_source_list_items(sources, messages, loading=loading),
        },
    )


def render_serve_report_ui(messages: dict[str, str]) -> str:
    return replace_template_tokens(
        load_asset_text("serve_report_manager.html"),
        {
            "REPORTS": escape(messages["workspace_reports"]),
            "REPORTS_COPY": escape(messages["workspace_reports_copy"]),
            "CLOSE": escape(messages["close"]),
            "REPORT_INVENTORY": escape(messages["report_inventory"]),
            "REPORT_BINDINGS": escape(messages["report_bindings"]),
        },
    )


def render_language_control(messages: dict[str, str], locale: str) -> str:
    options = [
        ("en", messages["language_en"]),
        ("zh-CN", messages["language_zh_cn"]),
    ]
    option_html = "".join(
        f'<option value="{escape(value)}" {"selected" if value == locale else ""}>{escape(label)}</option>'
        for value, label in options
    )
    return f"""
      <label class="serve-language-select">
        <span>{escape(messages["language"])}</span>
        <select data-locale-select aria-label="{escape(messages["language"])}">
          {option_html}
        </select>
      </label>"""


def render_source_add_form(
    kind: str,
    messages: dict[str, str],
    adapter_defaults: dict[str, str],
) -> str:
    label_key = {
        "path": "serve_path_source",
        "db": "serve_db_source",
        "input_table": "serve_input_table_source",
    }[kind]
    name = "input_table" if kind == "input_table" else kind
    help_id = f"source-{kind}-auto-help"
    help_copy = (
        f'<span class="copy" id="{escape(help_id)}">'
        f'{escape(messages["serve_auto_adapter_help"])}</span>'
    )
    if kind == "path":
        field_tag = f'<textarea name="{escape(name)}" autocomplete="off" required rows="4" data-path-picker-target aria-describedby="{escape(help_id)}"></textarea>'
    elif kind == "db":
        select_adapter_title = escape(messages["serve_select_adapter_for_default_db"])
        field_tag = f"""<span class="db-path-control">
                <textarea name="{escape(name)}" autocomplete="off" required rows="2" aria-describedby="{escape(help_id)}"></textarea>
                <span class="db-default-actions">
                  <button class="step-toggle-button" type="button" data-adapter-default-db-save disabled title="{select_adapter_title}">{escape(messages["serve_save_adapter_default_db"])}</button>
                  <button class="step-toggle-button" type="button" data-adapter-default-db-clear disabled title="{select_adapter_title}">{escape(messages["serve_clear_adapter_default_db"])}</button>
                </span>
              </span>"""
    else:
        field_tag = f'<input name="{escape(name)}" autocomplete="off" required aria-describedby="{escape(help_id)}">'
    path_picker = ""
    if kind == "path":
        path_picker = f"""
            <div class="source-picker-actions">
              <button class="step-toggle-button" type="button" data-path-picker>{escape(messages["serve_choose_path_files"])}</button>
            </div>"""
    session_field = ""
    if kind == "db":
        session_field = f"""
            <label>{escape(messages["serve_session_id"])}
              <input name="session_id" autocomplete="off">
            </label>"""
    inspect_button = ""
    picker = ""
    if kind == "db":
        inspect_button = f"""
              <button class="step-toggle-button" type="button" data-db-inspect>{escape(messages["serve_inspect_db"])}</button>"""
        picker = f"""
            <div class="db-session-picker" data-db-session-picker hidden></div>"""
    return f"""
          <form class="source-form" data-source-add-form data-source-kind="{escape(kind)}">
            <label>{escape(messages[label_key])}
              {field_tag}
              {help_copy}
            </label>
            {path_picker}
            {session_field}
            <div class="source-form-actions">
              {inspect_button}
              <span class="source-add-actions">
                {render_adapter_select(messages, adapter_defaults)}
                <button class="step-toggle-button" type="submit">{escape(messages["serve_add_source"])}</button>
              </span>
            </div>
            {picker}
          </form>"""


def render_upload_form(messages: dict[str, str], adapter_defaults: dict[str, str]) -> str:
    return f"""
          <form class="source-form upload-form" data-source-upload-form>
            <strong>{escape(messages["serve_upload_snapshot"])}</strong>
            <label>{escape(messages["serve_upload_file"])}
              <input name="file" type="file" accept=".json,.jsonl,application/json,application/x-ndjson" required>
            </label>
            <div class="source-form-actions">
              <span class="source-add-actions">
                {render_adapter_select(messages, adapter_defaults)}
                <button class="step-toggle-button" type="submit">{escape(messages["serve_upload"])}</button>
              </span>
            </div>
          </form>"""


def render_adapter_select(messages: dict[str, str], adapter_defaults: dict[str, str]) -> str:
    options = [
        ("auto", messages["serve_adapter_auto"]),
        *[(adapter_id, adapter_id) for adapter_id in available_adapter_ids()],
    ]
    option_html = "".join(
        render_adapter_option(value, label, adapter_defaults)
        for value, label in options
    )
    return f"""
              <label class="source-adapter-select">
                <span>{escape(messages["serve_adapter"])}</span>
                <select name="adapter" aria-label="{escape(messages["serve_adapter"])}">
                  {option_html}
                </select>
              </label>"""


def render_adapter_option(
    value: str,
    label: str,
    adapter_defaults: dict[str, str],
) -> str:
    default_db = adapter_defaults.get(value)
    default_attr = f' data-default-db="{escape(default_db)}"' if default_db else ""
    selected = "selected" if value == "auto" else ""
    return f'<option value="{escape(value)}" {selected}{default_attr}>{escape(label)}</option>'


def render_source_list_items(
    sources: list[dict[str, Any]],
    messages: dict[str, str],
    *,
    loading: bool = False,
) -> str:
    if loading:
        return f'<li class="source-row empty loading">{escape(messages["serve_scanning_runs"])}</li>'
    if not sources:
        return f'<li class="source-row empty">{escape(messages["serve_no_sources"])}</li>'
    return "".join(render_source_list_item(source, messages) for source in sources)


def render_source_list_item(
    source: dict[str, Any],
    messages: dict[str, str],
) -> str:
    label = str(source.get("label") or source.get("source_key") or "source")
    alias = str(source.get("source_alias") or "")
    display_label = alias or label
    kind = str(source.get("kind") or "source")
    adapter = str(source.get("adapter") or "-")
    status = str(source.get("last_status") or "-")
    active = bool(source.get("active", True))
    source_key = str(source.get("source_key") or "")
    trial_key = str(source.get("trial_key") or "")
    source_checkbox = (
        f'<label class="select-box"><input type="checkbox" data-source-row-select="{escape(source_key)}" '
        f'aria-label="{escape(messages["select_source"])}: {escape(source_key)}"><span></span></label>'
        if source_key
        else ""
    )
    state_label = messages["serve_active"] if active else messages["serve_archived"]
    alias_html = escape(alias) if alias else '<span class="muted">-</span>'
    alias_cell = (
        f'<span class="editable-source-cell" data-source-inline-edit="alias" '
        f'data-source-key="{escape(source_key)}" data-trial-key="{escape(trial_key)}" '
        f'data-value="{escape(alias)}" title="{escape(messages["double_click_to_edit"])}">'
        f'{alias_html}</span>'
    )
    return f"""
            <li class="source-row {'archived' if not active else ''}" data-source-row data-source-key="{escape(source_key)}">
              <div class="source-row-select">{source_checkbox}</div>
              <div class="source-row-main">
                <strong>{escape(display_label)}</strong>
                {render_source_origin(label, alias)}
                <span>{escape(kind)} / {escape(adapter)} / {escape(status)} / {escape(state_label)}</span>
                {alias_cell}
              </div>
            </li>"""


def render_source_origin(label: str, alias: str) -> str:
    if not alias:
        return ""
    return f'<span class="source-origin">{escape(label)}</span>'
