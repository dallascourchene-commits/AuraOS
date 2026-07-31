"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright-core");

const BASE_URL = process.env.AURA_CONSTRUCTION_PASCAL_FOUNDRY_URL || "http://127.0.0.1:8768/";
const OUTPUT_DIR = process.env.AURA_RUNTIME_EVIDENCE_DIR || "/tmp/aura-construction-pascal-foundry-runtime";
const CHAPTER_TIMEOUT_MS = Number(process.env.AURA_P4_CHAPTER_TIMEOUT_MS || 240000);

const SCREENSHOTS = Object.freeze({
  INITIAL: "00-bilateral-intent.png",
  FRAME_CONSTRUCTION: "01-design-3d.png",
  SHOW_FLOOR_PLAN: "02-floorplan-2d.png",
  SHOW_AS_BUILT: "03-as-built.png",
  COMPARE_REPRESENTATIONS: "04-compare.png",
  REVIEW_CANDIDATES: "07-construction-candidates.png",
  AURA_WATCH_THIS: "09-capture-started.png",
  MARK_INCIDENT: "10-incident-marked.png",
  FINALIZE_REPLAY: "11-replay-proof.png",
  RUN_RUNTIME_V2: "12-repair-route.png",
  DEGRADED_PREVIEW: "13-preview-rollback.png",
  CURRENT_REPROOF: "14-current-reproof.png",
  RETURN_TO_CONSTRUCTION: "15-observatory.png",
  DISSOLVE: "16-dissolved.png",
});

function ensureDirectory(directory) {
  fs.mkdirSync(directory, { recursive: true });
}

function writeJson(name, value) {
  const resolvedOutputDir = path.resolve(OUTPUT_DIR);
  const targetPath = path.resolve(path.join(OUTPUT_DIR, name));
  if (!targetPath.startsWith(resolvedOutputDir + path.sep) && targetPath !== resolvedOutputDir) {
    throw new Error(`Path traversal detected: ${name} resolves outside OUTPUT_DIR`);
  }
  fs.writeFileSync(targetPath, `${JSON.stringify(value, null, 2)}\n`);
}

function resolveChromiumExecutable() {
  const candidates = [
    process.env.AURA_CHROMIUM_EXECUTABLE,
    chromium.executablePath?.(),
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
  ].filter(Boolean);
  return candidates.find((candidate) => fs.existsSync(candidate));
}

async function capture(page, filename, selector = null) {
  const target = path.join(OUTPUT_DIR, filename);
  if (selector) {
    const node = page.locator(selector);
    if (await node.count()) {
      await node.scrollIntoViewIfNeeded();
      await node.screenshot({ path: target });
      return target;
    }
  }
  await page.screenshot({ path: target, fullPage: true });
  return target;
}

async function jsonFromPage(page, url, options = {}) {
  return page.evaluate(async ({ target, init }) => {
    const response = await fetch(target, { credentials: "same-origin", cache: "no-store", ...init });
    const payload = await response.json();
    if (!response.ok || payload.ok !== true) {
      throw new Error(payload.error || payload.reason || `request failed: ${response.status}`);
    }
    return payload;
  }, { target: url, init: options });
}

async function inspect(page, label) {
  return page.evaluate((currentLabel) => {
    const parse = (value) => {
      try { return value ? JSON.parse(value) : null; } catch (_) { return null; }
    };
    const receiptText = document.getElementById("construction-director-receipt")?.textContent || "";
    const status = document.getElementById("construction-director-status")?.textContent || "";
    const current = document.getElementById("construction-director-current")?.textContent || "";
    const decisionStatus = document.getElementById("construction-decision-status")?.textContent || "";
    const activeView = document.querySelector("[data-construction-view][aria-pressed='true']")?.dataset?.constructionView || null;
    const canvas = document.querySelector("#construction-canvas");
    const gl = canvas?.getContext?.("webgl2");
    return {
      label: currentLabel,
      status,
      current,
      decisionStatus,
      activeView,
      receipt: parse(receiptText),
      chapterOptionCount: document.querySelectorAll("#construction-director-chapters option").length,
      nextDisabled: Boolean(document.querySelector("[data-director-control='NEXT']")?.disabled),
      dissolved: status.toLowerCase().includes("dissolved"),
      p3Present: Boolean(document.getElementById("construction-decision-foundry")),
      pascalPresent: Boolean(document.querySelector("[data-pascal-workbench-frame], .pascal-workbench-frame")),
      asBuiltPresent: Boolean(document.getElementById("construction-as-built-frame")),
      webgl2Available: Boolean(gl),
      bodyText: document.body.innerText.slice(0, 12000),
    };
  }, label);
}

