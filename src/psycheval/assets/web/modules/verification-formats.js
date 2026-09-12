import { esc, statusLabel, t } from "./shared.js";

const number = value => typeof value === "number" && Number.isFinite(value);
const record = value => value && typeof value === "object" && !Array.isArray(value);
const literal = value => value === null || value === undefined ? "—" : typeof value === "object" ? JSON.stringify(value) : String(value);
const label = value => t(`verification_${value}`, value);

function renderVerificationSummary(meta) {
  const evidence = meta?.verifier_evidence || {};
  const tests = evidence.tests || {};
  const entries = [
    [t("verification_run_status", "Run status"), statusLabel(meta?.status)],
    [t("score", "Score"), meta?.score ?? evidence.score],
    [t("workbuddy_score_source", "Score source"), meta?.score_message || evidence.score_source],
  ];
  if (tests.passed !== undefined || tests.total !== undefined) entries.push([t("tests_passed_total", "Tests passed / total"), `${tests.passed ?? "—"} / ${tests.total ?? "—"}`]);
  if (tests.status) entries.push([t("test_status", "Test status"), label(tests.status)]);
  if (evidence.status && evidence.status !== "present") entries.push([t("verification_evidence", "Evidence"), evidence.status === "missing" && ["running", "pending"].includes(meta?.status) ? t("verification_not_generated", "Not generated yet") : label(evidence.status)]);
  if (evidence.harbor_reward !== undefined) entries.push([t("harbor_reward", "Harbor reward"), evidence.harbor_reward]);
  if (evidence.reward_consistency && evidence.reward_consistency !== "matched") entries.push([t("reward_consistency", "Reward consistency"), label(evidence.reward_consistency)]);
  return `<dl class="verification-summary">${entries.map(([name, value]) => `<div><dt>${esc(name)}</dt><dd>${esc(literal(value))}</dd></div>`).join("")}</dl>`;
}

function verdictRow(value, index) {
  if (!record(value)) return null;
  const name = value.item_id ?? value.id;
  const status = value.status ?? value.verdict;
  if (typeof name !== "string" || typeof status !== "string") return null;
  return { name, status, score: number(value.score) ? value.score : null,
    reason: typeof value.reason === "string" ? value.reason : "",
    evidence: Array.isArray(value.evidence_ids) ? value.evidence_ids.filter(id => typeof id === "string") : [], key: index };
}

function rewardDetails(data) {
  const rows = [];
  function visit(name, value, depth = 0) {
    if (depth > 16) throw new Error("nested reward limit");
    if (Array.isArray(value)) { value.forEach((item, index) => visit(`${name} [${index + 1}]`, item, depth + 1)); return; }
    if (!record(value) || !number(value.score)) throw new Error("invalid reward detail");
    if (value.kind === "group" && Array.isArray(value.components)) {
      rows.push({ name, score: value.score, status: "group", reason: literal(value.aggregation), evidence: [] });
      for (const component of value.components) {
        if (!record(component) || typeof component.name !== "string" || !number(component.weight)) throw new Error("invalid reward component");
        visit(`${name} / ${component.name} (${t("verification_weight", "weight")} ${component.weight})`, component.detail, depth + 1);
      }
    } else if (["programmatic", "llm", "agent"].includes(value.kind) && Array.isArray(value.criteria)) {
      rows.push({ name, score: value.score, status: value.kind, reason: [value.judge_output, ...(Array.isArray(value.warnings) ? value.warnings : [])].filter(value => typeof value === "string").join("\n"), evidence: [] });
      for (const criterion of value.criteria) {
        if (!record(criterion) || typeof criterion.name !== "string" || !number(criterion.value) || !number(criterion.weight)) throw new Error("invalid criterion");
        rows.push({ name: `${name} / ${criterion.name}`, score: criterion.value, status: criterion.error ? "error" : "criterion",
          reason: [criterion.description, criterion.reasoning, criterion.error, `${t("verification_weight", "weight")}: ${criterion.weight}`].filter(value => typeof value === "string").join("\n"), evidence: [] });
      }
    } else throw new Error("unknown reward detail");
  }
  Object.entries(data).forEach(([name, value]) => visit(name, value));
  return rows;
}

