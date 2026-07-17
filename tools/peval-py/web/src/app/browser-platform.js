// @ts-check

/**
 * @param {Window & typeof globalThis} scope
 */
function createBrowserPlatform(scope) {
  return {
    document: scope.document,
    window: scope,
    destroy() {},
  };
}

export { createBrowserPlatform };
