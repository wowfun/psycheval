import { t } from "./shared.js";

const JSON_EXPANSION_LIMIT = 1000;
const JSON_AUTO_DEPTH = 16;

class JsonNumber {
  constructor(source) { this.source = source; }
}

function createJsonView(content) {
  const value = JSON.parse(content, (key, item, context) => typeof item === "number" ? new JsonNumber(context?.source ?? (Object.is(item, -0) ? "-0" : String(item))) : item);
  const root = document.createElement("div"); root.className = "json-view";
  function text(className, value) {
    const node = document.createElement("span"); node.className = className; node.textContent = value;
    return node;
  }
  function row(key, item, arrayIndex, isRoot, depth, budget) {
    budget.remaining -= 1;
    const object = item !== null && typeof item === "object" && !(item instanceof JsonNumber);
    const keys = object ? Object.keys(item) : [];
    const longString = typeof item === "string" && (item.length > 160 || item.includes("\n"));
    const branch = keys.length > 0 || longString;
    const node = document.createElement(branch ? "details" : "div");
    node.className = branch ? "json-branch" : "json-leaf";
    if (isRoot) node.dataset.jsonRoot = "";
    else node.dataset.jsonKey = key;
    const line = branch ? document.createElement("summary") : node;
    if (!isRoot) line.append(text("json-key", arrayIndex ? `[${key}]` : JSON.stringify(key)), ": ");
    if (!branch) {
      const type = item instanceof JsonNumber ? "number" : item === null ? "null" : typeof item;
      line.append(text(`json-value json-${type}`, item instanceof JsonNumber ? item.source : JSON.stringify(item)));
      return node;
    }
    line.append(text(longString ? "json-value json-string" : "json-collection", longString
      ? `${JSON.stringify(item.slice(0, 100))}…`
      : `${Array.isArray(item) ? "[…]" : "{…}"} ${t("json_items", "{count} items").replace("{count}", String(keys.length))}`));
    const children = document.createElement("div"); children.className = "json-children";
    node.append(line, children);
    let populated = false;
    function populate(budget) {
      populated = true;
      if (longString) {
        const full = document.createElement("div"); full.className = "json-string-text"; full.textContent = item;
        children.append(full); return;
      }
      let shown = 0;
      const more = document.createElement("button"); more.className = "action-button compact json-more";
      children.append(more);
      function next(budget) {
        const end = Math.min(shown + 100, keys.length);
        for (; shown < end && budget.remaining > 0; shown += 1) {
          const key = keys[shown];
          more.before(row(key, item[key], Array.isArray(item), false, depth + 1, budget));
        }
        if (shown === keys.length) more.remove();
        else more.textContent = `${t("json_show_more", "Show more")} (${shown} / ${keys.length})`;
      }
      more.addEventListener("click", () => next({ remaining: JSON_EXPANSION_LIMIT })); next(budget);
    }
    node.addEventListener("toggle", () => {
      if (node.open && !populated) populate({ remaining: JSON_EXPANSION_LIMIT });
    });
    if (budget.remaining > 0 && depth < JSON_AUTO_DEPTH) {
      populate(budget); node.open = true;
    }
    return node;
  }
  root.append(row(null, value, false, true, 0, { remaining: JSON_EXPANSION_LIMIT }));
  return root;
}

export { createJsonView };
