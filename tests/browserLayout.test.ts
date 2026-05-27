import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { chromium } from "playwright";

const css = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");
const browserExecutable = [
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
].find((path) => existsSync(path));

assert.ok(css.includes(".inference-progress-rail"), "bottom console should style the structured inference progress rail");
assert.ok(css.includes(".inference-progress-track"), "bottom console should style a horizontal SSE-backed progress track");
assert.ok(css.includes(".inference-timeline"), "bottom console should style structured inference timeline rows");

function panelMarkup(title: string, orientation: string) {
  return `
    <div class="ortho-panel ortho-${orientation}">
      <div class="ortho-title"><strong>${title}</strong><span>1/64</span></div>
      <div class="ortho-canvas" style="--slice-aspect: 1 / 1; --slice-pixel-aspect: 1 / 1;">
        <div class="ortho-image-stage">
          <img class="ortho-source" alt="${title}" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' fill='%23222'/%3E%3C/svg%3E" />
          <span class="ortho-crosshair ortho-crosshair-x" style="top:50%"></span>
          <span class="ortho-crosshair ortho-crosshair-y" style="left:50%"></span>
        </div>
      </div>
    </div>
  `;
}

function fixture() {
  return `
    <style>${css}</style>
    <main class="app-shell">
      <aside class="rail">
        <div class="brand">CT</div>
        <button class="active"><span>分割</span></button>
      </aside>
      <section class="main-stage">
        <header class="topbar"><h1>Segmentation GUI</h1><div class="top-actions"><button class="primary-button">运行分割</button></div></header>
        <section class="content-grid">
          <section class="study-column">
            <div class="viewer-toolbar"><div class="tool-group"><button>WL</button><button>Zoom</button></div><div class="scan-status">切片 1/64</div></div>
            <div class="viewer-frame">
              <div class="ct-canvas">
                <div class="orthogonal-shell">
                  <div class="orthogonal-viewer">
                    <div class="orthogonal-grid">
                      ${panelMarkup("Axial", "axial")}
                      ${panelMarkup("Sagittal", "sagittal")}
                      ${panelMarkup("Coronal", "coronal")}
                    </div>
                    <div class="voxel-readout"><span>Voxel (1, 1, 1)</span><span>HU 42</span><span>肝脏</span></div>
                  </div>
                </div>
              </div>
              <div class="viewer-caption"><span>原图</span><span>结果</span></div>
            </div>
          </section>
          <aside class="inspector"><section class="panel"><div class="section-head"><h2>分割控制</h2></div></section></aside>
        </section>
        <footer class="bottom-console">
          <div class="console-head"><h2>流程日志</h2></div>
          <section class="inference-progress-rail is-running" aria-label="实时推理进度">
            <div class="inference-progress-main">
              <div class="inference-progress-top"><strong>推理运行中</strong><span>20%</span></div>
              <div class="inference-progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="20">
                <span style="width:20%"></span>
              </div>
              <div class="inference-progress-meta">
                <span>nnUNetv2 命令运行中</span>
                <span>job_demo_001</span>
                <span>质量推理</span>
                <span>1分05秒</span>
              </div>
            </div>
            <ol class="inference-timeline">
              <li><span>20%</span><p>nnUNetv2 命令运行中</p></li>
              <li><span>14%</span><p>已准备训练权重</p></li>
            </ol>
          </section>
        </footer>
      </section>
    </main>
  `;
}

function splitFixture() {
  const imageSrc = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==";
  return `
    <style>${css}</style>
    <div class="ortho-canvas compare-split has-mask" style="width:400px; --compare-position:75%; --slice-aspect: 1 / 1; --slice-pixel-aspect: 1 / 1; --mask-opacity: .58;">
      <div class="ortho-image-stage">
        <img class="ortho-source" src="${imageSrc}" alt="">
        <img class="ortho-mask" src="${imageSrc}" alt="">
      </div>
    </div>
    <div class="ortho-canvas compare-split no-mask" style="width:400px; --compare-position:75%; --slice-aspect: 1 / 1; --slice-pixel-aspect: 1 / 1;">
      <div class="ortho-image-stage">
        <img class="ortho-source" src="${imageSrc}" alt="">
      </div>
    </div>
  `;
}

type LayoutSnapshot = {
  viewport: { width: number; height: number };
  document: { clientWidth: number; scrollWidth: number };
  grid: { columns: string; rows: string };
  frame: DOMRect;
  rail: DOMRect;
  panels: DOMRect[];
  canvases: DOMRect[];
  images: { objectFit: string; pointerEvents: string; userDrag: string | null }[];
};

type SplitSnapshot = {
  clipPath: string;
  dividerContent: string;
  noMaskDividerContent: string;
};

