import {
  AUTHORITY_ENVELOPE,
  RENDERER_STATES,
  validateRenderPlan,
  validateSceneProjection,
} from "./renderer_adapter.js";

export const GAUSSIAN_REPRESENTATION_VERSION = "AURA_SPATIAL_GAUSSIAN_RENDERER_V1";
export const GAUSSIAN_FALLBACKS = Object.freeze([
  "POINT_CLOUD",
  "ACCESSIBLE_DESCRIPTION",
  "HEADLESS_PROOF",
]);

const DIGEST = /^[0-9a-f]{64}$/;
const DEFAULT_LIMITS = Object.freeze({
  maxVisibleSplats: 1_000_000,
  maxDecodedBytes: 192 * 1024 * 1024,
  maxGpuBytes: 256 * 1024 * 1024,
  maxSortItems: 1_000_000,
  maxAllocationBytes: 320 * 1024 * 1024,
  maxFrameMs: 50,
});
const GPU_BYTES_PER_SPLAT = 52;
const SORT_BYTES_PER_SPLAT = 4;

function finiteVector(value, length, label, { nonNegative = false } = {}) {
  if (
    !Array.isArray(value) ||
    value.length !== length ||
    value.some(
      (item) =>
        typeof item !== "number" ||
        !Number.isFinite(item) ||
        (nonNegative && item < 0),
    )
  ) {
    throw new TypeError(`${label} must be a finite ${length}-vector`);
  }
  return Object.freeze([...value]);
}

function boundedPositiveInteger(value, label, maximum) {
  if (!Number.isInteger(value) || value < 1 || value > maximum) {
    throw new RangeError(`${label} must be an integer in [1, ${maximum}]`);
  }
  return value;
}

function normalizeLimits(input, plan) {
  const overrides = input || {};
  const source = { ...DEFAULT_LIMITS, ...overrides };
  const planGpu = plan.budget.max_gpu_bytes;
  const planAllocation = plan.budget.max_asset_bytes;
  const maxGpuBytes = boundedPositiveInteger(
    Object.hasOwn(overrides, "maxGpuBytes") ? source.maxGpuBytes : Math.min(source.maxGpuBytes, planGpu),
    "maxGpuBytes",
    Math.max(1, planGpu),
  );
  if (maxGpuBytes > planGpu) throw new RangeError("Gaussian GPU budget exceeds render plan");
  const maxDecodedBytes = boundedPositiveInteger(
    Object.hasOwn(overrides, "maxDecodedBytes")
      ? source.maxDecodedBytes
      : Math.min(source.maxDecodedBytes, planAllocation),
    "maxDecodedBytes",
    512 * 1024 * 1024,
  );
  const maxAllocationBytes = boundedPositiveInteger(
    Object.hasOwn(overrides, "maxAllocationBytes")
      ? source.maxAllocationBytes
      : Math.min(source.maxAllocationBytes, planAllocation),
    "maxAllocationBytes",
    768 * 1024 * 1024,
  );
  if (maxDecodedBytes > planAllocation || maxAllocationBytes > planAllocation) {
    throw new RangeError("Gaussian allocation budget exceeds render plan");
  }
  const frameBudget = Object.hasOwn(overrides, "maxFrameMs")
    ? source.maxFrameMs
    : Math.min(source.maxFrameMs, plan.budget.max_cpu_ms_per_frame);
  return Object.freeze({
    maxVisibleSplats: boundedPositiveInteger(
      source.maxVisibleSplats,
      "maxVisibleSplats",
      2_000_000,
    ),
    maxDecodedBytes,
    maxGpuBytes,
    maxSortItems: boundedPositiveInteger(source.maxSortItems, "maxSortItems", 2_000_000),
    maxAllocationBytes,
    maxFrameMs:
      typeof frameBudget === "number" &&
      Number.isFinite(frameBudget) &&
      frameBudget > 0 &&
      frameBudget <= plan.budget.max_cpu_ms_per_frame
        ? frameBudget
        : (() => {
            throw new RangeError("Gaussian frame budget exceeds render plan");
          })(),
  });
}

