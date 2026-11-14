import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { startFixture, stopFixture } from "./fixture-process.mjs";
let fixture;
test.beforeAll(async () => { fixture = await startFixture({ PEVAL_E2E_TIMELINE:"1", PEVAL_E2E_TIMELINE_PARALLEL:"1", PYTHONPATH:process.cwd() }); });
test.afterAll(async () => { await stopFixture(fixture); });
async function openTrial(page) {
  await page.goto(fixture.origin);
  await page.locator("#leaderboard tbody tr").first().click();
  await expect(page.locator("#detail-sidebar")).toBeVisible();
}

async function seedTimedTrial(page) {
  await page.evaluate(async () => {
    const {state} = await import("/assets/peval/modules/runtime.js");
    const {renderDetailSidebar} = await import("/assets/peval/modules/detail-sidebar.js");
    const index = state.view.trajectory_meta.findIndex(meta => meta.trial_key === state.selectedTrial);
    const trajectory = state.view.trajectory[index], meta = state.view.trajectory_meta[index];
    trajectory.steps = Array.from({length:40}, (_, index) => ({step_id:index+1, source:index ? "agent" : "user", message:`Stage ${index+1}`}));
    meta.steps = trajectory.steps.map(step => ({step_id:step.step_id, timestamp_ms:1767225600000+step.step_id*500, duration_ms:1000, duration_source:"opencode_native_model_call"}));
    meta.timestamp_semantics = "utc_epoch_milliseconds";
    meta.evaluation = { ...meta.evaluation, phase_timing: { agent_execution: { duration_ms: 21000 } } };
    state.detailSidebar.tab = "timing";
    renderDetailSidebar();
  });
}

test("Timing loads on demand, rejects a stale activation and restores shared tabs", async ({page}) => {
  const requests = [];
  page.on("request", request => { if (/modules\/timeline-/.test(request.url())) requests.push(request.url()); });
  await openTrial(page);
  await expect(page.locator("#trace")).toHaveCount(0);
  await page.locator("[data-trial-tab=info]").click();
  expect(requests).toEqual([]);
  let release;
  const arrived = new Promise(resolve => { release = resolve; });
  let pending;
  await page.route("**/modules/timeline-shell.js", route => { pending = route; release(); });
  await page.locator("[data-trial-tab=timing]").click();
  await arrived;
  const staleSource = new URL(page.url()).searchParams.get("source");
  await page.locator(`#leaderboard tbody tr[data-source-key]:not([data-source-key="${staleSource}"])`).first().click();
  await page.locator("[data-trial-tab=info]").click();
  await pending.continue();
  await page.unroute("**/modules/timeline-shell.js");
  // Wait for the module graph itself, not an arbitrary delay.
  await page.evaluate(() => import("/assets/peval/modules/timeline-shell.js"));
  await expect(page.locator("[data-timeline-chart]")).toHaveCount(0);
  await page.locator("[data-trial-tab=timing]").click();
  await expect(page.locator("[data-timeline-chart] canvas")).toBeVisible();
  await expect(page.locator(".timeline-table-section")).toHaveAttribute("open", "");
  await page.locator(".timeline-table-section > summary").press("Enter");
  await expect(page.locator(".timeline-table-section")).not.toHaveAttribute("open", "");
  await page.locator("[data-trial-tab=info]").click();
  await page.locator("[data-trial-tab=timing]").click();
  await expect(page.locator(".timeline-table-section")).not.toHaveAttribute("open", "");
  await page.locator(".timeline-table-section > summary").press("Space");
  await page.locator('.timeline-diagnostics [data-table-sort="duration_ms"]').click();
  await page.locator('.timeline-diagnostics [data-filter-menu="stage"] > summary').click();
  await page.locator('.timeline-diagnostics [data-filter-key="stage"]').first().check();
  await page.locator('.timeline-diagnostics [data-filter-apply="stage"]').click();
  const filtered = await page.locator(".timeline-detail-row").count();
  await page.locator("[data-trial-tab=info]").click();
  await page.locator("[data-trial-tab=timing]").click();
  await expect(page.locator(".timeline-table-section")).toHaveAttribute("open", "");
  await expect(page.locator('.timeline-diagnostics [data-table-sort="duration_ms"]')).toHaveClass(/active/);
  await expect(page.locator(".timeline-detail-row")).toHaveCount(filtered);
  const href = page.url();
  expect(new URL(href).searchParams.get("tab")).toBe("timing");
  await page.reload();
  await expect(page.locator("[data-trial-tab=timing]")).toHaveAttribute("aria-selected", "true");
  await expect(page.locator("[data-timeline-chart] canvas")).toBeVisible();
  const source = new URL(href).searchParams.get("source");
  const other = page.locator(`#leaderboard tbody tr[data-source-key]:not([data-source-key="${source}"])`).first();
  const otherSource = await other.getAttribute("data-source-key");
  await other.click();
  await expect(page.locator("[data-trial-tab=trajectory]")).toHaveAttribute("aria-selected", "true");
  await page.goBack();
  await expect(page.locator("[data-trial-tab=timing]")).toHaveAttribute("aria-selected", "true");
  await page.goForward();
  await expect.poll(() => new URL(page.url()).searchParams.get("source")).toBe(otherSource);
  await page.locator("[data-trial-tab=info]").click();
  await page.reload();
  await expect(page.locator("[data-trial-tab=info]")).toHaveAttribute("aria-selected", "true");
  await page.goto(href);
  await expect(page.locator("[data-timeline-chart] canvas")).toBeVisible();
  await page.evaluate(() => { window.oldTimingChart = window.echarts.getInstanceByDom(document.querySelector("[data-timeline-chart]")); });
  await page.locator("[data-trial-tab=info]").click();
  expect(await page.evaluate(() => window.oldTimingChart.isDisposed())).toBe(true);
});

