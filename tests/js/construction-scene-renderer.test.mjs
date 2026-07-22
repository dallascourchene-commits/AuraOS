import assert from "node:assert/strict";
import test from "node:test";

import {
  ConstructionMeshPass,
} from "../../aura_spatial_web/construction_mesh_pass.js";
import {
  ConstructionGaussianPass,
  deriveDegreeZeroCovariance,
} from "../../aura_spatial_web/webgl2_gaussian_pass.js";
import {
  ConstructionOverlayPass,
} from "../../aura_spatial_web/construction_overlay_pass.js";
import {
  ConstructionSceneRenderer,
} from "../../aura_spatial_web/construction_scene_renderer.js";
import { planFixture, sceneFixture } from "./spatial-fixture.mjs";

const REPRESENTATION_DIGEST =
  "9dc87e33a5190c866adbbc940603bbcde292ad3d1728d3cdae54f7adaa56c599";

function constructionFixture() {
  const scene = structuredClone(sceneFixture());
  scene.frames.push({
    frame_id: "frame:upper",
    parent_frame_id: "frame:root",
    handedness: "RIGHT_HANDED",
    up_axis: "Y_UP",
    unit_scale_meters: 1,
    translation: [0, 4, 0],
    rotation_xyzw: [0, 0, 0, 1],
    scale: [1, 1, 1],
    source_refs: ["fixture:upper"],
    truth_class: "PRESENTATION",
    projection_only: true,
  });
  scene.assets = [
    {
      asset_id: "asset:mesh",
      asset_type: "MESH",
      uri: "demo_assets/construction/mesh.glb",
      media_type: "model/gltf-binary",
      content_digest: `sha256:${"1".repeat(64)}`,
      byte_length: 128,
      frame_id: "frame:root",
      bounds_min: [0, 0, 0],
      bounds_max: [1, 1, 1],
      source_refs: ["fixture:mesh"],
      truth_class: "PRESENTATION",
      immutable: true,
      metadata: {},
    },
    {
      asset_id: "asset:plane",
      asset_type: "PLANE",
      uri: "demo_assets/construction/floor.svg",
      media_type: "image/svg+xml",
      content_digest: `sha256:${"2".repeat(64)}`,
      byte_length: 64,
      frame_id: "frame:root",
      bounds_min: [0, 0, 0],
      bounds_max: [1, 0, 1],
      source_refs: ["fixture:plane"],
      truth_class: "PRESENTATION",
      immutable: true,
      metadata: {},
    },
    {
      asset_id: "asset:splats",
      asset_type: "GAUSSIAN_SPLAT",
      uri: "demo_assets/construction/splats.spz",
      media_type: "application/vnd.aura.spz",
      content_digest: `sha256:${"3".repeat(64)}`,
      byte_length: 48,
      frame_id: "frame:upper",
      bounds_min: [0, 0, 0],
      bounds_max: [1, 1, 1],
      source_refs: ["fixture:splats"],
      truth_class: "PRESENTATION",
      immutable: true,
      metadata: {
        import_receipt_digest: "a".repeat(64),
        representation_digest: REPRESENTATION_DIGEST,
        representation_digest_version: "AURA_GAUSSIAN_REPRESENTATION_V1",
        representation_bytes_per_splat: 60,
        sh_degree: 0,
        gaussian_sh_degree: 0,
        gaussian_color_space: "SPZ_INTERNAL_WIDE_RGB",
      },
    },
  ];
  scene.entities[0].asset_ids = ["asset:mesh", "asset:plane"];
  scene.entities[0].metadata = {
    package_ref: "package-a",
    status: "BLOCKED",
    status_overlay: true,
  };
  scene.entities[1].frame_id = "frame:upper";
  scene.entities[1].asset_ids = ["asset:splats"];
  scene.entities[1].metadata = {
    admissible: true,
    candidate_ref: "candidate-b",
  };
  const plan = structuredClone(planFixture("HEADLESS"));
  plan.scene_entity_count = scene.entities.length;
  plan.scene_link_count = scene.links.length;
  plan.scene_asset_count = scene.assets.length;
  plan.scene_asset_bytes = scene.assets.reduce(
    (total, asset) => total + asset.byte_length,
    0,
  );
  return { scene, plan };
}

