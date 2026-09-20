// @ts-check

const bindingId = target => JSON.stringify([target.kind, target.key]);
const signature = bindings => JSON.stringify(bindings.map(bindingId).sort());
const reportLibraryStore = {
  items: [], total: 0, page: 1, pageSize: 50, search: "",
  kinds: new Set(), datasets: new Map(), jobs: new Map(),
  activeRef: null, tab: "preview", loading: false, importing: false,
  reports: new Map(), drafts: new Map(),
};

function acceptReport(report) {
  const store = reportLibraryStore;
  store.reports.set(report.report_ref, report);
  let draft = store.drafts.get(report.report_ref);
  if (!draft) {
    draft = { baseline: [], values: new Map(), version: 0, saving: false, deleting: false };
    store.drafts.set(report.report_ref, draft);
  }
  if (!draft.saving && !draft.deleting && !draftChanged(draft) && report.associations_available !== false) {
    draft.baseline = report.bindings || [];
    draft.values = new Map(draft.baseline.map(item => [bindingId(item), item]));
  } else {
    // Refresh labels and availability without changing membership in a local draft.
    for (const item of report.bindings || []) {
      if (draft.values.has(bindingId(item))) draft.values.set(bindingId(item), item);
    }
  }
  return report;
}

function draftChanged(draft) {
  return signature([...draft.values.values()]) !== signature(draft.baseline);
}
function reportBindingsChanged() {
  return [...reportLibraryStore.drafts.values()].some(draftChanged);
}
function editBinding(ref, target, selected) {
  const draft = reportLibraryStore.drafts.get(ref);
  if (!draft) return;
  if (selected) draft.values.set(bindingId(target), target);
  else draft.values.delete(bindingId(target));
  draft.version += 1;
}
function completeSave(ref, report, version, submitted) {
  const draft = reportLibraryStore.drafts.get(ref);
  reportLibraryStore.reports.set(ref, report);
  draft.baseline = report.bindings || submitted;
  if (draft.version === version) draft.values = new Map(draft.baseline.map(item => [bindingId(item), item]));
}

export { acceptReport, bindingId, completeSave, draftChanged, editBinding, reportBindingsChanged, reportLibraryStore };
