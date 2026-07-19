import assert from "node:assert/strict";
import test from "node:test";

import { GaussianRenderer, describeGaussianAssets } from "../../aura_spatial_web/gaussian_renderer.js";
import { HeadlessRenderer } from "../../aura_spatial_web/headless_renderer.js";
import { planFixture, sceneFixture } from "./spatial-fixture.mjs";

function gaussianScene() {
  const scene = structuredClone(sceneFixture());
  scene.assets = [
    {
      asset_id: "asset:gaussian",
      asset_type: "GAUSSIAN_SPLAT",
      uri: "aura://assets/gaussian.spz",
      media_type: "application/vnd.spz",
      content_digest: `sha256:${"d".repeat(64)}`,
      byte_length: 48,
      frame_id: "frame:root",
      bounds_min: [0, 0, 0],
      bounds_max: [1, 1, 1],
      source_refs: ["fixture:gaussian"],
      truth_class: "DERIVED",
      immutable: true,
      metadata: { representation: "GAUSSIAN_SPLAT", projection_only: true },
    },
  ];
  scene.entities[0].asset_ids = ["asset:gaussian"];
  return scene;
}

function gaussianPlan(renderer = "HEADLESS") {
  const plan = structuredClone(planFixture(renderer));
  plan.scene_asset_count = 1;
  plan.scene_asset_bytes = 48;
  return plan;
}

function payload(count = 1) {
  return {
    asset_id: "asset:gaussian",
    source_digest: "d".repeat(64),
    positions: Array.from({ length: count }, (_, index) => [index, 0, 0]),
    rotations_xyzw: Array.from({ length: count }, () => [0, 0, 0, 1]),
    scales_xyz: Array.from({ length: count }, () => [1, 1, 1]),
    opacities: Array.from({ length: count }, () => 1),
    colors_rgba: Array.from({ length: count }, () => [255, 0, 255, 255]),
  };
}

test("Gaussian renderer retains the admitted presentation owner and headless fallback", async () => {
  let time = 0;
  const renderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    limits: { maxGpuBytes: 1024, maxDecodedBytes: 1024, maxFrameMs: 20 },
    now: () => time++,
  });
  await renderer.initialize(gaussianScene(), gaussianPlan(), [payload()]);
  const receipt = await renderer.present();
  assert.equal(receipt.renderer, "HEADLESS");
  assert.equal(receipt.representation, "ACCESSIBLE_HEADLESS_FALLBACK");
  assert.equal(receipt.splat_count, 1);
  assert.equal(receipt.renderer_authority, false);
  assert.equal(renderer.headlessProof().presentation_owner_retained, undefined);
  assert.deepEqual(renderer.headlessProof().deterministic_order, ["asset:gaussian"]);
  assert.equal((await renderer.dispose()).state, "DISPOSED");
});



test("Gaussian point-cloud fallback is executed rather than merely claimed", async () => {
  let fallbackResources;
  let tick = 0;
  const renderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    drawPointCloudPass: async (resources, context) => {
      fallbackResources = resources;
      assert.equal(context.projection_only, true);
    },
    limits: { maxGpuBytes: 1024, maxDecodedBytes: 1024, maxFrameMs: 20 },
    now: () => tick++,
  });
  await renderer.initialize(gaussianScene(), gaussianPlan(), [payload(2)]);
  const receipt = await renderer.present({ cameraPosition: [0, 0, 0] });
  assert.equal(receipt.representation, "POINT_CLOUD_FALLBACK");
  assert.equal(receipt.evidence_class, "MEASURED");
  assert.deepEqual([...fallbackResources.sorted_indices], [1, 0]);
  assert.equal(fallbackResources.positions.length, 6);
  assert.equal(fallbackResources.colors_rgba.length, 8);
});