function gaussianPayload() {
  return {
    asset_id: "asset:splats",
    source_digest: "3".repeat(64),
    derived_asset_digest: "a".repeat(64),
    representation_digest: REPRESENTATION_DIGEST,
    sh_degree: 0,
    color_space: "SPZ_INTERNAL_WIDE_RGB",
    positions: [[0, 0, 0]],
    rotations_xyzw: [[0, 0, 0, 1]],
    scales_xyz: [[1, 1, 1]],
    opacities: [1],
    sh_coefficients: [[0, 0, 0]],
    colors_rgba: [[255, 0, 255, 255]],
  };
}

test("degree-zero covariance preserves identity-axis scale", () => {
  const covariance = deriveDegreeZeroCovariance(
    new Float32Array([0, 0, 0, 1]),
    new Float32Array([1, 2, 3]),
  );
  assert.deepEqual([...covariance], [1, 0, 0, 4, 0, 9]);
});

test("mesh pass admits exact scene mesh and disposes retained resources", async () => {
  const { scene, plan } = constructionFixture();
  let draws = 0;
  let drawDisposals = 0;
  let releases = 0;
  const mesh = new ConstructionMeshPass({
    drawMesh: async (_resource, context) => {
      draws += 1;
      assert.deepEqual(context.exploded_offset, [0, 3, 0]);
      assert.equal(context.renderer_authority, false);
      return () => {
        drawDisposals += 1;
      };
    },
    releaseMesh: async () => {
      releases += 1;
    },
  });
  mesh.initialize(scene, plan, [
    {
      asset_id: "asset:mesh",
      source_digest: "1".repeat(64),
      vertex_count: 3,
      index_count: 3,
      gpu_bytes: 256,
      bounds_min: [0, 0, 0],
      bounds_max: [1, 1, 1],
      resource: { vao: 1 },
    },
  ]);
  const receipt = await mesh.present({
    explodedOffsets: { "frame:root": [0, 3, 0] },
  });
  assert.equal(receipt.drawn_asset_count, 1);
  assert.equal(draws, 1);
  assert.equal((await mesh.dispose()).state, "DISPOSED");
  assert.equal(drawDisposals, 1);
  assert.equal(releases, 1);
});

test("Gaussian pass enforces degree zero, covariance, depth ordering, and cleanup", async () => {
  const { scene, plan } = constructionFixture();
  let covariance = null;
  let disposed = 0;
  const presentationRenderer = {
    kind: "HEADLESS",
    async initialize() {},
    async present() {
      return { renderer: "HEADLESS", outcome: "PRESENTED" };
    },
    async dispose() {
      return { state: "DISPOSED" };
    },
  };
  const gaussian = new ConstructionGaussianPass({
    presentationRenderer,
    drawGaussianPass: async (resources, context) => {
      covariance = [...resources.covariance_3d];
      assert.equal(context.depth_order, "BACK_TO_FRONT");
      assert.equal(context.depth_write, false);
      assert.deepEqual(context.exploded_offset, [0, 5, 0]);
      return () => {
        disposed += 1;
      };
    },
    now: () => 0,
  });
  await gaussian.initialize(scene, plan, [gaussianPayload()]);
  const receipt = await gaussian.present({
    explodedOffsets: { "frame:upper": [0, 5, 0] },
  });
  assert.deepEqual(covariance, [1, 0, 0, 1, 0, 1]);
  assert.equal(receipt.representation, "DEGREE_ZERO_GAUSSIAN_PASS");
  assert.equal(receipt.visible_splat_count, 1);
  assert.equal((await gaussian.dispose()).state, "DISPOSED");
  assert.equal(disposed, 1);
});

