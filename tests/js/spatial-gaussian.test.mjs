import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";

import {
  GAUSSIAN_REPRESENTATION_DIGEST_VERSION,
  GaussianRenderer,
  describeGaussianAssets,
} from "../../aura_spatial_web/gaussian_renderer.js";
import { HeadlessRenderer } from "../../aura_spatial_web/headless_renderer.js";
import { planFixture, sceneFixture } from "./spatial-fixture.mjs";

const SOURCE_DIGEST = "d".repeat(64);
const RECEIPT_DIGEST = "a".repeat(64);

function representationDigest(value) {
  const coefficientCount = (value.sh_degree + 1) ** 2 * 3;
  const header = Buffer.alloc(9);
  header.writeUInt32LE(value.positions.length, 0);
  header.writeUInt8(value.sh_degree, 4);
  header.writeUInt32LE(coefficientCount, 5);
  const hash = createHash("sha256");
  hash.update(Buffer.from(`${GAUSSIAN_REPRESENTATION_DIGEST_VERSION}\0`, "ascii"));
  hash.update(header);
  for (const values of [
    value.positions,
    value.rotations_xyzw,
    value.scales_xyz,
    value.opacities.map((item) => [item]),
    value.sh_coefficients,
  ]) {
    for (const vector of values) {
      for (const component of vector) {
        const encoded = Buffer.alloc(4);
        encoded.writeFloatLE(component, 0);
        hash.update(encoded);
      }
    }
  }
  for (const color of value.colors_rgba) hash.update(Buffer.from(color));
  return hash.digest("hex");
}

function payload(count = 1) {
  const value = {
    asset_id: "asset:gaussian",
    source_digest: SOURCE_DIGEST,
    derived_asset_digest: RECEIPT_DIGEST,
    representation_digest: "0".repeat(64),
    sh_degree: 0,
    color_space: "SPZ_INTERNAL_WIDE_RGB",
    positions: Array.from({ length: count }, (_, index) => [index, 0, 0]),
    rotations_xyzw: Array.from({ length: count }, () => [0, 0, 0, 1]),
    scales_xyz: Array.from({ length: count }, () => [1, 1, 1]),
    opacities: Array.from({ length: count }, () => 1),
    sh_coefficients: Array.from({ length: count }, () => [0, 0, 0]),
    colors_rgba: Array.from({ length: count }, () => [255, 0, 255, 255]),
  };
  value.representation_digest = representationDigest(value);
  return value;
}

function gaussianScene(value = payload()) {
  const scene = structuredClone(sceneFixture());
  scene.assets = [
    {
      asset_id: "asset:gaussian",
      asset_type: "GAUSSIAN_SPLAT",
      uri: "aura://assets/gaussian.spz",
      media_type: "application/vnd.spz",
      content_digest: `sha256:${SOURCE_DIGEST}`,
      byte_length: 48,
      frame_id: "frame:root",
      bounds_min: [0, 0, 0],
      bounds_max: [1, 1, 1],
      source_refs: ["fixture:gaussian"],
      truth_class: "DERIVED",
      immutable: true,
      metadata: {
        import_receipt_digest: RECEIPT_DIGEST,
        representation_digest: value.representation_digest,
        representation_digest_version: GAUSSIAN_REPRESENTATION_DIGEST_VERSION,
        representation_bytes_per_splat: 48 + ((value.sh_degree + 1) ** 2 * 3 * 4),
        sh_degree: value.sh_degree,
        gaussian_sh_degree: value.sh_degree,
        gaussian_color_space: value.color_space,
        projection_only: true,
      },
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

function limits(overrides = {}) {
  return {
    maxGpuBytes: 1024 * 1024,
    maxDecodedBytes: 1024 * 1024,
    maxAllocationBytes: 1024 * 1024,
    maxFrameMs: 20,
    ...overrides,
  };
}

test("Gaussian renderer retains the admitted presentation owner and headless fallback", async () => {
  let time = 0;
  const value = payload();
  const renderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    limits: limits(),
    now: () => time++,
  });
  await renderer.initialize(gaussianScene(value), gaussianPlan(), [value]);
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
  const value = payload(2);
  const renderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    drawPointCloudPass: async (resources, context) => {
      fallbackResources = resources;
      assert.equal(context.projection_only, true);
    },
    limits: limits(),
    now: () => tick++,
  });
  await renderer.initialize(gaussianScene(value), gaussianPlan(), [value]);
  const receipt = await renderer.present({ cameraPosition: [0, 0, 0] });
  assert.equal(receipt.representation, "POINT_CLOUD_FALLBACK");
  assert.equal(receipt.evidence_class, "MEASURED");
  assert.deepEqual([...fallbackResources.sorted_indices], [1, 0]);
  assert.equal(fallbackResources.positions.length, 6);
  assert.equal(fallbackResources.colors_rgba.length, 8);
});

