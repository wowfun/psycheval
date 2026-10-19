import contract from "../timing-sources.json" with { type: "json" };
import { t } from "./runtime.js";

function timingSource(source) {
  const name = String(source || "").toLowerCase();
  const family = contract.families.find(item => name.startsWith(item.prefix)) || {};
  const definition = { ...family, ...contract.sources[name] };
  return {
    ...definition,
    label: definition.label ? t(...definition.label) : "",
    hint: definition.hint ? t(...definition.hint) : "",
  };
}
function timestampFallbackAllowed(semantics) {
  return !contract.non_duration_timestamps.includes(String(semantics || "").toLowerCase());
}
export { timingSource, timestampFallbackAllowed };
