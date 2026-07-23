import {
  AUTHORITY_ENVELOPE,
  RENDERER_STATES,
  validateRenderPlan,
  validateSceneProjection,
} from "./renderer_adapter.js";

export const GAUSSIAN_REPRESENTATION_VERSION = "AURA_SPATIAL_GAUSSIAN_RENDERER_V1";
export const GAUSSIAN_REPRESENTATION_DIGEST_VERSION = "AURA_GAUSSIAN_REPRESENTATION_V1";
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
const BASE_REPRESENTATION_BYTES_PER_SPLAT = 48;
const SORT_BYTES_PER_SPLAT = 4;
const JS_SOURCE_BYTES_PER_SPLAT = 2_304;
const JS_SOURCE_BYTES_PER_COEFFICIENT = 128;
const DIGEST_HEADER_BYTES =
  new TextEncoder().encode(`${GAUSSIAN_REPRESENTATION_DIGEST_VERSION}\0`).length + 9;

function safeProduct(left, right, label) {
  const result = left * right;
  if (!Number.isSafeInteger(result) || result < 0) {
    throw new RangeError(`${label} exceeds safe integer bounds`);
  }
  return result;
}

function boundedPositiveInteger(value, label, maximum) {
  if (!Number.isInteger(value) || value < 1 || value > maximum) {
    throw new RangeError(`${label} must be an integer in [1, ${maximum}]`);
  }
  return value;
}

function finiteFloat32(value, label, { nonNegative = false } = {}) {
  if (typeof value !== "number" || !Number.isFinite(value) || (nonNegative && value < 0)) {
    throw new TypeError(`${label} must be finite${nonNegative ? " and non-negative" : ""}`);
  }
  const converted = Math.fround(value);
  if (!Number.isFinite(converted)) {
    throw new TypeError(`${label} exceeds finite Float32 representation`);
  }
  return converted;
}

