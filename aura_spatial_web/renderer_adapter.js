export const RENDERER_ADAPTER_VERSION = "AURA_SPATIAL_RENDERER_ADAPTER_V1";
export const RENDERER_STATES = Object.freeze({
  NEW: "NEW",
  INITIALIZED: "INITIALIZED",
  PRESENTED: "PRESENTED",
  LOST: "LOST",
  DISPOSED: "DISPOSED",
});
export const AUTHORITY_ENVELOPE = Object.freeze({
  projection_only: true,
  renderer_authority: false,
  execution_authority: false,
  patch_authority: false,
  production_mutation: false,
  automatic_merge: false,
  human_review_required: true,
});

const ID = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$/;
const DIGEST = /^[0-9a-f]{64}$/;
const CONTENT_DIGEST = /^(sha256|blake2b-256):[0-9a-f]{64}$/;
const CONTROL = /[\u0000-\u001f\u007f]/;
const RENDERERS = new Set([
  "WEBXR",
  "WEBGPU",
  "WEBGL2",
  "ACCESSIBLE_2D",
  "HEADLESS",
]);
const HANDEDNESS = new Set(["RIGHT_HANDED", "LEFT_HANDED"]);
const UP_AXES = new Set(["X_UP", "Y_UP", "Z_UP"]);
const TRUTH_CLASSES = new Set(["EXACT", "DERIVED", "PRESENTATION", "HYPOTHESIS"]);
const SCENE_KEYS = new Set([
  "scene_id",
  "purpose_digest",
  "root_frame_id",
  "frames",
  "assets",
  "entities",
  "links",
  "source_refs",
  "renderer_hints",
  "truth_policy",
  "patch_authority",
  "vsa_patch_authority",
  "execution_authority",
  "version",
  "schema_version",
  "scene_digest",
]);
const FRAME_KEYS = new Set([
  "frame_id",
  "parent_frame_id",
  "handedness",
  "up_axis",
  "unit_scale_meters",
  "translation",
  "rotation_xyzw",
  "scale",
  "source_refs",
  "truth_class",
  "projection_only",
]);
const ASSET_KEYS = new Set([
  "asset_id",
  "asset_type",
  "uri",
  "media_type",
  "content_digest",
  "byte_length",
  "frame_id",
  "bounds_min",
  "bounds_max",
  "source_refs",
  "truth_class",
  "immutable",
  "metadata",
]);
const ENTITY_KEYS = new Set([
  "entity_id",
  "entity_type",
  "label",
  "frame_id",
  "asset_ids",
  "source_refs",
  "position",
  "rotation_xyzw",
  "scale",
  "truth_class",
  "selectable",
  "projection_only",
  "patch_authority",
  "metadata",
]);
const LINK_KEYS = new Set([
  "link_id",
  "source_entity_id",
  "target_entity_id",
  "relation",
  "source_refs",
  "truth_class",
  "directed",
  "projection_only",
  "metadata",
]);
const PLAN_KEYS = new Set([
  "plan_id",
  "scene_id",
  "scene_digest",
  "device_profile_digest",
  "selected_renderer",
  "fallback_renderers",
  "budget",
  "scene_entity_count",
  "scene_link_count",
  "scene_asset_count",
  "scene_asset_bytes",
  "reasons",
  "source_refs",
  "accessible_fallback_required",
  "xr_user_activation_observed",
  "projection_only",
  "renderer_authority",
  "execution_authority",
  "patch_authority",
  "version",
  "schema_version",
  "render_plan_digest",
]);
const BUDGET_KEYS = new Set([
  "max_entities",
  "max_links",
  "max_assets",
  "max_asset_bytes",
  "max_cpu_ms_per_frame",
  "max_gpu_bytes",
  "max_network_bytes",
]);
const HARD_LIMITS = Object.freeze({
  frames: 10_000,
  entities: 10_000,
  links: 40_000,
  assets: 4_096,
  assetBytes: 1_099_511_627_776,
  gpuBytes: 1_099_511_627_776,
  networkBytes: 1_099_511_627_776,
  sourceRefs: 256,
  sourceRefBytes: 2_048,
});

function assertPlainObject(value, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError(`${label} must be an object`);
  }
  return value;
}

