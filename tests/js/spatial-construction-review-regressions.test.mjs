import assert from "node:assert/strict";
import test from "node:test";

import { ConstructionMeshPass } from "../../aura_spatial_web/construction_mesh_pass.js";
import { ConstructionOverlayPass } from "../../aura_spatial_web/construction_overlay_pass.js";
import { ConstructionSceneRenderer } from "../../aura_spatial_web/construction_scene_renderer.js";
import { GaussianRenderer } from "../../aura_spatial_web/gaussian_renderer.js";
import { RENDERER_STATES } from "../../aura_spatial_web/renderer_adapter.js";
import { planFixture, sceneFixture } from "./spatial-fixture.mjs";

class PresentationRenderer {
  constructor() {
    this.kind = "HEADLESS";
    this.state = RENDERER_STATES.NEW;
    this.initialized = 0;
    this.disposed = 0;
    this.camera = { yaw: 0, pitch: 0, distance: 12, target: [0, 0, 0] };
  }

  async initialize() {
    this.initialized += 1;
    this.state = RENDERER_STATES.INITIALIZED;
  }

  async present() {
    return Object.freeze({ outcome: "PRESENTED", renderer: this.kind });
  }

  async dispose() {
    if (this.state === RENDERER_STATES.DISPOSED) return;
    this.disposed += 1;
    this.state = RENDERER_STATES.DISPOSED;
  }
}

function frame(frameId, elevation) {
  return {
    frame_id: frameId,
    parent_frame_id: "frame:root",
    handedness: "RIGHT_HANDED",
    up_axis: "Y_UP",
    unit_scale_meters: 1,
    translation: [0, elevation, 0],
    rotation_xyzw: [0, 0, 0, 1],
    scale: [1, 1, 1],
    source_refs: [`fixture:${frameId}`],
    truth_class: "PRESENTATION",
    projection_only: true,
  };
}

function meshAsset(assetId, frameId, digestCharacter) {
  return {
    asset_id: assetId,
    asset_type: "MESH",
    uri: `aura://construction/${assetId}.glb`,
    media_type: "model/gltf-binary",
    content_digest: `sha256:${digestCharacter.repeat(64)}`,
    byte_length: 128,
    frame_id: frameId,
    bounds_min: [0, 0, 0],
    bounds_max: [1, 1, 1],
    source_refs: [`fixture:${assetId}`],
    truth_class: "PRESENTATION",
    immutable: true,
    metadata: {
      source_transform: {
        translation: [0, 0, 0],
        rotation_xyzw: [0, 0, 0, 1],
        scale: [1, 1, 1],
      },
    },
  };
}

function entity(entityId, frameId, assetIds, metadata = {}) {
  return {
    entity_id: entityId,
    entity_type: assetIds.length ? "ASSET_INSTANCE" : "DOMAIN_NODE",
    label: entityId,
    frame_id: frameId,
    asset_ids: assetIds,
    source_refs: [`fixture:${entityId}`],
    position: [0, 0, 0],
    rotation_xyzw: [0, 0, 0, 1],
    scale: [1, 1, 1],
    truth_class: "PRESENTATION",
    selectable: true,
    projection_only: true,
    patch_authority: false,
    metadata,
  };
}

function meshScene() {
  const scene = structuredClone(sceneFixture());
  scene.frames.push(frame("frame:storey:one", 4), frame("frame:storey:two", 8));
  scene.assets = [
    meshAsset("asset:mesh:one", "frame:storey:one", "1"),
    meshAsset("asset:mesh:two", "frame:storey:two", "2"),
  ];
  scene.entities = [
    entity("entity:storey:one", "frame:storey:one", ["asset:mesh:one"]),
    entity("entity:storey:two", "frame:storey:two", ["asset:mesh:two"]),
    entity("entity:status:two", "frame:storey:two", [], {
      status_overlay: "BLOCKED",
      planned_start_day: 1,
    }),
  ];
  scene.links = [];
  const plan = structuredClone(planFixture("HEADLESS"));
  plan.scene_entity_count = scene.entities.length;
  plan.scene_link_count = 0;
  plan.scene_asset_count = scene.assets.length;
  plan.scene_asset_bytes = scene.assets.reduce((total, item) => total + item.byte_length, 0);
  return { scene, plan };
}

