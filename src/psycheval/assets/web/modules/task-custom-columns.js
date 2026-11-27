import { beginFeedback } from "./action-feedback.js";
import { normalizeTableListValue } from "./data-tables.js";
import { closeModalSurface, openModalSurface } from "./modal-surfaces.js";
import { esc, formatMessage, t } from "./shared.js";

const CUSTOM_COLUMN_PREFIX = "meta:";
const CUSTOM_SCHEMA_VERSION = 1;
const MAX_DISCOVERED_CUSTOM_COLUMNS = 64;
const MAX_CUSTOM_KEY_BYTES = 128;
const MAX_CUSTOM_STRING_BYTES = 16 * 1024;
const MAX_CUSTOM_LIST_ITEMS = 128;
const MAX_CUSTOM_LIST_ITEM_BYTES = 256;
const RESERVED_METADATA_KEYS = new Set(["category", "difficulty", "source_case"]);
const VALID_COLUMN_TYPES = new Set(["text", "enum", "number", "boolean", "list"]);

const utf8Encoder = new TextEncoder();

function utf8Length(value) {
  return utf8Encoder.encode(String(value)).length;
}

function hasControlChars(value) {
  return /\p{Cc}/u.test(String(value));
}

function hasDisallowedTextControls(value) {
  for (const char of String(value)) {
    if (/\p{Cc}/u.test(char) && char !== "\t" && char !== "\n" && char !== "\r") return true;
  }
  return false;
}

function validateCustomColumnKey(rawKey) {
  if (typeof rawKey !== "string") throw new Error(t("task_custom_key_invalid", "Enter a nonblank key without control characters (at most 128 UTF-8 bytes)"));
  const key = rawKey;
  if (!key || key !== key.trim() || hasControlChars(key) || utf8Length(key) > MAX_CUSTOM_KEY_BYTES) {
    throw new Error(t("task_custom_key_invalid", "Enter a nonblank key without control characters (at most 128 UTF-8 bytes)"));
  }
  if (RESERVED_METADATA_KEYS.has(key)) {
    throw new Error(formatMessage("task_custom_key_reserved", "Key “{key}” is reserved in task.toml [metadata]", { key }));
  }
  return key;
}

