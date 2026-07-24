from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"screenshot-proof anchor missing: {label}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    probe = Path("tests/runtime/construction_demo_browser_probe.cjs")
    replace_once(
        probe,
        'const { chromium } = require("playwright");\n',
        'const { chromium } = require("playwright");\nconst { PNG } = require("pngjs");\n',
        "PNG decoder import",
    )
    replace_once(
        probe,
        '''async function snapshot(page, name) {
  const target = path.join(OUTPUT_DIR, `${name}.png`);
  await page.screenshot({ path: target, fullPage: true });
  return target;
}
''',
        '''async function snapshot(page, name) {
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
''',
        "user-visible canvas screenshot analyzer",
    )
    replace_once(
        probe,
        '''function assertVisiblePresentation(receipt, mode) {
  const webgl = receipt.visualEvidence?.webgl;
  if (!webgl || webgl.samples < 1 || webgl.nonBackgroundSamples < 1 || webgl.error !== 0) {
    throw new Error(`${mode} presentation produced no verified WebGL pixels`);
  }
  if (["MESH", "HYBRID"].includes(mode) && receipt.visualEvidence.wireframeLines < 12) {
    throw new Error(`${mode} presentation produced no verified wireframe geometry`);
  }
}
''',
        '''function assertVisiblePresentation(receipt, mode) {
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
''',
        "screenshot-based visible presentation predicate",
    )
    replace_once(
        probe,
        '''    const receipt = await inspectPage(page, `after-mode-${mode}`);
    receipts.push(receipt);
''',
        '''    const receipt = await inspectPage(page, `after-mode-${mode}`);
    receipt.canvasScreenshot = await snapshotCanvas(page, `mode-${mode}-canvas`);
    receipts.push(receipt);
''',
        "mode screenshot receipt",
    )
    replace_once(
        probe,
        '''    assertVisiblePresentation(initial, "HYBRID");
    await snapshot(page, "initial");
''',
        '''    initial.canvasScreenshot = await snapshotCanvas(page, "initial-canvas");
    assertVisiblePresentation(initial, "HYBRID");
    await snapshot(page, "initial");
''',
        "initial screenshot receipt",
    )

    profile = Path(".aura/runtime_profiles/construction_demo.v1.json")
    replace_once(
        profile,
        '''      "browser-evidence.json",
      "initial.png",
      "after-tour.png"
''',
        '''      "browser-evidence.json",
      "initial.png",
      "initial-canvas.png",
      "mode-MESH-canvas.png",
      "mode-SPLATS-canvas.png",
      "mode-HYBRID-canvas.png",
      "after-tour.png"
''',
        "required visual evidence artifacts",
    )

    diagnostic = Path(".github/workflows/aura-construction-runtime-diagnostic.yml")
    replace_once(
        diagnostic,
        "npm install --no-audit --no-fund playwright@1.55.0\n",
        "npm install --no-audit --no-fund playwright@1.55.0 pngjs@7.0.0\n",
        "persistent PNG proof dependency",
    )

    regressions = Path("tests/js/spatial-construction-review-regressions.test.mjs")
    regressions.write_text(
        regressions.read_text(encoding="utf-8")
        + '''


test("Construction visual proof reads the user-visible screenshot, not the transient default framebuffer", async () => {
  const { readFile } = await import("node:fs/promises");
  const probe = await readFile(
    new URL("../runtime/construction_demo_browser_probe.cjs", import.meta.url),
    "utf8",
  );
  const profile = JSON.parse(
    await readFile(
      new URL("../../.aura/runtime_profiles/construction_demo.v1.json", import.meta.url),
      "utf8",
    ),
  );
  assert.match(probe, /PNG\.sync\.read/);
  assert.match(probe, /snapshotCanvas/);
  assert.match(probe, /chromaticPixels/);
  assert.doesNotMatch(probe, /nonBackgroundSamples < 1/);
  for (const name of [
    "initial-canvas.png",
    "mode-MESH-canvas.png",
    "mode-SPLATS-canvas.png",
    "mode-HYBRID-canvas.png",
  ]) {
    assert.ok(profile.probe.required_artifacts.includes(name));
  }
});
''',
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
