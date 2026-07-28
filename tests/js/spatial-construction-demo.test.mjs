import assert from "node:assert/strict";
import test from "node:test";

import { ConstructionMeshPass } from "../../aura_spatial_web/construction_mesh_pass.js";
import { ConstructionOverlayPass } from "../../aura_spatial_web/construction_overlay_pass.js";
import { ConstructionSceneRenderer } from "../../aura_spatial_web/construction_scene_renderer.js";
import { GaussianRenderer } from "../../aura_spatial_web/gaussian_renderer.js";
import {
  RENDERER_STATES,
  validateRenderPlan,
  validateSceneProjection,
} from "../../aura_spatial_web/renderer_adapter.js";
import { createWebGL2GaussianPass } from "../../aura_spatial_web/webgl2_gaussian_pass.js";
import { planFixture, sceneFixture } from "./spatial-fixture.mjs";

const REPRESENTATION_DIGEST = "9dc87e33a5190c866adbbc940603bbcde292ad3d1728d3cdae54f7adaa56c599";

function constructionFixture() {
  const scene = structuredClone(sceneFixture());
  scene.frames.push({
    frame_id: "frame:storey",
    parent_frame_id: "frame:root",
    handedness: "RIGHT_HANDED",
    up_axis: "Y_UP",
    unit_scale_meters: 1,
    translation: [0, 4, 0],
    rotation_xyzw: [0, 0, 0, 1],
    scale: [1, 1, 1],
    source_refs: ["fixture:storey"],
    truth_class: "PRESENTATION",
    projection_only: true,
  });
  scene.assets = [
    {
      asset_id: "asset:mesh",
      asset_type: "MESH",
      uri: "aura://construction/mesh.glb",
      media_type: "model/gltf-binary",
      content_digest: `sha256:${"1".repeat(64)}`,
      byte_length: 128,
      frame_id: "frame:storey",
      bounds_min: [0, 0, 0],
      bounds_max: [1, 1, 1],
      source_refs: ["fixture:mesh"],
      truth_class: "PRESENTATION",
      immutable: true,
      metadata: {
        source_transform: {
          translation: [0, 0, 0],
          rotation_xyzw: [0, 0, 0, 1],
          scale: [1, 1, 1],
        },
      },
    },
    {
      asset_id: "asset:plan",
      asset_type: "PLANE",
      uri: "aura://construction/plan.svg",
      media_type: "image/svg+xml",
      content_digest: `sha256:${"2".repeat(64)}`,
      byte_length: 64,
      frame_id: "frame:storey",
      bounds_min: [0, 0, 0],
      bounds_max: [1, 0, 1],
      source_refs: ["fixture:plan"],
      truth_class: "PRESENTATION",
      immutable: true,
      metadata: {},
    },
    {
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
        representation_digest: REPRESENTATION_DIGEST,
        representation_digest_version: "AURA_GAUSSIAN_REPRESENTATION_V1",
        representation_bytes_per_splat: 60,
        sh_degree: 0,
        gaussian_sh_degree: 0,
        gaussian_color_space: "SPZ_INTERNAL_WIDE_RGB",
      },
    },
  ];
  scene.entities = [
    {
      entity_id: "entity:storey",
      entity_type: "ASSET_INSTANCE",
      label: "Storey",
      frame_id: "frame:storey",
      asset_ids: ["asset:mesh", "asset:plan", "asset:splats"],
      source_refs: ["construction-demo-storey:fixture"],
      position: [0, 0, 0],
      rotation_xyzw: [0, 0, 0, 1],
      scale: [1, 1, 1],
      truth_class: "PRESENTATION",
      selectable: true,
      projection_only: true,
      patch_authority: false,
      metadata: {
        source_transform: { translation: [0, 4, 0], rotation_xyzw: [0, 0, 0, 1], scale: [1, 1, 1] },
        presentation_transform: { translation: [0, 0, 0], rotation_xyzw: [0, 0, 0, 1], scale: [1, 1, 1] },
      },
    },
    {
      entity_id: "entity:work",
      entity_type: "DOMAIN_NODE",
      label: "Blocked drilling",
      frame_id: "frame:storey",
      asset_ids: [],
      source_refs: ["construction-scope:fixture"],
      position: [0, 0, 0],
      rotation_xyzw: [0, 0, 0, 1],
      scale: [1, 1, 1],
      truth_class: "PRESENTATION",
      selectable: true,
      projection_only: true,
      patch_authority: false,
      metadata: { status_overlay: "BLOCKED", planned_start_day: 5, projection_only: true },
    },
    {
      entity_id: "entity:hazard",
      entity_type: "DOMAIN_NODE",
      label: "Hazard",
      frame_id: "frame:storey",
      asset_ids: [],
      source_refs: ["construction-demo-hazard:fixture"],
      position: [0, 0, 0],
      rotation_xyzw: [0, 0, 0, 1],
      scale: [1, 1, 1],
      truth_class: "PRESENTATION",
      selectable: true,
      projection_only: true,
      patch_authority: false,
      metadata: { severity: "CRITICAL", active: true },
    },
    {
      entity_id: "entity:trade",
      entity_type: "LABEL",
      label: "Electrical",
      frame_id: "frame:root",
      asset_ids: [],
      source_refs: ["construction-demo-trade:electrical"],
      position: [0, 0, 0],
      rotation_xyzw: [0, 0, 0, 1],
      scale: [1, 1, 1],
      truth_class: "PRESENTATION",
      selectable: true,
      projection_only: true,
      patch_authority: false,
      metadata: { overlay_kind: "TRADE" },
    },
    {
      entity_id: "entity:budget",
      entity_type: "DOMAIN_NODE",
      label: "Budget line",
      frame_id: "frame:storey",
      asset_ids: [],
      source_refs: ["construction-demo-budget:fixture"],
      position: [0, 0, 0],
      rotation_xyzw: [0, 0, 0, 1],
      scale: [1, 1, 1],
      truth_class: "PRESENTATION",
      selectable: true,
      projection_only: true,
      patch_authority: false,
      metadata: {
        overlay_kind: "BUDGET",
        committed_cad: 100,
        forecast_cad: 120,
        actual_cad: 80,
        truth_class: "SYNTHETIC_DEMO_BUDGET",
      },
    },
    {
      entity_id: "entity:inspection",
      entity_type: "DOMAIN_NODE",
      label: "Inspection",
      frame_id: "frame:storey",
      asset_ids: [],
      source_refs: ["construction-demo-inspection:fixture"],
      position: [0, 0, 0],
      rotation_xyzw: [0, 0, 0, 1],
      scale: [1, 1, 1],
      truth_class: "PRESENTATION",
      selectable: true,
      projection_only: true,
      patch_authority: false,
      metadata: {
        overlay_kind: "INSPECTION",
        status_overlay: "SCHEDULED",
        scheduled_day: 8,
      },
    },
    {
      entity_id: "entity:rule",
      entity_type: "DOMAIN_NODE",
      label: "Synthetic rule",
      frame_id: "frame:root",
      asset_ids: [],
      source_refs: ["construction-demo-rule:fixture"],
      position: [0, 0, 0],
      rotation_xyzw: [0, 0, 0, 1],
      scale: [1, 1, 1],
      truth_class: "PRESENTATION",
      selectable: true,
      projection_only: true,
      patch_authority: false,
      metadata: {
        overlay_kind: "SYNTHETIC_RULE",
        requirement: "Human review required",
        truth_class: "SYNTHETIC_DEMO_RULE",
      },
    },
  ];
  scene.links = [
    {
      link_id: "link:blocked",
      source_entity_id: "entity:work",
      target_entity_id: "entity:hazard",
      relation: "BLOCKED_BY",
      source_refs: ["fixture:blocked"],
      truth_class: "PRESENTATION",
      directed: true,
      projection_only: true,
      metadata: {},
    },
    {
      link_id: "link:dependency",
      source_entity_id: "entity:work",
      target_entity_id: "entity:inspection",
      relation: "DEPENDS_ON",
      source_refs: ["fixture:dependency"],
      truth_class: "PRESENTATION",
      directed: true,
      projection_only: true,
      metadata: {},
    },
  ];
  const plan = structuredClone(planFixture("HEADLESS"));
  plan.scene_entity_count = scene.entities.length;
  plan.scene_link_count = scene.links.length;
  plan.scene_asset_count = scene.assets.length;
  plan.scene_asset_bytes = scene.assets.reduce((total, item) => total + item.byte_length, 0);
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

