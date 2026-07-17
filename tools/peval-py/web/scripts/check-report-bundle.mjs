// @ts-check

import { readFile } from "node:fs/promises";

import {
  buildReportBundle,
  REPORT_BUNDLE_PATH,
} from "./report-bundle.mjs";

const [expected, actual] = await Promise.all([
  buildReportBundle(),
  readFile(REPORT_BUNDLE_PATH),
]);

if (!expected.equals(actual)) {
  throw new Error(
    "committed report.js is stale; run `npm --prefix tools/peval-py run build`",
  );
}
process.stdout.write("report.js matches the ESM source graph\n");
