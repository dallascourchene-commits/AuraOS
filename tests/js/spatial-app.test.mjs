import test from "node:test";
import assert from "node:assert/strict";

import {
  bootSpatialApp,
  selectBrowserPresentationRenderer,
} from "../../aura_spatial_web/app.js";
import { planFixture, sceneFixture } from "./spatial-fixture.mjs";

test("WebXR plans retain an admitted non-immersive presentation renderer", () => {
  const plan = planFixture("WEBXR");
  assert.equal(selectBrowserPresentationRenderer(plan), "ACCESSIBLE_2D");
});

test("WebXR plans fail closed without a presentation fallback", () => {
  const plan = { ...planFixture("WEBXR"), fallback_renderers: ["WEBXR"] };
  assert.throws(() => selectBrowserPresentationRenderer(plan), /fallback/);
});


test("boot falls back when the selected renderer cannot initialize", async () => {
  const disposed = [];
  function renderer(kind, { fail = false } = {}) {
    return {
      async initialize() {
        if (fail) throw new Error(`${kind} unavailable`);
      },
      present() {
        return { renderer: kind, outcome: "PRESENTED" };
      },
      dispose() {
        disposed.push(kind);
        return { renderer: kind, disposed: true };
      },
    };
  }
  const result = await bootSpatialApp({
    envelope: {
      scene: sceneFixture(),
      render_plan: planFixture("WEBGL2"),
    },
    sessionId: "spatial-session:test",
    accessibleContainer: {},
    rendererFactories: {
      WEBGL2: () => renderer("WEBGL2", { fail: true }),
      ACCESSIBLE_2D: () => renderer("ACCESSIBLE_2D"),
      HEADLESS: () => renderer("HEADLESS"),
    },
  });

  assert.equal(result.presentation_renderer, "ACCESSIBLE_2D");
  assert.deepEqual(disposed, ["WEBGL2"]);
  await result.dispose();
  assert.deepEqual(disposed, ["WEBGL2", "ACCESSIBLE_2D"]);
});
