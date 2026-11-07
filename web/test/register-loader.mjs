import { registerHooks } from "node:module";

// The browser URL and Node imports consume the same package-owned resource.
registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier === "../timing-sources.json" && context.parentURL?.endsWith("/modules/timing-source.js")) {
      return nextResolve(new URL("../../src/psycheval/harbor/timing-sources.json", import.meta.url).href, context);
    }
    return nextResolve(specifier, context);
  },
});