function assertExactKeys(value, expected, label) {
  assertPlainObject(value, label);
  const keys = Object.keys(value);
  if (keys.length !== expected.size || keys.some((key) => !expected.has(key))) {
    throw new TypeError(`${label} keys mismatch`);
  }
}

function assertIdentifier(value, label) {
  const text = String(value || "");
  if (!ID.test(text)) throw new TypeError(`${label} is invalid`);
  return text;
}

function assertDigest(value, label) {
  const text = String(value || "");
  if (!DIGEST.test(text)) throw new TypeError(`${label} must be lowercase sha256`);
  return text;
}

function boundedText(value, label, maximum = 512) {
  const text = String(value ?? "");
  if (CONTROL.test(text) || new TextEncoder().encode(text).length > maximum) {
    throw new TypeError(`${label} exceeds its text boundary`);
  }
  return text;
}

function boundedLimit(value, label, hardMaximum) {
  if (!Number.isInteger(value) || value < 1 || value > hardMaximum) {
    throw new RangeError(`${label} must be an integer in [1, ${hardMaximum}]`);
  }
  return value;
}

function boundedNonNegativeInteger(value, label, hardMaximum) {
  if (!Number.isInteger(value) || value < 0 || value > hardMaximum) {
    throw new RangeError(`${label} must be an integer in [0, ${hardMaximum}]`);
  }
  return value;
}

function boundedPositiveNumber(value, label, hardMaximum) {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0 || value > hardMaximum) {
    throw new RangeError(`${label} must be finite and in (0, ${hardMaximum}]`);
  }
  return value;
}

function normalizeRefs(value, label) {
  if (!Array.isArray(value) || value.length > HARD_LIMITS.sourceRefs) {
    throw new TypeError(`${label} must be a bounded array`);
  }
  const refs = [...new Set(value.map((item) => boundedText(item, label, HARD_LIMITS.sourceRefBytes)))].sort();
  return Object.freeze(refs);
}

const MAX_METADATA_DEPTH = 8;
const MAX_METADATA_ITEMS = 512;
const MAX_METADATA_BYTES = 65_536;

function normalizeMetadata(value, label, depth = 0, counter = { items: 0 }) {
  if (depth > MAX_METADATA_DEPTH) throw new RangeError(`${label} nesting ceiling exceeded`);
  counter.items += 1;
  if (counter.items > MAX_METADATA_ITEMS) throw new RangeError(`${label} item ceiling exceeded`);
  if (value === null || typeof value === "boolean" || typeof value === "string") return value;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new TypeError(`${label} numbers must be finite`);
    return value;
  }
  if (Array.isArray(value)) {
    return Object.freeze(value.map((item) => normalizeMetadata(item, label, depth + 1, counter)));
  }
  if (!value || typeof value !== "object" || Object.getPrototypeOf(value) !== Object.prototype) {
    throw new TypeError(`${label} must be bounded JSON-compatible metadata`);
  }
  const output = {};
  for (const key of Object.keys(value).sort()) {
    boundedText(key, `${label} key`, 256);
    output[key] = normalizeMetadata(value[key], label, depth + 1, counter);
  }
  return Object.freeze(output);
}

function boundedMetadata(value, label) {
  const normalized = normalizeMetadata(value, label);
  let serialized;
  try {
    serialized = JSON.stringify(normalized);
  } catch (error) {
    throw new TypeError(`${label} must be JSON-compatible`, { cause: error });
  }
  if (new TextEncoder().encode(serialized).length > MAX_METADATA_BYTES) {
    throw new RangeError(`${label} byte ceiling exceeded`);
  }
  return normalized;
}

export function assertFiniteVector(value, length, label, { positive = false } = {}) {
  if (
    !Array.isArray(value) ||
    value.length !== length ||
    value.some(
      (item) =>
        typeof item !== "number" ||
        !Number.isFinite(item) ||
        (positive && item <= 0),
    )
  ) {
    throw new TypeError(
      `${label} must be a finite ${length}-vector${positive ? " with positive values" : ""}`,
    );
  }
  return Object.freeze([...value]);
}

