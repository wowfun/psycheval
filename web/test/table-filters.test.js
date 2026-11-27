import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`<div id="root"></div>`);
const tables = await import("../../src/psycheval/assets/web/modules/data-tables.js");
test.after(() => browser.cleanup());

test("local filter choices derive from currently visible rows before and after Home initialization", () => {
  const root = document.getElementById("root");
  const columns = [
    { key: "name", label: "Job", filterable: true, value: row => row.name },
    { key: "status", label: "Status", filterable: true, value: row => row.status },
    { key: "tags", label: "Tags", filterable: true, value: row => row.tags, filterValues: row => row.tags },
  ];
  const rows = [
    { name: "job-2", status: "completed", tags: ["shared", "second"] },
    { name: "job-1", status: "unfinished", tags: ["shared", "first"] },
  ];
  const choices = key => [...root.querySelectorAll(`[data-filter-key="${key}"]`)].map(input => input.value);
  function render() {
    root.innerHTML = tables.renderDataTable({ tableId: "local", columns, rows: rows.slice(0, 1) });
    assert.deepEqual(choices("name"), ["job-2"]);
    assert.deepEqual(choices("status"), ["completed"]);
    assert.deepEqual(choices("tags"), ["second", "shared"]);
  }
  render();
  let catalogCalls = 0;
  tables.configureDataTable("leaderboard", { filterOptions: () => { catalogCalls++; return ["server-page-2"]; } });
  render();
  assert.equal(catalogCalls, 0);
  root.innerHTML = tables.renderDataTable({ tableId: "leaderboard", columns: [columns[0]], rows });
  assert.deepEqual(choices("name"), ["server-page-2"]);
  assert.equal(catalogCalls, 1);
});

test("local filters narrow options to visible rows, retain active selections, and clear through Apply", () => {
  const root = document.getElementById("root");
  const columns = [
    { key: "status", label: "Status", filterable: true, value: row => row.status },
    { key: "tags", label: "Tags", filterable: true, value: row => row.tags, filterValues: row => row.tags },
  ];
  const allRows = [
    { status: "completed", tags: ["shared", "second"] },
    { status: "unfinished", tags: ["shared", "first"] },
  ];
  let visibleSource = allRows;
  const choices = key => [...root.querySelectorAll(`[data-filter-key="${key}"]`)].map(input => input.value);
  function render() {
    const rows = tables.applyDataTableControls("drafts", visibleSource, columns);
    root.innerHTML = tables.renderDataTable({ tableId: "drafts", columns, rows });
    tables.bindDataTableControls(root, { tableId: "drafts", columns, rows, onChange: render });
    assert.equal(root.querySelector(".filter-menu").hasAttribute("popover"), false, "unsupported Popover uses the absolute-position fallback");
  }
  render();
  assert.deepEqual(choices("status"), ["completed", "unfinished"]);
  assert.deepEqual(choices("tags"), ["first", "second", "shared"]);
  const input = root.querySelector('input[data-filter-key="status"][value="completed"]');
  assert.ok(input);
  input.click();
  assert.equal(root.querySelectorAll("tbody tr").length, 2);
  root.querySelector('[data-filter-apply="status"]').click();
  assert.equal(root.querySelectorAll("tbody tr").length, 1);
  assert.deepEqual(choices("status"), ["completed"]);
  assert.deepEqual(choices("tags"), ["second", "shared"]);

  // Active selection stays clearable even when another condition hides every row.
  visibleSource = [];
  render();
  assert.deepEqual(choices("status"), ["completed"]);
  assert.equal(root.querySelector('input[data-filter-key="status"][value="completed"]').checked, true);
  assert.deepEqual(choices("tags"), []);

  visibleSource = allRows;
  render();
  root.querySelector('[data-filter-clear="status"]').click();
  assert.equal(root.querySelectorAll("tbody tr").length, 1);
  root.querySelector('[data-filter-apply="status"]').click();
  assert.equal(root.querySelectorAll("tbody tr").length, 2);
  assert.deepEqual(choices("status"), ["completed", "unfinished"]);
  assert.deepEqual(choices("tags"), ["first", "second", "shared"]);
});