test("expanded waterfall exports every stage and releases both chart surfaces", async ({page}, testInfo) => {
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await openTrial(page);
  await seedTimedTrial(page);
  const node = page.locator("[data-trial-panel=timing] [data-timeline-chart]");
  await expect(node.locator("canvas")).toBeVisible();
  await expect(page.locator(".timeline-diagnostics > :first-child")).toHaveClass(/timeline-phases-section/);
  await expect(page.locator(".timeline-section:not([open])")).toHaveCount(0);
  async function expectAlignedHeadings() {
    const headings = await page.locator(".timeline-diagnostics > * > .timeline-head").evaluateAll(headers => headers.map(header => {
      const heading = header.querySelector("h3").getBoundingClientRect(), bounds = header.getBoundingClientRect();
      const button = header.querySelector("button")?.getBoundingClientRect();
      const arrow = getComputedStyle(header, "::after");
      return { left: heading.left - bounds.left, right: button ? bounds.right - button.right : null, arrow: arrow.content, direction: getComputedStyle(header).flexDirection };
    }));
    expect(headings.length).toBeGreaterThanOrEqual(3);
    for (const heading of headings) {
      expect(Math.abs(heading.left)).toBeLessThan(1);
      expect(heading.direction).toBe("row");
      if (heading.right !== null) expect(Math.abs(heading.right)).toBeLessThan(1);
      else expect(heading.arrow).toContain("▾");
    }
  }
  await expectAlignedHeadings();
  await page.locator("#detail-sidebar").screenshot({path:testInfo.outputPath("timing-sidebar-desktop.png")});
  await page.evaluate(() => {
    const chart = window.echarts.getInstanceByDom(document.querySelector("[data-timeline-chart]"));
    window.originalTimingChart = chart;
    chart.dispatchAction({type:"dataZoom", dataZoomIndex:0, startValue:10, endValue:20});
  });
  await page.locator("[data-timeline-expand]").click();
  const modal = page.locator(".timeline-modal");
  await expect(modal).toBeVisible();
  await expect(modal.locator("canvas")).toBeVisible();
  await modal.screenshot({path:testInfo.outputPath("timing-expanded-desktop.png")});
  await modal.locator("[data-timeline-close]").press("Tab");
  await expect(modal.locator("[data-timeline-export]")).toBeFocused();
  const downloadPromise = page.waitForEvent("download");
  await modal.locator("[data-timeline-export]").click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^peval-timeline-.*\.png$/);
  const path = testInfo.outputPath("complete-waterfall.png");
  await download.saveAs(path);
  const bytes = await readFile(path);
  expect(bytes.subarray(0,8).toString("hex")).toBe("89504e470d0a1a0a");
  const image = await page.evaluate(async base64 => {
    const bitmap = await createImageBitmap(new Blob([Uint8Array.from(atob(base64), c => c.charCodeAt(0))], {type:"image/png"}));
    const result = {width:bitmap.width, height:bitmap.height}; bitmap.close(); return result;
  }, bytes.toString("base64"));
  expect(image.width).toBe(3200);
  expect(image.height).toBeGreaterThan(40*34*2);
  const states = await page.evaluate(() => ({
    source:window.originalTimingChart.getOption().dataZoom[0],
    expanded:window.echarts.getInstanceByDom(document.querySelector(".timeline-modal [data-timeline-chart]")).getOption().series[0].data.length,
  }));
  expect(states.source.startValue).toBe(10);
  expect(states.source.endValue).toBe(20);
  expect(states.expanded).toBe(40);
  await page.evaluate(() => {
    window.savedToBlob = HTMLCanvasElement.prototype.toBlob;
    HTMLCanvasElement.prototype.toBlob = callback => callback(null);
  });
  await modal.locator("[data-timeline-export]").click();
  await expect(modal.locator("[data-timeline-error]")).toContainText("Image export failed");
  await expect(modal.locator("[data-timeline-export]")).toBeEnabled();
  await page.evaluate(() => { HTMLCanvasElement.prototype.toBlob = window.savedToBlob; });
  await page.evaluate(() => { window.expandedTimingChart = window.echarts.getInstanceByDom(document.querySelector(".timeline-modal [data-timeline-chart]")); });
  await modal.locator("[data-timeline-close]").press("Escape");
  await expect(modal).toHaveCount(0);
  await expect(page.locator("[data-timeline-expand]")).toBeFocused();
  expect(await page.evaluate(() => window.expandedTimingChart.isDisposed())).toBe(true);
  for (let index=0; index<6; index++) await page.locator("#detail-sidebar [data-sidebar-resize]").press("Shift+ArrowRight");
  await expect(page.locator("#detail-sidebar [data-sidebar-resize]")).toHaveAttribute("aria-valuenow", "360");
  expect((await page.locator("#detail-sidebar").boundingBox()).width).toBe(360);
  await expect.poll(() => node.evaluate(node => node.clientWidth === node.querySelector("canvas")?.clientWidth)).toBe(true);
  expect(await node.evaluate(node => node.scrollWidth <= node.clientWidth)).toBe(true);
  await expectAlignedHeadings();
  await page.locator(".detail-sidebar-body").evaluate(node => { node.scrollTop = 0; });
  await page.locator("#detail-sidebar").screenshot({path:testInfo.outputPath("timing-sidebar-360.png")});
  await page.setViewportSize({width:390,height:844});
  await expectAlignedHeadings();
  await page.locator("#detail-sidebar").screenshot({path:testInfo.outputPath("timing-sidebar-mobile.png")});
  await page.locator("[data-timeline-expand]").click();
  await expect(modal.locator("canvas")).toBeVisible();
  await modal.screenshot({path:testInfo.outputPath("timing-expanded-mobile.png")});
  const point = await modal.locator("[data-timeline-chart]").evaluate(node => {
    const chart = window.echarts.getInstanceByDom(node), item = chart.getOption().series[0].data[0];
    return chart.convertToPixel({gridIndex:0}, [(item.value[0]+item.value[1])/2,item.value[2]]);
  });
  const bounds = await modal.locator("[data-timeline-chart]").boundingBox();
  await page.mouse.click(bounds.x+point[0], bounds.y+point[1]);
  await expect(modal).toHaveCount(0);
  await expect(page.locator("[data-trial-tab=trajectory]")).toHaveAttribute("aria-selected", "true");
  await expect(page.locator('#detail-sidebar details[data-step="1"]')).toHaveAttribute("open", "");
  expect(await page.evaluate(() => window.originalTimingChart.isDisposed())).toBe(true);
  expect(errors).toEqual([]);
});