function gaussianScene() {
  const scene = structuredClone(sceneFixture());
  scene.frames.push(frame("frame:storey", 4));
  scene.assets = [{
    asset_id: "asset:splats",
    asset_type: "GAUSSIAN_SPLAT",
    uri: "aura://construction/splats.spz",
    media_type: "application/vnd.aura.spz",
    content_digest: `sha256:${"3".repeat(64)}`,
    byte_length: 48,
    frame_id: "frame:storey",
    bounds_min: [0, 0, 0],
    bounds_max: [1, 1, 1],
    source_refs: ["fixture:splats"],
    truth_class: "PRESENTATION",
    immutable: true,
    metadata: {
      import_receipt_digest: "a".repeat(64),
      representation_digest: "b".repeat(64),
      representation_digest_version: "AURA_GAUSSIAN_REPRESENTATION_V1",
      representation_bytes_per_splat: 156,
      sh_degree: 2,
      gaussian_sh_degree: 2,
      gaussian_color_space: "SPZ_INTERNAL_WIDE_RGB",
    },
  }];
  scene.entities = [entity("entity:storey", "frame:storey", ["asset:splats"])];
  scene.links = [];
  const plan = structuredClone(planFixture("HEADLESS"));
  plan.scene_entity_count = 1;
  plan.scene_link_count = 0;
  plan.scene_asset_count = 1;
  plan.scene_asset_bytes = 48;
  return { scene, plan };
}

test("Construction renderer preserves storey elevations and aligns exploded overlays", async () => {
  const { scene, plan } = meshScene();
  const presentation = new PresentationRenderer();
  const renderer = new ConstructionSceneRenderer({
    presentationRenderer: presentation,
    meshPass: new ConstructionMeshPass({ drawMeshPass: async () => () => {} }),
    overlayPass: new ConstructionOverlayPass(),
  });
  await renderer.initialize(scene, plan, {
    meshPayloads: [
      {
        asset_id: "asset:mesh:one",
        source_digest: "1".repeat(64),
        decoded_byte_length: 128,
        resource: { local: true },
      },
      {
        asset_id: "asset:mesh:two",
        source_digest: "2".repeat(64),
        decoded_byte_length: 128,
        resource: { local: true },
      },
    ],
  });

  assert.deepEqual(
    renderer.getAssetRenderTransform("asset:mesh:one").translation,
    [0, 4, 0],
  );
  assert.deepEqual(
    renderer.getAssetRenderTransform("asset:mesh:two").translation,
    [0, 8, 0],
  );
  assert.deepEqual(
    renderer.getAssetPresentationTransform("asset:mesh:two").translation,
    [0, 0, 0],
  );

  renderer.explodeStoreys(3);
  assert.deepEqual(
    renderer.getAssetRenderTransform("asset:mesh:two").translation,
    [0, 11, 0],
  );
  assert.deepEqual(
    renderer.getAssetPresentationTransform("asset:mesh:two").translation,
    [0, 3, 0],
  );
  const exploded = renderer.overlayPass.buildModel();
  assert.deepEqual(
    exploded.presentation_transforms["frame:storey:two"].translation,
    [0, 11, 0],
  );
  assert.deepEqual(exploded.status[0].presentation_transform.translation, [0, 11, 0]);

  renderer.collapseStoreys();
  assert.deepEqual(
    renderer.getAssetRenderTransform("asset:mesh:two").translation,
    [0, 8, 0],
  );
  assert.deepEqual(
    renderer.overlayPass.buildModel().presentation_transforms["frame:storey:two"].translation,
    [0, 8, 0],
  );
  await renderer.dispose();
});
test("Construction renderer composes translated rotated and scaled parent frames", async () => {
  const { scene, plan } = meshScene();
  const root = scene.frames.find((item) => item.frame_id === "frame:root");
  root.translation = [10, 0, 0];
  root.rotation_xyzw = [0, 0, 1, 0];
  root.scale = [2, 2, 2];
  const presentation = new PresentationRenderer();
  const renderer = new ConstructionSceneRenderer({
    presentationRenderer: presentation,
    meshPass: new ConstructionMeshPass({ drawMeshPass: async () => () => {} }),
    overlayPass: new ConstructionOverlayPass(),
  });
  await renderer.initialize(scene, plan, {
    meshPayloads: [
      {
        asset_id: "asset:mesh:one",
        source_digest: "1".repeat(64),
        decoded_byte_length: 128,
        resource: { local: true },
      },
      {
        asset_id: "asset:mesh:two",
        source_digest: "2".repeat(64),
        decoded_byte_length: 128,
        resource: { local: true },
      },
    ],
  });
  assert.deepEqual(renderer.getAssetRenderTransform("asset:mesh:one").translation, [10, -8, 0]);
  assert.deepEqual(renderer.getAssetRenderTransform("asset:mesh:one").rotation_xyzw, [0, 0, 1, 0]);
  assert.deepEqual(renderer.getAssetRenderTransform("asset:mesh:one").scale, [2, 2, 2]);
  await renderer.dispose();
});