class TestPresentationRenderer {
  constructor() {
    this.kind = "HEADLESS";
    this.state = RENDERER_STATES.NEW;
    this.scene = null;
    this.plan = null;
    this.camera = { yaw: 0, pitch: 0, distance: 12, target: [0, 0, 0] };
    this.disposed = 0;
  }

  initialize(scene, plan) {
    this.scene = validateSceneProjection(scene);
    this.plan = validateRenderPlan(plan, this.scene);
    this.state = RENDERER_STATES.INITIALIZED;
    return this.status();
  }

  present() {
    this.state = RENDERER_STATES.PRESENTED;
    return Object.freeze({
      renderer: this.kind,
      outcome: "PRESENTED",
      scene_digest: this.scene.scene_digest,
      render_plan_digest: this.plan.render_plan_digest,
    });
  }

  orbit(yaw, pitch) {
    this.camera.yaw += yaw;
    this.camera.pitch += pitch;
  }

  zoom(delta) {
    this.camera.distance += delta;
  }

  pick() {
    return "entity:work";
  }

  dispose() {
    this.disposed += 1;
    this.state = RENDERER_STATES.DISPOSED;
    this.scene = null;
    this.plan = null;
    return this.status();
  }

  status() {
    return Object.freeze({ renderer: this.kind, state: this.state });
  }
}

