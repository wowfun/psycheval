from __future__ import annotations

from html import escape
from typing import Any

from peval_py.adapters import available_adapter_ids
from peval_py.config import HarborMount
from peval_py.html.assets import load_asset_text, replace_template_tokens


def render_serve_source_manager(
    sources: list[dict[str, Any]],
    messages: dict[str, str],
    locale: str,
    adapter_defaults: dict[str, str],
    harbor_mounts: tuple[HarborMount, ...],
    *,
    loading: bool = False,
    role: str = "admin",
    authentication_enabled: bool = False,
) -> str:
    count = len(sources)
    source_word = messages["serve_source_count"]
    if count != 1:
        source_word = messages["serve_sources_count"]
    source_summary = (
        messages["serve_loading_sources"] if loading else f"{count} {source_word}"
    )
    source_status = (
        messages["serve_scanning_runs"]
        if loading
        else messages["serve_latest_snapshots"]
    )
    if role != "admin":
        return render_guest_toolbar(
            messages,
            source_summary=source_summary,
            source_status=source_status,
            loading=loading,
        )
    auth_control = (
        '<span class="serve-role-badge admin">'
        + escape(messages["serve_admin_role"])
        + "</span>"
        + '<button class="action-button" type="button" data-admin-logout>'
        + escape(messages["serve_logout"])
        + "</button>"
        if authentication_enabled
        else ""
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
            "AUTH_CONTROL": auth_control,
            "LANGUAGE_CONTROL": render_language_control(messages, locale),
            "MANAGER_COPY": escape(messages["serve_source_manager_copy"]),
            "CLOSE": escape(messages["close"]),
            "ADD_SOURCE": escape(messages["serve_add_source"]),
            "SOURCE_FORMS": "".join(
                [
                    render_source_add_form("db", messages, adapter_defaults),
                    render_source_add_form("path", messages, adapter_defaults),
                ]
            ),
            "HARBOR_CONFIG": render_harbor_config(harbor_mounts, messages),
            "SOURCES": escape(messages["serve_sources"]),
            "RELOAD": escape(messages["serve_reload"]),
            "ARCHIVE_SELECTED": escape(messages["archive_selected"]),
            "DELETE_SELECTED": escape(messages["delete_selected"]),
            "SOURCE_LIST_ITEMS": render_source_list_items(
                sources, messages, loading=loading
            ),
        },
    )


def render_serve_report_ui(messages: dict[str, str], *, role: str = "admin") -> str:
    return replace_template_tokens(
        load_asset_text("serve_report_manager.html"),
        {
            "REPORTS": escape(messages["workspace_reports"]),
            "REPORTS_COPY": escape(
                messages[
                    "workspace_reports_copy"
                    if role == "admin"
                    else "workspace_reports_guest_copy"
                ]
            ),
            "CLOSE": escape(messages["close"]),
            "REPORT_INVENTORY": escape(messages["report_inventory"]),
            "REPORT_BINDINGS": escape(messages["report_bindings"]),
            "REPORT_BINDINGS_HIDDEN": " hidden" if role != "admin" else "",
            "REPORT_MANAGER_BODY_CLASS": " readonly" if role != "admin" else "",
            "VIEW_SAVE_DIALOG": render_view_save_dialog(messages, role=role),
        },
    )


