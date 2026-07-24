from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"review-fix anchor missing: {label}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    workflow = Path(".github/workflows/aura-construction-runtime-diagnostic.yml")
    replace_once(
        workflow,
        '''      - "aura_spatial_cli.py"
''',
        '''      - "aura_spatial_cli.py"
      - "requirements.txt"
''',
        "requirements workflow trigger",
    )
    replace_once(
        workflow,
        '''          ref: ${{ github.event.pull_request.head.sha }}
          fetch-depth: 1
''',
        '''          ref: ${{ github.event.pull_request.head.sha }}
          fetch-depth: 1
          persist-credentials: false
''',
        "checkout credential hardening",
    )

    probe = Path("tests/runtime/construction_demo_browser_probe.cjs")
    replace_once(
        probe,
        '''  const firstStorey = page.locator("#storey-list button").first();
  if ((await firstStorey.count()) > 0) {
    await firstStorey.click();
    await page.waitForTimeout(100);
    receipts.push(await inspectPage(page, "after-first-storey"));
  }
''',
        '''  const firstStorey = page.locator("#storey-list button").first();
  if ((await firstStorey.count()) < 1) {
    throw new Error("Construction browser rendered no storey controls");
  }
  await firstStorey.click();
  await page.waitForTimeout(100);
  receipts.push(await inspectPage(page, "after-first-storey"));
''',
        "required storey control",
    )
    replace_once(
        probe,
        '''    receipts.push({ label: `mode-${mode}-before-click`, disabled });
    if (!disabled) {
      await button.click();
      await page.waitForTimeout(150);
      receipts.push(await inspectPage(page, `after-mode-${mode}`));
    }
''',
        '''    receipts.push({ label: `mode-${mode}-before-click`, disabled });
    if (disabled) {
      throw new Error(`${mode} representation control is disabled`);
    }
    await button.click();
    await page.waitForTimeout(150);
    receipts.push(await inspectPage(page, `after-mode-${mode}`));
''',
        "required representation controls",
    )
    replace_once(
        probe,
        '''  const browser = await chromium.launch({
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
''',
        '''  let browser = null;
  let page = null;
  let exitCode = 0;
  try {
    browser = await chromium.launch({
      headless: true,
      args: [
        "--enable-webgl",
        "--ignore-gpu-blocklist",
        "--use-gl=swiftshader",
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
    await snapshot(page, "initial");
''',
        "guarded browser initialization",
    )
    replace_once(
        probe,
        '''    const finalState = receipts.at(-1);
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
''',
        '''    const finalState = receipts.at(-1);
    const finalTourStatus = String(finalState?.tourStatus || "");
    const tourFinished =
      finalTourStatus === "Tour complete" || finalTourStatus.includes("Renderer released");
    const failed =
      pageErrors.length > 0 ||
      requestFailures.length > 0 ||
      consoleMessages.some((message) => message.type === "error") ||
      receipts.some((receipt) => receipt.webgl2Available === false || receipt.webglContextLost === true) ||
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
''',
        "strict runtime health predicate",
    )
    replace_once(
        probe,
        '''    fs.writeFileSync(path.join(OUTPUT_DIR, "browser-evidence.json"), JSON.stringify(evidence, null, 2));
    await browser.close();
    process.stdout.write(`${JSON.stringify(evidence, null, 2)}\n`);
''',
        '''    fs.writeFileSync(path.join(OUTPUT_DIR, "browser-evidence.json"), JSON.stringify(evidence, null, 2));
    process.stdout.write(`${JSON.stringify(evidence, null, 2)}\n`);
''',
        "conditional browser cleanup",
    )

    regressions = Path("tests/js/spatial-construction-review-regressions.test.mjs")
    regressions.write_text(
        regressions.read_text(encoding="utf-8")
        + '''


test("Construction runtime diagnostic keeps dependency and browser-health gates wired", async () => {
  const { readFile } = await import("node:fs/promises");
  const workflow = await readFile(
    new URL("../../.github/workflows/aura-construction-runtime-diagnostic.yml", import.meta.url),
    "utf8",
  );
  const probe = await readFile(
    new URL("../runtime/construction_demo_browser_probe.cjs", import.meta.url),
    "utf8",
  );
  assert.match(workflow, /requirements\.txt/);
  assert.match(workflow, /persist-credentials: false/);
  assert.match(probe, /consoleMessages\.some\(\(message\) => message\.type === "error"\)/);
  assert.match(probe, /requires an intact WebGL2 context/);
  assert.match(probe, /rendered no storey controls/);
  assert.match(probe, /let browser = null/);
  assert.match(probe, /if \(browser\)/);
});
''',
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