function validateGaussianAsset(payload, sceneAsset, limits) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new TypeError("Gaussian asset payload must be an object");
  }
  const keys = new Set(Object.keys(payload));
  const expected = new Set([
    "asset_id",
    "source_digest",
    "positions",
    "rotations_xyzw",
    "scales_xyz",
    "opacities",
    "colors_rgba",
  ]);
  if (keys.size !== expected.size || [...keys].some((key) => !expected.has(key))) {
    throw new TypeError("Gaussian asset payload keys mismatch");
  }
  if (payload.asset_id !== sceneAsset.asset_id) throw new TypeError("Gaussian asset identity mismatch");
  if (!DIGEST.test(String(payload.source_digest || ""))) {
    throw new TypeError("Gaussian source_digest must be lowercase sha256");
  }
  const expectedDigest = sceneAsset.content_digest.split(":", 2)[1];
  if (payload.source_digest !== expectedDigest) {
    throw new TypeError("Gaussian asset digest is stale or ambiguous");
  }
  const count = payload.positions?.length;
  if (!Number.isInteger(count) || count < 1 || count > limits.maxVisibleSplats) {
    throw new RangeError("Gaussian visible-splat budget exceeded");
  }
  for (const name of ["rotations_xyzw", "scales_xyz", "opacities", "colors_rgba"]) {
    if (!Array.isArray(payload[name]) || payload[name].length !== count) {
      throw new TypeError(`Gaussian ${name} count mismatch`);
    }
  }
  const gpuBytes = count * GPU_BYTES_PER_SPLAT;
  const sortBytes = count * SORT_BYTES_PER_SPLAT;
  const allocationBytes = gpuBytes + sortBytes;
  if (
    gpuBytes > limits.maxDecodedBytes ||
    gpuBytes > limits.maxGpuBytes ||
    allocationBytes > limits.maxAllocationBytes
  ) {
    throw new RangeError("Gaussian allocation budget exceeded before buffer creation");
  }
  const positions = payload.positions.map((item, index) =>
    finiteVector(item, 3, `Gaussian position ${index}`),
  );
  const rotations = payload.rotations_xyzw.map((item, index) => {
    const rotation = finiteVector(item, 4, `Gaussian rotation ${index}`);
    const norm = Math.sqrt(rotation.reduce((total, value) => total + value * value, 0));
    if (norm < 0.999 || norm > 1.001) throw new TypeError("Gaussian rotation must be normalized");
    return rotation;
  });
  const scales = payload.scales_xyz.map((item, index) =>
    finiteVector(item, 3, `Gaussian scale ${index}`, { nonNegative: true }),
  );
  const opacities = payload.opacities.map((item) => {
    if (typeof item !== "number" || !Number.isFinite(item) || item < 0 || item > 1) {
      throw new TypeError("Gaussian opacity must be finite and normalized");
    }
    return item;
  });
  const colors = payload.colors_rgba.map((item) => {
    if (
      !Array.isArray(item) ||
      item.length !== 4 ||
      item.some((channel) => !Number.isInteger(channel) || channel < 0 || channel > 255)
    ) {
      throw new TypeError("Gaussian fallback colors must be RGBA8");
    }
    return Object.freeze([...item]);
  });
  return Object.freeze({
    asset_id: payload.asset_id,
    source_digest: payload.source_digest,
    count,
    gpu_bytes: gpuBytes,
    allocation_bytes: allocationBytes,
    positions: Object.freeze(positions),
    rotations_xyzw: Object.freeze(rotations),
    scales_xyz: Object.freeze(scales),
    opacities: Object.freeze(opacities),
    colors_rgba: Object.freeze(colors),
  });
}

function flatten(values, components, Type = Float32Array) {
  const output = new Type(values.length * components);
  let offset = 0;
  for (const value of values) {
    output.set(value, offset);
    offset += components;
  }
  return output;
}

function sortedIndices(asset, cameraPosition, maximum) {
  if (asset.count > maximum) throw new RangeError("Gaussian sort-item budget exceeded");
  const camera = finiteVector(cameraPosition, 3, "cameraPosition");
  const order = Uint32Array.from({ length: asset.count }, (_, index) => index);
  order.sort((left, right) => {
    const a = asset.positions[left];
    const b = asset.positions[right];
    const da = (a[0] - camera[0]) ** 2 + (a[1] - camera[1]) ** 2 + (a[2] - camera[2]) ** 2;
    const db = (b[0] - camera[0]) ** 2 + (b[1] - camera[1]) ** 2 + (b[2] - camera[2]) ** 2;
    return db - da || left - right;
  });
  return order;
}

