// @ts-check

const evaluationReportStore = {
  reports: [],
  activeRef: null,
  manager: {
    search: "",
    page: 1,
    pageData: { page: 1, page_size: 100, total: 0 },
    searchTimer: null,
    loading: false,
  },
};

function normalizedEvaluationReports(reports) {
  return (Array.isArray(reports) ? reports : [])
    .filter(report => report && report.report_ref && report.primary_source_key)
    .map(report => ({
      report_ref: String(report.report_ref),
      title: String(report.title || report.source_label || report.filename || report.report_ref),
      filename: String(report.filename || "analysis.md"),
      format: "markdown",
      source_keys: Array.from(new Set(
        (Array.isArray(report.source_keys) ? report.source_keys : [])
          .map(key => String(key || "").trim())
          .filter(Boolean),
      )),
      primary_source_key: String(report.primary_source_key),
      source_label: String(report.source_label || report.title || report.primary_source_key),
    }));
}

function applyEvaluationReportPage(payload) {
  const page = payload && typeof payload === "object" ? payload : {};
  evaluationReportStore.reports.splice(
    0,
    evaluationReportStore.reports.length,
    ...normalizedEvaluationReports(page.items),
  );
  evaluationReportStore.manager.pageData = {
    page: Math.max(1, Number(page.page || 1)),
    page_size: Math.max(1, Number(page.page_size || 100)),
    total: Math.max(0, Number(page.total || 0)),
  };
  evaluationReportStore.manager.page = evaluationReportStore.manager.pageData.page;
  return evaluationReportStore.reports;
}

function evaluationReportForRef(reportRef) {
  const wanted = String(reportRef || "");
  return evaluationReportStore.reports.find(report => report.report_ref === wanted) || null;
}

export {
  applyEvaluationReportPage,
  evaluationReportForRef,
  evaluationReportStore,
  normalizedEvaluationReports,
};
