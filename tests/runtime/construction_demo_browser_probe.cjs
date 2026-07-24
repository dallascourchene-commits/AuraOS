"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");
const { PNG } = require("pngjs");

const BASE_URL = process.env.AURA_CONSTRUCTION_DEMO_URL || "http://127.0.0.1:8767/demo/construction";
const OUTPUT_DIR = process.env.AURA_RUNTIME_EVIDENCE_DIR || "/tmp/aura-construction-runtime";

function ensureDirectory(directory) {
  fs.mkdirSync(directory, { recursive: true });
}

async function snapshot(page, name) {
  const target = path.join(OUTPUT_DIR, `${name}.png`);
  await page.screenshot({ path: target, fullPage: true });
  return target;
}

function analyzePng(buffer) {
  const image = PNG.sync.read(buffer);
  let opaquePixels = 0;
  let chromaticPixels = 0;
  for (let offset = 0; offset < image.data.length; offset += 4) {
    const red = image.data[offset];
    const green = image.data[offset + 1];
    const blue = image.data[offset + 2];
    const alpha = image.data[offset + 3];
    if (alpha === 0) continue;
    opaquePixels += 1;
    const maximum = Math.max(red, green, blue);
    const minimum = Math.min(red, green, blue);
    if (maximum >= 45 && maximum - minimum >= 18) chromaticPixels += 1;
  }
  return {
    width: image.width,
    height: image.height,
    opaquePixels,
    chromaticPixels,
    chromaticRatio: opaquePixels ? chromaticPixels / opaquePixels : 0,
  };
}

async function snapshotCanvas(page, name) {
  const target = path.join(OUTPUT_DIR, `${name}.png`);
  const buffer = await page.locator("#construction-canvas").screenshot({ path: target });
  return { path: target, ...analyzePng(buffer) };
}

async function inspectPage(page, label) {
  return page.evaluate((pageLabel) => {
    const modeButtons = [...document.querySelectorAll("button[data-mode]")].map((button) => ({
      mode: button.dataset.mode,
      disabled: button.disabled,
      active: button.classList.contains("active"),
      title: button.title,
    }));
    const canvas = document.querySelector("#construction-canvas");
    const gl = canvas?.getContext?.("webgl2");
    const sampleWebGl = () => {
      if (!canvas || !gl || gl.isContextLost?.()) {
        return { samples: 0, nonBackgroundSamples: 0, error: null };
      }
      const pixel = new Uint8Array(4);
      const columns = 32;
      const rows = 18;
      let samples = 0;
      let nonBackgroundSamples = 0;
      for (let row = 0; row < rows; row += 1) {
        for (let column = 0; column < columns; column += 1) {
          const x = Math.min(canvas.width - 1, Math.floor(((column + 0.5) / columns) * canvas.width));
          const y = Math.min(canvas.height - 1, Math.floor(((row + 0.5) / rows) * canvas.height));
          gl.readPixels(x, y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixel);
          samples += 1;
          const total = pixel[0] + pixel[1] + pixel[2];
          const spread = Math.max(pixel[0], pixel[1], pixel[2]) - Math.min(pixel[0], pixel[1], pixel[2]);
          if (pixel[3] > 0 && (total > 70 || spread > 20)) nonBackgroundSamples += 1;
        }
      }
      return {
        samples,
        nonBackgroundSamples,
        error: gl.getError?.() ?? null,
      };
    };
    return {
      label: pageLabel,
      sceneState: document.querySelector("#scene-state")?.textContent || null,
      tourStatus: document.querySelector("#tour-status")?.textContent || null,
      selectedCard: document.querySelector("#selected-card")?.textContent || null,
      intentLine: document.querySelector("#intent-line")?.textContent || null,
      storeyButtons: document.querySelectorAll("#storey-list button").length,
      modeButtons,
      canvas: canvas
        ? {
            clientWidth: canvas.clientWidth,
            clientHeight: canvas.clientHeight,
            width: canvas.width,
            height: canvas.height,
          }
        : null,
      webgl2Available: Boolean(gl),
      webglContextLost: Boolean(gl?.isContextLost?.()),
      visualEvidence: {
        webgl: sampleWebGl(),
        wireframeGroups: document.querySelectorAll(
          "#construction-mesh-overlay .construction-wireframe-storey",
        ).length,
        wireframeLines: document.querySelectorAll(
          "#construction-mesh-overlay .construction-wireframe-storey line",
        ).length,
      },
      bodyText: document.body.innerText.slice(0, 6000),
    };
  }, label);
}

async function waitForInitialState(page) {
  await page.waitForFunction(() => {
    const value = document.querySelector("#scene-state")?.textContent || "";
    return value !== "Loading" && value.length > 0;
  }, null, { timeout: 30_000 });
}

function assertVisiblePresentation(receipt, mode) {
  const screenshot = receipt.canvasScreenshot;
  if (
    !screenshot ||
    screenshot.width < 1 ||
    screenshot.height < 1 ||
    screenshot.chromaticPixels < 25
  ) {
    throw new Error(`${mode} presentation produced no verified user-visible canvas pixels`);
  }
  if (["MESH", "HYBRID"].includes(mode) && receipt.visualEvidence.wireframeLines < 12) {
    throw new Error(`${mode} presentation produced no verified wireframe geometry`);
  }
}


