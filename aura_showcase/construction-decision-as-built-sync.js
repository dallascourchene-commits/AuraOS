import { createConstructionWebGL2SceneRenderer } from "/aura_spatial_web/construction_scene_renderer.js";
import { createConstructionWireframePass } from "/aura_spatial_web/construction_wireframe_pass.js";

const VERSION = "AURA_CONSTRUCTION_P3_AS_BUILT_SYNC_V1";
const MESSAGE_TYPE = "AURA_CONSTRUCTION_P3_AS_BUILT_SYNC";
const RECEIPT_TYPE = "AURA_CONSTRUCTION_P3_AS_BUILT_RECEIPT";
const READY_TYPE = "AURA_CONSTRUCTION_P3_AS_BUILT_READY";
const HEX64 = /^[0-9a-f]{64}$/;
const ALLOWED_KEYS = new Set([
  "version",
  "projection_digest",
  "state_digest",
  "as_built_scene_digest",
  "as_built_frame_id",
  "as_built_entity_id",
  "selected_issue_id",
  "timeline_day",
  "overlays",
]);
const ALLOWED_OVERLAYS = new Set([
  "floorPlans",
  "status",
  "trades",
  "blockers",
  "budgets",
  "inspections",
  "dependencies",
  "syntheticRules",
]);
const GAUSSIAN_REPRESENTATION_DIGEST =
  "5e4620fc5ea92315714eaf3bfe0247f4a18f6ed51997efb9c5c389d20536d7b7";

const canvas = document.getElementById("construction-canvas");
const meshOverlay = document.getElementById("construction-mesh-overlay");
const statusNode = document.getElementById("scene-state");
const intentNode = document.getElementById("intent-line");
let packet = null;
let renderer = null;
let latest = null;
let applying = false;

function post(type, payload) {
  parent.postMessage({ type, payload }, location.origin);
}

function resizeCanvas() {
  const ratio = Math.min(2, globalThis.devicePixelRatio || 1);
  const width = Math.max(1, Math.floor(canvas.clientWidth * ratio));
  const height = Math.max(1, Math.floor(canvas.clientHeight * ratio));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
}

function meshPayloads(scene) {
  return scene.assets
    .filter((asset) => asset.asset_type === "MESH")
    .map((asset) => ({
      asset_id: asset.asset_id,
      source_digest: asset.content_digest.split(":", 2).at(-1),
      decoded_byte_length: Math.max(1, asset.byte_length),
      resource: Object.freeze({
        asset_id: asset.asset_id,
        bounds: [asset.bounds_min, asset.bounds_max],
      }),
    }));
}

function gaussianGeometry() {
  const positions = [];
  for (const x of [-8, -4, 0, 4, 8]) {
    for (const z of [-8, -4, 0, 4, 8]) positions.push([x, 2, z]);
  }
  return {
    positions,
    rotations_xyzw: positions.map(() => [0, 0, 0, 1]),
    scales_xyz: positions.map(() => [1.2, 0.18, 1.2]),
    opacities: positions.map(() => 0.68),
    sh_coefficients: positions.map(() => [0, 0, 0]),
    colors_rgba: positions.map(() => [210, 80, 255, 190]),
  };
}

function gaussianPayloads(scene) {
  const geometry = gaussianGeometry();
  return scene.assets
    .filter((asset) => asset.asset_type === "GAUSSIAN_SPLAT")
    .map((asset) => ({
      asset_id: asset.asset_id,
      source_digest: asset.content_digest.split(":", 2).at(-1),
      derived_asset_digest: asset.metadata.import_receipt_digest,
      representation_digest: GAUSSIAN_REPRESENTATION_DIGEST,
      sh_degree: 0,
      color_space: "SPZ_INTERNAL_WIDE_RGB",
      ...geometry,
    }));
}

function boundedText(value, name) {
  if (typeof value !== "string" || !value || value.length > 192) {
    throw new Error(`${name} is invalid`);
  }
  return value;
}

function validate(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("P3 as-built synchronization packet must be an object");
  }
  const keys = Object.keys(value);
  if (keys.some((key) => !ALLOWED_KEYS.has(key)) || keys.length !== ALLOWED_KEYS.size) {
    throw new Error("P3 as-built synchronization packet keys mismatch");
  }
  if (value.version !== VERSION) throw new Error("unsupported P3 as-built sync version");
  for (const key of ["projection_digest", "state_digest", "as_built_scene_digest"]) {
    if (!HEX64.test(value[key])) throw new Error(`${key} must be an exact digest`);
  }
  if (value.state_digest !== packet.state_digest) {
    throw new Error("P3 as-built state identity is stale");
  }
  if (value.as_built_scene_digest !== packet.scene.scene_digest) {
    throw new Error("P3 as-built scene identity is stale");
  }
  const frameId = boundedText(value.as_built_frame_id, "as_built_frame_id");
  if (!packet.scene.frames.some((item) => item.frame_id === frameId)) {
    throw new Error("P3 as-built frame is not admitted by the current scene");
  }
  const entityId = boundedText(value.as_built_entity_id, "as_built_entity_id");
  const entity = packet.scene.entities.find((item) => item.entity_id === entityId);
  if (!entity || entity.frame_id !== frameId) {
    throw new Error("P3 as-built entity is hidden, stale, or belongs to another frame");
  }
  boundedText(value.selected_issue_id, "selected_issue_id");
  if (typeof value.timeline_day !== "number" || !Number.isFinite(value.timeline_day)) {
    throw new Error("timeline_day must be finite");
  }
  if (value.timeline_day < 0 || value.timeline_day > 30) {
    throw new Error("timeline_day must be between 0 and 30");
  }
  if (!Array.isArray(value.overlays) || value.overlays.length > ALLOWED_OVERLAYS.size) {
    throw new Error("as-built overlays must be a bounded array");
  }
  const overlays = [...new Set(value.overlays)];
  if (overlays.length !== value.overlays.length || overlays.some((item) => !ALLOWED_OVERLAYS.has(item))) {
    throw new Error("as-built overlays contain an unadmitted layer");
  }
  return { ...value, overlays };
}