function fakeGl() {
  let next = 1;
  const calls = {
    drawInstances: [],
    deletedBuffers: 0,
    deletedPrograms: 0,
    deletedVaos: 0,
    uniformMatrices: new Map(),
  };
  return {
    calls,
    VERTEX_SHADER: 1,
    FRAGMENT_SHADER: 2,
    COMPILE_STATUS: 3,
    LINK_STATUS: 4,
    ARRAY_BUFFER: 5,
    STATIC_DRAW: 6,
    FLOAT: 7,
    BLEND: 8,
    SRC_ALPHA: 9,
    ONE_MINUS_SRC_ALPHA: 10,
    DEPTH_TEST: 11,
    TRIANGLE_STRIP: 12,
    createShader: () => ({ id: next++ }),
    shaderSource() {},
    compileShader() {},
    getShaderParameter: () => true,
    getShaderInfoLog: () => "",
    deleteShader() {},
    createProgram: () => ({ id: next++ }),
    attachShader() {},
    linkProgram() {},
    getProgramParameter: () => true,
    getProgramInfoLog: () => "",
    deleteProgram() { calls.deletedPrograms += 1; },
    createVertexArray: () => ({ id: next++ }),
    bindVertexArray() {},
    deleteVertexArray() { calls.deletedVaos += 1; },
    createBuffer: () => ({ id: next++ }),
    bindBuffer() {},
    bufferData() {},
    deleteBuffer() { calls.deletedBuffers += 1; },
    getAttribLocation: (_program, name) => ({ a_corner: 0, a_position: 1, a_rotation: 2, a_scale: 3, a_color: 4 })[name],
    enableVertexAttribArray() {},
    vertexAttribPointer() {},
    vertexAttribDivisor() {},
    useProgram() {},
    getUniformLocation: (_program, name) => name,
    uniformMatrix4fv(location, _transpose, value) {
      calls.uniformMatrices.set(location, Array.from(value));
    },
    uniform3fv() {},
    enable() {},
    blendFunc() {},
    depthMask() {},
    drawArraysInstanced(_mode, _first, _vertices, instances) { calls.drawInstances.push(instances); },
    isContextLost: () => false,
  };
}

test("Construction mesh pass preserves source transforms and releases every draw handle", async () => {
  const { scene } = constructionFixture();
  let disposed = 0;
  let observed = null;
  const pass = new ConstructionMeshPass({
    drawMeshPass: async (_resource, context) => {
      observed = context;
      return () => { disposed += 1; };
    },
  });
  pass.initialize(scene, [{
    asset_id: "asset:mesh",
    source_digest: "1".repeat(64),
    decoded_byte_length: 256,
    resource: { local: true },
  }]);
  pass.setPresentationTransform("frame:storey", {
    translation: [0, 6, 0], rotation_xyzw: [0, 0, 0, 1], scale: [1, 1, 1],
  });
  const receipt = await pass.present();
  assert.equal(receipt.visible_mesh_count, 1);
  assert.deepEqual(observed.source_transform.translation, [0, 0, 0]);
  assert.deepEqual(observed.presentation_transform.translation, [0, 6, 0]);
  assert.equal(observed.source_transform_immutable, true);
  await pass.present();
  assert.equal(disposed, 1);
  await pass.dispose();
  assert.equal(disposed, 2);
  assert.equal(pass.status().active_disposer_count, 0);
});

