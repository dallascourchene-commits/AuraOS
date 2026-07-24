from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"final-fix anchor missing: {label}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    wrapper = Path("scripts/aura_architecture_harness.py")
    replace_once(
        wrapper,
        "from __future__ import annotations\n",
        "from __future__ import annotations\n\n# ruff: noqa: E402 -- repository bootstrap must precede root-level imports.\n",
        "wrapper bootstrap lint boundary",
    )
    replace_once(
        wrapper,
        '''for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

_ORIGINAL_DOCTOR = _core.doctor
''',
        '''for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

# Explicit aliases preserve the dynamic compatibility seam for static analysis.
DEFAULT_INLINE_MAX_BYTES = _core.DEFAULT_INLINE_MAX_BYTES
_read_git_blob = _core._read_git_blob

_ORIGINAL_DOCTOR = _core.doctor
''',
        "wrapper compatibility aliases",
    )

    harness = Path("scripts/aura_runtime_refactor_harness.py")
    replace_once(
        harness,
        '''    verification_ok = all(
        item["returncode"] == 0 for item in verification_receipts
    )
    artifacts_ok = all(
        item["present"] and item["within_size_limit"]
        for item in artifacts
    )
    ok = (
        readiness.get("ok") is True
        and probe_receipt.get("returncode") == 0
        and success_ok
        and artifacts_ok
        and verification_ok
        and tree_unchanged
    )
''',
        '''    verification_ok = all(
        item["returncode"] == 0 for item in verification_receipts
    )
    command_capture_ok = (
        probe_receipt.get("capture_complete") is True
        and all(
            item.get("capture_complete") is True
            for item in environment_receipts
        )
        and all(
            item.get("capture_complete") is True
            for item in verification_receipts
        )
    )
    server_capture_ok = server_output.get("capture_complete") is True
    artifacts_ok = all(
        item["present"] and item["within_size_limit"]
        for item in artifacts
    )
    ok = (
        readiness.get("ok") is True
        and probe_receipt.get("returncode") == 0
        and success_ok
        and artifacts_ok
        and verification_ok
        and command_capture_ok
        and server_capture_ok
        and tree_unchanged
    )
''',
        "capture completion gate",
    )
    replace_once(
        harness,
        '''        "verification": verification_receipts,
        "artifacts": artifacts,
        "server_output": server_output,
''',
        '''        "verification": verification_receipts,
        "command_capture_complete": command_capture_ok,
        "server_capture_complete": server_capture_ok,
        "artifacts": artifacts,
        "server_output": server_output,
''',
        "capture completion receipt",
    )

    probe = Path("tests/runtime/construction_demo_browser_probe.cjs")
    replace_once(
        probe,
        '''    const canvas = document.querySelector("#construction-canvas");
    const gl = canvas?.getContext?.("webgl2");
    return {
''',
        '''    const canvas = document.querySelector("#construction-canvas");
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
''',
        "bounded WebGL visual sampler",
    )
    replace_once(
        probe,
        '''      webgl2Available: Boolean(gl),
      webglContextLost: Boolean(gl?.isContextLost?.()),
      bodyText: document.body.innerText.slice(0, 6000),
''',
        '''      webgl2Available: Boolean(gl),
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
''',
        "visual evidence receipt",
    )
    replace_once(
        probe,
        '''async function exerciseManualControls(page, receipts) {
''',
        '''function assertVisiblePresentation(receipt, mode) {
  const webgl = receipt.visualEvidence?.webgl;
  if (!webgl || webgl.samples < 1 || webgl.nonBackgroundSamples < 1 || webgl.error !== 0) {
    throw new Error(`${mode} presentation produced no verified WebGL pixels`);
  }
  if (["MESH", "HYBRID"].includes(mode) && receipt.visualEvidence.wireframeLines < 12) {
    throw new Error(`${mode} presentation produced no verified wireframe geometry`);
  }
}


async function exerciseManualControls(page, receipts) {
''',
        "visual assertion helper",
    )
    replace_once(
        probe,
        '''    await page.waitForTimeout(150);
    receipts.push(await inspectPage(page, `after-mode-${mode}`));
''',
        '''    await page.waitForTimeout(150);
    const receipt = await inspectPage(page, `after-mode-${mode}`);
    receipts.push(receipt);
    if (!String(receipt.sceneState || "").startsWith(`${mode} · PRESENTED`)) {
      throw new Error(`${mode} representation did not become active`);
    }
    assertVisiblePresentation(receipt, mode);
''',
        "representation visual proof",
    )
    replace_once(
        probe,
        '''        "--use-gl=swiftshader",
        "--disable-gpu-sandbox",
''',
        '''        "--use-gl=swiftshader",
        "--enable-unsafe-swiftshader",
        "--disable-gpu-sandbox",
''',
        "trusted loopback SwiftShader opt-in",
    )
    replace_once(
        probe,
        '''    if (initial.storeyButtons < 1) {
      throw new Error("Construction browser rendered no storey controls");
    }
    await snapshot(page, "initial");
''',
        '''    if (initial.storeyButtons < 1) {
      throw new Error("Construction browser rendered no storey controls");
    }
    assertVisiblePresentation(initial, "HYBRID");
    await snapshot(page, "initial");
''',
        "initial visual proof",
    )
    replace_once(
        probe,
        '''    const finalTourStatus = String(finalState?.tourStatus || "");
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
''',
        '''    const finalTourStatus = String(finalState?.tourStatus || "");
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
''',
        "intentional dissolution context boundary",
    )

    harness_tests = Path("tests/test_aura_runtime_refactor_harness.py")
    replace_once(
        harness_tests,
        '''    assert result["server_output"]["stdout"]["truncated"] is True
    assert (output / "server.stdout.log").stat().st_size <= MAX_OUTPUT_BYTES
''',
        '''    assert result["server_output"]["stdout"]["truncated"] is True
    assert result["server_capture_complete"] is True
    assert result["command_capture_complete"] is True
    assert (output / "server.stdout.log").stat().st_size <= MAX_OUTPUT_BYTES
''',
        "capture completion test assertions",
    )

    regressions = Path("tests/js/spatial-construction-review-regressions.test.mjs")
    regressions.write_text(
        regressions.read_text(encoding="utf-8")
        + '''


test("Construction browser proof requires visible modes and intentional dissolution", async () => {
  const { readFile } = await import("node:fs/promises");
  const probe = await readFile(
    new URL("../runtime/construction_demo_browser_probe.cjs", import.meta.url),
    "utf8",
  );
  assert.match(probe, /nonBackgroundSamples/);
  assert.match(probe, /wireframeLines/);
  assert.match(probe, /representation did not become active/);
  assert.match(probe, /finalSceneState === "Dissolved"/);
  assert.match(probe, /unexpectedContextLoss/);
  assert.match(probe, /enable-unsafe-swiftshader/);
});
''',
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