export function describeGaussianAssets(assets) {
  if (!Array.isArray(assets)) throw new TypeError("Gaussian assets must be an array");
  return Object.freeze(
    assets.map((asset) =>
      Object.freeze({
        asset_id: asset.asset_id,
        splat_count: asset.count,
        fallback: "POINT_CLOUD_RGBA8",
        description: `${asset.count} Gaussian splats; point-cloud, accessible, and headless fallbacks available`,
        ...AUTHORITY_ENVELOPE,
      }),
    ),
  );
}

export class GaussianRenderer {
  constructor({
    presentationRenderer,
    drawGaussianPass = null,
    drawPointCloudPass = null,
    limits = null,
    now = () => globalThis.performance?.now?.() ?? Date.now(),
  } = {}) {
    if (!presentationRenderer || typeof presentationRenderer.initialize !== "function") {
      throw new TypeError("Gaussian renderer requires a retained presentation renderer");
    }
    if (drawGaussianPass !== null && typeof drawGaussianPass !== "function") {
      throw new TypeError("drawGaussianPass must be callable when supplied");
    }
    if (drawPointCloudPass !== null && typeof drawPointCloudPass !== "function") {
      throw new TypeError("drawPointCloudPass must be callable when supplied");
    }
    this.presentationRenderer = presentationRenderer;
    this.drawGaussianPass = drawGaussianPass;
    this.drawPointCloudPass =
      drawPointCloudPass ||
      (typeof presentationRenderer.drawPointCloudPass === "function"
        ? presentationRenderer.drawPointCloudPass.bind(presentationRenderer)
        : null);
    this.requestedLimits = limits;
    this.now = now;
    this.state = RENDERER_STATES.NEW;
    this.scene = null;
    this.plan = null;
    this.assets = Object.freeze([]);
    this.limits = null;
    this.buffers = new Set();
    this.cancelled = false;
  }

  async initialize(scenePayload, planPayload, gaussianPayloads, { signal } = {}) {
    if (this.state !== RENDERER_STATES.NEW) throw new Error("Gaussian renderer may initialize only once");
    if (signal?.aborted) throw new Error("Gaussian initialization cancelled");
    this.scene = validateSceneProjection(scenePayload);
    this.plan = validateRenderPlan(planPayload, this.scene);
    this.limits = normalizeLimits(this.requestedLimits, this.plan);
    if (!Array.isArray(gaussianPayloads)) throw new TypeError("gaussianPayloads must be an array");
    const manifests = new Map(
      this.scene.assets
        .filter((asset) => asset.asset_type === "GAUSSIAN_SPLAT")
        .map((asset) => [asset.asset_id, asset]),
    );
    if (gaussianPayloads.length !== manifests.size) {
      throw new TypeError("Gaussian payloads must exactly cover scene Gaussian manifests");
    }
    const seen = new Set();
    const assets = gaussianPayloads.map((payload) => {
      if (seen.has(payload?.asset_id)) throw new TypeError("Gaussian asset payload is duplicated");
      seen.add(payload?.asset_id);
      const manifest = manifests.get(payload?.asset_id);
      if (!manifest) throw new TypeError("Gaussian payload is not admitted by the scene");
      return validateGaussianAsset(payload, manifest, this.limits);
    });
    const totalGpuBytes = assets.reduce((total, asset) => total + asset.gpu_bytes, 0);
    const totalAllocationBytes = assets.reduce(
      (total, asset) => total + asset.allocation_bytes,
      0,
    );
    const totalSplats = assets.reduce((total, asset) => total + asset.count, 0);
    if (
      totalGpuBytes > this.limits.maxDecodedBytes ||
      totalGpuBytes > this.limits.maxGpuBytes ||
      totalAllocationBytes > this.limits.maxAllocationBytes ||
      totalSplats > this.limits.maxVisibleSplats
    ) {
      throw new RangeError("Gaussian aggregate allocation budget exceeded");
    }
    await this.presentationRenderer.initialize(scenePayload, planPayload);
    if (signal?.aborted) {
      await this.presentationRenderer.dispose();
      throw new Error("Gaussian initialization cancelled");
    }
    this.assets = Object.freeze([...assets].sort((a, b) => a.asset_id.localeCompare(b.asset_id)));
    this.state = RENDERER_STATES.INITIALIZED;
    return this.status();
  }