test("Construction overlay pass supports timeline, layers, isolation, and headless fallback", async () => {
  const { scene } = constructionFixture();
  const pass = new ConstructionOverlayPass();
  pass.initialize(scene);
  pass.setTimelineDay(4);
  let model = pass.buildModel();
  assert.equal(model.status.some((item) => item.entity_id === "entity:work"), false);
  assert.equal(model.floor_plans.length, 1);
  assert.equal(model.blockers.length, 1);
  assert.equal(model.budgets.length, 1);
  assert.deepEqual(
    {
      committed_cad: model.budgets[0].committed_cad,
      forecast_cad: model.budgets[0].forecast_cad,
      actual_cad: model.budgets[0].actual_cad,
    },
    { committed_cad: 100, forecast_cad: 120, actual_cad: 80 },
  );
  pass.setTimelineDay(5);
  pass.setLayer("dependencies", false);
  pass.setLayer("budgets", false);
  pass.setVisibleFrameIds(["frame:storey"]);
  model = pass.buildModel();
  assert.equal(model.status.some((item) => item.entity_id === "entity:work"), true);
  assert.equal(model.dependencies.length, 0);
  assert.equal(model.budgets.length, 0);
  assert.equal(model.source_geometry_mutated, false);
  assert.equal((await pass.present()).drawn, false);
  assert.equal((await pass.dispose()).active_disposer_count, 0);
});

test("degree-0 WebGL2 Gaussian pass caps visibility and deletes exact GPU resources", async () => {
  const gl = fakeGl();
  const pass = createWebGL2GaussianPass({ gl, maxVisibleSplats: 1 });
  const handle = await pass({
    positions: new Float32Array([0, 0, 0, 1, 1, 1]),
    rotations_xyzw: new Float32Array([0, 0, 0, 1, 0, 0, 0, 1]),
    scales_xyz: new Float32Array([1, 1, 1, 1, 1, 1]),
    opacities: new Float32Array([1, 1]),
    colors_rgba: new Uint8Array([255, 0, 255, 255, 0, 255, 255, 255]),
    sorted_indices: new Uint32Array([1, 0]),
  }, { asset_id: "asset:splats", sh_degree: 0 });
  assert.equal(handle.visible_count, 1);
  assert.equal(handle.capped, true);
  assert.deepEqual(gl.calls.drawInstances, [1]);
  handle.dispose();
  handle.dispose();
  assert.equal(gl.calls.deletedBuffers, 5);
  assert.equal(gl.calls.deletedPrograms, 1);
  assert.equal(gl.calls.deletedVaos, 1);
});

test("Construction scene renderer composes hybrid controls and exact cleanup", async () => {
  const { scene, plan } = constructionFixture();
  const presentation = new TestPresentationRenderer();
  let meshDisposed = 0;
  let gaussianDisposed = 0;
  let overlayDisposed = 0;
  const meshPass = new ConstructionMeshPass({
    drawMeshPass: async () => () => { meshDisposed += 1; },
  });
  const overlayPass = new ConstructionOverlayPass({
    drawOverlayPass: async () => () => { overlayDisposed += 1; },
  });
  const gaussian = new GaussianRenderer({
    presentationRenderer: presentation,
    drawGaussianPass: async () => ({ dispose() { gaussianDisposed += 1; } }),
    now: () => 0,
  });
  const renderer = new ConstructionSceneRenderer({
    presentationRenderer: presentation,
    meshPass,
    overlayPass,
    gaussianRenderer: gaussian,
  });
  await renderer.initialize(scene, plan, {
    meshPayloads: [{
      asset_id: "asset:mesh",
      source_digest: "1".repeat(64),
      decoded_byte_length: 256,
      resource: { local: true },
    }],
    gaussianPayloads: [gaussianPayload()],
  });
  assert.equal(renderer.status().representation_mode, "HYBRID");
  renderer.explodeStoreys(4);
  assert.deepEqual(renderer.getAssetPresentationTransform("asset:splats").translation, [0, 0, 0]);
  renderer.isolateStorey("frame:storey");
  renderer.toggleOverlay("dependencies", false);
  renderer.setTimelineDay(5);
  renderer.orbit(0.1, 0.2);
  renderer.zoom(1);
  renderer.pan(1, 2, 3);
  assert.equal(renderer.pick(0, 0), "entity:work");
  renderer.focusEntity("entity:work");
  const receipt = await renderer.present();
  assert.equal(receipt.representation_mode, "HYBRID");
  assert.equal(receipt.mesh_receipt.visible_mesh_count, 1);
  assert.equal(receipt.overlay_receipt.model.dependencies.length, 0);
  assert.equal(receipt.source_asset_coordinates_immutable, true);
  assert.equal(receipt.renderer_authority, false);
  assert.equal(receipt.physical_work_authority, false);
  assert.equal(receipt.professional_authority, false);
  assert.equal(receipt.inspector_state.selected_entity.projection_only, true);
  assert.equal(receipt.inspector_state.selected_entity.patch_authority, false);
  assert.equal(receipt.inspector_state.blueprint.media_type, "image/svg+xml");
  assert.equal(receipt.inspector_state.blueprint_resolution.status, "BOUND");
  const status = await renderer.dispose();
  assert.equal(status.state, "DISPOSED");
  assert.equal(meshDisposed, 1);
  assert.equal(gaussianDisposed, 1);
  assert.equal(overlayDisposed, 1);
  assert.equal(presentation.disposed, 1);
});

