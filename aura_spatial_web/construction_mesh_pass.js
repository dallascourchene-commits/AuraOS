import {
  AUTHORITY_ENVELOPE,
  RENDERER_STATES,
  validateRenderPlan,
  validateSceneProjection,
} from "./renderer_adapter.js";

export const CONSTRUCTION_MESH_PASS_VERSION = "AURA_CONSTRUCTION_MESH_PASS_V1";

const DIGEST = /^[0-9a-f]{64}$/;
const MAX_MESH_ASSETS = 256;
const MAX_MESH_ELEMENTS = 20_000_000;

function finiteVector(value, length, label) {
  if (
    !Array.isArray(value) ||
    value.length !== length ||
    value.some((item) => typeof item !== "number" || !Number.isFinite(item))
  ) {
    throw new TypeError(`${label} must be a finite ${length}-vector`);
  }
  return Object.freeze([...value]);
}

function boundedCount(value, label) {
  if (!Number.isInteger(value) || value < 0 || value > MAX_MESH_ELEMENTS) {
    throw new RangeError(`${label} must be an integer in [0, ${MAX_MESH_ELEMENTS}]`);
  }
  return value;
}

function requireDisposer(value) {
  if (typeof value === "function") return value;
  if (value && typeof value.dispose === "function") return value.dispose.bind(value);
  throw new TypeError("construction mesh draw pass must return a disposer");
}

function preflightMeshPayload(payload, manifest, plan) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new TypeError("construction mesh payload must be an object");
  }
  const keys = new Set(Object.keys(payload));
  const expected = new Set([
    "asset_id",
    "source_digest",
    "vertex_count",
    "index_count",
    "gpu_bytes",
    "bounds_min",
    "bounds_max",
    "resource",
  ]);
  if (keys.size !== expected.size || [...keys].some((key) => !expected.has(key))) {
    throw new TypeError("construction mesh payload keys mismatch");
  }
  if (payload.asset_id !== manifest.asset_id) {
    throw new TypeError("construction mesh asset identity mismatch");
  }
  const sourceDigest = String(payload.source_digest || "");
  if (!DIGEST.test(sourceDigest)) {
    throw new TypeError("construction mesh source_digest must be lowercase sha256");
  }
  if (sourceDigest !== manifest.content_digest.split(":", 2)[1]) {
    throw new TypeError("construction mesh source digest is stale or ambiguous");
  }
  const vertexCount = boundedCount(payload.vertex_count, "construction mesh vertex_count");
  const indexCount = boundedCount(payload.index_count, "construction mesh index_count");
  if (indexCount > 0 && indexCount % 3 !== 0) {
    throw new TypeError("construction mesh indices must describe triangles");
  }
  if (!Number.isInteger(payload.gpu_bytes) || payload.gpu_bytes < 0) {
    throw new RangeError("construction mesh gpu_bytes must be non-negative");
  }
  if (
    payload.gpu_bytes > plan.budget.max_gpu_bytes ||
    payload.gpu_bytes > plan.budget.max_asset_bytes
  ) {
    throw new RangeError("construction mesh allocation exceeds render plan");
  }
  const boundsMin = finiteVector(payload.bounds_min, 3, "construction mesh bounds_min");
  const boundsMax = finiteVector(payload.bounds_max, 3, "construction mesh bounds_max");
  if (boundsMin.some((value, index) => value > boundsMax[index])) {
    throw new TypeError("construction mesh bounds are inverted");
  }
  if (payload.resource === null || payload.resource === undefined) {
    throw new TypeError("construction mesh payload requires a retained resource");
  }
  return Object.freeze({
    asset_id: payload.asset_id,
    source_digest: sourceDigest,
    vertex_count: vertexCount,
    index_count: indexCount,
    gpu_bytes: payload.gpu_bytes,
    bounds_min: boundsMin,
    bounds_max: boundsMax,
    resource: payload.resource,
    frame_id: manifest.frame_id,
  });
}

export class ConstructionMeshPass {
  constructor({ drawMesh, releaseMesh = null } = {}) {
    if (typeof drawMesh !== "function") {
      throw new TypeError("ConstructionMeshPass requires drawMesh");
    }
    if (releaseMesh !== null && typeof releaseMesh !== "function") {
      throw new TypeError("releaseMesh must be callable when supplied");
    }
    this.drawMesh = drawMesh;
    this.releaseMesh = releaseMesh;
    this.state = RENDERER_STATES.NEW;
    this.scene = null;
    this.plan = null;
    this.assets = Object.freeze([]);
    this.visibleAssetIds = new Set();
    this.disposers = new Set();
    this.cancelled = false;
  }

