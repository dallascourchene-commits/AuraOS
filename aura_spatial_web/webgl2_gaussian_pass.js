import { AUTHORITY_ENVELOPE, RENDERER_STATES } from "./renderer_adapter.js";
import { GaussianRenderer } from "./gaussian_renderer.js";

export const CONSTRUCTION_GAUSSIAN_PASS_VERSION =
  "AURA_CONSTRUCTION_WEBGL2_GAUSSIAN_PASS_V1";

const MAX_COVARIANCE_SPLATS = 1_000_000;

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

function quaternionMatrix(x, y, z, w) {
  const xx = x * x;
  const yy = y * y;
  const zz = z * z;
  const xy = x * y;
  const xz = x * z;
  const yz = y * z;
  const wx = w * x;
  const wy = w * y;
  const wz = w * z;
  return [
    1 - 2 * (yy + zz),
    2 * (xy - wz),
    2 * (xz + wy),
    2 * (xy + wz),
    1 - 2 * (xx + zz),
    2 * (yz - wx),
    2 * (xz - wy),
    2 * (yz + wx),
    1 - 2 * (xx + yy),
  ];
}

export function deriveDegreeZeroCovariance(rotations, scales) {
  if (!(rotations instanceof Float32Array) || !(scales instanceof Float32Array)) {
    throw new TypeError("Gaussian rotations and scales must be Float32Array values");
  }
  if (rotations.length % 4 !== 0 || scales.length % 3 !== 0) {
    throw new TypeError("Gaussian rotations or scales have invalid width");
  }
  const count = rotations.length / 4;
  if (scales.length / 3 !== count || count > MAX_COVARIANCE_SPLATS) {
    throw new RangeError("Gaussian covariance count exceeds its boundary");
  }
  const covariance = new Float32Array(count * 6);
  for (let index = 0; index < count; index += 1) {
    const rotationOffset = index * 4;
    const scaleOffset = index * 3;
    const matrix = quaternionMatrix(
      rotations[rotationOffset],
      rotations[rotationOffset + 1],
      rotations[rotationOffset + 2],
      rotations[rotationOffset + 3],
    );
    const sx2 = scales[scaleOffset] ** 2;
    const sy2 = scales[scaleOffset + 1] ** 2;
    const sz2 = scales[scaleOffset + 2] ** 2;
    const covarianceOffset = index * 6;
    covariance[covarianceOffset] = matrix[0] ** 2 * sx2 + matrix[1] ** 2 * sy2 + matrix[2] ** 2 * sz2;
    covariance[covarianceOffset + 1] =
      matrix[0] * matrix[3] * sx2 + matrix[1] * matrix[4] * sy2 + matrix[2] * matrix[5] * sz2;
    covariance[covarianceOffset + 2] =
      matrix[0] * matrix[6] * sx2 + matrix[1] * matrix[7] * sy2 + matrix[2] * matrix[8] * sz2;
    covariance[covarianceOffset + 3] = matrix[3] ** 2 * sx2 + matrix[4] ** 2 * sy2 + matrix[5] ** 2 * sz2;
    covariance[covarianceOffset + 4] =
      matrix[3] * matrix[6] * sx2 + matrix[4] * matrix[7] * sy2 + matrix[5] * matrix[8] * sz2;
    covariance[covarianceOffset + 5] = matrix[6] ** 2 * sx2 + matrix[7] ** 2 * sy2 + matrix[8] ** 2 * sz2;
  }
  return covariance;
}