test("Construction renderer resolves only canonically bound blueprints and reports ambiguity", async () => {
  const first = constructionFixture();
  const canonicalPlan = first.scene.assets.find(
    (asset) => asset.asset_type === "PLANE",
  );
  first.scene.assets.push({
    ...canonicalPlan,
    asset_id: "asset:unrelated-plan",
  });
  const firstPresentation = new TestPresentationRenderer();
  const firstRenderer = new ConstructionSceneRenderer({
    presentationRenderer: firstPresentation,
    meshPass: new ConstructionMeshPass({ drawMeshPass: async () => () => {} }),
    overlayPass: new ConstructionOverlayPass(),
    gaussianRenderer: new GaussianRenderer({
      presentationRenderer: firstPresentation,
      drawGaussianPass: async () => () => {},
      now: () => 0,
    }),
  });
  await firstRenderer.initialize(first.scene, {
    ...first.plan,
    scene_asset_count: first.scene.assets.length,
    scene_asset_bytes: first.scene.assets.reduce(
      (total, asset) => total + asset.byte_length,
      0,
    ),
  }, {
    meshPayloads: [{
      asset_id: "asset:mesh",
      source_digest: "1".repeat(64),
      decoded_byte_length: 256,
      resource: { local: true },
    }],
    gaussianPayloads: [gaussianPayload()],
  });
  firstRenderer.isolateStorey("frame:storey");
  assert.equal(
    firstRenderer.inspectorState().blueprint.asset_id,
    canonicalPlan.asset_id,
  );
  await firstRenderer.dispose();

  const second = constructionFixture();
  const secondPlan = second.scene.assets.find(
    (asset) => asset.asset_type === "PLANE",
  );
  const ambiguousPlan = {
    ...secondPlan,
    asset_id: "asset:ambiguous-plan",
  };
  second.scene.assets.push(ambiguousPlan);
  second.scene.entities.find(
    (entity) => entity.entity_type === "ASSET_INSTANCE",
  ).asset_ids.push(ambiguousPlan.asset_id);
  const secondPresentation = new TestPresentationRenderer();
  const secondRenderer = new ConstructionSceneRenderer({
    presentationRenderer: secondPresentation,
    meshPass: new ConstructionMeshPass({ drawMeshPass: async () => () => {} }),
    overlayPass: new ConstructionOverlayPass(),
    gaussianRenderer: new GaussianRenderer({
      presentationRenderer: secondPresentation,
      drawGaussianPass: async () => () => {},
      now: () => 0,
    }),
  });
  await secondRenderer.initialize(second.scene, {
    ...second.plan,
    scene_asset_count: second.scene.assets.length,
    scene_asset_bytes: second.scene.assets.reduce(
      (total, asset) => total + asset.byte_length,
      0,
    ),
  }, {
    meshPayloads: [{
      asset_id: "asset:mesh",
      source_digest: "1".repeat(64),
      decoded_byte_length: 256,
      resource: { local: true },
    }],
    gaussianPayloads: [gaussianPayload()],
  });
  secondRenderer.focusEntity("entity:work");
  assert.throws(
    () => secondRenderer.isolateStorey("frame:storey"),
    /status AMBIGUOUS, found 2/,
  );
  const inspector = secondRenderer.inspectorState();
  assert.equal(inspector.blueprint, null);
  assert.equal(inspector.blueprint_resolution.status, "AMBIGUOUS");
  assert.equal(secondRenderer.status().inspector_state.blueprint_resolution.status, "AMBIGUOUS");
  await secondRenderer.dispose();
});

