// @ts-check

import { mkdir, rename, writeFile } from "node:fs/promises";
import path from "node:path";

import {
  buildReportBundle,
  REPORT_BUNDLE_PATH,
} from "./report-bundle.mjs";

const bytes = await buildReportBundle();
const temporaryPath = `${REPORT_BUNDLE_PATH}.tmp`;
await mkdir(path.dirname(REPORT_BUNDLE_PATH), { recursive: true });
await writeFile(temporaryPath, bytes);
await rename(temporaryPath, REPORT_BUNDLE_PATH);
process.stdout.write(`wrote ${REPORT_BUNDLE_PATH} (${bytes.length} bytes)\n`);