async function waitForDirector(page) {
  await page.waitForFunction(() => {
    const status = document.getElementById("construction-director-status")?.textContent || "";
    return document.querySelectorAll("#construction-director-chapters option").length === 15 &&
      status && !status.includes("not started") && !status.includes("stopped safely");
  }, null, { timeout: 90000 });
}

async function advance(page, chapterId) {
  const before = await page.locator("#construction-director-receipt").textContent();
  await page.locator("[data-director-control='NEXT']").click();
  await page.waitForFunction(({ expected, previous }) => {
    const status = document.getElementById("construction-director-status")?.textContent || "";
    if (status.includes("stopped safely") || status.includes("sync failed")) {
      throw new Error(status);
    }
    const text = document.getElementById("construction-director-receipt")?.textContent || "";
    if (!text || text === previous) return false;
    try {
      const receipt = JSON.parse(text);
      return receipt.chapter_id === expected;
    } catch (_) {
      return false;
    }
  }, { expected: chapterId, previous: before || "" }, { timeout: CHAPTER_TIMEOUT_MS });
  await page.waitForFunction(() => {
    const status = document.getElementById("construction-director-status")?.textContent || "";
    return !status.includes("sync failed") && !status.includes("stopped safely") &&
      !document.querySelector("[data-director-control='NEXT']")?.disabled;
  }, null, { timeout: CHAPTER_TIMEOUT_MS }).catch(async () => {
    const state = await inspect(page, `blocked-${chapterId}`);
    if (!state.dissolved) throw new Error(`chapter ${chapterId} did not settle: ${state.status}`);
  });
  return inspect(page, chapterId);
}

function persistChapterArtifacts(receipt, state) {
  const effect = receipt?.effect_receipt || {};
  switch (receipt?.chapter_id) {
    case "FINALIZE_REPLAY":
      writeJson("incident-replay-packet.json", effect.packet || effect);
      break;
    case "RUN_RUNTIME_V2":
      writeJson("runtime-profile-v2-proof.json", effect);
      break;
    case "ROUTE_REPAIR":
      writeJson("repair-attempt.json", effect.attempt || effect);
      break;
    case "DEGRADED_PREVIEW":
      writeJson("preview-rollback-receipt.json", effect.preview || effect);
      break;
    case "CURRENT_REPROOF":
      writeJson("u7-current-reproof.json", effect);
      break;
    case "DISSOLVE":
      writeJson("cleanup-receipt.json", effect);
      break;
    default:
      break;
  }
  writeJson(`chapter-${String(receipt?.chapter_id || "unknown").toLowerCase()}.json`, { receipt, state });
}