export function validateSceneProjection(
  scene,
  {
    maxEntities = HARD_LIMITS.entities,
    maxLinks = HARD_LIMITS.links,
    maxAssets = HARD_LIMITS.assets,
  } = {},
) {
  assertExactKeys(scene, SCENE_KEYS, "scene");
  const entityLimit = boundedLimit(maxEntities, "maxEntities", HARD_LIMITS.entities);
  const linkLimit = boundedLimit(maxLinks, "maxLinks", HARD_LIMITS.links);
  const assetLimit = boundedLimit(maxAssets, "maxAssets", HARD_LIMITS.assets);
  const sceneId = assertIdentifier(scene.scene_id, "scene_id");
  const sceneDigest = assertDigest(scene.scene_digest, "scene_digest");
  const rootFrameId = assertIdentifier(scene.root_frame_id, "root_frame_id");
  boundedText(scene.purpose_digest, "purpose_digest", 2_048);
  boundedText(scene.truth_policy, "truth_policy", 4_096);
  if (scene.version !== "AURA_SPATIAL_CONTRACTS_V1" || scene.schema_version !== "1.0") {
    throw new TypeError("scene version boundary is invalid");
  }
  if (
    scene.execution_authority !== false ||
    scene.vsa_patch_authority !== false ||
    scene.patch_authority !== "exact_source_spans_and_hashes_only"
  ) {
    throw new TypeError("scene authority boundary is invalid");
  }
  if (!Array.isArray(scene.frames) || scene.frames.length < 1 || scene.frames.length > HARD_LIMITS.frames) {
    throw new RangeError("scene frames exceeds renderer budget");
  }
  for (const [key, limit] of [
    ["entities", entityLimit],
    ["links", linkLimit],
    ["assets", assetLimit],
  ]) {
    if (!Array.isArray(scene[key]) || scene[key].length > limit) {
      throw new RangeError(`scene ${key} exceeds renderer budget`);
    }
  }

  const frameIds = new Set();
  const frames = scene.frames
    .map((frame) => {
      assertExactKeys(frame, FRAME_KEYS, "frame");
      const frameId = assertIdentifier(frame.frame_id, "frame_id");
      if (frameIds.has(frameId)) throw new TypeError("frame identity is duplicated");
      frameIds.add(frameId);
      const parentFrameId = frame.parent_frame_id === null
        ? null
        : assertIdentifier(frame.parent_frame_id, "parent_frame_id");
      if (!HANDEDNESS.has(frame.handedness) || !UP_AXES.has(frame.up_axis)) {
        throw new TypeError("frame coordinate convention is invalid");
      }
      boundedPositiveNumber(frame.unit_scale_meters, `frame ${frameId} unit_scale_meters`, 1_000_000);
      assertFiniteVector(frame.translation, 3, `frame ${frameId} translation`);
      const rotation = assertFiniteVector(frame.rotation_xyzw, 4, `frame ${frameId} rotation_xyzw`);
      if (rotation.every((value) => value === 0)) throw new TypeError("frame quaternion cannot be zero");
      assertFiniteVector(frame.scale, 3, `frame ${frameId} scale`, { positive: true });
      normalizeRefs(frame.source_refs, `frame ${frameId} source_refs`);
      if (!TRUTH_CLASSES.has(frame.truth_class) || frame.projection_only !== true) {
        throw new TypeError("frame projection boundary is invalid");
      }
      return Object.freeze({ frame_id: frameId, parent_frame_id: parentFrameId });
    })
    .sort((a, b) => a.frame_id.localeCompare(b.frame_id));
  if (!frameIds.has(rootFrameId)) throw new TypeError("root frame is missing");
  for (const frame of frames) {
    if (frame.frame_id === rootFrameId && frame.parent_frame_id !== null) {
      throw new TypeError("root frame must not have a parent");
    }
    if (frame.parent_frame_id !== null && !frameIds.has(frame.parent_frame_id)) {
      throw new TypeError("frame references an unknown parent");
    }
  }

  const assetIds = new Set();
  const assets = scene.assets
    .map((asset) => {
      assertExactKeys(asset, ASSET_KEYS, "asset");
      const assetId = assertIdentifier(asset.asset_id, "asset_id");
      if (assetIds.has(assetId)) throw new TypeError("asset identity is duplicated");
      assetIds.add(assetId);
      if (asset.immutable !== true) throw new TypeError("asset must remain immutable");
      if (!CONTENT_DIGEST.test(String(asset.content_digest || ""))) {
        throw new TypeError("asset content_digest is invalid");
      }
      boundedNonNegativeInteger(asset.byte_length, "asset byte_length", HARD_LIMITS.assetBytes);
      const frameId = assertIdentifier(asset.frame_id, "asset frame_id");
      if (!frameIds.has(frameId)) throw new TypeError("asset references an unknown frame");
      boundedText(asset.uri, `asset ${assetId} uri`, 4_096);
      boundedText(asset.media_type, `asset ${assetId} media_type`, 256);
      if (!TRUTH_CLASSES.has(asset.truth_class)) throw new TypeError("asset truth_class is invalid");
      const boundsMin = assertFiniteVector(asset.bounds_min, 3, `asset ${assetId} bounds_min`);
      const boundsMax = assertFiniteVector(asset.bounds_max, 3, `asset ${assetId} bounds_max`);
      if (boundsMin.some((value, index) => value > boundsMax[index])) {
        throw new TypeError("asset bounds are inverted");
      }
      return Object.freeze({
        asset_id: assetId,
        asset_type: assertIdentifier(asset.asset_type, "asset_type"),
        content_digest: asset.content_digest,
        byte_length: asset.byte_length,
        frame_id: frameId,
        bounds_min: boundsMin,
        bounds_max: boundsMax,
        source_refs: normalizeRefs(asset.source_refs, `asset ${assetId} source_refs`),
        metadata: boundedMetadata(asset.metadata, `asset ${assetId} metadata`),
      });
    })
    .sort((a, b) => a.asset_id.localeCompare(b.asset_id));

  const entityIds = new Set();
  const entities = scene.entities
    .map((entity) => {
      assertExactKeys(entity, ENTITY_KEYS, "entity");
      const id = assertIdentifier(entity.entity_id, "entity_id");
      if (entityIds.has(id)) throw new TypeError("entity identity is duplicated");
      entityIds.add(id);
      if (entity.projection_only !== true || entity.patch_authority !== false) {
        throw new TypeError("entity authority boundary is invalid");
      }
      if (!Array.isArray(entity.asset_ids) || entity.asset_ids.length > 256) {
        throw new TypeError("entity asset_ids must be bounded");
      }
      const frameId = assertIdentifier(entity.frame_id, "entity frame_id");
      if (!frameIds.has(frameId)) throw new TypeError("entity references an unknown frame");
      const entityAssetIds = [...new Set(entity.asset_ids.map((value) => assertIdentifier(value, "entity asset_id")))].sort();
      for (const assetId of entityAssetIds) {
        if (!assetIds.has(assetId)) throw new TypeError("entity references an unknown asset");
      }
      const rotation = assertFiniteVector(entity.rotation_xyzw, 4, `entity ${id} rotation_xyzw`);
      if (rotation.every((value) => value === 0)) throw new TypeError("entity quaternion cannot be zero");
      if (!TRUTH_CLASSES.has(entity.truth_class) || typeof entity.selectable !== "boolean") {
        throw new TypeError("entity presentation fields are invalid");
      }
      return Object.freeze({
        entity_id: id,
        entity_type: assertIdentifier(entity.entity_type, "entity_type"),
        label: boundedText(entity.label, `entity ${id} label`),
        frame_id: frameId,
        position: assertFiniteVector(entity.position, 3, `entity ${id} position`),
        rotation_xyzw: rotation,
        scale: assertFiniteVector(entity.scale, 3, `entity ${id} scale`, { positive: true }),
        selectable: entity.selectable === true,
        asset_ids: Object.freeze(entityAssetIds),
        source_refs: normalizeRefs(entity.source_refs, `entity ${id} source_refs`),
      });
    })
    .sort((a, b) => a.entity_id.localeCompare(b.entity_id));

  const linkIds = new Set();
  const links = scene.links
    .map((link) => {
      assertExactKeys(link, LINK_KEYS, "link");
      const linkId = assertIdentifier(link.link_id, "link_id");
      if (linkIds.has(linkId)) throw new TypeError("link identity is duplicated");
      linkIds.add(linkId);
      const source = assertIdentifier(link.source_entity_id, "link source_entity_id");
      const target = assertIdentifier(link.target_entity_id, "link target_entity_id");
      if (
        !entityIds.has(source) ||
        !entityIds.has(target) ||
        source === target ||
        link.projection_only !== true
      ) {
        throw new TypeError("link referential integrity is invalid");
      }
      if (typeof link.directed !== "boolean") throw new TypeError("link directed must be boolean");
      if (!TRUTH_CLASSES.has(link.truth_class)) throw new TypeError("link truth_class is invalid");
      return Object.freeze({
        link_id: linkId,
        source_entity_id: source,
        target_entity_id: target,
        relation: assertIdentifier(link.relation, "link relation"),
        directed: link.directed,
        source_refs: normalizeRefs(link.source_refs, `link ${linkId} source_refs`),
      });
    })
    .sort((a, b) => a.link_id.localeCompare(b.link_id));

  return Object.freeze({
    scene_id: sceneId,
    scene_digest: sceneDigest,
    root_frame_id: rootFrameId,
    frames: Object.freeze(frames),
    entities: Object.freeze(entities),
    links: Object.freeze(links),
    assets: Object.freeze(assets),
    authority: AUTHORITY_ENVELOPE,
  });
}