test("overlay pass provides deterministic accessible selection and picking", async () => {
  const { scene, plan } = constructionFixture();
  let disposed = 0;
  const overlays = new ConstructionOverlayPass({
    drawOverlays: async (rows) => {
      assert.deepEqual(rows.map((row) => row.kind), ["WORK_STATUS", "PROPOSAL"]);
      return () => {
        disposed += 1;
      };
    },
    hitTest: async () => "entity:a",
  });
  overlays.initialize(scene, plan);
  assert.equal(await overlays.pick(10, 20), "entity:a");
  const receipt = await overlays.present();
  assert.equal(receipt.selected_entity_id, "entity:a");
  assert.equal(overlays.accessibleRows()[0].status, "BLOCKED");
  assert.equal((await overlays.dispose()).state, "DISPOSED");
  assert.equal(disposed, 1);
});

function stubPass(name, calls) {
  return {
    visible: [],
    initialize() {
      calls.push(`${name}:initialize`);
      return { state: "INITIALIZED" };
    },
    setVisibleAssets(ids) {
      this.visible = [...ids].sort();
      calls.push(`${name}:visible:${this.visible.join(",")}`);
      return this.visible;
    },
    async present(options = {}) {
      calls.push(`${name}:present`);
      return {
        renderer: name,
        outcome: "PRESENTED",
        exploded_offsets: options.explodedOffsets || {},
      };
    },
    async pick() {
      return "entity:a";
    },
    accessibleRows() {
      return [{ entity_id: "entity:a", label: "Alpha" }];
    },
    async markDeviceLost() {
      calls.push(`${name}:lost`);
      return { state: "LOST" };
    },
    async dispose() {
      calls.push(`${name}:dispose`);
      return { state: "DISPOSED" };
    },
    status() {
      return { name, visible: this.visible };
    },
  };
}

test("scene renderer composes hybrid passes, storey isolation, explode, and reverse cleanup", async () => {
  const { scene, plan } = constructionFixture();
  const calls = [];
  const mesh = stubPass("mesh", calls);
  const gaussian = stubPass("gaussian", calls);
  const overlay = stubPass("overlay", calls);
  const renderer = new ConstructionSceneRenderer({
    meshPass: mesh,
    gaussianPass: gaussian,
    overlayPass: overlay,
  });
  await renderer.initialize(scene, plan, {
    meshPayloads: [{}],
    gaussianPayloads: [{}],
  });
  assert.equal(renderer.status().mode, "HYBRID");
  renderer.isolateStoreys(["frame:upper"]);
  assert.deepEqual(mesh.visible, []);
  assert.deepEqual(gaussian.visible, ["asset:splats"]);
  const storey = renderer.setExploded(true, 8);
  assert.deepEqual(storey.exploded_offsets["frame:upper"], [0, 0, 0]);
  const receipt = await renderer.present();
  assert.deepEqual(receipt.composition_order, [
    "MESH_DEPTH_PASS",
    "GAUSSIAN_ALPHA_PASS",
    "CONSTRUCTION_OVERLAY_PASS",
  ]);
  assert.equal(receipt.accessible_rows[0].entity_id, "entity:a");
  assert.equal((await renderer.pick(1, 2)), "entity:a");
  assert.equal((await renderer.dispose()).state, "DISPOSED");
  assert.deepEqual(calls.slice(-3), [
    "overlay:dispose",
    "gaussian:dispose",
    "mesh:dispose",
  ]);
});

test("scene renderer propagates cancellation without presenting passes", async () => {
  const { scene, plan } = constructionFixture();
  const calls = [];
  const renderer = new ConstructionSceneRenderer({
    meshPass: stubPass("mesh", calls),
    gaussianPass: stubPass("gaussian", calls),
    overlayPass: stubPass("overlay", calls),
  });
  await renderer.initialize(scene, plan, {
    meshPayloads: [{}],
    gaussianPayloads: [{}],
  });
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(
    renderer.present({ signal: controller.signal }),
    /cancelled/,
  );
  assert.equal(calls.some((value) => value.endsWith(":present")), false);
  await renderer.dispose();
});