async function present() {
  resizeCanvas();
  const receipt = await renderer.present();
  statusNode.textContent = `${receipt.representation_mode} · ${receipt.outcome}`;
  return receipt;
}

async function apply() {
  if (applying || !latest || !renderer) return;
  applying = true;
  const requested = latest;
  try {
    const value = validate(requested);
    renderer.isolateStorey(value.as_built_frame_id);
    renderer.focusEntity(value.as_built_entity_id);
    renderer.setTimelineDay(value.timeline_day);
    for (const layer of ALLOWED_OVERLAYS) {
      renderer.toggleOverlay(layer, value.overlays.includes(layer));
    }
    const renderReceipt = await present();
    intentNode.textContent = `${value.selected_issue_id} · day ${value.timeline_day}`;
    post(RECEIPT_TYPE, {
      version: VERSION,
      projection_digest: value.projection_digest,
      state_digest: value.state_digest,
      as_built_scene_digest: value.as_built_scene_digest,
      as_built_frame_id: value.as_built_frame_id,
      as_built_entity_id: value.as_built_entity_id,
      selected_issue_id: value.selected_issue_id,
      timeline_day: value.timeline_day,
      overlays: value.overlays,
      render_receipt: renderReceipt,
      client_reported: true,
      renderer_authority: false,
      construction_truth: false,
      physical_work_authorized: false,
    });
  } catch (error) {
    post(RECEIPT_TYPE, {
      version: VERSION,
      projection_digest: requested?.projection_digest || "",
      ok: false,
      error: String(error?.message || error),
      client_reported: true,
      renderer_authority: false,
      construction_truth: false,
      physical_work_authorized: false,
    });
  } finally {
    applying = false;
    if (latest !== requested) void apply();
  }
}

async function initialize() {
  const response = await fetch("/api/construction-demo", {
    credentials: "same-origin",
    cache: "no-store",
  });
  const candidate = await response.json();
  if (!response.ok || candidate.ok !== true) {
    throw new Error(`Aura as-built packet failed with ${response.status}`);
  }
  if (!HEX64.test(candidate.state_digest) || !HEX64.test(candidate.scene?.scene_digest)) {
    throw new Error("Aura as-built packet lacks exact current identities");
  }
  packet = candidate;
  resizeCanvas();
  const drawMeshPass = createConstructionWireframePass({
    overlay: meshOverlay,
    getCamera: () => renderer?.presentationRenderer?.camera,
    getCanvas: () => canvas,
  });
  const localRenderer = createConstructionWebGL2SceneRenderer({
    canvas,
    drawMeshPass,
    drawOverlayPass: async () => () => {},
    maxVisibleSplats: 250_000,
  });
  try {
    await localRenderer.initialize(packet.scene, packet.render_plan, {
      meshPayloads: meshPayloads(packet.scene),
      gaussianPayloads: gaussianPayloads(packet.scene),
    });
    localRenderer.setRepresentationMode("HYBRID");
    renderer = localRenderer;
    await present();
    post(READY_TYPE, {
      version: VERSION,
      state_digest: packet.state_digest,
      as_built_scene_digest: packet.scene.scene_digest,
      renderer_authority: false,
      construction_truth: false,
    });
    void apply();
  } catch (error) {
    localRenderer.dispose?.();
    if (renderer === localRenderer) {
      renderer = null;
    }
    throw error;
  }
}

window.addEventListener("message", (event) => {
  if (event.origin !== location.origin || event.source !== parent) return;
  const envelope = event.data;
  if (!envelope || envelope.type !== MESSAGE_TYPE) return;
  latest = envelope.payload;
  void apply();
});
window.addEventListener("resize", () => {
  if (renderer) void present();
});
window.addEventListener("beforeunload", () => renderer?.dispose?.());

initialize().catch((error) => {
  statusNode.textContent = "Failed closed";
  intentNode.textContent = String(error?.message || error);
  post(RECEIPT_TYPE, {
    version: VERSION,
    ok: false,
    error: String(error?.message || error),
    client_reported: true,
    renderer_authority: false,
    construction_truth: false,
    physical_work_authorized: false,
  });
});
