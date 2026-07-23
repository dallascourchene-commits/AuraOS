import {
  AUTHORITY_ENVELOPE,
  validateSceneProjection,
} from "./renderer_adapter.js";

export const CONSTRUCTION_MESH_PASS_VERSION = "AURA_CONSTRUCTION_MESH_PASS_V1";

const DIGEST = /^[0-9a-f]{64}$/;
const DEFAULT_LIMITS = Object.freeze({
  maxVisibleMeshes: 64,
  maxDecodedBytes: 256 * 1024 * 1024,
});

function boundedInteger(value, label, maximum) {
  if (!Number.isInteger(value) || value < 1 || value > maximum) {
    throw new RangeError(`${label} must be an integer in [1, ${maximum}]`);
  }
  return value;
}

function finiteVector(value, length, label, { positive = false } = {}) {
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
    throw new TypeError(`${label} must be a finite ${length}-vector`);
  }
  return Object.freeze([...value]);
}

function canonicalTransform(value, label) {
  const source = value || {};
  return Object.freeze({
    translation: finiteVector(source.translation || [0, 0, 0], 3, `${label}.translation`),
    rotation_xyzw: finiteVector(
      source.rotation_xyzw || [0, 0, 0, 1],
      4,
      `${label}.rotation_xyzw`,
    ),
    scale: finiteVector(source.scale || [1, 1, 1], 3, `${label}.scale`, {
      positive: true,
    }),
  });
}

function requireDisposer(value) {
  if (typeof value === "function") return value;
  if (value && typeof value.dispose === "function") return value.dispose.bind(value);
  throw new TypeError("Construction mesh draw pass must return a disposal handle");
}

function normalizeLimits(input) {
  const source = { ...DEFAULT_LIMITS, ...(input || {}) };
  return Object.freeze({
    maxVisibleMeshes: boundedInteger(source.maxVisibleMeshes, "maxVisibleMeshes", 4096),
    maxDecodedBytes: boundedInteger(
      source.maxDecodedBytes,
      "maxDecodedBytes",
      1024 * 1024 * 1024,
    ),
  });
}

function admitMeshPayload(payload, manifest) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new TypeError("Construction mesh payload must be an object");
  }
  if (payload.asset_id !== manifest.asset_id) {
    throw new TypeError("Construction mesh payload identity mismatch");
  }
  const sourceDigest = String(payload.source_digest || "");
  if (!DIGEST.test(sourceDigest)) {
    throw new TypeError("Construction mesh source_digest must be lowercase sha256");
  }
  if (sourceDigest !== manifest.content_digest.split(":", 2)[1]) {
    throw new TypeError("Construction mesh payload is stale for its scene manifest");
  }
  if (!Number.isInteger(payload.decoded_byte_length) || payload.decoded_byte_length < 0) {
    throw new TypeError("Construction mesh decoded_byte_length must be non-negative");
  }
  if (!payload.resource || typeof payload.resource !== "object") {
    throw new TypeError("Construction mesh payload requires a decoded local resource");
  }
  return Object.freeze({
    asset_id: payload.asset_id,
    source_digest: sourceDigest,
    decoded_byte_length: payload.decoded_byte_length,
    resource: payload.resource,
    frame_id: manifest.frame_id,
    source_transform: canonicalTransform(
      manifest.metadata?.source_transform,
      "source_transform",
    ),
  });
}

export class ConstructionMeshPass {
  constructor({ drawMeshPass, limits = null } = {}) {
    if (typeof drawMeshPass !== "function") {
      throw new TypeError("ConstructionMeshPass requires drawMeshPass");
    }
    this.drawMeshPass = drawMeshPass;
    this.limits = normalizeLimits(limits);
    this.scene = null;
    this.meshes = Object.freeze([]);
    this.presentationTransforms = new Map();
    this.visibleFrameIds = null;
    this.disposers = new Set();
    this.initialized = false;
    this.disposed = false;
  }