test("Construction renderer cancellation and device loss fail closed", async () => {
  const { scene, plan } = constructionFixture();
  const presentation = new TestPresentationRenderer();
  const meshPass = new ConstructionMeshPass({ drawMeshPass: async () => () => {} });
  const overlayPass = new ConstructionOverlayPass();
  const gaussian = new GaussianRenderer({
    presentationRenderer: presentation,
    drawGaussianPass: async () => () => {},
    now: () => 0,
  });
  const renderer = new ConstructionSceneRenderer({
    presentationRenderer: presentation,
    meshPass,
    overlayPass,
    gaussianRenderer: gaussian,
  });
  await renderer.initialize(scene, plan, {
    meshPayloads: [{
      asset_id: "asset:mesh",
      source_digest: "1".repeat(64),
      decoded_byte_length: 256,
      resource: { local: true },
    }],
    gaussianPayloads: [gaussianPayload()],
  });
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(renderer.present({ signal: controller.signal }), /cancelled/);
  const status = await renderer.markDeviceLost();
  assert.equal(status.state, "LOST");
  assert.equal(status.renderer_authority, false);
  assert.equal(presentation.disposed, 1);
  await renderer.dispose();
  assert.equal(presentation.disposed, 1);
});

test("Construction renderer Gaussian initialization failure disposes shared presentation once", async () => {
  const { scene, plan } = constructionFixture();
  const sharedPresentation = new TestPresentationRenderer();
  sharedPresentation.initialize = () => {
    throw new Error("Gaussian initialization forced failure");
  };
  const failingGaussian = new GaussianRenderer({
    presentationRenderer: sharedPresentation,
    drawGaussianPass: async () => () => {},
    now: () => 0,
  });
  const renderer = new ConstructionSceneRenderer({
    presentationRenderer: sharedPresentation,
    meshPass: new ConstructionMeshPass({ drawMeshPass: async () => () => {} }),
    overlayPass: new ConstructionOverlayPass(),
    gaussianRenderer: failingGaussian,
  });
  await assert.rejects(
    renderer.initialize(scene, plan, {
      meshPayloads: [{
        asset_id: "asset:mesh",
        source_digest: "1".repeat(64),
        decoded_byte_length: 256,
        resource: { local: true },
      }],
      gaussianPayloads: [gaussianPayload()],
    }),
    /initialization/
  );
  assert.equal(sharedPresentation.disposed, 1);
  assert.equal(renderer.status().state, "LOST");
  await renderer.dispose();
  assert.equal(sharedPresentation.disposed, 1);
});

test("Construction renderer mid-flight abort becomes terminal and releases resources", async () => {
  const { scene, plan } = constructionFixture();
  const presentation = new TestPresentationRenderer();
  let blockingResolve = null;
  const blockingPromise = new Promise((resolve) => { blockingResolve = resolve; });
  let meshDisposed = 0;
  const renderer = new ConstructionSceneRenderer({
    presentationRenderer: presentation,
    meshPass: new ConstructionMeshPass({
      drawMeshPass: async () => {
        await blockingPromise;
        return () => { meshDisposed += 1; };
      },
    }),
    overlayPass: new ConstructionOverlayPass(),
    gaussianRenderer: new GaussianRenderer({
      presentationRenderer: presentation,
      drawGaussianPass: async () => () => {},
      now: () => 0,
    }),
  });
  await renderer.initialize(scene, plan, {
    meshPayloads: [{
      asset_id: "asset:mesh",
      source_digest: "1".repeat(64),
      decoded_byte_length: 256,
      resource: { local: true },
    }],
    gaussianPayloads: [gaussianPayload()],
  });
  const controller = new AbortController();
  const presentPromise = renderer.present({ signal: controller.signal });
  controller.abort();
  blockingResolve();
  await assert.rejects(presentPromise, /cancelled/);
  assert.equal(renderer.status().state, "LOST");
  assert.equal(meshDisposed, 0);
  await renderer.dispose();
  await renderer.dispose();
});


