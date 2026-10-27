import { expect } from "@playwright/test";

export function expectSummaryImageSize(width, height, kind) {
  if (kind === "bar") expect(width).toBe(2000);
  else expect(width).toBeGreaterThanOrEqual(2000);
  expect(height).toBeGreaterThan(600);
  expect(width).toBeLessThanOrEqual(16384);
  expect(height).toBeLessThanOrEqual(16384);
  expect(width * height).toBeLessThanOrEqual(32_000_000);
}