  initialize(scenePayload, meshPayloads) {
    if (this.initialized || this.disposed) {
      throw new Error("Construction mesh pass may initialize only once");
    }
    this.scene = validateSceneProjection(scenePayload);
    if (!Array.isArray(meshPayloads)) {
      throw new TypeError("meshPayloads must be an array");
    }
    const manifests = new Map(
      this.scene.assets
        .filter((asset) => asset.asset_type === "MESH")
        .map((asset) => [asset.asset_id, asset]),
    );
    if (meshPayloads.length !== manifests.size) {
      throw new TypeError("meshPayloads must exactly cover scene mesh manifests");
    }
    const seen = new Set();
    const meshes = [];
    let totalBytes = 0;
    for (const payload of meshPayloads) {
      if (seen.has(payload?.asset_id)) {
        throw new TypeError("Construction mesh payload is duplicated");
      }
      seen.add(payload?.asset_id);
      const manifest = manifests.get(payload?.asset_id);
      if (!manifest) throw new TypeError("Construction mesh payload is not admitted by scene");
      const mesh = admitMeshPayload(payload, manifest);
      totalBytes += mesh.decoded_byte_length;
      if (!Number.isSafeInteger(totalBytes) || totalBytes > this.limits.maxDecodedBytes) {
        throw new RangeError("Construction mesh decoded-byte budget exceeded");
      }
      meshes.push(mesh);
    }
    this.meshes = Object.freeze(meshes.sort((a, b) => a.asset_id.localeCompare(b.asset_id)));
    for (const mesh of this.meshes) {
      this.presentationTransforms.set(
        mesh.frame_id,
        canonicalTransform(null, "presentation_transform"),
      );
    }
    this.initialized = true;
    return this.status();
  }

  setVisibleFrameIds(frameIds = null) {
    if (frameIds === null) {
      this.visibleFrameIds = null;
      return;
    }
    if (!Array.isArray(frameIds) || frameIds.some((item) => typeof item !== "string")) {
      throw new TypeError("visible frame IDs must be null or an array of strings");
    }
    this.visibleFrameIds = new Set(frameIds);
  }

  setPresentationTransform(frameId, transform) {
    if (!this.presentationTransforms.has(frameId)) {
      throw new RangeError("unknown Construction mesh frame");
    }
    this.presentationTransforms.set(
      frameId,
      canonicalTransform(transform, "presentation_transform"),
    );
  }

  resetPresentationTransforms() {
    for (const frameId of this.presentationTransforms.keys()) {
      this.presentationTransforms.set(
        frameId,
        canonicalTransform(null, "presentation_transform"),
      );
    }
  }

  async present({ signal } = {}) {
    if (!this.initialized || this.disposed) {
      throw new Error("Construction mesh pass is not initialized");
    }
    if (signal?.aborted) throw new Error("Construction mesh presentation cancelled");
    await this.releaseDrawResources();
    const visible = this.meshes.filter(
      (mesh) => this.visibleFrameIds === null || this.visibleFrameIds.has(mesh.frame_id),
    );
    if (visible.length > this.limits.maxVisibleMeshes) {
      throw new RangeError("Construction visible-mesh budget exceeded");
    }
    try {
      for (const mesh of visible) {
        if (signal?.aborted) throw new Error("Construction mesh presentation cancelled");
        const disposer = requireDisposer(
          await this.drawMeshPass(
            mesh.resource,
            Object.freeze({
              asset_id: mesh.asset_id,
              frame_id: mesh.frame_id,
              source_digest: mesh.source_digest,
              source_transform: mesh.source_transform,
              presentation_transform: this.presentationTransforms.get(mesh.frame_id),
              source_transform_immutable: true,
              ...AUTHORITY_ENVELOPE,
            }),
          ),
        );
        if (signal?.aborted) {
          await this.releaseDrawResources();
          this.initialized = false;
          this.disposed = true;
          throw new Error("Construction mesh presentation cancelled");
        }
        this.disposers.add(disposer);
      }
    } catch (error) {
      await this.releaseDrawResources();
      this.initialized = false;
      this.disposed = true;
      throw error;
    }
    return Object.freeze({
      version: CONSTRUCTION_MESH_PASS_VERSION,
      outcome: "PRESENTED",
      visible_mesh_count: visible.length,
      decoded_byte_length: visible.reduce(
        (total, item) => total + item.decoded_byte_length,
        0,
      ),
      source_transform_immutable: true,
      ...AUTHORITY_ENVELOPE,
    });
  }

  async releaseDrawResources() {
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

  async dispose() {
    if (this.disposed) return this.status();
    try {
      await this.releaseDrawResources();
    } finally {
      this.meshes = Object.freeze([]);
      this.presentationTransforms.clear();
      this.visibleFrameIds = null;
      this.scene = null;
      this.initialized = false;
      this.disposed = true;
    }
    return this.status();
  }

  status() {
    return Object.freeze({
      version: CONSTRUCTION_MESH_PASS_VERSION,
      initialized: this.initialized,
      disposed: this.disposed,
      admitted_mesh_count: this.meshes.length,
      active_disposer_count: this.disposers.size,
      source_transform_immutable: true,
      ...AUTHORITY_ENVELOPE,
    });
  }
}