def render_view_save_dialog(
    messages: dict[str, str], *, role: str = "admin"
) -> str:
    save_view = escape(messages["save_view"])
    cancel = escape(messages["cancel"])
    current_configuration = escape(messages["view_current_configuration"])
    view_name = escape(messages["view_name"])
    view_notes = escape(messages["view_notes"])
    save = escape(messages["save"])
    if role == "admin":
        location = f"""
        <fieldset class="view-save-location">
          <legend>{escape(messages["view_save_location"])}</legend>
          <label><input type="radio" name="view_location" value="workspace" checked> {escape(messages["view_workspace"])}</label>
          <label><input type="radio" name="view_location" value="browser"> {escape(messages["view_this_browser"])}</label>
        </fieldset>"""
    else:
        location = f"""
        <input type="hidden" name="view_location" value="browser">
        <p class="copy view-save-location-copy">{escape(messages["view_guest_local_copy"])}</p>"""
    return f"""
  <div class="view-save-backdrop" data-view-save-dialog hidden data-serve-only>
    <section class="view-save-dialog" role="dialog" aria-modal="true" aria-labelledby="view-save-title">
      <header class="view-save-head">
        <h2 id="view-save-title">{save_view}</h2>
        <button type="button" class="action-button compact" data-view-save-cancel aria-label="{cancel}">{cancel}</button>
      </header>
      <form data-view-save-form>
        <section class="view-current-configuration" aria-labelledby="view-current-configuration-title">
          <h3 id="view-current-configuration-title">{current_configuration}</h3>
          <dl data-view-current-configuration></dl>
        </section>
        {location}
        <label>{view_name}
          <input name="name" autocomplete="off" required maxlength="120" data-view-name-input>
        </label>
        <label>{view_notes}
          <textarea name="notes" rows="7" data-view-notes-input></textarea>
        </label>
        <div class="view-save-actions">
          <button type="button" class="action-button" data-view-save-cancel>{cancel}</button>
          <button type="submit" class="action-button primary">{save}</button>
        </div>
      </form>
    </section>
  </div>"""


def render_guest_toolbar(
    messages: dict[str, str],
    *,
    source_summary: str,
    source_status: str,
    loading: bool,
) -> str:
    status_class = "loading" if loading else ""
    guest_role = escape(messages["serve_guest_role"])
    workspace_reports = escape(messages["workspace_reports"])
    login = escape(messages["serve_login"])
    login_copy = escape(messages["serve_login_copy"])
    close = escape(messages["close"])
    admin_password = escape(messages["serve_admin_password"])
    return f"""
  <section class="serve-source-toolbar" data-serve-only>
    <div class="serve-source-heading">
      <h1>__TITLE__</h1>
      <div class="serve-source-status">
        <strong data-source-count>{escape(source_summary)}</strong>
        <span class="{status_class}" data-source-status aria-live="polite">{escape(source_status)}</span>
      </div>
    </div>
    <div class="workspace-description note-body" data-workspace-description hidden></div>
    <div class="serve-source-actions">
      <span class="serve-role-badge guest">{guest_role}</span>
      <button class="action-button" type="button" data-report-manager-open>{workspace_reports}</button>
      <button class="action-button primary" type="button" data-admin-login-open>{login}</button>
    </div>
  </section>
  <div class="auth-backdrop" data-admin-login-dialog hidden data-serve-only>
    <section class="auth-dialog" role="dialog" aria-modal="true" aria-labelledby="admin-login-title">
      <header class="source-manager-head">
        <div>
          <h2 id="admin-login-title">{login}</h2>
          <p class="copy">{login_copy}</p>
        </div>
        <button class="action-button compact" type="button" data-admin-login-close aria-label="{close}">{close}</button>
      </header>
      <form data-admin-login-form>
        <label>{admin_password}
          <input name="password" type="password" autocomplete="current-password" required>
        </label>
        <p class="serve-notice" data-admin-login-status aria-live="polite" hidden></p>
        <div class="source-form-actions">
          <button class="action-button primary" type="submit">{login}</button>
        </div>
      </form>
    </section>
  </div>"""


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
    }[kind]
    name = kind
    help_id = f"source-{kind}-auto-help"
    help_copy = (
        f'<span class="copy" id="{escape(help_id)}">'
        f"{escape(messages['serve_auto_adapter_help'])}</span>"
    )
    if kind == "path":
        field_tag = f'<textarea name="{escape(name)}" autocomplete="off" required rows="4" data-path-picker-target aria-describedby="{escape(help_id)}"></textarea>'
    elif kind == "db":
        select_adapter_title = escape(messages["serve_select_adapter_for_default_db"])
        field_tag = f"""<span class="db-path-control">
                <textarea name="{escape(name)}" autocomplete="off" required rows="2" aria-describedby="{escape(help_id)}"></textarea>
                <span class="db-default-actions">
                  <button class="action-button" type="button" data-adapter-default-db-save disabled title="{select_adapter_title}">{escape(messages["serve_save_adapter_default_db"])}</button>
                  <button class="action-button" type="button" data-adapter-default-db-clear disabled title="{select_adapter_title}">{escape(messages["serve_clear_adapter_default_db"])}</button>
                </span>
              </span>"""
    path_picker = ""
    if kind == "path":
        path_picker = f"""
            <div class="source-picker-actions">
              <button class="action-button" type="button" data-path-picker>{escape(messages["serve_choose_path_files"])}</button>
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
              <button class="action-button" type="button" data-db-inspect>{escape(messages["serve_inspect_db"])}</button>"""
        picker = """
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
                <button class="action-button primary" type="submit">{escape(messages["serve_add_source"])}</button>
              </span>
            </div>
            {picker}
          </form>"""