function finiteVector(value, length, label, options = {}) {
  if (!Array.isArray(value) || value.length !== length) {
    throw new TypeError(`${label} must be a finite ${length}-vector`);
  }
  return value.map((item, index) => finiteFloat32(item, `${label}[${index}]`, options));
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

function metadataDigest(metadata, key, label) {
  const value = String(metadata?.[key] || "");
  if (!DIGEST.test(value)) throw new TypeError(`${label} must be lowercase sha256`);
  return value;
}

function allocateFloat32Vectors(values, width, label, options = {}) {
  const output = new Float32Array(values.length * width);
  for (let index = 0; index < values.length; index += 1) {
    const vector = finiteVector(values[index], width, `${label} ${index}`, options);
    output.set(vector, index * width);
  }
  return output;
}

function allocateFloat32Scalars(values, label, { minimum = -Infinity, maximum = Infinity } = {}) {
  const output = new Float32Array(values.length);
  for (let index = 0; index < values.length; index += 1) {
    const value = finiteFloat32(values[index], `${label} ${index}`);
    if (value < minimum || value > maximum) {
      throw new TypeError(`${label} must be in [${minimum}, ${maximum}]`);
    }
    output[index] = value;
  }
  return output;
}

function allocateColors(values) {
  const output = new Uint8Array(values.length * 4);
  for (let index = 0; index < values.length; index += 1) {
    const color = values[index];
    if (
      !Array.isArray(color) ||
      color.length !== 4 ||
      color.some((channel) => !Number.isInteger(channel) || channel < 0 || channel > 255)
    ) {
      throw new TypeError("Gaussian fallback colors must be RGBA8");
    }
    output.set(color, index * 4);
  }
  return output;
}

function assertNormalizedRotations(rotations) {
  for (let offset = 0; offset < rotations.length; offset += 4) {
    const norm = Math.sqrt(
      rotations[offset] ** 2 +
        rotations[offset + 1] ** 2 +
        rotations[offset + 2] ** 2 +
        rotations[offset + 3] ** 2,
    );
    if (norm < 0.999 || norm > 1.001) {
      throw new TypeError("Gaussian rotation must be normalized");
    }
  }
}

function digestInput(asset) {
  const version = new TextEncoder().encode(`${GAUSSIAN_REPRESENTATION_DIGEST_VERSION}\0`);
  const byteLength =
    DIGEST_HEADER_BYTES +
    asset.positions.byteLength +
    asset.rotations_xyzw.byteLength +
    asset.scales_xyz.byteLength +
    asset.opacities.byteLength +
    asset.sh_coefficients.byteLength +
    asset.colors_rgba.byteLength;
  const bytes = new Uint8Array(byteLength);
  bytes.set(version, 0);
  const view = new DataView(bytes.buffer);
  let offset = version.length;
  view.setUint32(offset, asset.count, true);
  offset += 4;
  view.setUint8(offset, asset.sh_degree);
  offset += 1;
  view.setUint32(offset, asset.coefficient_count, true);
  offset += 4;
  for (const values of [
    asset.positions,
    asset.rotations_xyzw,
    asset.scales_xyz,
    asset.opacities,
    asset.sh_coefficients,
  ]) {
    for (const value of values) {
      view.setFloat32(offset, value, true);
      offset += 4;
    }
  }
  bytes.set(asset.colors_rgba, offset);
  return bytes;
}

async function sha256Hex(bytes) {
  if (!globalThis.crypto?.subtle) {
    throw new Error("Gaussian representation digest requires Web Crypto SHA-256");
  }
  const digest = new Uint8Array(await globalThis.crypto.subtle.digest("SHA-256", bytes));
  return [...digest].map((value) => value.toString(16).padStart(2, "0")).join("");
}

function preflightGaussianAsset(payload, sceneAsset, limits) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new TypeError("Gaussian asset payload must be an object");
  }
  const keys = new Set(Object.keys(payload));
  const expected = new Set([
    "asset_id",
    "source_digest",
    "derived_asset_digest",
    "representation_digest",
    "sh_degree",
    "color_space",
    "positions",
    "rotations_xyzw",
    "scales_xyz",
    "opacities",
    "sh_coefficients",
    "colors_rgba",
  ]);
  if (keys.size !== expected.size || [...keys].some((key) => !expected.has(key))) {
    throw new TypeError("Gaussian asset payload keys mismatch");
  }
  if (payload.asset_id !== sceneAsset.asset_id) throw new TypeError("Gaussian asset identity mismatch");
  if (!DIGEST.test(String(payload.source_digest || ""))) {
    throw new TypeError("Gaussian source_digest must be lowercase sha256");
  }
  const expectedSourceDigest = sceneAsset.content_digest.split(":", 2)[1];
  if (payload.source_digest !== expectedSourceDigest) {
    throw new TypeError("Gaussian asset source digest is stale or ambiguous");
  }
  const metadata = sceneAsset.metadata;
  if (!metadata || typeof metadata !== "object" || Array.isArray(metadata)) {
    throw new TypeError("Gaussian manifest lacks bounded import metadata");
  }
  const expectedReceiptDigest = metadataDigest(metadata, "import_receipt_digest", "import_receipt_digest");
  const expectedRepresentationDigest = metadataDigest(
    metadata,
    "representation_digest",
    "representation_digest",
  );
  if (metadata.representation_digest_version !== GAUSSIAN_REPRESENTATION_DIGEST_VERSION) {
    throw new TypeError("Gaussian representation digest version is unsupported");
  }
  if (payload.derived_asset_digest !== expectedReceiptDigest) {
    throw new TypeError("Gaussian import receipt digest is stale or ambiguous");
  }
  if (!DIGEST.test(String(payload.representation_digest || ""))) {
    throw new TypeError("Gaussian representation_digest must be lowercase sha256");
  }
  if (payload.representation_digest !== expectedRepresentationDigest) {
    throw new TypeError("Gaussian representation digest is stale or ambiguous");
  }
  if (!Number.isInteger(payload.sh_degree) || payload.sh_degree < 0 || payload.sh_degree > 4) {
    throw new TypeError("Gaussian sh_degree must be in [0, 4]");
  }
  if (metadata.gaussian_sh_degree !== payload.sh_degree && metadata.sh_degree !== payload.sh_degree) {
    throw new TypeError("Gaussian spherical-harmonic degree is stale or ambiguous");
  }
  if (
    !["SPZ_INTERNAL_WIDE_RGB", "srgb_rec709_display", "lin_rec709_display"].includes(payload.color_space) ||
    metadata.gaussian_color_space !== payload.color_space
  ) {
    throw new TypeError("Gaussian color-space metadata is stale or unsupported");
  }
  const count = payload.positions?.length;
  if (!Number.isInteger(count) || count < 1 || count > limits.maxVisibleSplats) {
    throw new RangeError("Gaussian visible-splat budget exceeded");
  }
  for (const name of [
    "rotations_xyzw",
    "scales_xyz",
    "opacities",
    "sh_coefficients",
    "colors_rgba",
  ]) {
    if (!Array.isArray(payload[name]) || payload[name].length !== count) {
      throw new TypeError(`Gaussian ${name} count mismatch`);
    }
  }
  const coefficientCount = (payload.sh_degree + 1) ** 2 * 3;
  const representationBytesPerSplat = BASE_REPRESENTATION_BYTES_PER_SPLAT + coefficientCount * 4;
  if (metadata.representation_bytes_per_splat !== representationBytesPerSplat) {
    throw new TypeError("Gaussian representation byte geometry is stale or ambiguous");
  }
  const representationBytes = safeProduct(count, representationBytesPerSplat, "Gaussian representation bytes");
  const sortBytes = safeProduct(count, SORT_BYTES_PER_SPLAT, "Gaussian sort bytes");
  const sourceBytesPerSplat =
    JS_SOURCE_BYTES_PER_SPLAT + coefficientCount * JS_SOURCE_BYTES_PER_COEFFICIENT;
  const sourcePayloadBytes = safeProduct(count, sourceBytesPerSplat, "Gaussian source payload estimate");
  const digestScratchBytes = DIGEST_HEADER_BYTES + representationBytes;
  const allocationBytes = sourcePayloadBytes + representationBytes + sortBytes + digestScratchBytes;
  if (!Number.isSafeInteger(allocationBytes)) {
    throw new RangeError("Gaussian allocation estimate exceeds safe integer bounds");
  }
  if (
    representationBytes > limits.maxDecodedBytes ||
    representationBytes > limits.maxGpuBytes ||
    allocationBytes > limits.maxAllocationBytes
  ) {
    throw new RangeError("Gaussian allocation budget exceeded before buffer creation");
  }

  return Object.freeze({
    count,
    coefficient_count: coefficientCount,
    representation_bytes: representationBytes,
    allocation_bytes: allocationBytes,
  });
}

