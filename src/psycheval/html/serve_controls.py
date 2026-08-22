from __future__ import annotations

from html import escape
from typing import Any

from psycheval.adapters import available_adapter_ids
from psycheval.config import HarborDataset, HarborMount
from psycheval.html.assets import load_asset_text, replace_template_tokens


def render_serve_header(
    sources: list[dict[str, Any]],
    messages: dict[str, str],
    locale: str,
    *,
    page: str,
    loading: bool = False,
    role: str = "admin",
    authentication_enabled: bool = False,
) -> str:
    pages = [
        ("home", "/", messages["workspace_home"]),
        ("datasets", "/datasets", messages["harbor_datasets"]),
        ("reports", "/reports", messages["workspace_reports"]),
    ]
    if role == "admin":
        pages.append(("sources", "/sources", messages["serve_source_manager"]))
    links = "".join(
        f'<a href="{href}" class="workspace-nav-link'
        f'{" active" if key == page else ""}"'
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
        language = render_language_control(messages, locale)
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
  <header class="workspace-header" data-serve-only>
    <div class="workspace-header-left">
      <a class="workspace-brand" href="/">__TITLE__</a>
      <nav class="workspace-nav" aria-label="{escape(messages["workspace_navigation"])}">
        {links}
      </nav>
    </div>
    <div class="workspace-utilities">
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
      <aside class="workspace-views" id="workspace-views" hidden data-serve-only></aside>
      <aside class="step-drawer" id="step-drawer" hidden></aside>
    </div>
  </div>"""


def render_serve_source_manager(
    sources: list[dict[str, Any]],
    messages: dict[str, str],
    adapter_defaults: dict[str, str],
    harbor_mounts: tuple[HarborMount, ...],
    harbor_datasets: tuple[HarborDataset, ...] = (),
    harbor_revision: str = "",
    *,
    loading: bool = False,
) -> str:
    return replace_template_tokens(
        load_asset_text("serve_source_manager.html"),
        {
            "WORKSPACE_LABEL": escape(messages["workspace_label"]),
            "SOURCE_MANAGER": escape(messages["serve_source_manager"]),
            "MANAGER_COPY": escape(messages["serve_source_manager_copy"]),
            "ADD_SOURCE": escape(messages["serve_add_source"]),
            "SOURCE_FORMS": "".join(
                [
                    render_source_add_form("db", messages, adapter_defaults),
                    render_source_add_form("path", messages, adapter_defaults),
                ]
            ),
            "HARBOR_CONFIG": render_harbor_config(
                harbor_mounts, harbor_datasets, harbor_revision, messages
            ),
            "SOURCES": escape(messages["serve_sources"]),
            "RELOAD": escape(messages["serve_reload"]),
            "ARCHIVE_SELECTED": escape(messages["archive_selected"]),
            "DELETE_SELECTED": escape(messages["delete_selected"]),
            "SOURCE_LIST_ITEMS": render_source_list_items(
                sources, messages, loading=loading
            ),
        },
    )


def render_serve_report_page(messages: dict[str, str], *, role: str = "admin") -> str:
    return replace_template_tokens(
        load_asset_text("serve_report_manager.html"),
        {
            "WORKSPACE_LABEL": escape(messages["workspace_label"]),
            "REPORTS": escape(messages["workspace_reports"]),
            "REPORTS_COPY": escape(
                messages[
                    "workspace_reports_copy"
                    if role == "admin"
                    else "workspace_reports_guest_copy"
                ]
            ),
            "RELOAD": escape(messages["serve_reload"]),
            "REPORT_INVENTORY": escape(messages["report_inventory"]),
            "REPORT_BINDINGS": escape(messages["report_bindings"]),
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


def render_serve_overlays(
    messages: dict[str, str],
    *,
    page: str,
    role: str,
    authentication_enabled: bool,
) -> str:
    parts: list[str] = []
    if role != "admin" and authentication_enabled:
        parts.append(render_auth_dialog(messages))
    if page == "home":
        parts.append(render_view_save_dialog(messages, role=role))
    if page in {"home", "reports"}:
        parts.append(
            '<aside class="report-reader" id="workspace-report-reader" '
            "hidden data-serve-only></aside>"
        )
    return "".join(parts)


def render_auth_dialog(messages: dict[str, str]) -> str:
    login = escape(messages["serve_login"])
    login_copy = escape(messages["serve_login_copy"])
    close = escape(messages["close"])
    admin_password = escape(messages["serve_admin_password"])
    return f"""
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
    datasets: tuple[HarborDataset, ...],
    revision: str,
    messages: dict[str, str],
) -> str:
    existing = "".join(
        render_harbor_mount_form(mount, datasets, revision, messages)
        for mount in mounts
    )
    return f"""
          <section class="harbor-config" aria-label="{escape(messages["serve_harbor_config"])}">
            <header class="harbor-config-head">
              <strong>{escape(messages["serve_harbor_config"])}</strong>
              <span>{escape(messages["serve_harbor_config_copy"])}</span>
            </header>
            <div class="harbor-mount-list">{existing}</div>
            {render_harbor_mount_form(None, datasets, revision, messages)}
          </section>"""


