import assert from "node:assert/strict";
import test from "node:test";
import { canvasImageScale, canvasPngBlob } from "../../src/psycheval/assets/web/modules/canvas-image.js";

test("image density respects the shared dimension and rounded pixel budgets without truncation", () => {
  assert.equal(canvasImageScale(1000, 1000), 2);
  assert.equal(canvasImageScale(1000, 8000, { minimum: 2 }), 2);
  assert.equal(canvasImageScale(1000, 8001, { minimum: 2 }), null);
  assert.equal(canvasImageScale(1600, 16384), 1);
  assert.equal(canvasImageScale(1600, 16385), null);
  assert.equal(canvasImageScale(8000, 4001), null);
  for (const [width, height] of [[1600, 15000], [4001, 2001], [3000, 3000]]) {
    const scale = canvasImageScale(width, height);
    assert.ok(scale >= 1 && scale < 2);
    const w = Math.ceil(width * scale), h = Math.ceil(height * scale);
    assert.ok(w <= 16384 && h <= 16384 && w * h <= 32_000_000);
    assert.ok(Math.ceil(width * (scale + 0.001)) * Math.ceil(height * (scale + 0.001)) > 32_000_000
      || Math.ceil(height * (scale + 0.001)) > 16384);
  }
});

test("PNG encoding normalizes allocation and encoding failures and preserves successful output", async () => {
  const unavailable = new Error("Image unavailable"), blob = new Blob(["png"]);
  const context = { getImageData() {} };
  assert.equal(await canvasPngBlob({ height: 10, toBlob: callback => callback(blob) }, context, unavailable), blob);
  for (const toBlob of [callback => callback(null), () => { throw new Error("encoding failed"); }]) {
    await assert.rejects(canvasPngBlob({ height: 10, toBlob }, context, unavailable), error => error === unavailable);
  }
  await assert.rejects(canvasPngBlob({ height: 10, toBlob() { assert.fail("must not encode after allocation failure"); } },
    { getImageData() { throw new Error("allocation failed"); } }, unavailable), error => error === unavailable);
});