test("Construction renderer rejects higher-order splats before initializing owners", async () => {
  const { scene, plan } = gaussianScene();
  const presentation = new PresentationRenderer();
  const renderer = new ConstructionSceneRenderer({
    presentationRenderer: presentation,
    meshPass: new ConstructionMeshPass({ drawMeshPass: async () => () => {} }),
    overlayPass: new ConstructionOverlayPass(),
    gaussianRenderer: new GaussianRenderer({
      presentationRenderer: presentation,
      drawGaussianPass: async () => () => {},
      now: () => 0,
    }),
  });

  await assert.rejects(
    renderer.initialize(scene, plan, {
      gaussianPayloads: [{
        asset_id: "asset:splats",
        sh_degree: 2,
      }],
    }),
    /degree-0/,
  );
  assert.equal(renderer.status().state, "LOST");
  assert.equal(presentation.initialized, 0);
  assert.equal(presentation.disposed, 0);
});


test("Construction renderer matches canonical unit-scaled frame composition", async () => {
  const { scene, plan } = meshScene();
  const root = scene.frames.find((item) => item.frame_id === "frame:root");
  root.unit_scale_meters = 0.001;
  root.translation = [1000, 0, 0];
  root.rotation_xyzw = [0, 0, 1, 1];
  root.scale = [2, 2, 2];
  const storey = scene.frames.find((item) => item.frame_id === "frame:storey:one");
  storey.unit_scale_meters = 0.01;
  storey.translation = [0, 400, 0];
  storey.rotation_xyzw = [0, 0, 0, 2];

  const renderer = new ConstructionSceneRenderer({
    presentationRenderer: new PresentationRenderer(),
    meshPass: new ConstructionMeshPass({ drawMeshPass: async () => () => {} }),
    overlayPass: new ConstructionOverlayPass(),
  });
  await renderer.initialize(scene, plan, {
    meshPayloads: [
      {
        asset_id: "asset:mesh:one",
        source_digest: "1".repeat(64),
        decoded_byte_length: 128,
        resource: { local: true },
      },
      {
        asset_id: "asset:mesh:two",
        source_digest: "2".repeat(64),
        decoded_byte_length: 128,
        resource: { local: true },
      },
    ],
  });

  const transform = renderer.getAssetRenderTransform("asset:mesh:one");
  const expectedRotation = [0, 0, Math.sqrt(0.5), Math.sqrt(0.5)];
  const expectedTranslation = [-7, 0, 0];
  const expectedScale = [0.02, 0.02, 0.02];
  for (const [actual, expected] of [
    [transform.translation, expectedTranslation],
    [transform.rotation_xyzw, expectedRotation],
    [transform.scale, expectedScale],
  ]) {
    actual.forEach((value, index) => {
      assert.ok(Math.abs(value - expected[index]) < 1e-9);
    });
  }
  await renderer.dispose();
});


test("Construction demo browser refuses real-pack synthetic substitution and serializes tour steps", async () => {
  const { readFile } = await import("node:fs/promises");
  const source = await readFile(
    new URL("../../aura_spatial_web/construction_demo_app.js", import.meta.url),
    "utf8",
  );
  assert.match(source, /fallback_asset_pack !== true/);
  assert.match(source, /refusing synthetic geometry substitution/);
  assert.match(source, /stepInFlight/);
  assert.match(source, /state\.tourIndex \+= 1/);
  assert.doesNotMatch(source, /state\.tourIndex\+\+/);
});


test("Construction recording UI advertises only implemented representation modes", async () => {
  const { readFile } = await import("node:fs/promises");
  const source = await readFile(
    new URL("../../aura_spatial_web/construction_demo_app.js", import.meta.url),
    "utf8",
  );
  assert.match(source, /setRepresentationMode\("SPLATS"\)/);
  assert.match(source, /button\.disabled = !supported/);
  assert.match(source, /Browser GLB decoding and mesh drawing are not implemented/);
});