test("Construction storey isolation filters Gaussian assets", async () => {
  const { scene, plan } = constructionFixture();
  scene.frames.push({
    frame_id: "frame:storey:second",
    parent_frame_id: "frame:root",
    handedness: "RIGHT_HANDED",
    up_axis: "Y_UP",
    unit_scale_meters: 1,
    translation: [0, 8, 0],
    rotation_xyzw: [0, 0, 0, 1],
    scale: [1, 1, 1],
    source_refs: ["fixture:storey:second"],
    truth_class: "PRESENTATION",
    projection_only: true,
  });
  scene.assets.push({
    asset_id: "asset:splats:second",
    asset_type: "GAUSSIAN_SPLAT",
    uri: "aura://construction/splats-second.spz",
    media_type: "application/vnd.aura.spz",
    content_digest: `sha256:${"4".repeat(64)}`,
    byte_length: 48,
    frame_id: "frame:storey:second",
    bounds_min: [0, 0, 0],
    bounds_max: [1, 1, 1],
    source_refs: ["fixture:splats:second"],
    truth_class: "PRESENTATION",
    immutable: true,
    metadata: {
      import_receipt_digest: "b".repeat(64),
      representation_digest: REPRESENTATION_DIGEST,
      representation_digest_version: "AURA_GAUSSIAN_REPRESENTATION_V1",
      representation_bytes_per_splat: 60,
      sh_degree: 0,
      gaussian_sh_degree: 0,
      gaussian_color_space: "SPZ_INTERNAL_WIDE_RGB",
    },
  });
  scene.entities.push({
    entity_id: "entity:storey:second",
    entity_type: "ASSET_INSTANCE",
    label: "Second storey",
    frame_id: "frame:storey:second",
    asset_ids: ["asset:splats:second"],
    source_refs: ["construction-demo-storey:second"],
    position: [0, 0, 0],
    rotation_xyzw: [0, 0, 0, 1],
    scale: [1, 1, 1],
    truth_class: "PRESENTATION",
    selectable: true,
    projection_only: true,
    patch_authority: false,
    metadata: {
      source_transform: { translation: [0, 8, 0], rotation_xyzw: [0, 0, 0, 1], scale: [1, 1, 1] },
      presentation_transform: { translation: [0, 0, 0], rotation_xyzw: [0, 0, 0, 1], scale: [1, 1, 1] },
    },
  });
  plan.scene_entity_count = scene.entities.length;
  plan.scene_asset_count = scene.assets.length;
  plan.scene_asset_bytes = scene.assets.reduce((total, item) => total + item.byte_length, 0);

  const presentation = new TestPresentationRenderer();
  const drawn = [];
  const renderer = new ConstructionSceneRenderer({
    presentationRenderer: presentation,
    meshPass: new ConstructionMeshPass({ drawMeshPass: async () => () => {} }),
    overlayPass: new ConstructionOverlayPass(),
    gaussianRenderer: new GaussianRenderer({
      presentationRenderer: presentation,
      drawGaussianPass: async (_resources, context) => {
        drawn.push(context.asset_id);
        return () => {};
      },
      now: () => 0,
    }),
  });
  const secondPayload = {
    ...gaussianPayload(),
    asset_id: "asset:splats:second",
    source_digest: "4".repeat(64),
    derived_asset_digest: "b".repeat(64),
  };
  await renderer.initialize(scene, plan, {
    meshPayloads: [{
      asset_id: "asset:mesh",
      source_digest: "1".repeat(64),
      decoded_byte_length: 256,
      resource: { local: true },
    }],
    gaussianPayloads: [gaussianPayload(), secondPayload],
  });

  renderer.isolateStorey("frame:storey");
  const isolated = await renderer.present();
  assert.equal(isolated.base_receipt.splat_count, 1);
  assert.deepEqual(drawn, ["asset:splats"]);

  renderer.showAllStoreys();
  const all = await renderer.present();
  assert.equal(all.base_receipt.splat_count, 2);
  assert.deepEqual(drawn.slice(-2), ["asset:splats", "asset:splats:second"]);
  await renderer.dispose();
});