async function materializeGaussianAsset(payload, preflight) {
  const count = preflight.count;
  const coefficientCount = preflight.coefficient_count;
  const representationBytes = preflight.representation_bytes;
  const allocationBytes = preflight.allocation_bytes;
  const positions = allocateFloat32Vectors(payload.positions, 3, "Gaussian position");
  const rotations = allocateFloat32Vectors(payload.rotations_xyzw, 4, "Gaussian rotation");
  assertNormalizedRotations(rotations);
  const scales = allocateFloat32Vectors(payload.scales_xyz, 3, "Gaussian scale", {
    nonNegative: true,
  });
  const opacities = allocateFloat32Scalars(payload.opacities, "Gaussian opacity", {
    minimum: 0,
    maximum: 1,
  });
  const coefficients = allocateFloat32Vectors(
    payload.sh_coefficients,
    coefficientCount,
    "Gaussian spherical harmonic",
  );
  const colors = allocateColors(payload.colors_rgba);
  const asset = {
    asset_id: payload.asset_id,
    source_digest: payload.source_digest,
    derived_asset_digest: payload.derived_asset_digest,
    representation_digest: payload.representation_digest,
    sh_degree: payload.sh_degree,
    color_space: payload.color_space,
    coefficient_count: coefficientCount,
    count,
    gpu_bytes: representationBytes,
    allocation_bytes: allocationBytes,
    positions,
    rotations_xyzw: rotations,
    scales_xyz: scales,
    opacities,
    sh_coefficients: coefficients,
    colors_rgba: colors,
  };
  const observedRepresentationDigest = await sha256Hex(digestInput(asset));
  if (observedRepresentationDigest !== payload.representation_digest) {
    throw new TypeError("Gaussian representation digest does not match decoded attributes");
  }
  return Object.freeze(asset);
}

