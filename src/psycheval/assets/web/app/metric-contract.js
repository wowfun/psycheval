// @ts-check
const METRIC_SELECTION_LIMIT = 32;
function validMetricId(value) {
  if (typeof value !== "string") return false;
  if (value.length <= 128 && /^[a-z][a-z0-9_]*$/.test(value)) return true;
  const match = /^(atif\.extra|reward):(.+)$/.exec(value);
  if (!match) return false;
  try {
    const key = decodeURIComponent(match[2]);
    const encoded = encodeURIComponent(key).replace(/[!'()*]/g, c => "%" + c.charCodeAt(0).toString(16).toUpperCase());
    return Boolean(key.trim()) && !/\p{C}/u.test(key) && new TextEncoder().encode(key).length <= 128 && encoded === match[2];
  } catch { return false; }
}
function validMetricSelection(value) {
  return Array.isArray(value) && value.length <= METRIC_SELECTION_LIMIT && value.every(validMetricId) && new Set(value).size === value.length;
}
export { METRIC_SELECTION_LIMIT, validMetricId, validMetricSelection };
