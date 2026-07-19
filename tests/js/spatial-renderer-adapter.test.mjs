import test from "node:test";
import assert from "node:assert/strict";

import { HeadlessRenderer } from "../../aura_spatial_web/headless_renderer.js";
import {
  validateRenderPlan,
  validateSceneProjection,
} from "../../aura_spatial_web/renderer_adapter.js";
import { planFixture, sceneFixture } from "./spatial-fixture.mjs";

test("headless adapter preserves authority and disposes", () => {
  const renderer = new HeadlessRenderer();
  renderer.initialize(sceneFixture(), planFixture());
  const receipt = renderer.present();
  assert.equal(receipt.renderer_authority, false);
  assert.equal(receipt.entity_count, 2);
  assert.equal(renderer.dispose().state, "DISPOSED");
});

test("scene validation rejects authority drift and malformed identities", () => {
  const authority = sceneFixture();
  authority.execution_authority = true;
  assert.throws(() => validateSceneProjection(authority), /authority/);

  const scale = sceneFixture();
  scale.entities[0].scale = [1, 0, 1];
  assert.throws(() => validateSceneProjection(scale), /positive/);

  const duplicateLink = sceneFixture();
  duplicateLink.links.push({ ...duplicateLink.links[0] });
  assert.throws(() => validateSceneProjection(duplicateLink), /duplicated/);

  const staleSchema = sceneFixture();
  staleSchema.schema_version = "AURA_SPATIAL_SCENE_SCHEMA_V1";
  assert.throws(() => validateSceneProjection(staleSchema), /version/);

  const unknownFrame = sceneFixture();
  unknownFrame.entities[0].frame_id = "frame:missing";
  assert.throws(() => validateSceneProjection(unknownFrame), /unknown frame/);

  const extraAuthority = sceneFixture();
  extraAuthority.automatic_merge = true;
  assert.throws(() => validateSceneProjection(extraAuthority), /keys mismatch/);
});

test("render plan validation rejects duplicate and inconsistent fallbacks", () => {
  const scene = validateSceneProjection(sceneFixture());
  const duplicate = planFixture("WEBGL2");
  duplicate.fallback_renderers = ["ACCESSIBLE_2D", "ACCESSIBLE_2D"];
  assert.throws(() => validateRenderPlan(duplicate, scene), /fallback/);

  const wrongCount = planFixture("WEBGL2");
  wrongCount.scene_entity_count = 1;
  assert.throws(() => validateRenderPlan(wrongCount, scene), /inconsistent/);

  const legacyBudget = planFixture("WEBGL2");
  legacyBudget.budget.max_cpu_milliseconds = 100;
  delete legacyBudget.budget.max_cpu_ms_per_frame;
  assert.throws(() => validateRenderPlan(legacyBudget, scene), /keys mismatch/);

  const extraAuthority = planFixture("WEBGL2");
  extraAuthority.automatic_merge = true;
  assert.throws(() => validateRenderPlan(extraAuthority, scene), /keys mismatch/);
});
