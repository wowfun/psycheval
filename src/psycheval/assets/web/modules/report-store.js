// @ts-check

const reportStore = {
  reports: [],
  manager: {
    selectedId: null,
    search: "",
    page: 1,
    pageData: { page: 1, page_size: 100, total: 0 },
    sourceRows: [],
    searchTimer: null,
    draftBindings: new Set(),
    dirty: false,
    loading: false,
    busy: false,
    opener: null,
  },
  reader: {
    openId: null,
    opener: null,
    width: null,
    objectUrl: null,
    previewObserver: null,
  },
};

function normalizedReports(reports = reportStore.reports) {
  return (Array.isArray(reports) ? reports : [])
    .filter(report => report && report.report_id && report.filename)
    .map(report => ({
      report_id: String(report.report_id),
      filename: String(report.filename),
      format: String(report.format || "").toLowerCase() === "html" ? "html" : "markdown",
      source_keys: Array.from(new Set(
        (Array.isArray(report.source_keys) ? report.source_keys : [])
          .map(key => String(key || "").trim())
          .filter(Boolean),
      )),
    }))
    .sort((left, right) => right.report_id.localeCompare(
      left.report_id,
      undefined,
      { numeric: true },
    ));
}

function replaceReports(reports) {
  const normalized = normalizedReports(reports);
  reportStore.reports.splice(0, reportStore.reports.length, ...normalized);
  return reportStore.reports;
}

function reportForId(reportId) {
  const wanted = String(reportId || "");
  return reportStore.reports.find(report => report.report_id === wanted) || null;
}

function syncReportDraft() {
  reportStore.manager.draftBindings = new Set(
    reportForId(reportStore.manager.selectedId)?.source_keys || [],
  );
  reportStore.manager.dirty = false;
}

function applyReportCatalog(reports) {
  const selectedId = reportStore.manager.selectedId;
  replaceReports(reports);
  if (!reportForId(selectedId)) {
    reportStore.manager.selectedId = reportStore.reports[0]?.report_id || null;
    syncReportDraft();
  } else if (!reportStore.manager.dirty) {
    syncReportDraft();
  }
  return reportStore.reports;
}

function reportBindingsChanged() {
  const persisted = new Set(reportForId(reportStore.manager.selectedId)?.source_keys || []);
  const draft = reportStore.manager.draftBindings;
  return persisted.size !== draft.size || [...persisted].some(key => !draft.has(key));
}

export {
  applyReportCatalog,
  normalizedReports,
  replaceReports,
  reportBindingsChanged,
  reportForId,
  reportStore,
  syncReportDraft,
};