test("Gaussian pass is replaceable, sorted, bounded, and releases its resource lease", async () => {
  let resources;
  let disposed = 0;
  let tick = 0;
  const value = payload(2);
  const renderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    drawGaussianPass: async (renderResources, context) => {
      resources = renderResources;
      assert.equal(context.renderer_authority, false);
      return { dispose: async () => disposed++ };
    },
    limits: limits({ maxVisibleSplats: 2, maxSortItems: 2 }),
    now: () => tick++,
  });
  await renderer.initialize(gaussianScene(value), gaussianPlan(), [value]);
  const receipt = await renderer.present({ cameraPosition: [0, 0, 0] });
  assert.equal(receipt.representation, "GAUSSIAN_SPLAT_PASS");
  assert.equal(receipt.evidence_class, "MEASURED");
  assert.deepEqual([...resources.sorted_indices], [1, 0]);
  assert.equal(renderer.status().representation_buffer_count, 1);
  assert.equal(renderer.status().representation_disposer_count, 1);
  assert.equal((await renderer.markDeviceLost()).state, "LOST");
  assert.equal(disposed, 1);
  assert.equal(renderer.status().representation_buffer_count, 0);
});

test("Gaussian limits reject source-heap undercount, stale representation, Float32 overflow, and bad values", async () => {
  const two = payload(2);
  const visible = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    limits: limits({ maxVisibleSplats: 1 }),
    now: () => 0,
  });
  await assert.rejects(visible.initialize(gaussianScene(two), gaussianPlan(), [two]), /visible-splat budget/);

  const one = payload();
  const allocation = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    limits: limits({ maxAllocationBytes: 2800 }),
    now: () => 0,
  });
  await assert.rejects(
    allocation.initialize(gaussianScene(one), gaussianPlan(), [one]),
    /allocation budget exceeded before buffer creation/,
  );

  const staleSource = payload();
  staleSource.source_digest = "e".repeat(64);
  const staleSourceRenderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    limits: limits(),
    now: () => 0,
  });
  await assert.rejects(
    staleSourceRenderer.initialize(gaussianScene(staleSource), gaussianPlan(), [staleSource]),
    /source digest/,
  );

  const substituted = payload();
  substituted.positions[0][0] = 0.5;
  const substitutedRenderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    limits: limits(),
    now: () => 0,
  });
  await assert.rejects(
    substitutedRenderer.initialize(gaussianScene(substituted), gaussianPlan(), [substituted]),
    /does not match decoded attributes/,
  );

  const overflow = payload();
  overflow.positions[0][0] = Number.MAX_VALUE;
  const overflowRenderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    limits: limits(),
    now: () => 0,
  });
  await assert.rejects(
    overflowRenderer.initialize(gaussianScene(overflow), gaussianPlan(), [overflow]),
    /Float32/,
  );

  const invalid = payload();
  invalid.scales_xyz[0][0] = -1;
  const invalidRenderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    limits: limits(),
    now: () => 0,
  });
  await assert.rejects(invalidRenderer.initialize(gaussianScene(invalid), gaussianPlan(), [invalid]), /scale/);
});

test("Gaussian cancellation is rechecked after async draw and cannot emit PRESENTED", async () => {
  const controller = new AbortController();
  let disposed = 0;
  const value = payload();
  const renderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    drawGaussianPass: async () => {
      controller.abort();
      return { dispose: async () => disposed++ };
    },
    limits: limits(),
    now: () => 0,
  });
  await renderer.initialize(gaussianScene(value), gaussianPlan(), [value]);
  await assert.rejects(renderer.present({ signal: controller.signal }), /cancelled/);
  assert.equal(renderer.status().state, "LOST");
  assert.equal(disposed, 1);
});

test("Gaussian cancellation before initialization and plan ceilings fail closed", async () => {
  const controller = new AbortController();
  controller.abort();
  const value = payload();
  const cancelled = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    limits: limits(),
    now: () => 0,
  });
  await assert.rejects(
    cancelled.initialize(gaussianScene(value), gaussianPlan(), [value], { signal: controller.signal }),
    /cancelled/,
  );

  const planBound = gaussianPlan();
  planBound.budget.max_asset_bytes = 64;
  const overPlan = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    limits: limits({ maxGpuBytes: 64, maxDecodedBytes: 128, maxAllocationBytes: 128 }),
    now: () => 0,
  });
  await assert.rejects(
    overPlan.initialize(gaussianScene(value), planBound, [value]),
    /allocation budget exceeds render plan/,
  );
});