async function main() {
  ensureDirectory(OUTPUT_DIR);
  const consoleMessages = [];
  const pageErrors = [];
  const requestFailures = [];
  const chapterReceipts = [];
  let browser = null;
  let page = null;
  let exitCode = 0;
  try {
    const executablePath = resolveChromiumExecutable();
    browser = await chromium.launch({
      headless: true,
      ...(executablePath ? { executablePath } : {}),
      args: ["--enable-webgl", "--ignore-gpu-blocklist", "--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--disable-gpu-sandbox"],
    });
    const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
    page = await context.newPage();
    page.on("console", (message) => consoleMessages.push({ type: message.type(), text: message.text() }));
    page.on("pageerror", (error) => pageErrors.push({ name: error.name, message: error.message, stack: error.stack }));
    page.on("requestfailed", (request) => requestFailures.push({ url: request.url(), failure: request.failure() }));
    await page.goto(BASE_URL, { waitUntil: "networkidle", timeout: 90000 });
    await waitForDirector(page);

    const manifest = await jsonFromPage(page, "/api/construction/director/manifest");
    const projection = await jsonFromPage(page, "/api/construction/decision-lane");
    writeJson("construction-foundry-projection.json", projection.projection);
    await capture(page, SCREENSHOTS.INITIAL);
    const initial = await inspect(page, "initial");
    if (!initial.p3Present || initial.chapterOptionCount !== 15) throw new Error("P4 Director or P3 lane did not initialize");

    for (const chapter of manifest.manifest.chapters) {
      const state = await advance(page, chapter.chapter_id);
      const receipt = state.receipt;
      if (!receipt || receipt.chapter_id !== chapter.chapter_id) throw new Error(`missing exact receipt for ${chapter.chapter_id}`);
      chapterReceipts.push(receipt);
      persistChapterArtifacts(receipt, state);
      const screenshot = SCREENSHOTS[chapter.chapter_id];
      if (screenshot) await capture(page, screenshot);
      if (chapter.chapter_id === "REVIEW_CANDIDATES") {
        await capture(page, "05-obligation-inspector.png", "#construction-evidence-pins");
        await capture(page, "06-timeline-budget-crews.png", "#construction-selection-summary");
        await capture(page, "08-construction-decision.png", "#construction-decision-packet");
      }
    }

    const finalState = await inspect(page, "final");
    await page.locator("[data-director-control='RESTART']").click();
    await page.waitForFunction(() => {
      const status = document.getElementById("construction-director-status")?.textContent || "";
      return status.includes("0/15 chapters proven") &&
        !status.toLowerCase().includes("dissolved") &&
        document.querySelectorAll("#construction-director-chapters option").length === 15;
    }, null, { timeout: 90000 });
    const relaunchedState = await inspect(page, "relaunched");
    const relaunchSucceeded = !relaunchedState.dissolved && relaunchedState.chapterOptionCount === 15;
    const archive = {
      version: "AURA_CONSTRUCTION_PASCAL_PR5_ATTEMPT_ARCHIVE_INDEX_V1",
      arenaId: "construction",
      entries: chapterReceipts
        .filter((receipt) => ["FINALIZE_REPLAY", "RUN_RUNTIME_V2", "ROUTE_REPAIR", "DEGRADED_PREVIEW", "SUCCESSFUL_PREVIEW", "CURRENT_REPROOF"].includes(receipt.chapter_id))
        .map((receipt) => ({
          chapterId: receipt.chapter_id,
          receiptDigest: receipt.receipt_digest,
          transitionDigest: receipt.transition_digest,
          effectReceipt: receipt.effect_receipt,
        })),
      automaticPromotion: false,
      humanReviewRequired: true,
    };
    writeJson("attempt-archive-index.json", archive);
    const allAuthorityFalse = chapterReceipts.every((receipt) =>
      Object.values(receipt.authority || {}).every((value) => value === false));
    const exactOrder = chapterReceipts.map((receipt) => receipt.chapter_id)
      .join("|") === manifest.manifest.chapters.map((chapter) => chapter.chapter_id).join("|");
    const artifacts = fs.readdirSync(OUTPUT_DIR).sort();
    const evidence = {
      version: "AURA_CONSTRUCTION_PASCAL_SPATIAL_FOUNDRY_BROWSER_PROOF_V1",
      url: BASE_URL,
      manifestDigest: manifest.manifest.manifest_digest,
      chapterCount: chapterReceipts.length,
      exactOrder,
      finalState,
      relaunchedState,
      relaunchSucceeded,
      chapterReceipts,
      artifacts,
      consoleMessages,
      pageErrors,
      requestFailures,
      allAuthorityFalse,
      sourceMutation: false,
      productionMutation: false,
      automaticMerge: false,
      physicalWorkAuthorized: false,
      professionalAuthority: false,
      humanReviewRequired: true,
      ok: exactOrder && finalState.dissolved && relaunchSucceeded && allAuthorityFalse && pageErrors.length === 0 &&
        requestFailures.length === 0 && !consoleMessages.some((item) => item.type === "error"),
    };
    writeJson("browser-evidence.json", evidence);
    process.stdout.write(`${JSON.stringify(evidence, null, 2)}\n`);
    if (!evidence.ok) exitCode = 1;
  } catch (error) {
    exitCode = 1;
    pageErrors.push({ name: error.name, message: error.message, stack: error.stack });
    if (page) {
      try { await capture(page, "runtime-failure.png"); } catch (_) { /* retain original failure */ }
    }
    const evidence = {
      version: "AURA_CONSTRUCTION_PASCAL_SPATIAL_FOUNDRY_BROWSER_PROOF_V1",
      url: BASE_URL,
      chapterReceipts,
      consoleMessages,
      pageErrors,
      requestFailures,
      sourceMutation: false,
      productionMutation: false,
      automaticMerge: false,
      physicalWorkAuthorized: false,
      professionalAuthority: false,
      humanReviewRequired: true,
      ok: false,
    };
    writeJson("browser-evidence.json", evidence);
    process.stdout.write(`${JSON.stringify(evidence, null, 2)}\n`);
  } finally {
    if (browser) await browser.close().catch(() => {});
  }
  process.exitCode = exitCode;
}

main();