test("Gaussian pass is replaceable, sorted, bounded, and honestly measured", async () => {
  let resources;
  let tick = 0;
  const renderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    drawGaussianPass: async (value, context) => {
      resources = value;
      assert.equal(context.renderer_authority, false);
    },
    limits: {
      maxVisibleSplats: 2,
      maxSortItems: 2,
      maxGpuBytes: 1024,
      maxDecodedBytes: 1024,
      maxFrameMs: 20,
    },
    now: () => tick++,
  });
  await renderer.initialize(gaussianScene(), gaussianPlan(), [payload(2)]);
  const receipt = await renderer.present({ cameraPosition: [0, 0, 0] });
  assert.equal(receipt.representation, "GAUSSIAN_SPLAT_PASS");
  assert.equal(receipt.evidence_class, "MEASURED");
  assert.deepEqual([...resources.sorted_indices], [1, 0]);
  assert.equal(renderer.status().representation_buffer_count, 1);
  assert.equal(renderer.markDeviceLost().state, "LOST");
  assert.equal(renderer.status().representation_buffer_count, 0);
});

test("Gaussian limits reject allocation, stale digest, invalid values, and cancellation before draw", async () => {
  const allocation = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    limits: { maxVisibleSplats: 1, maxGpuBytes: 52, maxDecodedBytes: 52, maxFrameMs: 20 },
    now: () => 0,
  });
  await assert.rejects(
    allocation.initialize(gaussianScene(), gaussianPlan(), [payload(2)]),
    /visible-splat budget/,
  );

  const stale = payload();
  stale.source_digest = "e".repeat(64);
  const staleRenderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    limits: { maxGpuBytes: 1024, maxDecodedBytes: 1024, maxFrameMs: 20 },
    now: () => 0,
  });
  await assert.rejects(staleRenderer.initialize(gaussianScene(), gaussianPlan(), [stale]), /digest/);

  const invalid = payload();
  invalid.scales_xyz[0][0] = -1;
  const invalidRenderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    limits: { maxGpuBytes: 1024, maxDecodedBytes: 1024, maxFrameMs: 20 },
    now: () => 0,
  });
  await assert.rejects(invalidRenderer.initialize(gaussianScene(), gaussianPlan(), [invalid]), /scale/);

  const controller = new AbortController();
  controller.abort();
  const cancelled = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    limits: { maxGpuBytes: 1024, maxDecodedBytes: 1024, maxFrameMs: 20 },
    now: () => 0,
  });
  await assert.rejects(
    cancelled.initialize(gaussianScene(), gaussianPlan(), [payload()], { signal: controller.signal }),
    /cancelled/,
  );

  const planBound = gaussianPlan();
  planBound.budget.max_asset_bytes = 64;
  const overPlan = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    limits: { maxGpuBytes: 64, maxDecodedBytes: 128, maxAllocationBytes: 128, maxFrameMs: 20 },
    now: () => 0,
  });
  await assert.rejects(
    overPlan.initialize(gaussianScene(), planBound, [payload()]),
    /allocation budget exceeds render plan/,
  );
});

test("Gaussian pass failure clears representation buffers and enters lost state", async () => {
  const renderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    drawGaussianPass: async () => {
      throw new Error("draw failed");
    },
    limits: { maxGpuBytes: 1024, maxDecodedBytes: 1024, maxFrameMs: 20 },
    now: () => 0,
  });
  await renderer.initialize(gaussianScene(), gaussianPlan(), [payload()]);
  await assert.rejects(renderer.present(), /draw failed/);
  assert.equal(renderer.status().state, "LOST");
  assert.equal(renderer.status().representation_buffer_count, 0);
});

test("accessible descriptions expose no action authority", () => {
  const descriptions = describeGaussianAssets([
    { asset_id: "asset:gaussian", count: 4 },
  ]);
  assert.equal(descriptions[0].splat_count, 4);
  assert.equal(descriptions[0].projection_only, true);
  assert.equal(descriptions[0].execution_authority, false);
});