export function validateRenderPlan(plan, scene) {
  assertExactKeys(plan, PLAN_KEYS, "render plan");
  const planId = assertIdentifier(plan.plan_id, "plan_id");
  const renderPlanDigest = assertDigest(plan.render_plan_digest, "render_plan_digest");
  const deviceProfileDigest = assertDigest(plan.device_profile_digest, "device_profile_digest");
  if (plan.scene_id !== scene.scene_id || plan.scene_digest !== scene.scene_digest) {
    throw new TypeError("render plan is stale for scene");
  }
  if (!RENDERERS.has(plan.selected_renderer)) {
    throw new TypeError("unsupported selected renderer");
  }
  if (!Array.isArray(plan.fallback_renderers) || plan.fallback_renderers.length > RENDERERS.size) {
    throw new TypeError("fallback_renderers must be bounded");
  }
  const fallback = [...new Set(plan.fallback_renderers.map(String))];
  if (
    fallback.length !== plan.fallback_renderers.length ||
    fallback.some((renderer) => !RENDERERS.has(renderer) || renderer === plan.selected_renderer)
  ) {
    throw new TypeError("fallback_renderers are invalid");
  }
  if (!fallback.includes("ACCESSIBLE_2D") && plan.selected_renderer !== "ACCESSIBLE_2D") {
    throw new TypeError("ACCESSIBLE_2D fallback is required");
  }
  if (
    plan.projection_only !== true ||
    plan.renderer_authority !== false ||
    plan.execution_authority !== false ||
    plan.patch_authority !== false
  ) {
    throw new TypeError("render plan authority boundary is invalid");
  }
  if (
    plan.accessible_fallback_required !== true ||
    typeof plan.xr_user_activation_observed !== "boolean" ||
    plan.version !== "AURA_SPATIAL_RENDER_CONTRACTS_V1" ||
    plan.schema_version !== "1.0"
  ) {
    throw new TypeError("render plan contract boundary is invalid");
  }
  if (plan.selected_renderer === "WEBXR" && plan.xr_user_activation_observed !== true) {
    throw new TypeError("WEBXR requires observed user activation");
  }
  assertExactKeys(plan.budget, BUDGET_KEYS, "render plan budget");
  const budget = Object.freeze({
    max_entities: boundedLimit(plan.budget.max_entities, "budget.max_entities", 1_000_000),
    max_links: boundedNonNegativeInteger(plan.budget.max_links, "budget.max_links", 4_000_000),
    max_assets: boundedNonNegativeInteger(plan.budget.max_assets, "budget.max_assets", 100_000),
    max_asset_bytes: boundedNonNegativeInteger(plan.budget.max_asset_bytes, "budget.max_asset_bytes", HARD_LIMITS.assetBytes),
    max_cpu_ms_per_frame: boundedPositiveNumber(plan.budget.max_cpu_ms_per_frame, "budget.max_cpu_ms_per_frame", 10_000),
    max_gpu_bytes: boundedNonNegativeInteger(plan.budget.max_gpu_bytes, "budget.max_gpu_bytes", HARD_LIMITS.gpuBytes),
    max_network_bytes: boundedNonNegativeInteger(plan.budget.max_network_bytes, "budget.max_network_bytes", HARD_LIMITS.networkBytes),
  });
  const countPairs = [
    ["scene_entity_count", "max_entities", scene.entities.length],
    ["scene_link_count", "max_links", scene.links.length],
    ["scene_asset_count", "max_assets", scene.assets.length],
  ];
  for (const [countName, budgetName, actual] of countPairs) {
    if (plan[countName] !== actual || actual > budget[budgetName]) {
      throw new RangeError(`render plan ${countName} is inconsistent with ${budgetName}`);
    }
  }
  const sceneAssetBytes = scene.assets.reduce((total, asset) => total + asset.byte_length, 0);
  if (
    !Number.isInteger(plan.scene_asset_bytes) ||
    plan.scene_asset_bytes !== sceneAssetBytes ||
    plan.scene_asset_bytes > budget.max_asset_bytes
  ) {
    throw new RangeError("render plan scene_asset_bytes is inconsistent with max_asset_bytes");
  }
  const reasons = normalizeRefs(plan.reasons, "render plan reasons");
  const sourceRefs = normalizeRefs(plan.source_refs, "render plan source_refs");
  if (reasons.length < 1 || sourceRefs.length < 1) {
    throw new TypeError("render plan reasons and source_refs must not be empty");
  }
  return Object.freeze({
    plan_id: planId,
    scene_id: scene.scene_id,
    scene_digest: scene.scene_digest,
    render_plan_digest: renderPlanDigest,
    device_profile_digest: deviceProfileDigest,
    selected_renderer: plan.selected_renderer,
    fallback_renderers: Object.freeze(fallback),
    budget,
    scene_entity_count: plan.scene_entity_count,
    scene_link_count: plan.scene_link_count,
    scene_asset_count: plan.scene_asset_count,
    scene_asset_bytes: plan.scene_asset_bytes,
    reasons,
    source_refs: sourceRefs,
    accessible_fallback_required: true,
    xr_user_activation_observed: plan.xr_user_activation_observed,
    projection_only: true,
    renderer_authority: false,
    execution_authority: false,
    patch_authority: false,
    version: plan.version,
    schema_version: plan.schema_version,
  });
}

