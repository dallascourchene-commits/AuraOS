import test from "node:test";
import assert from "node:assert/strict";

import { selectBrowserPresentationRenderer } from "../../aura_spatial_web/app.js";
import { planFixture } from "./spatial-fixture.mjs";

test("WebXR plans retain an admitted non-immersive presentation renderer", () => {
  const plan = planFixture("WEBXR");
  assert.equal(selectBrowserPresentationRenderer(plan), "ACCESSIBLE_2D");
});

test("WebXR plans fail closed without a presentation fallback", () => {
  const plan = { ...planFixture("WEBXR"), fallback_renderers: ["WEBXR"] };
  assert.throws(() => selectBrowserPresentationRenderer(plan), /fallback/);
});
