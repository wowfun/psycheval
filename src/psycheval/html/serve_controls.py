from __future__ import annotations

from html import escape

from psycheval.adapters import available_adapter_ids
from psycheval.html.assets import load_asset_text, replace_template_tokens


def render_serve_header(
    messages: dict[str, str],
    locale: str,
    *,
    page: str,
    role: str = "admin",
    authentication_enabled: bool = False,
) -> str:
    pages = [
        ("home", "/", messages["workspace_home"]),
        ("datasets", "/datasets", messages["harbor_datasets"]),
        ("reports", "/reports", messages["workspace_reports"]),
    ]
    if role == "admin":
        pages.append(("config", "/config", messages["workspace_configuration"]))
    links = "".join(
        f'<a href="{href}" class="workspace-nav-link'
        f'{" active" if key == page else ""}"'
        f' data-workspace-route="{key}"'
        f"{' aria-current="page"' if key == page else ''}>{escape(label)}</a>"
        for key, href, label in pages
    )
    if role == "admin":
        auth_control = (
            '<span class="serve-role-badge admin">'
            + escape(messages["serve_admin_role"])
            + "</span>"
        )
        if authentication_enabled:
            auth_control += (
                '<button class="action-button" type="button" data-admin-logout>'
                + escape(messages["serve_logout"])
                + "</button>"
            )
        language = (
            '<button class="action-button acp-launch" type="button" data-acp-open '
            f'aria-haspopup="dialog" disabled>{escape(messages["acp_client"])}'
            '<span class="acp-launch-mark" aria-hidden="true"></span></button>'
            + render_language_control(messages, locale)
        )
    else:
        auth_control = (
            '<span class="serve-role-badge guest">'
            + escape(messages["serve_guest_role"])
            + "</span>"
            + '<button class="action-button primary" type="button" data-admin-login-open>'
            + escape(messages["serve_login"])
            + "</button>"
        )
        language = ""
    return f"""
  <header class="workspace-header">
    <div class="workspace-header-left">
      <a class="workspace-brand" href="/" data-workspace-route="home">__TITLE__</a>
      <nav class="workspace-nav" aria-label="{escape(messages["workspace_navigation"])}">
        {links}
      </nav>
    </div>
    <div class="workspace-utilities">
      <p class="workspace-shell-status" data-global-shell-status role="status" aria-live="polite" hidden></p>
      {auth_control}
      {language}
    </div>
  </header>"""


def render_serve_home() -> str:
    return """
    <div class="workspace-description note-body" data-workspace-description hidden></div>
  <div class="workspace-content">
    <main class="workspace-main">
      <section id="report-notes"></section>
      <div class="workspace-main-scroll" data-workspace-main-scroll>
        <section class="panel-stack workspace-leaderboard-region" id="leaderboard-region"></section>
        <section class="panel-stack" id="comparison"></section>
        <section class="trace-panel" id="trace"></section>
      </div>
    </main>
    <div class="workspace-side-region" id="workspace-side-region">
      <aside class="workspace-views" id="workspace-views" hidden></aside>
      <aside class="detail-sidebar" id="detail-sidebar" hidden></aside>
    </div>
  </div>"""