async function exerciseManualControls(page, receipts) {
  const controls = [
    "#orbit-left",
    "#orbit-right",
    "#zoom-in",
    "#zoom-out",
    "#explode",
    "#collapse",
    "#show-all",
  ];
  for (const selector of controls) {
    await page.click(selector);
    await page.waitForTimeout(100);
    receipts.push(await inspectPage(page, `after-${selector.slice(1)}`));
  }
  const firstStorey = page.locator("#storey-list button").first();
  if ((await firstStorey.count()) < 1) {
    throw new Error("Construction browser rendered no storey controls");
  }
  await firstStorey.click();
  await page.waitForTimeout(100);
  receipts.push(await inspectPage(page, "after-first-storey"));
}

async function exerciseRepresentationControls(page, receipts) {
  for (const mode of ["MESH", "SPLATS", "HYBRID"]) {
    const button = page.locator(`button[data-mode="${mode}"]`);
    const disabled = await button.isDisabled();
    receipts.push({ label: `mode-${mode}-before-click`, disabled });
    if (disabled) {
      throw new Error(`${mode} representation control is disabled`);
    }
    await button.click();
    await page.waitForTimeout(150);
    const receipt = await inspectPage(page, `after-mode-${mode}`);
    receipt.canvasScreenshot = await snapshotCanvas(page, `mode-${mode}-canvas`);
    receipts.push(receipt);
    if (!String(receipt.sceneState || "").startsWith(`${mode} · PRESENTED`)) {
      throw new Error(`${mode} representation did not become active`);
    }
    assertVisiblePresentation(receipt, mode);
  }
}

async function exerciseTour(page, receipts) {
  await page.click("#play-tour");
  await page.waitForFunction(() => {
    const text = document.querySelector("#tour-status")?.textContent || "";
    return text === "Tour complete" || text.includes("Presentation stopped") || text.includes("Renderer released");
  }, null, { timeout: 90_000 });
  receipts.push(await inspectPage(page, "after-tour"));
}

async function main() {
  ensureDirectory(OUTPUT_DIR);
  const consoleMessages = [];
  const pageErrors = [];
  const requestFailures = [];
  const receipts = [];

  let browser = null;
  let page = null;
  let exitCode = 0;
  try {
    browser = await chromium.launch({
      headless: true,
      args: [
        "--enable-webgl",
        "--ignore-gpu-blocklist",
        "--use-gl=swiftshader",
        "--enable-unsafe-swiftshader",
        "--disable-gpu-sandbox",
      ],
    });
    const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
    page = await context.newPage();
    page.on("console", (message) => consoleMessages.push({ type: message.type(), text: message.text() }));
    page.on("pageerror", (error) => pageErrors.push({ name: error.name, message: error.message, stack: error.stack }));
    page.on("requestfailed", (request) => requestFailures.push({ url: request.url(), failure: request.failure() }));

    await page.goto(BASE_URL, { waitUntil: "networkidle", timeout: 45_000 });
    await waitForInitialState(page);
    const initial = await inspectPage(page, "initial");
    receipts.push(initial);
    if (!initial.webgl2Available || initial.webglContextLost) {
      throw new Error("Construction browser requires an intact WebGL2 context");
    }
    if (!initial.canvas || initial.canvas.width < 1 || initial.canvas.height < 1) {
      throw new Error("Construction browser canvas has invalid dimensions");
    }
    if (initial.storeyButtons < 1) {
      throw new Error("Construction browser rendered no storey controls");
    }
    initial.canvasScreenshot = await snapshotCanvas(page, "initial-canvas");
    assertVisiblePresentation(initial, "HYBRID");
    await snapshot(page, "initial");

    await exerciseManualControls(page, receipts);
    await exerciseRepresentationControls(page, receipts);
    await exerciseTour(page, receipts);
    await snapshot(page, "after-tour");

    const finalState = receipts.at(-1);
    const finalTourStatus = String(finalState?.tourStatus || "");
    const finalSceneState = String(finalState?.sceneState || "");
    const tourFinished =
      finalSceneState === "Dissolved" && finalTourStatus.includes("Renderer released");
    const unexpectedContextLoss = receipts.some(
      (receipt) =>
        receipt.webglContextLost === true &&
        String(receipt.sceneState || "") !== "Dissolved",
    );
    const failed =
      pageErrors.length > 0 ||
      requestFailures.length > 0 ||
      consoleMessages.some((message) => message.type === "error") ||
      receipts.some((receipt) => receipt.webgl2Available === false) ||
      unexpectedContextLoss ||
      receipts.some((receipt) => String(receipt.sceneState || "").toLowerCase().includes("failed")) ||
      !tourFinished ||
      finalTourStatus.includes("Presentation stopped");
    if (failed) exitCode = 1;
  } catch (error) {
    exitCode = 1;
    pageErrors.push({ name: error.name, message: error.message, stack: error.stack });
    if (page) {
      try {
        receipts.push(await inspectPage(page, "exception"));
        await snapshot(page, "exception");
      } catch (_) {
        // Preserve the original browser failure.
      }
    }
  } finally {
    if (browser) {
      try {
        await browser.close();
      } catch (error) {
        exitCode = 1;
        pageErrors.push({ name: error.name, message: error.message, stack: error.stack });
      }
    }
    const evidence = {
      version: "AURA_CONSTRUCTION_BROWSER_PROBE_V1",
      url: BASE_URL,
      receipts,
      consoleMessages,
      pageErrors,
      requestFailures,
      ok: exitCode === 0,
      productionMutation: false,
      automaticPatch: false,
      automaticMerge: false,
      humanReviewRequired: true,
    };
    fs.writeFileSync(path.join(OUTPUT_DIR, "browser-evidence.json"), JSON.stringify(evidence, null, 2));
    process.stdout.write(`${JSON.stringify(evidence, null, 2)}\n`);
  }
  process.exitCode = exitCode;
}

main();