  async present({ cameraPosition = [0, 0, 0], signal } = {}) {
    if (this.state !== RENDERER_STATES.INITIALIZED) throw new Error("Gaussian renderer is not initialized");
    if (signal?.aborted || this.cancelled) throw new Error("Gaussian presentation cancelled");
    const started = this.now();
    let baseReceipt;
    let representation = "ACCESSIBLE_HEADLESS_FALLBACK";
    let evidenceClass = "CALCULATED";
    let drawn = 0;
    try {
      baseReceipt = await this.presentationRenderer.present();
      for (const asset of this.assets) {
        if (signal?.aborted || this.cancelled) throw new Error("Gaussian presentation cancelled");
        const order = sortedIndices(asset, cameraPosition, this.limits.maxSortItems);
        const resources = Object.freeze({
          positions: flatten(asset.positions, 3),
          rotations_xyzw: flatten(asset.rotations_xyzw, 4),
          scales_xyz: flatten(asset.scales_xyz, 3),
          opacities: Float32Array.from(asset.opacities),
          colors_rgba: flatten(asset.colors_rgba, 4, Uint8Array),
          sorted_indices: order,
        });
        this.buffers.add(resources);
        const context = {
          asset_id: asset.asset_id,
          splat_count: asset.count,
          scene_digest: this.scene.scene_digest,
          render_plan_digest: this.plan.render_plan_digest,
          signal,
          ...AUTHORITY_ENVELOPE,
        };
        if (this.drawGaussianPass) {
          await this.drawGaussianPass(resources, context);
          representation = "GAUSSIAN_SPLAT_PASS";
          evidenceClass = "MEASURED";
        } else if (this.drawPointCloudPass) {
          await this.drawPointCloudPass(
            Object.freeze({
              positions: resources.positions,
              colors_rgba: resources.colors_rgba,
              sorted_indices: resources.sorted_indices,
            }),
            context,
          );
          representation = "POINT_CLOUD_FALLBACK";
          evidenceClass = "MEASURED";
        }
        drawn += asset.count;
      }
    } catch (error) {
      this.buffers.clear();
      this.cancelled = true;
      this.state = RENDERER_STATES.LOST;
      throw error;
    }
    const elapsed = this.now() - started;
    if (!Number.isFinite(elapsed) || elapsed < 0 || elapsed > this.limits.maxFrameMs) {
      await this.dispose();
      throw new RangeError("Gaussian frame-time budget exceeded");
    }
    this.state = RENDERER_STATES.PRESENTED;
    return Object.freeze({
      renderer: this.presentationRenderer.kind,
      representation,
      outcome: "PRESENTED",
      evidence_class: evidenceClass,
      scene_digest: this.scene.scene_digest,
      render_plan_digest: this.plan.render_plan_digest,
      splat_count: drawn,
      gpu_bytes: this.assets.reduce((total, asset) => total + asset.gpu_bytes, 0),
      allocation_bytes: this.assets.reduce(
        (total, asset) => total + asset.allocation_bytes,
        0,
      ),
      elapsed_ms: elapsed,
      base_receipt: baseReceipt,
      fallbacks: GAUSSIAN_FALLBACKS,
      ...AUTHORITY_ENVELOPE,
    });
  }

  headlessProof() {
    if (!this.scene || !this.plan) throw new Error("Gaussian renderer is not initialized");
    return Object.freeze({
      version: GAUSSIAN_REPRESENTATION_VERSION,
      scene_digest: this.scene.scene_digest,
      render_plan_digest: this.plan.render_plan_digest,
      assets: describeGaussianAssets(this.assets),
      deterministic_order: this.assets.map((asset) => asset.asset_id),
      ...AUTHORITY_ENVELOPE,
    });
  }

  markDeviceLost() {
    if (this.state === RENDERER_STATES.DISPOSED) return this.status();
    this.cancelled = true;
    this.buffers.clear();
    this.state = RENDERER_STATES.LOST;
    return this.status();
  }

  async dispose() {
    this.cancelled = true;
    this.buffers.clear();
    this.assets = Object.freeze([]);
    this.scene = null;
    this.plan = null;
    await this.presentationRenderer.dispose();
    this.state = RENDERER_STATES.DISPOSED;
    return this.status();
  }

  status() {
    return Object.freeze({
      version: GAUSSIAN_REPRESENTATION_VERSION,
      renderer: this.presentationRenderer.kind,
      state: this.state,
      representation_buffer_count: this.buffers.size,
      presentation_owner_retained: true,
      ...AUTHORITY_ENVELOPE,
    });
  }
}
