import assert from "node:assert/strict";
import test from "node:test";

import { buildAccessibleSceneModel } from "../../aura_spatial_web/accessibility.js";
import { GaussianRenderer } from "../../aura_spatial_web/gaussian_renderer.js";
import { HeadlessRenderer } from "../../aura_spatial_web/headless_renderer.js";
import { validateSceneProjection } from "../../aura_spatial_web/renderer_adapter.js";
import { planFixture, sceneFixture } from "./spatial-fixture.mjs";

function mixedFixture() {
  const scene = structuredClone(sceneFixture());
  scene.assets = [
    {
      asset_id: "asset:mesh",
      asset_type: "MESH",
      uri: "aura://assets/mesh.gltf",
      media_type: "model/gltf+json",
      content_digest: `sha256:${"1".repeat(64)}`,
      byte_length: 128,
      frame_id: "frame:root",
      bounds_min: [0, 0, 0],
      bounds_max: [1, 1, 0],
      source_refs: ["fixture:mesh"],
      truth_class: "DERIVED",
      immutable: true,
      metadata: {},
    },
    {
      asset_id: "asset:points",
      asset_type: "POINT_CLOUD",
      uri: "aura://assets/points.ply",
      media_type: "application/vnd.ply",
      content_digest: `sha256:${"2".repeat(64)}`,
      byte_length: 64,
      frame_id: "frame:root",
      bounds_min: [0, 0, 0],
      bounds_max: [1, 1, 1],
      source_refs: ["fixture:points"],
      truth_class: "DERIVED",
      immutable: true,
      metadata: {},
    },
    {
      asset_id: "asset:splats",
      asset_type: "GAUSSIAN_SPLAT",
      uri: "aura://assets/splats.spz",
      media_type: "application/vnd.spz",
      content_digest: `sha256:${"3".repeat(64)}`,
      byte_length: 48,
      frame_id: "frame:root",
      bounds_min: [0, 0, 0],
      bounds_max: [1, 1, 1],
      source_refs: ["fixture:splats"],
      truth_class: "DERIVED",
      immutable: true,
      metadata: {
        import_receipt_digest: "4".repeat(64),
        gaussian_sh_degree: 0,
        gaussian_color_space: "SPZ_INTERNAL_WIDE_RGB",
      },
    },
  ];
  scene.entities[0].asset_ids = ["asset:splats", "asset:mesh", "asset:points"];
  const plan = structuredClone(planFixture("HEADLESS"));
  plan.scene_asset_count = 3;
  plan.scene_asset_bytes = 240;
  return { scene, plan };
}

test("mixed topology, mesh, points, and splats preserve deterministic identity and accessible selection", () => {
  const { scene } = mixedFixture();
  const validated = validateSceneProjection(scene);
  assert.deepEqual(validated.assets.map((asset) => asset.asset_id), [
    "asset:mesh",
    "asset:points",
    "asset:splats",
  ]);
  assert.deepEqual(validated.entities[0].asset_ids, [
    "asset:mesh",
    "asset:points",
    "asset:splats",
  ]);
  const accessible = buildAccessibleSceneModel(scene);
  assert.equal(accessible.rows[0].selectable, true);
  assert.equal(accessible.renderer_authority, false);
  assert.equal(accessible.execution_authority, false);
});

test("mixed scene Gaussian layer uses point/headless fallback without changing presentation ownership", async () => {
  const { scene, plan } = mixedFixture();
  let fallbackDrawn = 0;
  const renderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    drawPointCloudPass: async (resources) => {
      fallbackDrawn += resources.sorted_indices.length;
    },
    now: () => 0,
  });
  await renderer.initialize(scene, plan, [
    {
      asset_id: "asset:splats",
      source_digest: "3".repeat(64),
      derived_asset_digest: "4".repeat(64),
      positions: [[0, 0, 0]],
      rotations_xyzw: [[0, 0, 0, 1]],
      scales_xyz: [[1, 1, 1]],
      opacities: [1],
      colors_rgba: [[255, 0, 255, 255]],
      sh_degree: 0,
      sh_coefficients: [[1, 0, 1]],
      color_space: "SPZ_INTERNAL_WIDE_RGB",
    },
  ]);
  const receipt = await renderer.present();
  assert.equal(receipt.renderer, "HEADLESS");
  assert.equal(receipt.representation, "POINT_CLOUD_FALLBACK");
  assert.equal(receipt.renderer_authority, false);
  assert.equal(fallbackDrawn, 1);
  assert.equal(receipt.base_receipt.renderer, "HEADLESS");
  assert.equal((await renderer.dispose()).state, "DISPOSED");
});
