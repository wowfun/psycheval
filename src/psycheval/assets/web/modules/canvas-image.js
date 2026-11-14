// A conservative shared resource budget, independent of browser-specific maxima.
const MAX_DIMENSION = 16384, MAX_PIXELS = 32_000_000;

function canvasImageScale(width, height, { minimum = 1, preferred = 2 } = {}) {
  if (![width, height, minimum, preferred].every(value => Number.isFinite(value) && value > 0) || minimum > preferred) return null;
  const fits = scale => {
    const w = Math.ceil(width * scale), h = Math.ceil(height * scale);
    return w <= MAX_DIMENSION && h <= MAX_DIMENSION && w * h <= MAX_PIXELS;
  };
  if (fits(preferred)) return preferred;
  if (!fits(minimum)) return null;
  // Search using the rounded allocation dimensions, including their pixel cost.
  let low = minimum, high = preferred;
  for (let i = 0; i < 32; i++) {
    const mid = (low + high) / 2;
    if (fits(mid)) low = mid;
    else high = mid;
  }
  return low;
}

async function canvasPngBlob(canvas, context, unavailableError) {
  try {
    // Detect allocation failure before offering a blank or invalid download.
    context.getImageData(0, canvas.height - 1, 1, 1);
    return await new Promise((resolve, reject) => canvas.toBlob(blob => {
      if (blob) resolve(blob);
      else reject(unavailableError);
    }, "image/png"));
  } catch {
    throw unavailableError;
  }
}

export { canvasImageScale, canvasPngBlob };
