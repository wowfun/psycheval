// @ts-check
import { RENDER_OPTIONS } from "../app/render-options.js";

function dateValue(value) {
  if (value === null || value === undefined || String(value).trim() === "") return null;
  const source = String(value).trim();
  const date = typeof value === "number" || /^-?\d+(?:\.\d+)?$/.test(source)
    ? new Date(Number(value))
    : /(?:Z|[+-]\d{2}:\d{2})$/i.test(source) ? new Date(source) : null;
  return date && Number.isFinite(date.getTime()) ? date : null;
}
function unknownValue(value) {
  return value === null || value === undefined || String(value).trim() === "" ? "-" : String(value);
}
function timezoneFormatter(timezone) {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", fractionalSecondDigits: 3,
    hourCycle: "h23", timeZoneName: "longOffset",
  });
}
let formatter = timezoneFormatter(RENDER_OPTIONS.effective_timezone || "UTC");

function formatDate(value, mode = "full") {
  const date = dateValue(value);
  if (!date) return unknownValue(value);
  const parts = Object.fromEntries(formatter.formatToParts(date).map(part => [part.type, part.value]));
  const offset = parts.timeZoneName === "GMT" ? "+00:00" : parts.timeZoneName.replace("GMT", "");
  const clock = `${parts.hour}:${parts.minute}:${parts.second}.${parts.fractionalSecond} ${offset}`;
  return mode === "clock" ? clock : `${parts.year}-${parts.month}-${parts.day} ${clock}`;
}
function fmtDate(value) { return formatDate(value); }
function fmtClockMs(value) { return formatDate(value, "clock"); }
// Export values retain their established UTC representation.
function formatUtcDate(value) { return dateValue(value)?.toISOString() ?? unknownValue(value).trim(); }
function formatUtcClock(value) { return dateValue(value)?.toISOString().split("T")[1] ?? unknownValue(value); }
function renderDateTime(value, mode = "full") {
  const date = dateValue(value);
  if (!date) return unknownValue(value).replace(/[&<>"']/g, char => `&#${char.charCodeAt(0)};`);
  return `<time datetime="${date.toISOString()}" data-display-time="${mode === "clock" ? "clock" : "full"}" title="${fmtDate(value)}">${formatDate(value, mode)}</time>`;
}
function setDisplayTimezone(timezone) {
  formatter = timezoneFormatter(timezone);
  document.querySelectorAll("time[data-display-time]").forEach(node => {
    const value = node.getAttribute("datetime");
    node.textContent = formatDate(value, node.getAttribute("data-display-time") || "full");
    node.setAttribute("title", fmtDate(value));
    const cell = node.closest('td[data-value-type="datetime"]');
    if (cell) {
      const text = cell.textContent || "";
      cell.setAttribute("title", text);
      cell.setAttribute("aria-label", text);
    }
  });
}
export { fmtDate, fmtClockMs, formatUtcDate, formatUtcClock, renderDateTime, setDisplayTimezone };