test("missing chart library leaves the timing table usable", async ({page}) => {
  await page.route("**/assets/echarts/**", route => route.abort());
  await openTrial(page);
  await page.locator("[data-trial-tab=timing]").click();
  await expect(page.locator("[data-timeline-fallback]")).toBeVisible();
  await expect(page.locator(".timeline-table-section")).toHaveAttribute("open", "");
  await expect(page.locator(".timeline-detail-row").first()).toBeVisible();
  await expect(page.locator("[data-timeline-expand]")).toBeDisabled();
});

for (const surface of ["catalog", "timing table"]) {
  test(`${surface} controls retain the waterfall instance and zoom`, async ({page}) => {
    await openTrial(page);
    await seedTimedTrial(page);
    await expect(page.locator("[data-timeline-chart] canvas")).toBeVisible();
    await page.evaluate(() => {
      window.retainedTimingChart = window.echarts.getInstanceByDom(document.querySelector("[data-timeline-chart]"));
      window.retainedTimingChart.dispatchAction({type:"dataZoom", dataZoomIndex:0, startValue:10, endValue:20});
    });
    async function expectRetained() {
      expect(await page.evaluate(() => {
        const chart = window.echarts.getInstanceByDom(document.querySelector("[data-timeline-chart]"));
        return chart === window.retainedTimingChart && !chart.isDisposed()
          && chart.getOption().dataZoom[0].startValue === 10 && chart.getOption().dataZoom[0].endValue === 20;
      })).toBe(true);
    }
    if (surface === "catalog") {
      await page.locator('#leaderboard label:has([data-table-row-select])').first().click();
      await expectRetained();
      await page.evaluate(async () => {
        const {loadCatalogPage} = await import("/assets/peval/modules/serve-catalog.js");
        await loadCatalogPage({sort:"score", direction:"asc", search:"e2e", page_size:1, page:2});
      });
      await expectRetained();
      await page.locator('.toolbar-view-menu > summary').click();
      await page.locator('[data-metric-scope][value="root"]').check();
      await expect.poll(() => page.evaluate(() => window.retainedTimingChart.isDisposed())).toBe(true);
      await expect(page.locator("[data-timeline-chart] canvas")).toBeVisible();
    } else {
      await page.locator('.timeline-diagnostics [data-table-sort="duration_ms"]').click();
      await expectRetained();
      await page.locator('.timeline-diagnostics [data-filter-menu="stage"] > summary').click();
      await page.locator('.timeline-diagnostics [data-filter-key="stage"][value="Input processing"]').check();
      await page.locator('.timeline-diagnostics [data-filter-apply="stage"]').click();
      await expectRetained();
      await expect(page.locator(".timeline-detail-row")).toHaveCount(1);
    }
  });
}
