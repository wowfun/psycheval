import { fmtNum, t } from "./shared.js";
import { downloadBlob } from "./export.js";
import { originNote, radarMetricLabel, radarOption } from "./leaderboard-radar.js";

const WIDTH = 1000, SCALE = 2, MARGIN = 32, GAP = 24;
const INK = "#292c36", MUTED = "#596171", RULE = "#dadce2";
const font = (size, bold = false) => `${bold ? "600 " : ""}${size}px "Segoe UI", "Microsoft YaHei", sans-serif`;

function imageTooLarge(kind) {
  return new Error(kind === "radar"
    ? t("summary_export_radar_too_large", "The radar image is too large. Select fewer metrics or shorten metric names; fewer comparison groups may also reduce the legend.")
    : t("summary_export_too_large", "The image is too large. Narrow the filters or choose a grouping with fewer groups."));
}

function checkImageSize(width, height, kind = "bar") {
  if (width * SCALE > 16384 || height * SCALE > 16384 || width * height * SCALE ** 2 > 32_000_000) throw imageTooLarge(kind);
}

// Measure and wrap before allocating the output canvas; no label is truncated.
function wrappedLines(context, text, width) {
  return String(text).split("\n").flatMap(paragraph => {
    const lines = [];
    let line = "";
    for (const character of paragraph) {
      if (line && context.measureText(line + character).width > width) {
        lines.push(line); line = "";
      }
      line += character;
    }
    lines.push(line);
    return lines;
  });
}

// Place labels just beyond their axis endpoints and expand the plot until their
// measured rectangles fit without overlap. The same geometry drives ECharts.
function radarImagePlot(radar, context) {
  context.font = font(14);
  const labels = radar.axes.map(axis => {
    const definition = radar.definitions.find(item => item.key === axis.key);
    const unit = definition?.unit ? ` (${definition.unit})` : "";
    const lines = wrappedLines(context, `${radarMetricLabel(radar, axis.key)}${unit} ${axis.direction > 0 ? "↑" : "↓"}`, 180);
    return { lines, width: Math.max(...lines.map(line => context.measureText(line).width)), height: lines.length * 21 };
  });
  for (let radius = 190; ; radius += 32) {
    const boxes = labels.map((label, index) => {
      const angle = Math.PI / 2 + index * 2 * Math.PI / labels.length;
      const dx = Math.cos(angle), dy = -Math.sin(angle);
      const x = (radius + 14) * dx, y = (radius + 14) * dy;
      const align = Math.abs(dx) < 1e-8 ? "center" : dx < 0 ? "right" : "left";
      return { ...label, align, x: x - (dx < -1e-8 ? label.width : Math.abs(dx) < 1e-8 ? label.width / 2 : 0),
        y: y - (dy < -1e-8 ? label.height : Math.abs(dy) < 1e-8 ? label.height / 2 : 0) };
    });
    const left = Math.min(-radius, ...boxes.map(box => box.x)) - 16;
    const right = Math.max(radius, ...boxes.map(box => box.x + box.width)) + 16;
    const top = Math.min(-radius, ...boxes.map(box => box.y)) - 16;
    const bottom = Math.max(radius, ...boxes.map(box => box.y + box.height)) + 16;
    const width = Math.max(WIDTH - 2 * MARGIN, Math.ceil(right - left));
    const height = Math.max(640, Math.ceil(bottom - top));
    checkImageSize(width + 2 * MARGIN, height + 2 * MARGIN, "radar");
    const overlaps = boxes.some((a, i) => boxes.slice(0, i).some(b =>
      a.x < b.x + b.width + 4 && b.x < a.x + a.width + 4 && a.y < b.y + b.height + 4 && b.y < a.y + a.height + 4));
    if (overlaps) continue;
    const center = [-left + (width - (right - left)) / 2, -top + (height - (bottom - top)) / 2];
    return { width, height, radius, center, labels: boxes.map(box => ({ ...box, x: box.x + center[0], y: box.y + center[1] })) };
  }
}

