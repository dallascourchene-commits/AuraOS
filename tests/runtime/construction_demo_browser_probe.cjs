"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

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
  if ((await firstStorey.count()) > 0) {
    await firstStorey.click();
    await page.waitForTimeout(100);
    receipts.push(await inspectPage(page, "after-first-storey"));
  }
}

async function exerciseRepresentationControls(page, receipts) {
  for (const mode of ["MESH", "SPLATS", "HYBRID"]) {
    const button = page.locator(`button[data-mode="${mode}"]`);
    const disabled = await button.isDisabled();
    receipts.push({ label: `mode-${mode}-before-click`, disabled });
    if (!disabled) {
      await button.click();
      await page.waitForTimeout(150);
      receipts.push(await inspectPage(page, `after-mode-${mode}`));
    }
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

  const browser = await chromium.launch({
    headless: true,
    args: [
      "--enable-webgl",
      "--ignore-gpu-blocklist",
      "--use-gl=swiftshader",
      "--disable-gpu-sandbox",
    ],
  });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();
  page.on("console", (message) => consoleMessages.push({ type: message.type(), text: message.text() }));
  page.on("pageerror", (error) => pageErrors.push({ name: error.name, message: error.message, stack: error.stack }));
  page.on("requestfailed", (request) => requestFailures.push({ url: request.url(), failure: request.failure() }));

  let exitCode = 0;
  try {
    await page.goto(BASE_URL, { waitUntil: "networkidle", timeout: 45_000 });
    await waitForInitialState(page);
    receipts.push(await inspectPage(page, "initial"));
    await snapshot(page, "initial");

    await exerciseManualControls(page, receipts);
    await exerciseRepresentationControls(page, receipts);
    await exerciseTour(page, receipts);
    await snapshot(page, "after-tour");

    const finalState = receipts.at(-1);
    const failed =
      pageErrors.length > 0 ||
      requestFailures.length > 0 ||
      receipts.some((receipt) => String(receipt.sceneState || "").toLowerCase().includes("failed")) ||
      String(finalState?.tourStatus || "").includes("Presentation stopped");
    if (failed) exitCode = 1;
  } catch (error) {
    exitCode = 1;
    pageErrors.push({ name: error.name, message: error.message, stack: error.stack });
    try {
      receipts.push(await inspectPage(page, "exception"));
      await snapshot(page, "exception");
    } catch (_) {
      // Preserve the original browser failure.
    }
  } finally {
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
    await browser.close();
    process.stdout.write(`${JSON.stringify(evidence, null, 2)}\n`);
  }
  process.exitCode = exitCode;
}

main();
