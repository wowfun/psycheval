import { state, render } from "./runtime.js";
import { tableControls } from "./data-tables.js";
import { captureAppliedViewSnapshots } from "./workspace-views.js";
import { cancelHomeLocationRequests, catalogSortKey } from "./serve-catalog.js";
import { cancelWorkspaceReportRequest, closeWorkspaceReportReader } from "./workspace-reports.js";
import { closeDetailSidebar } from "./detail-sidebar.js";
import { HOME_QUERY } from "../app/workspace-location.js";
import { tableSortKey } from "../app/catalog-sort.js";

const FILTER_KEYS = { source_category: "categories", source_tags: "tags", agent: "agents", model: "models", task_name: "tasks", job_name: "jobs", model_provider: "providers", dataset_id: "datasets", status: "results" };
function captureHomeLocation() {
  const object = { ...state.homeLocationTarget };
  return { object, state: {
    query: { ...Object.fromEntries(Object.keys(HOME_QUERY).map(key => [key, state.catalogQuery[key]])), sort: catalogSortKey(state.catalogQuery.sort) },
    views: captureAppliedViewSnapshots(),
    summary: { group_by: state.leaderboardSummaryGroupBy, statistic: state.leaderboardSummaryStatistic, table_open: state.leaderboardSummaryTableOpen },
  } };
}
function restoreHomeLocation(location) {
  cancelHomeLocationRequests();
  cancelWorkspaceReportRequest({ catalog: true });
  closeDetailSidebar({ restoreFocus: false, render: false, locationKind: "replace" });
  closeWorkspaceReportReader({ restoreFocus: false, locationKind: "replace" });
  const query = location.state.query;
  state.catalogQuery = { ...query, views: [] };
  state.sharedViewSnapshots = location.state.views;
  state.workspaceAppliedViewNames.clear();
  state.workspaceViewSelection.clear();
  state.rowSelection.clear();
  state.search = { query: query.search, scope: query.state === "all" ? "all" : "visible", normalSourceMode: query.state };
  state.serveSourceMode = query.state;
  state.leaderboardSummaryGroupBy = location.state.summary.group_by;
  state.leaderboardSummaryStatistic = location.state.summary.statistic;
  state.leaderboardSummaryTableOpen = location.state.summary.table_open;
  const controls = tableControls("leaderboard");
  controls.filters = Object.fromEntries(Object.entries(FILTER_KEYS).map(([key, field]) => [key, [...query[field]]]));
  controls.sort = tableSortKey(query.sort);
  controls.direction = query.direction;
  state.selectedSourceKey = state.selectedTrial = state.selectedStep = state.selectedTrajectory = state.selectedArtifactRevision = null;
  state.homeLocationTarget = { ...location.object };
  if (state.view) render({ ...state.view, trajectory: [], trajectory_meta: [], annotations: { notes: [], analysis: [], report_notes: [] } });
}
export { captureHomeLocation, restoreHomeLocation };
