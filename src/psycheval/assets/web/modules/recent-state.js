// Bounded session-local presentation state; reading an identity keeps it recent.
function createRecentState(limit = 64) {
  const entries = new Map();
  return {
    get(key) {
      const value = entries.get(key) || {};
      entries.delete(key); entries.set(key, value);
      if (entries.size > limit) entries.delete(entries.keys().next().value);
      return value;
    },
  };
}
export { createRecentState };