export class ConstructionGaussianPass {
  constructor({
    presentationRenderer,
    drawGaussianPass = null,
    drawPointCloudPass = null,
    limits = null,
    now,
  } = {}) {
    if (!presentationRenderer) {
      throw new TypeError("ConstructionGaussianPass requires a presentationRenderer");
    }
    if (drawGaussianPass !== null && typeof drawGaussianPass !== "function") {
      throw new TypeError("drawGaussianPass must be callable when supplied");
    }
    this.drawGaussianPass = drawGaussianPass;
    this.visibleAssetIds = new Set();
    this.assetFrames = new Map();
    this.payloadCounts = new Map();
    this.explodedOffsets = Object.freeze({});
    this.renderer = new GaussianRenderer({
      presentationRenderer,
      drawGaussianPass: drawGaussianPass
        ? async (resources, context) => {
            if (!this.visibleAssetIds.has(context.asset_id)) return () => {};
            if (context.sh_degree !== 0) {
              throw new TypeError("Construction Gaussian pass admits degree-0 SH only");
            }
            const covariance = deriveDegreeZeroCovariance(
              resources.rotations_xyzw,
              resources.scales_xyz,
            );
            const frameId = this.assetFrames.get(context.asset_id);
            const explodedOffset = Object.hasOwn(this.explodedOffsets, frameId)
              ? finiteVector(
                  this.explodedOffsets[frameId],
                  3,
                  "Construction Gaussian exploded offset",
                )
              : Object.freeze([0, 0, 0]);
            return drawGaussianPass(
              Object.freeze({
                ...resources,
                covariance_3d: covariance,
                degree_zero_rgba: resources.colors_rgba,
              }),
              Object.freeze({
                ...context,
                frame_id: frameId,
                exploded_offset: explodedOffset,
                blend_mode: "PREMULTIPLIED_ALPHA",
                depth_order: "BACK_TO_FRONT",
                depth_write: false,
                depth_test: true,
                ...AUTHORITY_ENVELOPE,
              }),
            );
          }
        : null,
      drawPointCloudPass,
      limits,
      now,
    });
  }

  async initialize(scenePayload, planPayload, gaussianPayloads, options = {}) {
    if (!Array.isArray(gaussianPayloads)) {
      throw new TypeError("gaussianPayloads must be an array");
    }
    for (const payload of gaussianPayloads) {
      if (payload?.sh_degree !== 0) {
        throw new TypeError("Construction Gaussian pass admits degree-0 SH only");
      }
    }
    const gaussianAssets = scenePayload?.assets?.filter(
      (asset) => asset.asset_type === "GAUSSIAN_SPLAT",
    );
    if (!Array.isArray(gaussianAssets)) {
      throw new TypeError("scene Gaussian assets must be an array");
    }
    this.assetFrames = new Map(
      gaussianAssets.map((asset) => [asset.asset_id, asset.frame_id]),
    );
    this.payloadCounts = new Map(
      gaussianPayloads.map((payload) => [payload.asset_id, payload.positions?.length || 0]),
    );
    this.visibleAssetIds = new Set(gaussianAssets.map((asset) => asset.asset_id));
    return this.renderer.initialize(scenePayload, planPayload, gaussianPayloads, options);
  }

  setVisibleAssets(assetIds) {
    if (!Array.isArray(assetIds)) throw new TypeError("assetIds must be an array");
    const admitted = new Set(this.assetFrames.keys());
    const next = new Set();
    for (const assetId of assetIds) {
      if (!admitted.has(assetId)) throw new TypeError("visible Gaussian asset is not admitted");
      next.add(assetId);
    }
    this.visibleAssetIds = next;
    return Object.freeze([...next].sort());
  }

  async present({ explodedOffsets = {}, ...options } = {}) {
    if (!explodedOffsets || typeof explodedOffsets !== "object" || Array.isArray(explodedOffsets)) {
      throw new TypeError("explodedOffsets must be an object");
    }
    this.explodedOffsets = Object.freeze({ ...explodedOffsets });
    const receipt = await this.renderer.present(options);
    const visibleSplatCount = [...this.visibleAssetIds].reduce(
      (total, assetId) => total + (this.payloadCounts.get(assetId) || 0),
      0,
    );
    return Object.freeze({
      ...receipt,
      version: CONSTRUCTION_GAUSSIAN_PASS_VERSION,
      representation: this.drawGaussianPass
        ? "DEGREE_ZERO_GAUSSIAN_PASS"
        : receipt.representation,
      visible_asset_ids: Object.freeze([...this.visibleAssetIds].sort()),
      visible_splat_count: visibleSplatCount,
      blend_mode: "PREMULTIPLIED_ALPHA",
      depth_order: "BACK_TO_FRONT",
      depth_write: false,
      depth_test: true,
      ...AUTHORITY_ENVELOPE,
    });
  }

  async markDeviceLost() {
    return this.renderer.markDeviceLost();
  }

  async dispose() {
    this.visibleAssetIds.clear();
    this.assetFrames.clear();
    this.payloadCounts.clear();
    this.explodedOffsets = Object.freeze({});
    return this.renderer.dispose();
  }

  status() {
    const status = this.renderer.status();
    return Object.freeze({
      ...status,
      version: CONSTRUCTION_GAUSSIAN_PASS_VERSION,
      visible_asset_count: this.visibleAssetIds.size,
      state: status.state || RENDERER_STATES.NEW,
      ...AUTHORITY_ENVELOPE,
    });
  }
}
