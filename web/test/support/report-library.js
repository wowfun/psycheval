export const reportPageHtml = `
  <script type="application/json" id="peval-i18n">{}</script>
  <script type="application/json" id="peval-render-options">{"mode":"serve","role":"admin"}</script>
  <section data-workspace-page="reports"><div data-report-manager>
    <div data-report-manager-status hidden></div><div data-report-toolbar></div>
    <div data-report-inventory></div><div data-report-pagination></div>
    <aside id="report-library-detail" hidden></aside>
  </div></section>`;

export const response = (payload, status = 200) => new Response(JSON.stringify(payload), {
  status, headers: { "Content-Type": status >= 400 ? "application/problem+json" : "application/json" },
});
export const target = (kind, key) => ({ kind, key, label: `${kind} ${key}`, available: true });
export const report = (name, bindings = [], origin = "imported") => ({
  report_ref: `${origin === "imported" ? "package" : "analysis"}:${name}`, report_id: name,
  title: `${name}.md`, filename: `${name}.md`, format: "markdown", origin,
  updated_at_ms: 1000, source_keys: [], bindings,
  associations: bindings.map(item => ({ ...item, origins: ["manual"] })),
});
export const pageOf = (items, page = 1, total = items.length) => ({ items, total, page, page_size: 50 });
export const tick = () => new Promise(resolve => setTimeout(resolve, 0));
export function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
}