function interpretVerificationFile(path, content, truncated = false) {
  if (truncated) return null;
  const filename = path.split("/").at(-1);
  try {
    if (filename === "reward.txt" && content.trim() && number(Number(content.trim()))) return { metrics: [["reward", Number(content.trim())]], rows: [] };
    if (filename.endsWith(".xml")) {
      if (/<!DOCTYPE|<!ENTITY/i.test(content)) return null;
      const xml = new window.DOMParser().parseFromString(content, "application/xml");
      if (xml.querySelector("parsererror") || !["testsuite", "testsuites"].includes(xml.documentElement.localName)) return null;
      const rows = [...xml.querySelectorAll("testcase")].map((item, index) => {
        const children = [...item.children];
        const detail = children.find(node => node.localName === "error") || children.find(node => node.localName === "failure") || children.find(node => node.localName === "skipped");
        return { key: index, name: [item.getAttribute("classname"), item.getAttribute("name")].filter(Boolean).join(" / "),
          status: detail?.localName === "failure" ? "fail" : detail?.localName || "pass",
          duration: item.getAttribute("time"), reason: detail ? [detail.getAttribute("message"), detail.textContent].filter(Boolean).join("\n") : "", evidence: [] };
      });
      return { metrics: ["pass", "fail", "error", "skipped"].map(status => [label(status), rows.filter(row => row.status === status).length]), rows };
    }
    if (!filename.endsWith(".json")) return null;
    const data = JSON.parse(content);
    if (filename === "reward.json" && number(data)) return { metrics: [["reward", data]], rows: [] };
    if (!record(data)) return null;
    if (filename === "reward.json" && Object.values(data).length && Object.values(data).every(number)) {
      const entries = Object.entries(data);
      return entries.length <= 50 ? { metrics: entries, rows: [] } : { metrics: [], rows: entries.map(([name, score]) => ({ name, score, status: "reward", reason: "", evidence: [] })) };
    }
    if (filename === "reward-details.json" && Object.keys(data).length) return { metrics: [], rows: rewardDetails(data) };
    if (!["score.json", "llm_judge.json"].includes(filename)) return null;
    const fields = ["reward", "overall", "test_pass_rate", "rule_component_score", "llm_judge_component_score", "tests_passed", "tests_total", "llm_judge"];
    const metrics = fields.filter(key => number(data[key])).map(key => [key, data[key]]);
    for (const key of ["test_status", "judge_status"]) if (typeof data[key] === "string") metrics.push([key, label(data[key])]);
    const verdicts = Array.isArray(data.verdicts) && data.verdicts.length ? data.verdicts : data.rubrics;
    const rows = Array.isArray(verdicts) ? verdicts.map(verdictRow).filter(Boolean) : [];
    if (!metrics.length && !rows.length) return null;
    const merge = data.metadata?.score_merge || data.score_merge;
    if (merge?.method === "weighted_sum" && ["rule_weight", "rule_score", "llm_weight", "llm_score", "overall"].every(key => number(merge[key]))) {
      metrics.push([t("verification_formula", "Recorded formula"), `${merge.rule_weight} × ${merge.rule_score} + ${merge.llm_weight} × ${merge.llm_score} = ${merge.overall}`]);
    }
    return { metrics, rows };
  } catch { return null; }
}

function renderVerificationDocument(model, onEvidence) {
  const root = document.createElement("div");
  root.className = "verification-document";
  const metrics = document.createElement("dl");
  metrics.className = "verification-metrics";
  for (const [name, value] of model.metrics) {
    const pair = document.createElement("div");
    const term = document.createElement("dt"); const description = document.createElement("dd");
    term.textContent = label(name); description.textContent = literal(value);
    pair.append(term, description); metrics.append(pair);
  }
  root.append(metrics);
  if (!model.rows.length) return root;
  const controls = document.createElement("div"); controls.className = "verification-filters";
  const search = document.createElement("input"); search.type = "search";
  search.placeholder = t("verification_search_results", "Search results"); search.setAttribute("aria-label", search.placeholder);
  const status = document.createElement("select"); status.setAttribute("aria-label", t("test_status", "Test status"));
  for (const value of ["all", ...new Set(model.rows.map(row => row.status))]) {
    const option = document.createElement("option"); option.value = value; option.textContent = label(value); status.append(option);
  }
  controls.append(search, status); root.append(controls);
  const list = document.createElement("div"); list.className = "verification-verdicts";
  const pager = document.createElement("div"); pager.className = "verification-pager";
  root.append(list, pager);
  let page = 0;
  const priority = value => ["error", "fail", "failed", "failure"].includes(value) ? 0 : 1;
  const rows = [...model.rows].sort((a, b) => priority(a.status) - priority(b.status));
  function render() {
    const query = search.value.toLocaleLowerCase();
    const filtered = rows.filter(row => (status.value === "all" || row.status === status.value) && `${row.name}\n${row.reason}`.toLocaleLowerCase().includes(query));
    const pages = Math.max(1, Math.ceil(filtered.length / 50)); page = Math.min(page, pages - 1);
    list.replaceChildren();
    for (const row of filtered.slice(page * 50, (page + 1) * 50)) {
      const detail = document.createElement("details"); detail.className = "verification-verdict"; detail.dataset.status = row.status;
      const summary = document.createElement("summary");
      const name = document.createElement("span"); name.textContent = row.name;
      const result = document.createElement("span"); result.className = "verification-verdict-result";
      result.textContent = [label(row.status), row.score !== null && row.score !== undefined ? literal(row.score) : null, row.duration ? `${row.duration}s` : null].filter(Boolean).join(" · ");
      summary.append(name, result); detail.append(summary);
      const reason = document.createElement("pre"); reason.textContent = row.reason || t("verification_no_reason", "No reason recorded"); detail.append(reason);
      for (const id of row.evidence || []) {
        const button = document.createElement("button"); button.className = "action-button compact"; button.textContent = id;
        button.addEventListener("click", () => onEvidence?.(id)); detail.append(button);
      }
      list.append(detail);
    }
    if (!filtered.length) list.textContent = t("verification_no_matches", "No matching results");
    pager.replaceChildren();
    const previous = document.createElement("button"); previous.textContent = "←"; previous.className = "action-button compact";
    previous.setAttribute("aria-label", t("previous", "Previous")); previous.disabled = page === 0;
    const next = document.createElement("button"); next.textContent = "→"; next.className = "action-button compact";
    next.setAttribute("aria-label", t("next", "Next")); next.disabled = page >= pages - 1;
    const count = document.createElement("span"); count.textContent = `${page + 1} / ${pages} · ${filtered.length}`;
    previous.onclick = () => { page -= 1; render(); }; next.onclick = () => { page += 1; render(); };
    pager.append(previous, count, next);
  }
  search.oninput = status.onchange = () => { page = 0; render(); };
  render();
  return root;
}

export { interpretVerificationFile, renderVerificationDocument, renderVerificationSummary };