function encodeCustomColumnKey(rawKey) {
  const key = validateCustomColumnKey(rawKey);
  return CUSTOM_COLUMN_PREFIX + encodeURIComponent(key).replace(
    /[!'()*]/g,
    char => `%${char.charCodeAt(0).toString(16).toUpperCase()}`,
  );
}

function decodeCustomColumnKey(columnKey) {
  if (typeof columnKey !== "string" || !columnKey.startsWith(CUSTOM_COLUMN_PREFIX)) return null;
  let decoded;
  try {
    decoded = decodeURIComponent(columnKey.slice(CUSTOM_COLUMN_PREFIX.length));
  } catch {
    return null;
  }
  try {
    const validated = validateCustomColumnKey(decoded);
    return encodeCustomColumnKey(validated) === columnKey ? validated : null;
  } catch {
    return null;
  }
}

function isCustomColumnKey(columnKey) {
  return decodeCustomColumnKey(columnKey) !== null;
}

function customSchemaStorageKey(workspaceId) {
  return `peval.tasks-custom-columns.v${CUSTOM_SCHEMA_VERSION}.${String(workspaceId || "default")}`;
}

function parseEnumOptions(raw) {
  const parts = Array.isArray(raw) ? raw : String(raw ?? "").split(/[\r\n,，]+/);
  const out = [];
  const seen = new Set();
  for (const item of parts) {
    const text = String(item ?? "").trim();
    if (!text || seen.has(text)) continue;
    seen.add(text);
    out.push(text);
  }
  return out;
}

function normalizeSchemaEntry(entry) {
  if (!entry || typeof entry !== "object") return null;
  let key;
  try {
    key = validateCustomColumnKey(String(entry.key ?? "").trim());
  } catch {
    return null;
  }
  const type = VALID_COLUMN_TYPES.has(entry.type) ? entry.type : "text";
  const options = type === "enum" ? parseEnumOptions(entry.options) : [];
  if (type === "enum" && !options.length) return { key, type: "text", options: [] };
  return { key, type, options };
}

function loadCustomColumnSchemas({ workspaceId, storage } = {}) {
  if (!storage) return [];
  try {
    const parsed = JSON.parse(storage.getItem(customSchemaStorageKey(workspaceId)) || "[]");
    if (!Array.isArray(parsed)) return [];
    const seen = new Set();
    const out = [];
    for (const item of parsed) {
      const normalized = normalizeSchemaEntry(item);
      if (!normalized || seen.has(normalized.key)) continue;
      seen.add(normalized.key);
      out.push(normalized);
    }
    return out;
  } catch {
    return [];
  }
}

function saveCustomColumnSchemas(schemas, { workspaceId, storage } = {}) {
  if (!storage) return;
  try {
    const clean = [];
    const seen = new Set();
    for (const item of Array.isArray(schemas) ? schemas : []) {
      const normalized = normalizeSchemaEntry(item);
      if (!normalized || seen.has(normalized.key)) continue;
      seen.add(normalized.key);
      clean.push(normalized);
    }
    storage.setItem(customSchemaStorageKey(workspaceId), JSON.stringify(clean));
  } catch {
    // Browser storage is optional presentation state.
  }
}

function isComplexCustomValue(value) {
  if (value === null || value === undefined) return false;
  if (typeof value === "string" || typeof value === "boolean") return false;
  if (typeof value === "number") return !Number.isFinite(value);
  if (Array.isArray(value)) {
    return value.some(item => typeof item !== "string" || !item.trim());
  }
  return true;
}

function customValuePresent(value) {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim() !== "";
  if (Array.isArray(value)) return value.length > 0;
  return true;
}

function inferredTypeFromStats(stats) {
  if (!stats || !stats.count) return "text";
  if (stats.hasComplex) return "readonly";
  if (stats.allBool) return "boolean";
  if (stats.allNum) return "number";
  if (stats.allList) return "list";
  return "text";
}

function discoverCustomColumns(allInventoryRows, schemas = []) {
  const schemaMap = new Map();
  for (const item of schemas) {
    const normalized = normalizeSchemaEntry(item);
    if (normalized) schemaMap.set(normalized.key, normalized);
  }
  const statsByKey = new Map();
  const invalidKeys = new Set();
  let orderIndex = 0;

  for (const row of allInventoryRows) {
    const metadata = row?.task?.custom_metadata;
    if (!metadata || typeof metadata !== "object") continue;
    const isTask = row?.kind === "task";
    const isReadOnly = Boolean(row.dataset?.read_only);
    for (const [rawKey, value] of Object.entries(metadata)) {
      if (invalidKeys.has(rawKey)) continue;
      let stats = statsByKey.get(rawKey);
      if (!stats) {
        try {
          validateCustomColumnKey(rawKey);
        } catch {
          invalidKeys.add(rawKey);
          continue;
        }
        stats = {
          rawKey,
          order: orderIndex++,
          count: 0,
          hasWritableData: false,
          hasReadOnlyData: false,
          hasComplex: false,
          allBool: true,
          allNum: true,
          allList: true,
        };
        statsByKey.set(rawKey, stats);
      }
      if (value === undefined || value === null) continue;
      stats.count += 1;
      if (isTask) {
        if (isReadOnly) stats.hasReadOnlyData = true;
        else stats.hasWritableData = true;
      }
      if (!stats.hasComplex && isComplexCustomValue(value)) stats.hasComplex = true;
      if (stats.allBool && typeof value !== "boolean") stats.allBool = false;
      if (stats.allNum && (typeof value !== "number" || !Number.isFinite(value))) stats.allNum = false;
      if (stats.allList && !Array.isArray(value)) stats.allList = false;
    }
  }

  let discoveredEntries = [...statsByKey.values()];
  if (discoveredEntries.length > MAX_DISCOVERED_CUSTOM_COLUMNS) {
    const definedKeys = new Set(schemaMap.keys());
    const keptDefined = discoveredEntries.filter(entry => definedKeys.has(entry.rawKey));
    const remainingBudget = Math.max(0, MAX_DISCOVERED_CUSTOM_COLUMNS - keptDefined.length);
    const extra = discoveredEntries
      .filter(entry => !definedKeys.has(entry.rawKey))
      .sort((left, right) => right.count - left.count || left.order - right.order)
      .slice(0, remainingBudget);
    discoveredEntries = [...keptDefined, ...extra].sort((left, right) => left.order - right.order);
  }

  const allKeys = discoveredEntries.map(entry => entry.rawKey);
  const included = new Set(allKeys);
  for (const key of schemaMap.keys()) {
    if (!included.has(key)) {
      included.add(key);
      allKeys.push(key);
    }
  }

  return allKeys.map(rawKey => {
    const schema = schemaMap.get(rawKey) || null;
    const stats = statsByKey.get(rawKey) || null;
    const inferredType = inferredTypeFromStats(stats);
    return {
      key: encodeCustomColumnKey(rawKey),
      rawKey,
      label: rawKey,
      type: schema ? schema.type : inferredType,
      options: schema?.type === "enum" ? [...schema.options] : [],
      defined: Boolean(schema),
      inferredType,
      hasData: Boolean(stats?.count),
      hasWritableData: Boolean(stats?.hasWritableData),
      hasReadOnlyData: Boolean(stats?.hasReadOnlyData),
    };
  });
}

function formatCustomColumnValue(value, type = "text") {
  if (value === null || value === undefined) return "";
  if (typeof value === "boolean") return value ? t("yes", "Yes") : t("no", "No");
  if (Array.isArray(value)) {
    return value.map(item => (typeof item === "object" && item !== null ? JSON.stringify(item) : String(item))).join(", ");
  }
  if (typeof value === "object") return JSON.stringify(value);
  if (type === "boolean") {
    if (value === "true") return t("yes", "Yes");
    if (value === "false") return t("no", "No");
  }
  return String(value);
}

function parseCustomColumnInput(type, rawInput, options = []) {
  if (type === "list") {
    const list = normalizeTableListValue(rawInput);
    if (!list.length) return null;
    if (list.length > MAX_CUSTOM_LIST_ITEMS) {
      throw new Error(t("task_custom_list_too_many", "At most 128 list items are allowed"));
    }
    for (const item of list) {
      if (hasControlChars(item) || utf8Length(item) > MAX_CUSTOM_LIST_ITEM_BYTES) {
        throw new Error(t("task_custom_list_item_invalid", "Each list item must be nonblank without control characters (at most 256 UTF-8 bytes)"));
      }
    }
    return list;
  }
  const text = String(rawInput ?? "").trim();
  if (!text) return null;
  if (type === "number") {
    const num = Number(text);
    if (!Number.isFinite(num)) throw new Error(t("task_custom_number_invalid", "Enter a finite number, or clear the value"));
    if (Number.isInteger(num) && !Number.isSafeInteger(num)) {
      throw new Error(t("task_custom_number_invalid", "Enter a finite number, or clear the value"));
    }
    return num;
  }
  if (type === "boolean") {
    if (text === "true") return true;
    if (text === "false") return false;
    throw new Error(t("task_custom_bool_invalid", "Choose Yes, No, or clear the value"));
  }
  if (type === "enum") {
    const allowed = new Set(options);
    if (allowed.size && !allowed.has(text)) {
      throw new Error(t("task_custom_enum_invalid", "Choose an allowed option, or clear the value"));
    }
  }
  if (hasDisallowedTextControls(text) || utf8Length(text) > MAX_CUSTOM_STRING_BYTES) {
    throw new Error(t("task_custom_value_invalid", "Enter valid text without control characters (at most 16 KiB)"));
  }
  return text;
}

function scalarGroupToken(value) {
  if (value === null || value === undefined) return null;
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : null;
  if (typeof value === "string") return value.trim() ? value : null;
  if (typeof value === "object") return JSON.stringify(value);
  const text = String(value);
  return text.trim() ? text : null;
}

function customColumnGroupKeys(value) {
  if (Array.isArray(value)) {
    const keys = [];
    const seen = new Set();
    for (const item of value) {
      const token = scalarGroupToken(item);
      if (token !== null && !seen.has(token)) {
        seen.add(token);
        keys.push(token);
      }
    }
    return keys.length ? keys : [null];
  }
  return [scalarGroupToken(value)];
}

function fieldError(message, field) {
  const error = new Error(message);
  error.field = field;
  return error;
}

function openCustomColumnModal({
  mode = "create",
  column = null,
  existingKeys = new Set(),
  selectedEditableCount = 0,
  visibleEditableCount = 0,
  selectedReadOnlyCount = 0,
  visibleReadOnlyCount = 0,
  opener = document.activeElement,
  onSubmit,
}) {
  const isEdit = mode === "edit";
  const title = isEdit
    ? t("task_custom_column_edit", "Edit custom column")
    : t("task_custom_column_new", "New custom column");
  const root = document.createElement("div");
  root.className = "action-form-overlay";
  root.hidden = true;
  root.setAttribute("role", "dialog");
  root.setAttribute("aria-modal", "true");
  root.setAttribute("aria-label", title);

  const initialType = VALID_COLUMN_TYPES.has(column?.type) ? column.type : "text";
  const initialOptions = Array.isArray(column?.options) ? column.options.join("\n") : "";
  const typeOptions = [
    ["text", t("task_custom_type_text", "Text")],
    ["enum", t("task_custom_type_enum", "Dropdown (Enum)")],
    ["number", t("task_custom_type_number", "Number")],
    ["boolean", t("task_custom_type_boolean", "Boolean")],
    ["list", t("task_custom_type_list", "List (tags)")],
  ];
  const form = document.createElement("form");
  form.className = "action-form";
  form.dataset.customColumnForm = mode;
  form.innerHTML = `
    <h3>${esc(title)}</h3>
    <label>
      <span>${esc(t("task_custom_column_key", "Column key"))}</span>
      <input name="key" type="text" autocomplete="off" value="${esc(column?.rawKey || "")}" ${isEdit ? "readonly" : "required"}>
    </label>
    <label>
      <span>${esc(t("task_custom_column_type", "Value type"))}</span>
      <select name="type">${typeOptions.map(([value, label]) => `<option value="${esc(value)}" ${value === initialType ? "selected" : ""}>${esc(label)}</option>`).join("")}</select>
    </label>
    <label data-custom-options-field ${initialType === "enum" ? "" : "hidden"}>
      <span>${esc(t("task_custom_column_options", "Dropdown options (one per line)"))}</span>
      <textarea name="options" rows="4" autocomplete="off">${esc(initialOptions)}</textarea>
    </label>
    ${isEdit ? "" : `
      <label data-custom-default-field>
        <span>${esc(t("task_custom_column_default", "Default value (optional)"))}</span>
        <span data-custom-default-host></span>
      </label>
      <p class="action-form-hint" data-custom-default-hint>${esc(t("task_custom_column_default_hint", "Leave blank to add an empty column and persist values when editing cells."))}</p>
      <label data-custom-scope-field hidden>
        <span>${esc(t("task_custom_column_scope", "Apply default to"))}</span>
        <select name="scope">
          ${selectedEditableCount > 0 ? `<option value="selected" selected>${esc(formatMessage("task_custom_scope_selected", "Selected editable Tasks ({count})", { count: selectedEditableCount }))}</option>` : ""}
          <option value="visible" ${selectedEditableCount > 0 ? "" : "selected"}>${esc(formatMessage("task_custom_scope_visible", "Visible editable Tasks ({count})", { count: visibleEditableCount }))}</option>
        </select>
      </label>
      <p class="action-form-hint" data-custom-readonly-hint hidden></p>
    `}
    <div class="action-form-status"></div>
    <div class="source-form-actions">
      <button type="button" class="action-button" data-action-form-cancel="true">${esc(t("cancel", "Cancel"))}</button>
      <button type="submit" class="action-button primary">${esc(t("save", "Save"))}</button>
    </div>
  `;
  root.append(form);
  document.body.append(root);

  const keyInput = form.querySelector('input[name="key"]');
  const typeSelect = form.querySelector('select[name="type"]');
  const optionsField = form.querySelector("[data-custom-options-field]");
  const optionsInput = form.querySelector('textarea[name="options"]');
  const defaultHost = form.querySelector("[data-custom-default-host]");
  const defaultHint = form.querySelector("[data-custom-default-hint]");
  const scopeField = form.querySelector("[data-custom-scope-field]");
  const scopeSelect = form.querySelector('select[name="scope"]');
  const readOnlyHint = form.querySelector("[data-custom-readonly-hint]");
  const status = form.querySelector(".action-form-status");
  const cancel = form.querySelector("[data-action-form-cancel]");

  let defaultControl = null;

  function clearFieldErrors() {
    form.querySelectorAll("[aria-invalid]").forEach(node => {
      node.removeAttribute("aria-invalid");
      node.removeAttribute("aria-describedby");
    });
    form.querySelectorAll(".action-field-error").forEach(node => node.remove());
  }

  function attachFieldError(control, messageText) {
    if (!control) return;
    const id = `custom-column-error-${control.name || "field"}`;
    const note = document.createElement("p");
    note.className = "action-field-error danger";
    note.id = id;
    note.textContent = messageText;
    control.setAttribute("aria-invalid", "true");
    control.setAttribute("aria-describedby", id);
    control.after(note);
    control.focus();
  }

  function setControlsBusy(active) {
    form.toggleAttribute("aria-busy", active);
    form.querySelectorAll("button, select").forEach(node => { node.disabled = active; });
    form.querySelectorAll("input, textarea").forEach(node => {
      if (isEdit && node === keyInput) return;
      node.readOnly = active;
    });
  }

  function syncScopeVisibility() {
    if (isEdit || !scopeField) return;
    const hasDefault = Boolean(String(defaultControl?.value ?? "").trim());
    scopeField.hidden = !hasDefault;
    if (!readOnlyHint) return;
    const scope = scopeSelect?.value || "visible";
    const skipped = scope === "selected" ? selectedReadOnlyCount : visibleReadOnlyCount;
    readOnlyHint.hidden = !hasDefault || skipped <= 0;
    readOnlyHint.textContent = skipped > 0
      ? formatMessage("task_custom_readonly_skipped", "{count} read-only Tasks will be skipped.", { count: skipped })
      : "";
  }

  function renderDefaultInput(preserveValue = "") {
    if (isEdit || !defaultHost) return;
    const type = typeSelect.value;
    let control;
    if (type === "boolean") {
      control = document.createElement("select");
      control.name = "default_value";
      for (const [value, label] of [["", t("task_custom_unset", "Unset")], ["true", t("yes", "Yes")], ["false", t("no", "No")]]) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        option.selected = value === preserveValue;
        control.append(option);
      }
    } else if (type === "enum") {
      control = document.createElement("select");
      control.name = "default_value";
      const choices = parseEnumOptions(optionsInput.value);
      const unset = document.createElement("option");
      unset.value = "";
      unset.textContent = t("task_custom_unset", "Unset");
      control.append(unset);
      for (const choice of choices) {
        const option = document.createElement("option");
        option.value = choice;
        option.textContent = choice;
        option.selected = choice === preserveValue;
        control.append(option);
      }
    } else {
      control = document.createElement("input");
      control.name = "default_value";
      control.type = "text";
      control.autocomplete = "off";
      control.value = preserveValue;
      if (type === "list") control.placeholder = t("task_custom_list_hint", "Separate multiple values with commas");
    }
    defaultControl = control;
    defaultHost.replaceChildren(control);
    control.addEventListener("input", syncScopeVisibility);
    control.addEventListener("change", syncScopeVisibility);
    if (defaultHint) {
      const base = t("task_custom_column_default_hint", "Leave blank to add an empty column and persist values when editing cells.");
      defaultHint.textContent = type === "list"
        ? `${t("task_custom_list_hint", "Separate multiple values with commas")}. ${base}`
        : base;
    }
    syncScopeVisibility();
  }

  function syncTypeFields() {
    const type = typeSelect.value;
    optionsField.hidden = type !== "enum";
    renderDefaultInput("");
  }

  typeSelect.addEventListener("change", syncTypeFields);
  optionsInput.addEventListener("input", () => {
    if (typeSelect.value === "enum") renderDefaultInput(defaultControl?.value || "");
  });
  scopeSelect?.addEventListener("change", syncScopeVisibility);
  renderDefaultInput("");

  let busy = false;
  let feedback = null;
  const close = () => {
    if (busy) return;
    closeModalSurface(root);
  };
  cancel.addEventListener("click", close);
  root.addEventListener("keydown", event => {
    if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); close(); }
  });

  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (busy) return;
    clearFieldErrors();
    feedback?.dispose();
    feedback = beginFeedback(status);
    try {
      const rawKey = isEdit ? column.rawKey : String(keyInput.value || "").trim();
      let key;
      try {
        key = validateCustomColumnKey(rawKey);
      } catch (err) {
        throw fieldError(err.message, keyInput);
      }
      if (!isEdit && existingKeys.has(key)) {
        throw fieldError(formatMessage("task_custom_key_exists", "Custom column “{key}” already exists", { key }), keyInput);
      }
      const type = typeSelect.value;
      const options = type === "enum" ? parseEnumOptions(optionsInput.value) : [];
      if (type === "enum" && !options.length) {
        throw fieldError(t("task_custom_options_required", "Add at least one dropdown option"), optionsInput);
      }
      let defaultValue = null;
      const scope = scopeSelect?.value || "visible";
      if (!isEdit && defaultControl) {
        try {
          defaultValue = parseCustomColumnInput(type, defaultControl.value, options);
        } catch (err) {
          throw fieldError(err.message, defaultControl);
        }
        if (defaultValue !== null) {
          const targetCount = scope === "selected" ? selectedEditableCount : visibleEditableCount;
          if (targetCount < 1) {
            throw fieldError(t("task_custom_no_writable_tasks", "No editable Tasks in the selected scope to write default values."), scopeSelect || defaultControl);
          }
        }
      }
      busy = true;
      setControlsBusy(true);
      feedback.pending();
      const accepted = await onSubmit({ key, type, options, defaultValue, scope });
      busy = false;
      if (accepted !== false) close();
      else feedback.clear();
    } catch (error) {
      busy = false;
      setControlsBusy(false);
      feedback.error(error);
      if (error?.field) attachFieldError(error.field, error.message || String(error));
    } finally {
      busy = false;
      setControlsBusy(false);
    }
  });

  openModalSurface(root, {
    opener,
    focusTarget: isEdit ? typeSelect : keyInput,
    onRequestClose: close,
    onClose: () => { feedback?.dispose(); root.remove(); },
  });
  return root;
}

export {
  MAX_DISCOVERED_CUSTOM_COLUMNS,
  customColumnGroupKeys,
  customValuePresent,
  decodeCustomColumnKey,
  discoverCustomColumns,
  encodeCustomColumnKey,
  formatCustomColumnValue,
  isComplexCustomValue,
  isCustomColumnKey,
  loadCustomColumnSchemas,
  openCustomColumnModal,
  parseCustomColumnInput,
  saveCustomColumnSchemas,
  validateCustomColumnKey,
};
