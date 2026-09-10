import { serveApi } from "./http.js";
import { t } from "./shared.js";

const observers = new WeakMap();

function errorWithContext(context, error) {
  const message = String(error.message || error);
  return message === context ? context : `${context}: ${message}`;
}

/** Observe an accepted operation. Retrying this observer never repeats a write. */
async function watchOperation(id, { feedback, committed = false, onBusy = () => {}, onComplete = async () => {} }) {
  const owner = document, view = window;
  if (!observers.has(owner)) observers.set(owner, new Map());
  const active = observers.get(owner);
  active.get(id)?.();
  if (feedback.signal.aborted) return;
  const controller = new view.AbortController();
  let refreshing = false, polling = false, stopped = false, busy = false, timer;
  const setBusy = value => {
    if (busy === value) return;
    busy = value; onBusy(value);
  };
  const cancel = () => feedback.dispose();
  const stop = () => {
    if (stopped) return;
    stopped = true;
    view.clearTimeout(timer);
    controller.abort();
    view.removeEventListener("pagehide", cancel);
    feedback.signal.removeEventListener("abort", stop);
    if (active.get(id) === cancel) active.delete(id);
    setBusy(false);
  };
  active.set(id, cancel);
  view.addEventListener("pagehide", cancel, { once: true });
  feedback.signal.addEventListener("abort", stop, { once: true });
  const finish = async operation => {
    if (refreshing || stopped) return;
    refreshing = true;
    setBusy(true);
    feedback.pending(t("loading", "Loading"));
    try {
      await onComplete(operation);
      if (stopped) return;
      const failures = operation.failures || [];
      if (operation.state === "failed" || failures.length) {
        const summary = t("feedback_batch", "{succeeded} succeeded, {failed} failed")
          .replace("{succeeded}", String(operation.successes?.length || 0))
          .replace("{failed}", String(failures.length || 1));
        feedback.error(committed ? t("feedback_reconcile_failed", "Saved, but background reconciliation failed") : summary, {
          details: failures.length
            ? failures.map(item => `${item.item?.path ?? item.item?.task ?? item.item?.directory ?? item.index ?? ""}: ${item.error || ""}`)
            : [`${t("feedback_operation_failed", "Operation failed")}: ${operation.kind || ""} (${id})`],
          ...(committed ? { action: { label: t("serve_refresh", "Refresh"), run: () => finish(operation) } } : {}),
        });
      } else { feedback.success(); stop(); }
    } catch (error) {
      if (stopped) return;
      feedback.error(errorWithContext(committed ? t("feedback_refresh_failed", "Saved, but workspace refresh failed") : t("feedback_unknown", "The operation result is temporarily unavailable"), error), {
        action: { label: t("serve_refresh", "Refresh"), run: () => finish(operation) },
      });
    } finally { refreshing = false; setBusy(false); }
  };
  const poll = async (initial = false) => {
    if (polling || refreshing || stopped) return;
    polling = true;
    setBusy(true);
    if (initial) feedback.pending(committed ? t("feedback_saved_refreshing", "Saved; refreshing the workspace…") : t("loading", "Loading"));
    try {
      const operation = await serveApi(`/api/operations/${encodeURIComponent(id)}`, { signal: controller.signal });
      if (stopped) return;
      if (["queued", "running"].includes(operation.state)) {
        feedback.pending([
          committed ? t("feedback_saved_refreshing", "Saved; refreshing the workspace…") : "",
          `${operation.completed}/${operation.total}`,
        ].filter(Boolean).join(" "));
        timer = view.setTimeout(poll, 250);
      } else await finish(operation);
    } catch (error) {
      if (stopped) return;
      setBusy(false);
      feedback.error(`${t("feedback_unknown", "The operation result is temporarily unavailable")}: ${error.message || error}`, {
        action: { label: t("feedback_retry", "Check again"), run: () => poll(true) },
      });
    } finally { polling = false; }
  };
  await poll(true);
}

/** Recover a committed write by retrying only its read-side refresh. */
function offerRefresh(feedback, error, refresh) {
  let busy = false;
  const show = error => feedback.error(errorWithContext(t("feedback_refresh_failed", "Saved, but workspace refresh failed"), error), {
    action: { label: t("serve_refresh", "Refresh"), run: retry },
  });
  async function retry() {
    if (busy) return;
    busy = true;
    feedback.pending(t("loading", "Loading"));
    try { await refresh(); feedback.clear(); }
    catch (error) { show(error); }
    finally { busy = false; }
  }
  show(error);
}

export { watchOperation, offerRefresh };
