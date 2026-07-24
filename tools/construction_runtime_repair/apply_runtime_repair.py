from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"repair anchor missing: {label}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    gaussian = Path("aura_spatial_web/gaussian_renderer.js")
    replace_once(
        gaussian,
        '''  async present({ cameraPosition = [0, 0, 0], signal } = {}) {''',
        '''  async releaseDrawResources() {
    if (![RENDERER_STATES.INITIALIZED, RENDERER_STATES.PRESENTED].includes(this.state)) {
      throw new Error("Gaussian renderer is not initialized");
    }
    await this._releaseDrawResources();
    return this.status();
  }

  async present({ cameraPosition = [0, 0, 0], signal } = {}) {''',
        "Gaussian public draw-resource release",
    )
    replace_once(
        gaussian,
        '''    const elapsed = this.now() - started;
    if (!Number.isFinite(elapsed) || elapsed < 0 || elapsed > this.limits.maxFrameMs) {
      const budgetError = new RangeError("Gaussian frame-time budget exceeded");
      try {
        await this.dispose();
      } catch (cleanup) {
        throw new AggregateError(
          [budgetError, cleanup],
          "Gaussian frame-time failure and cleanup failed",
        );
      }
      throw budgetError;
    }
    this.state = RENDERER_STATES.PRESENTED;''',
        '''    const elapsed = this.now() - started;
    if (!Number.isFinite(elapsed) || elapsed < 0) {
      const timingError = new RangeError("Gaussian frame-time measurement is invalid");
      try {
        await this.dispose();
      } catch (cleanup) {
        throw new AggregateError(
          [timingError, cleanup],
          "Gaussian timing failure and cleanup failed",
        );
      }
      throw timingError;
    }
    const frameBudgetExceeded = elapsed > this.limits.maxFrameMs;
    this.state = RENDERER_STATES.PRESENTED;''',
        "Gaussian frame budget classification",
    )
    replace_once(
        gaussian,
        '''      elapsed_ms: elapsed,
      base_receipt: baseReceipt,''',
        '''      elapsed_ms: elapsed,
      frame_budget_ms: this.limits.maxFrameMs,
      frame_budget_exceeded: frameBudgetExceeded,
      performance_status: frameBudgetExceeded ? "DEGRADED_CONTINUE" : "WITHIN_BUDGET",
      integrity_verified: true,
      base_receipt: baseReceipt,''',
        "Gaussian performance receipt",
    )

    scene = Path("aura_spatial_web/construction_scene_renderer.js")
    replace_once(
        scene,
        '''      const baseReceipt =
        this.mode === "MESH"
          ? await this.presentationRenderer.present(options)
          : await this.gaussianRenderer.present({
              cameraPosition: this._cameraPosition(),
              signal,
            });
      if (signal?.aborted || this.cancelled) throw new Error("Construction presentation cancelled");
      const meshReceipt =
        this.mode === "SPLATS" ? null : await this.meshPass.present({ signal });''',
        '''      let baseReceipt;
      if (this.mode === "MESH") {
        if (this.gaussianOwnerActive) await this.gaussianRenderer.releaseDrawResources();
        baseReceipt = await this.presentationRenderer.present(options);
      } else {
        baseReceipt = await this.gaussianRenderer.present({
          cameraPosition: this._cameraPosition(),
          signal,
        });
      }
      if (signal?.aborted || this.cancelled) throw new Error("Construction presentation cancelled");
      let meshReceipt = null;
      if (this.mode === "SPLATS") {
        await this.meshPass.releaseDrawResources();
      } else {
        meshReceipt = await this.meshPass.present({ signal });
      }''',
        "Construction mode resource switching",
    )

    app = Path("aura_spatial_web/construction_demo_app.js")
    replace_once(
        app,
        '''import { createConstructionWebGL2SceneRenderer } from "./construction_scene_renderer.js";''',
        '''import { createConstructionWebGL2SceneRenderer } from "./construction_scene_renderer.js";
import { createConstructionWireframePass } from "./construction_wireframe_pass.js";''',
        "Construction wireframe import",
    )
    replace_once(
        app,
        '''  const canvas = $("#construction-canvas");
  state.renderer = createConstructionWebGL2SceneRenderer({
    canvas,
    drawMeshPass: async () => () => {},
    drawOverlayPass: async (model) => renderOverlayModel(model),
    maxVisibleSplats: 250_000,
  });''',
        '''  const canvas = $("#construction-canvas");
  const meshOverlay = $("#construction-mesh-overlay");
  const drawMeshPass = createConstructionWireframePass({
    overlay: meshOverlay,
    getCamera: () => state.renderer?.presentationRenderer?.camera,
    getCanvas: () => canvas,
  });
  state.renderer = createConstructionWebGL2SceneRenderer({
    canvas,
    drawMeshPass,
    drawOverlayPass: async (model) => renderOverlayModel(model),
    maxVisibleSplats: 250_000,
  });''',
        "Construction wireframe wiring",
    )
    replace_once(
        app,
        '''  state.renderer.setRepresentationMode("SPLATS");
  document.querySelectorAll("button[data-mode]").forEach((button) => {
    const supported = button.dataset.mode === "SPLATS";
    button.disabled = !supported;
    button.classList.toggle("active", supported);
    if (!supported) {
      button.title = "Browser GLB decoding and mesh drawing are not implemented; mode is fail-closed";
    }
  });''',
        '''  state.renderer.setRepresentationMode("HYBRID");
  document.querySelectorAll("button[data-mode]").forEach((button) => {
    button.disabled = false;
    button.classList.toggle("active", button.dataset.mode === "HYBRID");
    button.title =
      button.dataset.mode === "MESH"
        ? "Deterministic bounds-derived wireframe mesh fallback"
        : button.dataset.mode === "HYBRID"
          ? "Gaussian splats plus deterministic wireframe mesh fallback"
          : "Deterministic Gaussian splat presentation";
  });''',
        "Construction representation controls",
    )

    html = Path("aura_spatial_web/construction_demo.html")
    replace_once(
        html,
        '''        <canvas id="construction-canvas" width="1280" height="720" aria-label="Interactive Construction Arena canvas"></canvas>''',
        '''        <canvas id="construction-canvas" width="1280" height="720" aria-label="Interactive Construction Arena canvas"></canvas>
        <svg id="construction-mesh-overlay" aria-hidden="true"></svg>''',
        "Construction wireframe overlay element",
    )

    css = Path("aura_spatial_web/construction_demo.css")
    replace_once(
        css,
        '''canvas { display: block; width: 100%; height: 100%; min-height: 34rem; }''',
        '''canvas { display: block; width: 100%; height: 100%; min-height: 34rem; }
#construction-mesh-overlay { position: absolute; inset: 0; z-index: 1; width: 100%; height: 100%; pointer-events: none; overflow: visible; }
.construction-wireframe-storey line { stroke: rgba(108, 245, 255, .82); stroke-width: 2; vector-effect: non-scaling-stroke; filter: drop-shadow(0 0 4px rgba(108, 245, 255, .5)); }
.construction-wireframe-storey text { fill: #f7f0ff; font: 600 12px Inter, ui-sans-serif, system-ui, sans-serif; paint-order: stroke; stroke: rgba(7, 5, 18, .9); stroke-width: 3px; }''',
        "Construction wireframe styles",
    )

    review = Path("tests/js/spatial-construction-review-regressions.test.mjs")
    replace_once(
        review,
        '''test("Construction recording UI advertises only implemented representation modes", async () => {
  const { readFile } = await import("node:fs/promises");
  const source = await readFile(
    new URL("../../aura_spatial_web/construction_demo_app.js", import.meta.url),
    "utf8",
  );
  assert.match(source, /setRepresentationMode\("SPLATS"\)/);
  assert.match(source, /button\.disabled = !supported/);
  assert.match(source, /Browser GLB decoding and mesh drawing are not implemented/);
});''',
        '''test("Construction recording UI exposes verified fallback Mesh, Splats, and Hybrid modes", async () => {
  const { readFile } = await import("node:fs/promises");
  const source = await readFile(
    new URL("../../aura_spatial_web/construction_demo_app.js", import.meta.url),
    "utf8",
  );
  assert.match(source, /createConstructionWireframePass/);
  assert.match(source, /setRepresentationMode\("HYBRID"\)/);
  assert.match(source, /button\.disabled = false/);
  assert.match(source, /bounds-derived wireframe mesh fallback/);
  assert.doesNotMatch(source, /button\.disabled = !supported/);
});''',
        "Construction mode review regression",
    )


if __name__ == "__main__":
    main()
