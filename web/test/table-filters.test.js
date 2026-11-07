import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom(`<div id="root"></div>`);
const tables = await import("../../src/psycheval/assets/web/modules/data-tables.js");
test.after(() => browser.cleanup());

test("local filter choices use all supplied rows before and after Home initialization", () => {
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
    root.innerHTML = tables.renderDataTable({ tableId: "local", columns, rows: rows.slice(0, 1), filterOptionsRows: rows });
    assert.deepEqual(choices("name"), ["job-1", "job-2"]);
    assert.deepEqual(choices("status"), ["completed", "unfinished"]);
    assert.deepEqual(choices("tags"), ["first", "second", "shared"]);
  }
  render();
  let catalogCalls = 0;
  tables.configureLeaderboardDataTables({ filterOptions: () => { catalogCalls++; return ["server-page-2"]; } });
  render();
  assert.equal(catalogCalls, 0);
  root.innerHTML = tables.renderDataTable({ tableId: "leaderboard", columns: [columns[0]], rows });
  assert.deepEqual(choices("name"), ["server-page-2"]);
  assert.equal(catalogCalls, 1);
});

test("local filters apply drafts, preserve choices after filtering, and clear through Apply", () => {
  const root = document.getElementById("root");
  const columns = [{ key: "status", label: "Status", filterable: true, value: row => row.status }];
  const allRows = [{ status: "completed" }, { status: "unfinished" }];
  function render() {
    const rows = tables.applyDataTableControls("drafts", allRows, columns);
    root.innerHTML = tables.renderDataTable({ tableId: "drafts", columns, rows, filterOptionsRows: allRows });
    tables.bindDataTableControls(root, { tableId: "drafts", columns, rows, onChange: render });
  }
  render();
  const input = root.querySelector('input[value="completed"]');
  assert.ok(input);
  input.click();
  assert.equal(root.querySelectorAll("tbody tr").length, 2);
  root.querySelector("[data-filter-apply]").click();
  assert.equal(root.querySelectorAll("tbody tr").length, 1);
  assert.equal(root.querySelectorAll("[data-filter-key]").length, 2);
  root.querySelector("[data-filter-clear]").click();
  assert.equal(root.querySelectorAll("tbody tr").length, 1);
  root.querySelector("[data-filter-apply]").click();
  assert.equal(root.querySelectorAll("tbody tr").length, 2);
});