test("Gaussian pass failure clears representation buffers and enters lost state", async () => {
  const value = payload();
  const renderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    drawGaussianPass: async () => {
      throw new Error("draw failed");
    },
    limits: limits(),
    now: () => 0,
  });
  await renderer.initialize(gaussianScene(value), gaussianPlan(), [value]);
  await assert.rejects(renderer.present(), /draw failed/);
  assert.equal(renderer.status().state, "LOST");
  assert.equal(renderer.status().representation_buffer_count, 0);
});

test("Gaussian pass without disposal evidence is rejected and cleaned up", async () => {
  const value = payload();
  const renderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    drawGaussianPass: async () => undefined,
    limits: limits(),
    now: () => 0,
  });
  await renderer.initialize(gaussianScene(value), gaussianPlan(), [value]);
  await assert.rejects(renderer.present(), /disposal handle/);
  assert.equal(renderer.status().state, "LOST");
  assert.equal(renderer.status().representation_buffer_count, 0);
});

test("accessible descriptions expose no action authority", () => {
  const descriptions = describeGaussianAssets([{ asset_id: "asset:gaussian", count: 4 }]);
  assert.equal(descriptions[0].splat_count, 4);
  assert.equal(descriptions[0].projection_only, true);
  assert.equal(descriptions[0].execution_authority, false);
});

test("Gaussian pass carries bounded higher-order spherical harmonics and exact color space", async () => {
  let resources;
  let context;
  const value = payload();
  value.sh_degree = 2;
  value.color_space = "lin_rec709_display";
  value.sh_coefficients = [Array.from({ length: 27 }, (_, index) => index / 27)];
  value.representation_digest = representationDigest(value);
  const renderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    drawGaussianPass: async (renderResources, renderContext) => {
      resources = renderResources;
      context = renderContext;
      return { dispose: async () => {} };
    },
    limits: limits({ maxGpuBytes: 64 * 1024, maxDecodedBytes: 64 * 1024, maxAllocationBytes: 64 * 1024 }),
    now: (() => {
      let tick = 0;
      return () => tick++;
    })(),
  });
  await renderer.initialize(gaussianScene(value), gaussianPlan(), [value]);
  const receipt = await renderer.present();
  assert.equal(resources.sh_coefficients.length, 27);
  assert.equal(context.sh_degree, 2);
  assert.equal(context.color_space, "lin_rec709_display");
  assert.equal(receipt.gpu_bytes, 156);
  assert.ok(receipt.allocation_bytes >= 156);
  await renderer.dispose();
});

test("Gaussian aggregate preflight rejects before nested reads and typed-array materialization", async () => {
  const first = payload();
  const second = payload();
  second.asset_id = "asset:gaussian:second";
  let nestedReads = 0;
  for (const value of [first, second]) {
    const original = value.positions[0][0];
    Object.defineProperty(value.positions[0], 0, {
      configurable: true,
      enumerable: true,
      get() {
        nestedReads += 1;
        return original;
      },
    });
  }

  const scene = gaussianScene(first);
  scene.assets.push({ ...structuredClone(scene.assets[0]), asset_id: second.asset_id });
  scene.entities[0].asset_ids = [first.asset_id, second.asset_id];
  const plan = gaussianPlan();
  plan.scene_asset_count = 2;
  plan.scene_asset_bytes = 96;
  const renderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    limits: limits({ maxAllocationBytes: 5_000 }),
    now: () => 0,
  });

  await assert.rejects(
    renderer.initialize(scene, plan, [first, second]),
    /aggregate allocation budget exceeded before materialization/,
  );
  assert.equal(nestedReads, 0);
});

test("Gaussian initialization rejection disposes partial presentation resources and enters LOST", async () => {
  const value = payload();
  let disposed = 0;
  const presentationRenderer = {
    kind: "PARTIAL_TEST",
    async initialize() {
      throw new Error("partial initialization failed");
    },
    async present() {
      throw new Error("not reachable");
    },
    async dispose() {
      disposed += 1;
    },
  };
  const renderer = new GaussianRenderer({
    presentationRenderer,
    limits: limits(),
    now: () => 0,
  });

  await assert.rejects(
    renderer.initialize(gaussianScene(value), gaussianPlan(), [value]),
    /partial initialization failed/,
  );
  assert.equal(disposed, 1);
  assert.equal(renderer.status().state, "LOST");
});

