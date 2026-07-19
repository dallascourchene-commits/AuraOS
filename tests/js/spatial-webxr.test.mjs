import test from "node:test";
import assert from "node:assert/strict";

import { WebXRSessionAdapter } from "../../aura_spatial_web/webxr_session.js";
import { planFixture, sceneFixture } from "./spatial-fixture.mjs";

test("webxr requires explicit user gesture and bounded reference spaces", async () => {
  let ended = false;
  const xr = {
    isSessionSupported: async () => true,
    requestSession: async () => ({
      addEventListener() {},
      end: async () => {
        ended = true;
      },
    }),
  };
  const adapter = new WebXRSessionAdapter({ xr });
  await assert.rejects(
    () =>
      adapter.start({
        userActivation: false,
        scene: sceneFixture(),
        renderPlan: planFixture("WEBXR"),
      }),
    /explicit/,
  );
  await assert.rejects(
    () =>
      adapter.start({
        userActivation: true,
        scene: sceneFixture(),
        renderPlan: planFixture("WEBXR"),
        referenceSpaceType: "bounded-floor",
      }),
    /reference space/,
  );
  const started = await adapter.start({
    userActivation: true,
    scene: sceneFixture(),
    renderPlan: planFixture("WEBXR"),
  });
  assert.equal(started.raw_sensor_data_retained, false);
  await adapter.end();
  assert.equal(ended, true);
  assert.equal(adapter.sceneDigest, null);
});
