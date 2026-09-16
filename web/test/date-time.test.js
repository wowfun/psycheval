import assert from "node:assert/strict";
import test from "node:test";
import { installBrowserDom } from "./support/browser.js";

const browser = installBrowserDom('<script id="peval-render-options" type="application/json">{"effective_timezone":"Asia/Shanghai"}</script><div id="root"></div>');
const dates = await import("../../src/psycheval/assets/web/modules/date-time.js");
test.after(() => browser.cleanup());

test("bootstrap timezone and exact offsets including DST and milliseconds", () => {
  assert.equal(dates.fmtDate(0), "1970-01-01 08:00:00.000 +08:00");
  const cases = [
    ["UTC", "2026-01-01T23:45:06.007Z", "2026-01-01 23:45:06.007 +00:00"],
    ["Asia/Shanghai", "2026-01-01T23:45:06.007Z", "2026-01-02 07:45:06.007 +08:00"],
    ["Asia/Kolkata", "2026-01-01T23:45:06.123Z", "2026-01-02 05:15:06.123 +05:30"],
    ["America/New_York", "2026-03-08T06:59:59.999Z", "2026-03-08 01:59:59.999 -05:00"],
    ["America/New_York", "2026-03-08T07:00:00.000Z", "2026-03-08 03:00:00.000 -04:00"],
    ["America/New_York", "2026-11-01T05:59:59.999Z", "2026-11-01 01:59:59.999 -04:00"],
    ["America/New_York", "2026-11-01T06:00:00Z", "2026-11-01 01:00:00.000 -05:00"],
  ];
  for (const [zone, instant, expected] of cases) {
    dates.setDisplayTimezone(zone);
    assert.equal(dates.fmtDate(instant), expected);
    assert.equal(dates.fmtClockMs(instant), expected.slice(11));
    assert.equal(dates.formatUtcDate(instant), new Date(instant).toISOString());
  }
});

test("missing, naive and invalid values are preserved safely", () => {
  for (const value of [null, undefined, "", "  "]) assert.equal(dates.fmtDate(value), "-");
  for (const value of ["unknown", "2026-01-01T01:02:03", "  invalid  ", "<img src=x onerror=alert(1)>"]) {
    assert.equal(dates.fmtDate(value), value);
    const root = document.getElementById("root");
    root.innerHTML = dates.renderDateTime(value);
    assert.equal(root.textContent, value);
    assert.equal(root.children.length, 0);
  }
  assert.throws(() => dates.setDisplayTimezone("Invalid/Zone"), RangeError);
});

test("changing timezone updates existing times and hints without replacing drafts or table rows", () => {
  const root = document.getElementById("root");
  dates.setDisplayTimezone("UTC");
  root.innerHTML = `<input value="draft"><table><tbody><tr><td data-value-type="datetime">≈${dates.renderDateTime(0, "clock")}</td></tr></tbody></table><section hidden>${dates.renderDateTime(0)}</section>`;
  const input = root.querySelector("input"), row = root.querySelector("tr"), time = root.querySelector("time");
  input.value = "unsaved edit";
  dates.setDisplayTimezone("Asia/Kolkata");
  assert.equal(root.querySelector("input"), input);
  assert.equal(input.value, "unsaved edit");
  assert.equal(root.querySelector("tr"), row);
  assert.equal(root.querySelector("time"), time);
  assert.equal(time.textContent, "05:30:00.000 +05:30");
  assert.equal(time.title, "1970-01-01 05:30:00.000 +05:30");
  assert.equal(time.closest("td").title, "≈05:30:00.000 +05:30");
  assert.equal(root.querySelector("section").textContent, "1970-01-01 05:30:00.000 +05:30");
  assert.equal(dates.formatUtcDate(0), "1970-01-01T00:00:00.000Z");
  assert.equal(dates.formatUtcClock(0), "00:00:00.000Z");
});