def render_serve_configuration_page(
    messages: dict[str, str],
    adapter_defaults: dict[str, str],
) -> str:
    return replace_template_tokens(
        load_asset_text("serve_configuration.html"),
        {
            "CONFIGURATION": escape(messages["workspace_configuration"]),
            "ADD_SOURCE": escape(messages["serve_add_source"]),
            "SOURCE_FORMS": "".join(
                [
                    render_source_add_form("db", messages, adapter_defaults),
                    render_source_add_form("path", messages, adapter_defaults),
                ]
            ),
            "RELOAD": escape(messages["serve_reload"]),
            "RESCAN": escape(messages["serve_rescan"]),
            "TRAJECTORY_INGESTION": escape(messages["serve_trajectory_ingestion"]),
            "TRAJECTORY_INGESTION_COPY": escape(
                messages["serve_trajectory_ingestion_copy"]
            ),
            "ACP_AGENTS": escape(messages["serve_acp_agents"]),
            "ACP_AGENTS_COPY": escape(messages["serve_acp_agents_copy"]),
            "ACP_AGENTS_TRUST_COPY": escape(messages["serve_acp_agents_trust_copy"]),
            "LOCAL_PROCESS": escape(messages["serve_local_process"]),
            "ACP_OPENCODE_TEMPLATE": escape(messages["serve_acp_opencode_template"]),
            "ACP_OPENCODE_TEMPLATE_COPY": escape(
                messages["serve_acp_opencode_template_copy"]
            ),
            "ACP_AGENT_ID": escape(messages["serve_acp_agent_id"]),
            "ACP_AGENT_TITLE": escape(messages["serve_acp_agent_title"]),
            "ACP_COMMAND": escape(messages["serve_acp_command"]),
            "ACP_ARGS": escape(messages["serve_acp_args"]),
            "ADD_ACP_AGENT": escape(messages["serve_add_acp_agent"]),
            "CANCEL": escape(messages["cancel"]),
            "REMOVE_SELECTED_AGENTS": escape(messages["serve_remove_selected_agents"]),
            "PROMPT_ASSETS": escape(messages["serve_prompt_assets"]),
            "PROMPT_ASSETS_COPY": escape(messages["serve_prompt_assets_copy"]),
            "PROMPT_CONTENT": escape(messages["serve_prompt_content"]),
            "RESTORE_DEFAULT": escape(messages["serve_restore_default"]),
            "SAVE_PROMPT": escape(messages["serve_save_prompt"]),
            "DATASET_REGISTRY": escape(messages["serve_dataset_registry"]),
            "DATASET_REGISTRY_COPY": escape(messages["serve_dataset_registry_copy"]),
            "NEW_DATASET": escape(messages["harbor_add_dataset"]),
            "REGISTER_DATASET": escape(messages["harbor_register_dataset"]),
            "UNREGISTER_SELECTED": escape(messages["harbor_unregister_selected"]),
            "HARBOR_MOUNTS": escape(messages["serve_harbor_mounts"]),
            "HARBOR_MOUNTS_COPY": escape(messages["serve_harbor_config_copy"]),
            "ADD_HARBOR_MOUNT": escape(messages["serve_add_harbor_mount"]),
            "REMOVE_SELECTED_MOUNTS": escape(messages["harbor_remove_selected_mounts"]),
        },
    )


def render_serve_report_page(messages: dict[str, str], *, role: str = "admin") -> str:
    return replace_template_tokens(
        load_asset_text("serve_report_manager.html"),
        {
            "REPORTS": escape(messages["workspace_reports"]),
            "RELOAD": escape(messages["serve_reload"]),
            "REPORT_INVENTORY": escape(messages["report_inventory"]),
            "REPORT_BINDINGS": escape(messages["report_bindings"]),
            "REPORT_SEARCH_SESSIONS": escape(messages["report_search_sessions"]),
            "REPORT_BINDINGS_HIDDEN": " hidden" if role != "admin" else "",
            "REPORT_MANAGER_BODY_CLASS": " readonly" if role != "admin" else "",
        },
    )


def render_view_save_dialog(messages: dict[str, str], *, role: str = "admin") -> str:
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
  <div class="view-save-backdrop" data-view-save-dialog hidden>
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


def render_serve_overlays(
    messages: dict[str, str],
    *,
    role: str,
    authentication_enabled: bool,
) -> str:
    parts: list[str] = []
    if role != "admin" and authentication_enabled:
        parts.append(render_auth_dialog(messages))
    parts.append(render_view_save_dialog(messages, role=role))
    parts.append(
        '<aside class="report-reader" id="workspace-report-reader" hidden></aside>'
    )
    if role == "admin":
        parts.append(render_acp_drawer(messages))
    return "".join(parts)


