import { t } from "./shared.js";
import { timelineChartOption } from "./timeline-chart.js";
import { wrappedLines } from "./summary-chart.js";
import { canvasImageScale, canvasPngBlob } from "./canvas-image.js";

async function timelineImageBlob(trace, identity, coverage) {
  await document.fonts?.ready;
  if (!window.echarts) throw new Error(t("timeline_export_unavailable", "Image rendering is unavailable."));
  const width = 1600, plotHeight = Math.max(300, trace.stages.length * 34 + 96);
  const canvas = document.createElement("canvas"), host = document.createElement("div");
  let chart = null, plot = null;
  try {
    const context = canvas.getContext("2d");
    if (!context) throw new Error(t("timeline_export_unavailable", "Image rendering is unavailable."));
    context.font = "16px system-ui";
    const lines = [identity.trialKey, `${identity.trajectoryId} / ${identity.scope}`, coverage].flatMap(text => wrappedLines(value => context.measureText(value).width, text, width - 64));
    const header = 32 + lines.length * 24;
    const height = header + plotHeight;
    const scale = canvasImageScale(width, height);
    if (scale === null) throw new Error(t("timeline_export_too_large", "The complete waterfall is too large to export as an image."));
    canvas.width = Math.ceil(width * scale); canvas.height = Math.ceil(height * scale);
    context.scale(scale, scale); context.fillStyle = "#fff"; context.fillRect(0, 0, width, height);
    context.fillStyle = "#27231b"; context.font = "16px system-ui"; context.textBaseline = "top";
    lines.forEach((line, index) => context.fillText(line, 32, 16 + index * 24));
    chart = window.echarts.init(host, null, { renderer: "canvas", width, height: plotHeight, devicePixelRatio: scale });
    const option = timelineChartOption(trace, { width, full: true });
    option.grid.left = 360;
    option.yAxis.axisLabel.width = 330;
    chart.setOption(option, true);
    plot = chart.renderToCanvas({ pixelRatio: scale, backgroundColor: "#fff" });
    context.drawImage(plot, 0, header, width, plotHeight);
    return await canvasPngBlob(canvas, context, new Error(t("timeline_export_unavailable", "Image rendering is unavailable.")));
  } finally {
    chart?.dispose(); host.remove();
    if (plot) plot.width = plot.height = 0;
    canvas.width = canvas.height = 0;
  }
}
export { timelineImageBlob };
