// @ts-check

const SORT_COLUMNS = Object.freeze({
  last_turn_end: "finished_at_ms", session: "session_id", result: "status",
  task: "task_name", job: "job_name", provider: "model_provider", dataset: "dataset_id",
  agent: "agent", model: "model", created: "created", updated: "updated", source_key: "source_key",
});
const SORT_KEYS = new Set(Object.keys(SORT_COLUMNS));
const COLUMN_SORTS = Object.fromEntries(Object.entries(SORT_COLUMNS).map(([sort, column]) => [column, sort]));
const catalogSortKey = key => COLUMN_SORTS[key] || key || "last_turn_end";
const tableSortKey = key => SORT_COLUMNS[key] || key;
export { SORT_KEYS, catalogSortKey, tableSortKey };