def render_harbor_config(
    mounts: tuple[HarborMount, ...],
    messages: dict[str, str],
) -> str:
    existing = "".join(render_harbor_mount_form(mount, messages) for mount in mounts)
    return f"""
          <section class="harbor-config" aria-label="{escape(messages["serve_harbor_config"])}">
            <header class="harbor-config-head">
              <strong>{escape(messages["serve_harbor_config"])}</strong>
              <span>{escape(messages["serve_harbor_config_copy"])}</span>
            </header>
            <div class="harbor-mount-list">{existing}</div>
            {render_harbor_mount_form(None, messages)}
          </section>"""


def render_harbor_mount_form(
    mount: HarborMount | None,
    messages: dict[str, str],
) -> str:
    mount_id = mount.id if mount is not None else ""
    jobs_path = mount.path if mount is not None else ""
    task_paths = "\n".join(mount.task_paths) if mount is not None else ""
    title = mount_id or messages["serve_add_harbor_mount"]
    original = (
        f'<input name="original_id" type="hidden" value="{escape(mount_id)}">'
        if mount is not None
        else ""
    )
    remove = (
        f'<button class="action-button danger" type="button" data-harbor-mount-remove>{escape(messages["serve_remove_harbor_mount"])}</button>'
        if mount is not None
        else ""
    )
    submit = (
        messages["serve_save_harbor_mount"]
        if mount is not None
        else messages["serve_add_harbor_mount"]
    )
    return f"""
            <form class="source-form harbor-mount-form" data-harbor-mount-form>
              <strong>{escape(title)}</strong>
              {original}
              <label>{escape(messages["serve_harbor_mount_id"])}
                <input name="mount_id" autocomplete="off" required value="{escape(mount_id)}">
              </label>
              <label>{escape(messages["serve_harbor_jobs_path"])}
                <textarea name="jobs_path" autocomplete="off" required rows="2">{escape(jobs_path)}</textarea>
              </label>
              <label>{escape(messages["serve_harbor_task_paths"])}
                <textarea name="task_paths" autocomplete="off" rows="3" placeholder="{escape(messages["serve_one_path_per_line"])}">{escape(task_paths)}</textarea>
              </label>
              <div class="source-form-actions">
                {remove}
                <button class="action-button primary" type="submit">{escape(submit)}</button>
              </div>
            </form>"""


def render_adapter_select(
    messages: dict[str, str], adapter_defaults: dict[str, str]
) -> str:
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
        return (
            f'<li class="source-row empty">{escape(messages["serve_no_sources"])}</li>'
        )
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
        f"{alias_html}</span>"
    )
    return f"""
            <li class="source-row {"archived" if not active else ""}" data-source-row data-source-key="{escape(source_key)}">
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