async function snapshot(width: number, height: number): Promise<LayoutSnapshot> {
  const browser = await chromium.launch(browserExecutable ? { executablePath: browserExecutable } : undefined);
  const page = await browser.newPage({ viewport: { width, height } });
  try {
    await page.setContent(fixture(), { waitUntil: "load" });
    return await page.evaluate(() => {
      const rect = (element: Element) => {
        const box = element.getBoundingClientRect();
        return {
          x: box.x,
          y: box.y,
          width: box.width,
          height: box.height,
          top: box.top,
          right: box.right,
          bottom: box.bottom,
          left: box.left
        } as DOMRect;
      };
      const gridElement = document.querySelector(".orthogonal-grid")!;
      const gridStyle = getComputedStyle(gridElement);
      return {
        viewport: { width: window.innerWidth, height: window.innerHeight },
        document: { clientWidth: document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth },
        grid: { columns: gridStyle.gridTemplateColumns, rows: gridStyle.gridTemplateRows },
        frame: rect(document.querySelector(".viewer-frame")!),
        rail: rect(document.querySelector(".inference-progress-rail")!),
        panels: Array.from(document.querySelectorAll(".ortho-panel")).map(rect),
        canvases: Array.from(document.querySelectorAll(".ortho-canvas")).map(rect),
        images: Array.from(document.querySelectorAll(".ortho-canvas img")).map((image) => {
          const style = getComputedStyle(image);
          return {
            objectFit: style.objectFit,
            pointerEvents: style.pointerEvents,
            userDrag: style.getPropertyValue("-webkit-user-drag")
          };
        })
      };
    });
  } finally {
    await browser.close();
  }
}

async function splitSnapshot(): Promise<SplitSnapshot> {
  const browser = await chromium.launch(browserExecutable ? { executablePath: browserExecutable } : undefined);
  const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
  try {
    await page.setContent(splitFixture(), { waitUntil: "load" });
    return await page.evaluate(() => {
      const mask = document.querySelector(".has-mask .ortho-mask")!;
      const stageWithMask = document.querySelector(".has-mask .ortho-image-stage")!;
      const stageWithoutMask = document.querySelector(".no-mask .ortho-image-stage")!;
      return {
        clipPath: getComputedStyle(mask).clipPath,
        dividerContent: getComputedStyle(stageWithMask, "::after").content,
        noMaskDividerContent: getComputedStyle(stageWithoutMask, "::after").content
      };
    });
  } finally {
    await browser.close();
  }
}

const desktop = await snapshot(1366, 768);
assert.equal(desktop.panels.length, 3);
assert.ok(desktop.panels[0].left < desktop.panels[1].left, "desktop axial panel should occupy the left side");
assert.ok(Math.abs(desktop.panels[1].left - desktop.panels[2].left) < 2, "desktop sagittal and coronal panels should stack in the right column");
assert.ok(desktop.panels[1].top < desktop.panels[2].top, "desktop sagittal should be above coronal");
assert.ok(desktop.panels[0].height > desktop.panels[1].height + desktop.panels[2].height - 36, "desktop axial panel should span the side-stack height");
assert.ok(desktop.canvases[1].width >= 300 && desktop.canvases[2].width >= 300, "desktop sagittal/coronal canvases should have enough width for detail review");
assert.ok(desktop.canvases.every((box) => box.width >= 180 && box.height >= 140), "desktop canvases should stay readable");
assert.ok(desktop.rail.width >= 700 && desktop.rail.height <= 150, "desktop progress rail should fit below the viewer without becoming a tall panel");
assert.ok(desktop.document.scrollWidth <= desktop.document.clientWidth + 1, "desktop should not create horizontal page overflow");

const mobile = await snapshot(390, 844);
assert.equal(mobile.panels.length, 3);
assert.ok(mobile.grid.columns.split(" ").length === 1, "mobile grid should collapse to one column");
assert.ok(mobile.panels[0].top < mobile.panels[1].top && mobile.panels[1].top < mobile.panels[2].top, "mobile panels should stack vertically");
assert.ok(mobile.frame.height >= 560, "mobile viewer frame should keep usable height");
assert.ok(mobile.canvases.every((box) => box.width >= 260 && box.height >= 90), "mobile canvases should not collapse into thumbnails");
assert.ok(mobile.rail.width <= mobile.document.clientWidth && mobile.rail.height <= 230, "mobile progress rail should stack without horizontal overflow");
assert.ok(mobile.document.scrollWidth <= mobile.document.clientWidth + 1, "mobile should not create horizontal page overflow");

for (const image of [...desktop.images, ...mobile.images]) {
  assert.equal(image.objectFit, "contain");
  assert.equal(image.pointerEvents, "none");
}

const split = await splitSnapshot();
assert.notEqual(split.clipPath, "none", "orthogonal split mode should clip the mask layer");
assert.notEqual(split.dividerContent, "none", "orthogonal split mode should show a divider when mask exists");
assert.equal(split.noMaskDividerContent, "none", "orthogonal split mode should not show a divider without a mask");