  initialize(scenePayload, planPayload, meshPayloads, { signal } = {}) {
    if (this.state !== RENDERER_STATES.NEW) {
      throw new Error("Construction mesh pass may initialize only once");
    }
    if (signal?.aborted) throw new Error("Construction mesh initialization cancelled");
    this.scene = validateSceneProjection(scenePayload);
    this.plan = validateRenderPlan(planPayload, this.scene);
    if (!Array.isArray(meshPayloads)) {
      throw new TypeError("meshPayloads must be an array");
    }
    const manifests = new Map(
      this.scene.assets
        .filter((asset) => asset.asset_type === "MESH")
        .map((asset) => [asset.asset_id, asset]),
    );
    if (manifests.size > MAX_MESH_ASSETS) {
      throw new RangeError("construction mesh asset count exceeds its boundary");
    }
    if (meshPayloads.length !== manifests.size) {
      throw new TypeError("meshPayloads must exactly cover scene mesh manifests");
    }
    const seen = new Set();
    const admitted = [];
    for (const payload of meshPayloads) {
      if (signal?.aborted) throw new Error("Construction mesh initialization cancelled");
      if (seen.has(payload?.asset_id)) {
        throw new TypeError("construction mesh payload is duplicated");
      }
      seen.add(payload?.asset_id);
      const manifest = manifests.get(payload?.asset_id);
      if (!manifest) throw new TypeError("construction mesh payload is not admitted by scene");
      admitted.push(preflightMeshPayload(payload, manifest, this.plan));
    }
    const totalGpuBytes = admitted.reduce((total, asset) => total + asset.gpu_bytes, 0);
    if (totalGpuBytes > this.plan.budget.max_gpu_bytes) {
      throw new RangeError("construction mesh aggregate GPU budget exceeded");
    }
    this.assets = Object.freeze([...admitted].sort((left, right) => left.asset_id.localeCompare(right.asset_id)));
    this.visibleAssetIds = new Set(this.assets.map((asset) => asset.asset_id));
    this.state = RENDERER_STATES.INITIALIZED;
    return this.status();
  }

  setVisibleAssets(assetIds) {
    if (!Array.isArray(assetIds)) throw new TypeError("assetIds must be an array");
    const admitted = new Set(this.assets.map((asset) => asset.asset_id));
    const next = new Set();
    for (const assetId of assetIds) {
      if (!admitted.has(assetId)) throw new TypeError("visible mesh asset is not admitted");
      next.add(assetId);
    }
    this.visibleAssetIds = next;
    return Object.freeze([...next].sort());
  }

  async present({ explodedOffsets = {}, signal } = {}) {
    if (![RENDERER_STATES.INITIALIZED, RENDERER_STATES.PRESENTED].includes(this.state)) {
      throw new Error("Construction mesh pass is not initialized");
    }
    if (signal?.aborted || this.cancelled) throw new Error("Construction mesh presentation cancelled");
    if (!explodedOffsets || typeof explodedOffsets !== "object" || Array.isArray(explodedOffsets)) {
      throw new TypeError("explodedOffsets must be an object");
    }
    let drawn = 0;
    let gpuBytes = 0;
    try {
      for (const asset of this.assets) {
        if (!this.visibleAssetIds.has(asset.asset_id)) continue;
        if (signal?.aborted || this.cancelled) throw new Error("Construction mesh presentation cancelled");
        const offset = Object.hasOwn(explodedOffsets, asset.frame_id)
          ? finiteVector(explodedOffsets[asset.frame_id], 3, "construction exploded offset")
          : Object.freeze([0, 0, 0]);
        const disposer = requireDisposer(
          await this.drawMesh(
            asset.resource,
            Object.freeze({
              asset_id: asset.asset_id,
              frame_id: asset.frame_id,
              exploded_offset: offset,
              scene_digest: this.scene.scene_digest,
              render_plan_digest: this.plan.render_plan_digest,
              signal,
              ...AUTHORITY_ENVELOPE,
            }),
          ),
        );
        this.disposers.add(disposer);
        drawn += 1;
        gpuBytes += asset.gpu_bytes;
      }
    } catch (error) {
      await this._releaseDrawResources();
      this.cancelled = true;
      this.state = RENDERER_STATES.LOST;
      throw error;
    }
    this.state = RENDERER_STATES.PRESENTED;
    return Object.freeze({
      version: CONSTRUCTION_MESH_PASS_VERSION,
      representation: "GLB_MESH_PASS",
      outcome: "PRESENTED",
      scene_digest: this.scene.scene_digest,
      render_plan_digest: this.plan.render_plan_digest,
      drawn_asset_count: drawn,
      gpu_bytes: gpuBytes,
      visible_asset_ids: Object.freeze([...this.visibleAssetIds].sort()),
      ...AUTHORITY_ENVELOPE,
    });
  }

  async _releaseDrawResources() {
    let firstError = null;
    for (const dispose of [...this.disposers].reverse()) {
      try {
        await dispose();
      } catch (error) {
        firstError ||= error;
      }
    }
    this.disposers.clear();
    if (firstError) throw firstError;
  }

  async markDeviceLost() {
    this.cancelled = true;
    try {
      await this._releaseDrawResources();
    } finally {
      this.state = RENDERER_STATES.LOST;
    }
    return this.status();
  }

  async dispose() {
    this.cancelled = true;
    let firstError = null;
    try {
      await this._releaseDrawResources();
    } catch (error) {
      firstError = error;
    }
    if (this.releaseMesh) {
      for (const asset of [...this.assets].reverse()) {
        try {
          await this.releaseMesh(asset.resource, asset.asset_id);
        } catch (error) {
          firstError ||= error;
        }
      }
    }
    this.assets = Object.freeze([]);
    this.visibleAssetIds.clear();
    this.scene = null;
    this.plan = null;
    if (firstError) {
      this.state = RENDERER_STATES.LOST;
      throw firstError;
    }
    this.state = RENDERER_STATES.DISPOSED;
    return this.status();
  }

  status() {
    return Object.freeze({
      version: CONSTRUCTION_MESH_PASS_VERSION,
      state: this.state,
      admitted_asset_count: this.assets.length,
      visible_asset_count: this.visibleAssetIds.size,
      disposer_count: this.disposers.size,
      ...AUTHORITY_ENVELOPE,
    });
  }
}