test("degree-0 Gaussian pass applies the full rotated model matrix", async () => {
  const gl = fakeGl();
  const rootHalf = Math.sqrt(0.5);
  const pass = createWebGL2GaussianPass({
    gl,
    getPresentationTransform: () => ({
      translation: [1, 2, 3],
      rotation_xyzw: [0, 0, rootHalf, rootHalf],
      scale: [2, 3, 4],
    }),
  });
  const handle = await pass({
    positions: new Float32Array([0, 0, 0]),
    rotations_xyzw: new Float32Array([0, 0, 0, 1]),
    scales_xyz: new Float32Array([1, 1, 1]),
    opacities: new Float32Array([1]),
    colors_rgba: new Uint8Array([255, 255, 255, 255]),
    sorted_indices: new Uint32Array([0]),
  }, { asset_id: "asset:splats", sh_degree: 0 });

  const actual = gl.calls.uniformMatrices.get("u_model");
  const expected = [
    0, 2, 0, 0,
    -3, 0, 0, 0,
    0, 0, 4, 0,
    1, 2, 3, 1,
  ];
  assert.equal(actual.length, 16);
  actual.forEach((value, index) => {
    assert.ok(Math.abs(value - expected[index]) < 1e-6);
  });
  handle.dispose();
});

test("PUBLIC overlay classification survives provenance redaction", () => {
  const { scene } = constructionFixture();
  for (const entity of scene.entities) {
    entity.source_refs = ["0123456789abcdef"];
  }
  const pass = new ConstructionOverlayPass();
  pass.initialize(scene);
  const model = pass.buildModel();
  assert.equal(model.trades.length, 1);
  assert.equal(model.inspections.length, 1);
  assert.equal(model.synthetic_rules.length, 1);
});


test("Construction mesh cleanup failure is terminal, visible, and retryable", async () => {
  const { scene } = constructionFixture();
  let failCleanup = true;
  let released = 0;
  const pass = new ConstructionMeshPass({
    drawMeshPass: async () => async () => {
      if (failCleanup) throw new Error("forced mesh cleanup failure");
      released += 1;
    },
  });
  pass.initialize(scene, [{
    asset_id: "asset:mesh",
    source_digest: "1".repeat(64),
    decoded_byte_length: 256,
    resource: { local: true },
  }]);
  await pass.present();
  await assert.rejects(pass.present(), /forced mesh cleanup failure/);
  assert.equal(pass.status().disposed, true);
  assert.equal(pass.status().initialized, false);
  assert.equal(pass.status().active_disposer_count, 1);
  failCleanup = false;
  await pass.dispose();
  assert.equal(released, 1);
  assert.equal(pass.status().active_disposer_count, 0);
});

test("WebGL2 Gaussian partial buffer allocation releases earlier resources", async () => {
  const gl = fakeGl();
  const originalCreateBuffer = gl.createBuffer;
  let calls = 0;
  gl.createBuffer = () => {
    calls += 1;
    return calls === 2 ? null : originalCreateBuffer();
  };
  const pass = createWebGL2GaussianPass({ gl, maxVisibleSplats: 1 });
  await assert.rejects(
    pass({
      positions: new Float32Array([0, 0, 0]),
      rotations_xyzw: new Float32Array([0, 0, 0, 1]),
      scales_xyz: new Float32Array([1, 1, 1]),
      opacities: new Float32Array([1]),
      colors_rgba: new Uint8Array([255, 0, 255, 255]),
      sorted_indices: new Uint32Array([0]),
    }, { asset_id: "asset:splats", sh_degree: 0 }),
    /allocate Gaussian buffer/,
  );
  assert.equal(gl.calls.deletedBuffers, 1);
  assert.equal(gl.calls.deletedPrograms, 1);
  assert.equal(gl.calls.deletedVaos, 1);
});


test("Construction mesh pass releases a handle when abort occurs inside draw", async () => {
  const { scene } = constructionFixture();
  const controller = new AbortController();
  let disposed = 0;
  const pass = new ConstructionMeshPass({
    drawMeshPass: async () => {
      controller.abort();
      return () => { disposed += 1; };
    },
  });
  pass.initialize(scene, [{
    asset_id: "asset:mesh",
    source_digest: "1".repeat(64),
    decoded_byte_length: 256,
    resource: { local: true },
  }]);
  await assert.rejects(pass.present({ signal: controller.signal }), /cancelled/);
  assert.equal(disposed, 1);
  assert.equal(pass.status().active_disposer_count, 0);
  assert.equal(pass.status().disposed, true);
});