function summaryImageLayout(kind, snapshot, context) {
  const commands = [];
  const radarPlot = kind === "radar" ? radarImagePlot(snapshot.radar, context) : null;
  const imageWidth = radarPlot ? radarPlot.width + 2 * MARGIN : WIDTH;
  const text = (value, x, y, width, size = 14, color = INK, bold = false) => {
    context.font = font(size, bold);
    const lines = wrappedLines(context, value, width);
    const lineHeight = Math.ceil(size * 1.5);
    const height = lines.length * lineHeight;
    checkImageSize(imageWidth, y + height + MARGIN, kind);
    commands.push({ type: "text", lines, x, y, lineHeight, font: context.font, color });
    return height;
  };
  const rect = (x, y, width, height, color) => commands.push({ type: "rect", x, y, width, height, color });
  const innerWidth = imageWidth - 2 * MARGIN;
  let y = MARGIN;
  y += text(snapshot.title, MARGIN, y, innerWidth, 26, INK, true) + 4;
  y += text(snapshot.subtitle, MARGIN, y, innerWidth, 16, INK, true) + 4;
  y += text(snapshot.scope, MARGIN, y, innerWidth, 13, MUTED) + 12;
  const note = kind === "bar"
    ? `${t("summary_scale_note", "Each metric has its own scale. Compare bars only within a metric.")} - = ${t("summary_no_data", "No data")}`
    : t("summary_radar_scale", "Relative to all groups in the current query · farther out is better. × = no data (offset near the origin for readability).");
  y += text(note, MARGIN, y, innerWidth, 13, MUTED) + GAP;
  let plot = null;
  if (kind === "bar") {
    const cardWidth = (innerWidth - GAP) / 2;
    for (let index = 0; index < snapshot.bars.length; index += 2) {
      let bottom = y;
      snapshot.bars.slice(index, index + 2).forEach((metric, column) => {
        const x = MARGIN + column * (cardWidth + GAP);
        rect(x, y, cardWidth, 2, RULE);
        let rowY = y + 14;
        rowY += text(metric.definition.label, x, rowY, cardWidth, 17, INK, true) + 12;
        for (const item of metric.values) {
          const labelHeight = text(item.group.label, x, rowY, cardWidth - 146, 13);
          const valueHeight = text(`${item.formatted} · n=${fmtNum(item.count)}`, x + cardWidth - 130, rowY, 130, 13, MUTED);
          rowY += Math.max(labelHeight, valueHeight) + 6;
          rect(x, rowY, cardWidth, 8, "#edf0f4");
          rect(x + cardWidth * (item.zero || 0) / 100, rowY - 2, 1, 12, MUTED);
          if (item.width > 0) rect(x + cardWidth * (item.start || 0) / 100, rowY, cardWidth * item.width / 100, 8, "#536fa3");
          rowY += 24;
        }
        bottom = Math.max(bottom, rowY);
      });
      y = bottom + GAP;
    }
  } else {
    plot = { ...radarPlot, x: MARGIN, y };
    for (const label of plot.labels) {
      const offset = label.align === "right" ? label.width : label.align === "center" ? label.width / 2 : 0;
      commands.push({ type: "text", lines: label.lines, x: plot.x + label.x + offset, y: plot.y + label.y, align: label.align, lineHeight: 21, font: font(14), color: INK });
    }
    y += plot.height + GAP;
    y += text(t("summary_radar_groups", "Comparison groups"), MARGIN, y, innerWidth, 17, INK, true) + 12;
    for (const item of snapshot.radar.series) {
      rect(MARGIN, y + 8, 26, 4, item.color);
      y += text(`${item.group.label} · n=${fmtNum(item.group.count)}`, MARGIN + 40, y, innerWidth - 40, 14, INK, true);
      const missing = item.points.filter(point => point.value === null).map(point => radarMetricLabel(snapshot.radar, point.key));
      const notes = [originNote(item.points)];
      if (missing.length) notes.push(`× ${t("summary_no_data", "No data")}: ${missing.join(", ")}`);
      const equal = item.points.filter(point => point.value !== null && point.equal).map(point => radarMetricLabel(snapshot.radar, point.key));
      if (equal.length) notes.push(`${t("summary_radar_equal", "No group difference")}: ${equal.join(", ")}`);
      for (const note of notes.filter(Boolean)) y += text(note, MARGIN + 40, y, innerWidth - 40, 12, MUTED);
      y += 16;
    }
  }
  const height = Math.ceil(y + MARGIN);
  checkImageSize(imageWidth, height, kind);
  return { width: imageWidth, height, commands, plot };
}

async function summaryImageBlob(kind, snapshot) {
  if (!["bar", "radar"].includes(kind)) throw new Error("Unknown chart type");
  await document.fonts?.ready;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 1;
  let chart = null, chartCanvas = null;
  const chartHost = document.createElement("div");
  try {
    const context = canvas.getContext("2d");
    if (!context) throw new Error(t("summary_export_canvas_unavailable", "Image rendering is unavailable in this browser."));
    const layout = summaryImageLayout(kind, snapshot, context);
    canvas.width = layout.width * SCALE;
    canvas.height = layout.height * SCALE;
    context.scale(SCALE, SCALE);
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, layout.width, layout.height);
    if (layout.plot) {
      if (!window.echarts) throw new Error(t("summary_radar_unavailable", "Radar chart is unavailable. Switch to the bar chart or use the summary table."));
      const plot = layout.plot;
      chart = window.echarts.init(chartHost, null, { renderer: "canvas", width: plot.width, height: plot.height, devicePixelRatio: SCALE });
      chart.setOption(radarOption(snapshot.radar, plot.width, plot.height, { ink: INK, rule: RULE, hideAxisNames: true, radius: plot.radius, center: plot.center }), true);
      chartCanvas = chart.renderToCanvas({ pixelRatio: SCALE, backgroundColor: "#fff" });
      context.drawImage(chartCanvas, plot.x, plot.y, plot.width, plot.height);
    }
    context.textBaseline = "top";
    for (const command of layout.commands) {
      context.fillStyle = command.color;
      if (command.type === "rect") context.fillRect(command.x, command.y, command.width, command.height);
      else {
        context.font = command.font;
        context.textAlign = command.align || "left";
        command.lines.forEach((line, index) => context.fillText(line, command.x, command.y + index * command.lineHeight));
      }
    }
    return await new Promise((resolve, reject) => canvas.toBlob(blob => {
      if (blob) resolve(blob);
      else reject(new Error(t("summary_export_canvas_unavailable", "Image rendering is unavailable in this browser.")));
    }, "image/png"));
  } finally {
    chart?.dispose();
    chartHost.remove();
    if (chartCanvas) chartCanvas.width = chartCanvas.height = 0;
    canvas.width = canvas.height = 0;
  }
}

async function downloadSummaryImage(kind, snapshot) {
  const blob = await summaryImageBlob(kind, snapshot);
  downloadBlob(`peval-leaderboard-summary-${kind}.png`, "image/png", blob);
}

export { summaryImageLayout, summaryImageBlob, downloadSummaryImage };