function cameraVector(value) {
  return finiteVector(value, 3, "cameraPosition");
}

function sortedIndices(asset, cameraPosition, maximum) {
  if (asset.count > maximum) throw new RangeError("Gaussian sort-item budget exceeded");
  const camera = cameraVector(cameraPosition);
  const order = Uint32Array.from({ length: asset.count }, (_, index) => index);
  order.sort((left, right) => {
    const leftOffset = left * 3;
    const rightOffset = right * 3;
    const da =
      (asset.positions[leftOffset] - camera[0]) ** 2 +
      (asset.positions[leftOffset + 1] - camera[1]) ** 2 +
      (asset.positions[leftOffset + 2] - camera[2]) ** 2;
    const db =
      (asset.positions[rightOffset] - camera[0]) ** 2 +
      (asset.positions[rightOffset + 1] - camera[1]) ** 2 +
      (asset.positions[rightOffset + 2] - camera[2]) ** 2;
    return db - da || left - right;
  });
  return order;
}

function requireDisposer(value) {
  if (typeof value === "function") return value;
  if (value && typeof value === "object" && typeof value.dispose === "function") {
    return value.dispose.bind(value);
  }
  throw new TypeError("Gaussian draw pass must return a disposal handle");
}

export function describeGaussianAssets(assets) {
  if (!Array.isArray(assets)) throw new TypeError("Gaussian assets must be an array");
  return Object.freeze(
    assets.map((asset) =>
      Object.freeze({
        asset_id: asset.asset_id,
        splat_count: asset.count,
        fallback: "POINT_CLOUD_RGBA8",
        sh_degree: asset.sh_degree,
        color_space: asset.color_space,
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
    this.visibleAssetIds = null;
    this.limits = null;
    this.buffers = new Set();
    this.passDisposers = new Set();
    this.presentationDisposed = false;
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
    const admitted = [];
    for (const payload of gaussianPayloads) {
      if (signal?.aborted) throw new Error("Gaussian initialization cancelled");
      if (seen.has(payload?.asset_id)) throw new TypeError("Gaussian asset payload is duplicated");
      seen.add(payload?.asset_id);
      const manifest = manifests.get(payload?.asset_id);
      if (!manifest) throw new TypeError("Gaussian payload is not admitted by the scene");
      admitted.push(
        Object.freeze({
          payload,
          preflight: preflightGaussianAsset(payload, manifest, this.limits),
        }),
      );
    }
    const totalGpuBytes = admitted.reduce(
      (total, item) => total + item.preflight.representation_bytes,
      0,
    );
    const totalAllocationBytes = admitted.reduce(
      (total, item) => total + item.preflight.allocation_bytes,
      0,
    );
    const totalSplats = admitted.reduce((total, item) => total + item.preflight.count, 0);
    if (
      totalGpuBytes > this.limits.maxDecodedBytes ||
      totalGpuBytes > this.limits.maxGpuBytes ||
      totalAllocationBytes > this.limits.maxAllocationBytes ||
      totalSplats > this.limits.maxVisibleSplats
    ) {
      throw new RangeError("Gaussian aggregate allocation budget exceeded before materialization");
    }

    const assets = [];
    for (const item of admitted) {
      if (signal?.aborted) throw new Error("Gaussian initialization cancelled");
      assets.push(await materializeGaussianAsset(item.payload, item.preflight));
    }

    try {
      await this.presentationRenderer.initialize(scenePayload, planPayload);
      if (signal?.aborted) throw new Error("Gaussian initialization cancelled");
    } catch (error) {
      let cleanupError = null;
      try {
        await this._disposePresentationRenderer();
      } catch (cleanup) {
        cleanupError = cleanup;
      }
      this.assets = Object.freeze([]);
      this.scene = null;
      this.plan = null;
      this.limits = null;
      this.cancelled = true;
      this.state = RENDERER_STATES.LOST;
      if (cleanupError) {
        throw new AggregateError(
          [error, cleanupError],
          "Gaussian initialization and cleanup failed",
        );
      }
      throw error;
    }
    this.assets = Object.freeze([...assets].sort((a, b) => a.asset_id.localeCompare(b.asset_id)));
    this.state = RENDERER_STATES.INITIALIZED;
    return this.status();
  }

  setVisibleAssetIds(assetIds = null) {
    if (![RENDERER_STATES.INITIALIZED, RENDERER_STATES.PRESENTED].includes(this.state)) {
      throw new Error("Gaussian renderer is not initialized");
    }
    if (assetIds === null) {
      this.visibleAssetIds = null;
      return this.status();
    }
    if (!Array.isArray(assetIds) || assetIds.some((item) => typeof item !== "string")) {
      throw new TypeError("visible Gaussian asset IDs must be null or an array of strings");
    }
    const ids = [...new Set(assetIds)].sort();
    const known = new Set(this.assets.map((asset) => asset.asset_id));
    const unknown = ids.filter((assetId) => !known.has(assetId));
    if (unknown.length) throw new RangeError(`unknown Gaussian asset IDs: ${unknown.join(", ")}`);
    this.visibleAssetIds = new Set(ids);
    return this.status();
  }

  async _disposePresentationRenderer() {
    if (this.presentationDisposed) return;
    this.presentationDisposed = true;
    await this.presentationRenderer.dispose();
  }

  async _releaseDrawResources() {
    let firstError = null;
    for (const dispose of [...this.passDisposers].reverse()) {
      try {
        await dispose();
      } catch (error) {
        firstError ||= error;
      }
    }
    this.passDisposers.clear();
    this.buffers.clear();
    if (firstError) throw firstError;
  }

  async _releaseRepresentationResources() {
    let cleanupError = null;
    try {
      await this._releaseDrawResources();
    } catch (error) {
      cleanupError = error;
    }
    this.assets = Object.freeze([]);
    this.visibleAssetIds = null;
    if (cleanupError) throw cleanupError;
  }

  async present({ cameraPosition = [0, 0, 0], signal } = {}) {
    if (![RENDERER_STATES.INITIALIZED, RENDERER_STATES.PRESENTED].includes(this.state)) {
      throw new Error("Gaussian renderer is not initialized");
    }
    if (signal?.aborted || this.cancelled) throw new Error("Gaussian presentation cancelled");
    await this._releaseDrawResources();
    const visibleAssets =
      this.visibleAssetIds === null
        ? this.assets
        : this.assets.filter((asset) => this.visibleAssetIds.has(asset.asset_id));
    const started = this.now();
    let baseReceipt;
    let representation = "ACCESSIBLE_HEADLESS_FALLBACK";
    let evidenceClass = "CALCULATED";
    let drawn = 0;
    try {
      baseReceipt = await this.presentationRenderer.present();
      if (signal?.aborted || this.cancelled) throw new Error("Gaussian presentation cancelled");
      for (const asset of visibleAssets) {
        if (signal?.aborted || this.cancelled) throw new Error("Gaussian presentation cancelled");
        const order = sortedIndices(asset, cameraPosition, this.limits.maxSortItems);
        const resources = Object.freeze({
          positions: asset.positions,
          rotations_xyzw: asset.rotations_xyzw,
          scales_xyz: asset.scales_xyz,
          opacities: asset.opacities,
          sh_degree: asset.sh_degree,
          sh_coefficients: asset.sh_coefficients,
          colors_rgba: asset.colors_rgba,
          sorted_indices: order,
        });
        this.buffers.add(resources);
        const context = {
          asset_id: asset.asset_id,
          source_digest: asset.source_digest,
          derived_asset_digest: asset.derived_asset_digest,
          color_space: asset.color_space,
          sh_degree: asset.sh_degree,
          splat_count: asset.count,
          representation_digest: asset.representation_digest,
          scene_digest: this.scene.scene_digest,
          render_plan_digest: this.plan.render_plan_digest,
          signal,
          ...AUTHORITY_ENVELOPE,
        };
        if (this.drawGaussianPass) {
          const disposer = requireDisposer(await this.drawGaussianPass(resources, context));
          this.passDisposers.add(disposer);
          if (signal?.aborted || this.cancelled) throw new Error("Gaussian presentation cancelled");
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
          if (signal?.aborted || this.cancelled) throw new Error("Gaussian presentation cancelled");
          representation = "POINT_CLOUD_FALLBACK";
          evidenceClass = "MEASURED";
        }
        drawn += asset.count;
      }
    } catch (error) {
      let cleanupError = null;
      try {
        await this._releaseRepresentationResources();
      } catch (cleanup) {
        cleanupError = cleanup;
      }
      this.cancelled = true;
      this.state = RENDERER_STATES.LOST;
      if (cleanupError) throw new AggregateError([error, cleanupError], "Gaussian presentation and cleanup failed");
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
      gpu_bytes: visibleAssets.reduce((total, asset) => total + asset.gpu_bytes, 0),
      allocation_bytes: visibleAssets.reduce(
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

  async markDeviceLost() {
    if (this.state === RENDERER_STATES.DISPOSED) return this.status();
    this.cancelled = true;
    const errors = [];
    try {
      await this._releaseRepresentationResources();
    } catch (error) {
      errors.push(error);
    }
    try {
      await this._disposePresentationRenderer();
    } catch (error) {
      errors.push(error);
    }
    this.scene = null;
    this.plan = null;
    this.limits = null;
    this.visibleAssetIds = null;
    this.state = RENDERER_STATES.LOST;
    if (errors.length === 1) throw errors[0];
    if (errors.length > 1) throw new AggregateError(errors, "Gaussian device-loss cleanup failed");
    return this.status();
  }

  async dispose() {
    if (this.state === RENDERER_STATES.DISPOSED) return this.status();
    this.cancelled = true;
    const errors = [];
    try {
      await this._releaseRepresentationResources();
    } catch (error) {
      errors.push(error);
    }
    this.scene = null;
    this.plan = null;
    this.limits = null;
    this.visibleAssetIds = null;
    try {
      await this._disposePresentationRenderer();
    } catch (error) {
      errors.push(error);
    }
    if (errors.length) {
      this.state = RENDERER_STATES.LOST;
      if (errors.length === 1) throw errors[0];
      throw new AggregateError(errors, "Gaussian disposal failed");
    }
    this.state = RENDERER_STATES.DISPOSED;
    return this.status();
  }


  status() {
    return Object.freeze({
      version: GAUSSIAN_REPRESENTATION_VERSION,
      renderer: this.presentationRenderer.kind,
      state: this.state,
      representation_buffer_count: this.buffers.size,
      representation_disposer_count: this.passDisposers.size,
      presentation_owner_retained: !this.presentationDisposed,
      visible_asset_filter_count:
        this.visibleAssetIds === null ? null : this.visibleAssetIds.size,
      ...AUTHORITY_ENVELOPE,
    });
  }
}