def render_harbor_mount_form(
    mount: HarborMount | None,
    datasets: tuple[HarborDataset, ...],
    revision: str,
    messages: dict[str, str],
) -> str:
    mount_id = mount.id if mount is not None else ""
    jobs_path = mount.path if mount is not None else ""
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
              <input name="expected_revision" type="hidden" value="{escape(revision)}">
              <label>{escape(messages["serve_harbor_mount_id"])}
                <input name="mount_id" autocomplete="off" required value="{escape(mount_id)}">
              </label>
              <label>{escape(messages["serve_harbor_jobs_path"])}
                <textarea name="jobs_path" autocomplete="off" required rows="2">{escape(jobs_path)}</textarea>
              </label>
              {render_harbor_dataset_choices(mount, datasets, messages)}
              <div class="source-form-actions">
                {remove}
                <button class="action-button primary" type="submit">{escape(submit)}</button>
              </div>
            </form>"""


def render_harbor_dataset_choices(
    mount: HarborMount | None,
    datasets: tuple[HarborDataset, ...],
    messages: dict[str, str],
) -> str:
    selected = set(mount.dataset_ids if mount is not None else ())
    if not datasets:
        return (
            '<p class="copy harbor-dataset-empty">'
            + escape(messages["harbor_register_dataset_first"])
            + "</p>"
        )
    choices = "".join(
        '<label class="harbor-dataset-choice">'
        f'<input type="checkbox" name="dataset_ids" value="{escape(dataset.id)}" '
        f"{'checked' if dataset.id in selected else ''}>"
        f"<span><strong>{escape(dataset.id)}</strong>"
        f"<small>{escape(dataset.path)}</small></span></label>"
        for dataset in datasets
    )
    return f"""
              <fieldset class="harbor-dataset-choices">
                <legend>{escape(messages["harbor_mount_datasets"])}</legend>
                {choices}
              </fieldset>"""


def render_harbor_dataset_page(messages: dict[str, str], *, role: str = "admin") -> str:
    admin_dataset_actions = ""
    admin_task_actions = ""
    admin_file_actions = ""
    admin_editor_actions = ""
    if role == "admin":
        admin_dataset_actions = f"""
        <button class="action-button" type="button" data-harbor-add-dataset>{escape(messages["harbor_add_dataset"])}</button>
        <button class="action-button" type="button" data-harbor-register-dataset>{escape(messages["harbor_register_dataset"])}</button>"""
        admin_task_actions = f"""
      <div class="harbor-workbench-tools">
        <button class="action-button" type="button" data-harbor-edit-dataset data-harbor-live-action disabled>{escape(messages["harbor_edit"])}</button>
        <button class="action-button danger" type="button" data-harbor-remove-dataset data-harbor-live-action disabled>{escape(messages["harbor_remove"])}</button>
        <button class="action-button primary" type="button" data-harbor-create-task data-harbor-live-action disabled>{escape(messages["harbor_create_task"])}</button>
        <button class="action-button" type="button" data-harbor-sync-manifest data-harbor-live-action disabled>{escape(messages["harbor_sync_manifest"])}</button>
        <button class="action-button" type="button" data-harbor-rename-task data-harbor-live-action disabled>{escape(messages["harbor_rename"])}</button>
        <button class="action-button danger" type="button" data-harbor-trash-task data-harbor-live-action disabled>{escape(messages["harbor_trash"])}</button>
        <button class="action-button" type="button" data-harbor-restore-task data-harbor-trash-action hidden disabled>{escape(messages["harbor_restore"])}</button>
        <button class="action-button danger" type="button" data-harbor-purge-task data-harbor-trash-action hidden disabled>{escape(messages["harbor_purge"])}</button>
        <button class="action-button" type="button" data-harbor-show-trash disabled>{escape(messages["harbor_trash"])}</button>
        <span class="harbor-operation-status" data-harbor-operation-status aria-live="polite"></span>
      </div>"""
        admin_file_actions = f"""
          <div class="harbor-file-actions" data-harbor-file-actions hidden>
            <button class="action-button compact" type="button" data-harbor-new-file>{escape(messages["harbor_new_file"])}</button>
            <button class="action-button compact" type="button" data-harbor-new-directory>{escape(messages["harbor_new_folder"])}</button>
            <button class="action-button compact" type="button" data-harbor-upload>{escape(messages["harbor_upload"])}</button>
            <input type="file" data-harbor-upload-input hidden>
          </div>"""
        admin_editor_actions = f"""
            <div class="harbor-editor-actions">
              <button class="action-button compact" type="button" data-harbor-download hidden>{escape(messages["harbor_download"])}</button>
              <button class="action-button primary compact" type="button" data-harbor-save disabled>{escape(messages["save"])}</button>
            </div>"""
    return replace_template_tokens(
        load_asset_text("serve_harbor_datasets.html"),
        {
            "WORKSPACE_LABEL": escape(messages["workspace_label"]),
            "DATASETS": escape(messages["harbor_datasets"]),
            "DATASETS_COPY": escape(
                messages[
                    "harbor_datasets_copy"
                    if role == "admin"
                    else "harbor_datasets_guest_copy"
                ]
            ),
            "RELOAD": escape(messages["serve_reload"]),
            "DATASET_EMPTY": escape(messages["harbor_dataset_empty"]),
            "FILE_EMPTY": escape(messages["harbor_file_empty"]),
            "EDITOR_EMPTY": escape(messages["harbor_editor_empty"]),
            "TASKS": escape(messages["harbor_tasks"]),
            "SELECTED_TASK": escape(messages["harbor_selected_task"]),
            "TASK_DETAIL_EMPTY": escape(messages["harbor_task_detail_empty"]),
            "SEARCH": escape(messages["harbor_search"]),
            "FILES": escape(messages["harbor_files"]),
            "EDITOR": escape(messages["harbor_editor"]),
            "ADMIN_DATASET_ACTIONS": admin_dataset_actions,
            "ADMIN_TASK_ACTIONS": admin_task_actions,
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