export class RendererAdapter {
  constructor(kind) {
    if (!RENDERERS.has(kind)) throw new TypeError(`unsupported renderer kind: ${kind}`);
    this.kind = kind;
    this.state = RENDERER_STATES.NEW;
    this.scene = null;
    this.plan = null;
    this.resources = new Set();
  }

  initialize(scenePayload, planPayload) {
    if (this.state !== RENDERER_STATES.NEW) {
      throw new Error("renderer may initialize only once");
    }
    this.scene = validateSceneProjection(scenePayload);
    this.plan = validateRenderPlan(planPayload, this.scene);
    if (
      this.plan.selected_renderer !== this.kind &&
      !this.plan.fallback_renderers.includes(this.kind)
    ) {
      throw new Error("renderer is not admitted by plan");
    }
    this.state = RENDERER_STATES.INITIALIZED;
    return this.status();
  }

  present() {
    throw new Error("present() must be implemented by an adapter");
  }

  markPresented() {
    if (this.state !== RENDERER_STATES.INITIALIZED) {
      throw new Error("renderer is not initialized");
    }
    this.state = RENDERER_STATES.PRESENTED;
  }

  dispose() {
    this.resources.clear();
    this.scene = null;
    this.plan = null;
    this.state = RENDERER_STATES.DISPOSED;
    return this.status();
  }

  status() {
    return Object.freeze({
      version: RENDERER_ADAPTER_VERSION,
      renderer: this.kind,
      state: this.state,
      resource_count: this.resources.size,
      ...AUTHORITY_ENVELOPE,
    });
  }
}
