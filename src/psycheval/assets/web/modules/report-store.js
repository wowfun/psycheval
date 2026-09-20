// @ts-check

const reportStore = {
  reports: [],
  reader: {
    openId: null,
    objectUrl: null,
    previewObserver: null,
  },
};

function normalizedReports(reports = reportStore.reports) {
  return (Array.isArray(reports) ? reports : [])
    .filter(report => report && report.report_id && report.report_ref && report.filename)
    .map(report => ({
      report_id: String(report.report_id),
      report_ref: String(report.report_ref),
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

function applyReportCatalog(reports) {
  return replaceReports(reports);
}

export {
  applyReportCatalog,
  normalizedReports,
  replaceReports,
  reportForId,
  reportStore,
};