def render_acp_drawer(messages: dict[str, str]) -> str:
    return f"""
  <div class="acp-backdrop" data-acp-backdrop hidden></div>
  <aside class="acp-drawer" data-acp-drawer hidden role="dialog"
    aria-modal="true" aria-label="{escape(messages["acp_client"])}">
    <section class="acp-controls" aria-label="{escape(messages["acp_client"])}">
      <label><span>{escape(messages["acp_agent"])}</span>
        <select data-acp-agent></select>
      </label>
      <button class="action-button" type="button" data-acp-connect>{escape(messages["acp_connect"])}</button>
      <a class="action-button acp-configure" href="/config#acp-agents-title"
        data-workspace-route="config"
        data-acp-configure hidden>{escape(messages["acp_configure_agents"])}</a>
      <button class="action-button compact" type="button" data-acp-close
        aria-label="{escape(messages["close"])}">{escape(messages["close"])}</button>
    </section>
    <div class="acp-chat-frame">
      <div class="acp-chat-placeholder" data-acp-placeholder>{escape(messages["acp_empty"])}</div>
      <div class="acp-chat-host" data-acp-chat></div>
    </div>
    <section class="acp-prompt-assets">
      <label><span>{escape(messages["acp_prompt_asset"])}</span>
        <select data-acp-prompt-asset><option value="">{escape(messages["acp_prompt_custom"])}</option></select>
      </label>
      <button class="action-button compact" type="button" data-acp-use-prompt>{escape(messages["acp_use_prompt"])}</button>
    </section>
  </aside>"""


def render_auth_dialog(messages: dict[str, str]) -> str:
    login = escape(messages["serve_login"])
    login_copy = escape(messages["serve_login_copy"])
    close = escape(messages["close"])
    admin_password = escape(messages["serve_admin_password"])
    return f"""
  <div class="auth-backdrop" data-admin-login-dialog hidden>
    <section class="auth-dialog" role="dialog" aria-modal="true" aria-labelledby="admin-login-title">
      <header class="configuration-page-head">
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


def render_harbor_dataset_page(messages: dict[str, str], *, role: str = "admin") -> str:
    admin_task_actions = ""
    admin_file_actions = ""
    admin_editor_actions = ""
    if role == "admin":
        admin_task_actions = f"""
        <button class="action-button" type="button" data-harbor-show-trash aria-pressed="false" disabled>{escape(messages["show_archived"])}</button>
        <button class="action-button primary" type="button" data-harbor-create-task disabled>{escape(messages["harbor_create_task"])}</button>
        <button class="action-button" type="button" data-harbor-sync-manifest disabled>{escape(messages["harbor_sync_manifest"])}</button>
        <button class="action-button" type="button" data-harbor-state-selected disabled>{escape(messages["archive_selected"])}</button>
        <button class="action-button danger" type="button" data-harbor-delete-selected disabled>{escape(messages["delete_selected"])}</button>
        <span class="harbor-operation-status" data-harbor-operation-status aria-live="polite"></span>"""
        admin_file_actions = f"""
          <div class="harbor-file-actions" data-harbor-file-actions hidden>
            <button class="action-button compact" type="button" data-harbor-new-file>{escape(messages["harbor_new_file"])}</button>
            <button class="action-button compact" type="button" data-harbor-new-directory>{escape(messages["harbor_new_folder"])}</button>
            <button class="action-button compact" type="button" data-harbor-upload>{escape(messages["harbor_upload"])}</button>
            <input type="file" data-harbor-upload-input hidden>
          </div>"""
        admin_editor_actions = f"""
            <div class="harbor-editor-actions">
              <button class="action-button primary compact" type="button" data-harbor-save disabled>{escape(messages["save"])}</button>
            </div>"""
    return replace_template_tokens(
        load_asset_text("serve_harbor_datasets.html"),
        {
            "DATASETS": escape(messages["harbor_datasets"]),
            "DATASET_EMPTY": escape(messages["harbor_dataset_empty"]),
            "FILE_EMPTY": escape(messages["harbor_file_empty"]),
            "EDITOR_EMPTY": escape(messages["harbor_editor_empty"]),
            "TASKS": escape(messages["harbor_tasks"]),
            "SELECTED_TASK": escape(messages["harbor_selected_task"]),
            "TASK_DETAIL_EMPTY": escape(messages["harbor_task_detail_empty"]),
            "SEARCH": escape(messages["harbor_search"]),
            "FILES": escape(messages["harbor_files"]),
            "EDITOR": escape(messages["harbor_editor"]),
            "TASK_ACTIONS": f"""
      <div class="harbor-workbench-tools">
        {admin_task_actions}
        <button class="action-button" type="button" data-harbor-reload>{escape(messages["serve_reload"])}</button>
      </div>""",
            "ADMIN_FILE_ACTIONS": admin_file_actions,
            "ADMIN_EDITOR_ACTIONS": admin_editor_actions,
        },
    )


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
