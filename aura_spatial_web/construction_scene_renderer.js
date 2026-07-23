import { ConstructionMeshPass } from "./construction_mesh_pass.js";
import { ConstructionOverlayPass } from "./construction_overlay_pass.js";
import { GaussianRenderer } from "./gaussian_renderer.js";
import {
  AUTHORITY_ENVELOPE,
  RENDERER_STATES,
  validateRenderPlan,
  validateSceneProjection,
} from "./renderer_adapter.js";
import { WebGL2Renderer } from "./webgl2_renderer.js";
import { createWebGL2GaussianPass } from "./webgl2_gaussian_pass.js";

export const CONSTRUCTION_SCENE_RENDERER_VERSION = "AURA_CONSTRUCTION_SCENE_RENDERER_V1";
export const CONSTRUCTION_REPRESENTATION_MODES = Object.freeze([
  "MESH",
  "SPLATS",
  "HYBRID",
]);

const IDENTITY = Object.freeze([
  1, 0, 0, 0,
  0, 1, 0, 0,
  0, 0, 1, 0,
  0, 0, 0, 1,
]);

function finite(value, label) {
  const number = Number(value);
  if (!Number.isFinite(number)) throw new TypeError(`${label} must be finite`);
  return number;
}

function canonicalTransform(frame, label) {
  const translation = frame?.translation;
  const rotation = frame?.rotation_xyzw;
  const scale = frame?.scale;
  if (
    !Array.isArray(translation) ||
    translation.length !== 3 ||
    translation.some((item) => typeof item !== "number" || !Number.isFinite(item))
  ) {
    throw new TypeError(`${label}.translation must be a finite 3-vector`);
  }
  if (
    !Array.isArray(rotation) ||
    rotation.length !== 4 ||
    rotation.some((item) => typeof item !== "number" || !Number.isFinite(item))
  ) {
    throw new TypeError(`${label}.rotation_xyzw must be a finite 4-vector`);
  }
  if (
    !Array.isArray(scale) ||
    scale.length !== 3 ||
    scale.some((item) => typeof item !== "number" || !Number.isFinite(item) || item <= 0)
  ) {
    throw new TypeError(`${label}.scale must be a positive finite 3-vector`);
  }
  return Object.freeze({
    translation: Object.freeze([...translation]),
    rotation_xyzw: Object.freeze([...rotation]),
    scale: Object.freeze([...scale]),
  });
}

function viewProjection(renderer) {
  const camera = renderer?.camera;
  const canvas = renderer?.canvas;
  if (!camera) return IDENTITY;
  const width = canvas?.width || 800;
  const height = canvas?.height || 600;
  const aspect = width / Math.max(1, height);
  const scale = Math.max(1, camera.distance);
  const cosineYaw = Math.cos(camera.yaw);
  const sineYaw = Math.sin(camera.yaw);
  const cosinePitch = Math.cos(camera.pitch);
  const sinePitch = Math.sin(camera.pitch);
  const row0 = [cosineYaw / (scale * aspect), 0, -sineYaw / (scale * aspect)];
  const row1 = [
    (sinePitch * sineYaw) / scale,
    cosinePitch / scale,
    (sinePitch * cosineYaw) / scale,
  ];
  const row2 = [
    (-cosinePitch * sineYaw) / scale,
    sinePitch / scale,
    (-cosinePitch * cosineYaw) / scale,
  ];
  const target = camera.target;
  const translation = [
    -row0[0] * target[0] - row0[1] * target[1] - row0[2] * target[2],
    -row1[0] * target[0] - row1[1] * target[1] - row1[2] * target[2],
    -row2[0] * target[0] - row2[1] * target[1] - row2[2] * target[2],
  ];
  return [
    row0[0], row1[0], row2[0], 0,
    row0[1], row1[1], row2[1], 0,
    row0[2], row1[2], row2[2], 0,
    translation[0], translation[1], translation[2], 1,
  ];
}

function aggregate(errors, message) {
  const present = errors.filter(Boolean);
  if (!present.length) return null;
  return present.length === 1 ? present[0] : new AggregateError(present, message);
}

export class ConstructionSceneRenderer {
  constructor({
    presentationRenderer,
    meshPass,
    overlayPass,
    gaussianRenderer = null,
    drawGaussianPass = null,
    drawPointCloudPass = null,
    gaussianLimits = null,
  } = {}) {
    if (!presentationRenderer || typeof presentationRenderer.initialize !== "function") {
      throw new TypeError("Construction scene renderer requires a presentation renderer");
    }
    if (!(meshPass instanceof ConstructionMeshPass)) {
      throw new TypeError("Construction scene renderer requires ConstructionMeshPass");
    }
    if (!(overlayPass instanceof ConstructionOverlayPass)) {
      throw new TypeError("Construction scene renderer requires ConstructionOverlayPass");
    }
    if (gaussianRenderer !== null && !(gaussianRenderer instanceof GaussianRenderer)) {
      throw new TypeError("gaussianRenderer must be a GaussianRenderer when supplied");
    }
    this.presentationRenderer = presentationRenderer;
    this.meshPass = meshPass;
    this.overlayPass = overlayPass;
    this.gaussianRenderer =
      gaussianRenderer ||
      new GaussianRenderer({
        presentationRenderer,
        drawGaussianPass,
        drawPointCloudPass,
        limits: gaussianLimits,
      });
    this.scene = null;
    this.plan = null;
    this.state = RENDERER_STATES.NEW;
    this.mode = "HYBRID";
    this.selectedEntityId = null;
    this.storeyFrames = Object.freeze([]);
    this.assetFrames = new Map();
    this.basePresentationTransforms = new Map();
    this.presentationTransforms = new Map();
    this.hasMeshes = false;
    this.hasSplats = false;
    this.gaussianOwnerActive = false;
    this.cancelled = false;
  }

  async initialize(
    scenePayload,
    planPayload,
    { meshPayloads = [], gaussianPayloads = [], signal } = {},
  ) {
    if (this.state !== RENDERER_STATES.NEW) {
      throw new Error("Construction scene renderer may initialize only once");
    }
    if (signal?.aborted) throw new Error("Construction scene initialization cancelled");
    this.scene = validateSceneProjection(scenePayload);
    this.plan = validateRenderPlan(planPayload, this.scene);
    this.hasMeshes = this.scene.assets.some((item) => item.asset_type === "MESH");
    this.hasSplats = this.scene.assets.some((item) => item.asset_type === "GAUSSIAN_SPLAT");
    if (this.hasSplats) {
      const invalidManifest = this.scene.assets.some(
        (asset) =>
          asset.asset_type === "GAUSSIAN_SPLAT" &&
          (asset.metadata?.gaussian_sh_degree !== 0 || asset.metadata?.sh_degree !== 0),
      );
      const invalidPayload =
        Array.isArray(gaussianPayloads) && gaussianPayloads.some((payload) => payload?.sh_degree !== 0);
      if (invalidManifest || invalidPayload) {
        this.scene = null;
        this.plan = null;
        this.state = RENDERER_STATES.LOST;
        throw new TypeError("Construction renderer accepts degree-0 Gaussian SPZ assets only");
      }
    }
    this.storeyFrames = Object.freeze(
      this.scene.entities
        .filter((item) => item.entity_type === "ASSET_INSTANCE")
        .map((item) => item.frame_id)
        .filter((value, index, values) => values.indexOf(value) === index)
        .sort(),
    );
    for (const asset of this.scene.assets) {
      this.assetFrames.set(asset.asset_id, asset.frame_id);
    }
    const rawFrames = new Map(scenePayload.frames.map((frame) => [frame.frame_id, frame]));
    for (const frameId of this.storeyFrames) {
      const frame = rawFrames.get(frameId);
      if (!frame) throw new TypeError("Construction storey frame is missing");
      const transform = canonicalTransform(frame, `frame ${frameId}`);
      this.basePresentationTransforms.set(frameId, transform);
      this.presentationTransforms.set(frameId, transform);
    }

    try {
      this.meshPass.initialize(scenePayload, meshPayloads);
      this.overlayPass.initialize(scenePayload);
      for (const [frameId, transform] of this.presentationTransforms) {
        if (this.scene.assets.some((asset) => asset.asset_type === "MESH" && asset.frame_id === frameId)) {
          this.meshPass.setPresentationTransform(frameId, transform);
        }
        this.overlayPass.setPresentationTransform(frameId, transform);
      }
      if (this.hasSplats) {
        this.gaussianOwnerActive = true;
        await this.gaussianRenderer.initialize(
          scenePayload,
          planPayload,
          gaussianPayloads,
          { signal },
        );
      } else {
        await this.presentationRenderer.initialize(scenePayload, planPayload);
      }
    } catch (error) {
      const cleanup = await this._disposeOwnedResources();
      this.state = RENDERER_STATES.LOST;
      throw aggregate([error, cleanup], "Construction initialization and cleanup failed");
    }
    this.mode = this.hasMeshes && this.hasSplats ? "HYBRID" : this.hasSplats ? "SPLATS" : "MESH";
    this.state = RENDERER_STATES.INITIALIZED;
    return this.status();
  }

  setRepresentationMode(mode) {
    if (!CONSTRUCTION_REPRESENTATION_MODES.includes(mode)) {
      throw new RangeError(`unknown Construction representation mode: ${mode}`);
    }
    if (mode !== "SPLATS" && !this.hasMeshes) {
      throw new Error("Construction scene has no admitted mesh representation");
    }
    if (mode !== "MESH" && !this.hasSplats) {
      throw new Error("Construction scene has no admitted Gaussian representation");
    }
    this.mode = mode;
  }

  isolateStorey(frameId) {
    if (!this.storeyFrames.includes(frameId)) throw new RangeError("unknown Construction storey frame");
    this.meshPass.setVisibleFrameIds([frameId]);
    this.overlayPass.setVisibleFrameIds([frameId]);
    if (this.gaussianOwnerActive) {
      const visibleGaussianAssetIds = this.scene.assets
        .filter((asset) => asset.asset_type === "GAUSSIAN_SPLAT" && asset.frame_id === frameId)
        .map((asset) => asset.asset_id);
      this.gaussianRenderer.setVisibleAssetIds(visibleGaussianAssetIds);
    }
  }

  showAllStoreys() {
    this.meshPass.setVisibleFrameIds(null);
    this.overlayPass.setVisibleFrameIds(null);
    if (this.gaussianOwnerActive) this.gaussianRenderer.setVisibleAssetIds(null);
  }

  explodeStoreys(spacing = 3) {
    const amount = finite(spacing, "explode spacing");
    if (amount < 0 || amount > 100) throw new RangeError("explode spacing must be in [0, 100]");
    this.storeyFrames.forEach((frameId, index) => {
      const base = this.basePresentationTransforms.get(frameId);
      const transform = Object.freeze({
        translation: Object.freeze([
          base.translation[0],
          base.translation[1] + index * amount,
          base.translation[2],
        ]),
        rotation_xyzw: base.rotation_xyzw,
        scale: base.scale,
      });
      this.presentationTransforms.set(frameId, transform);
      if (this.scene.assets.some((asset) => asset.asset_type === "MESH" && asset.frame_id === frameId)) {
        this.meshPass.setPresentationTransform(frameId, transform);
      }
      this.overlayPass.setPresentationTransform(frameId, transform);
    });
  }

  collapseStoreys() {
    for (const frameId of this.storeyFrames) {
      const transform = this.basePresentationTransforms.get(frameId);
      this.presentationTransforms.set(frameId, transform);
      if (this.scene.assets.some((asset) => asset.asset_type === "MESH" && asset.frame_id === frameId)) {
        this.meshPass.setPresentationTransform(frameId, transform);
      }
      this.overlayPass.setPresentationTransform(frameId, transform);
    }
  }

  getAssetPresentationTransform(assetId) {
    const frameId = this.assetFrames.get(assetId);
    const current = this.presentationTransforms.get(frameId);
    const base = this.basePresentationTransforms.get(frameId);
    if (!current || !base) return null;
    return Object.freeze({
      translation: Object.freeze(
        current.translation.map((value, index) => value - base.translation[index]),
      ),
      rotation_xyzw: Object.freeze([0, 0, 0, 1]),
      scale: Object.freeze(
        current.scale.map((value, index) => value / base.scale[index]),
      ),
    });
  }

  getAssetRenderTransform(assetId) {
    const frameId = this.assetFrames.get(assetId);
    return this.presentationTransforms.get(frameId) || null;
  }

  toggleOverlay(name, visible) {
    this.overlayPass.setLayer(name, visible);
  }

  setTimelineDay(day) {
    this.overlayPass.setTimelineDay(day);
  }

  orbit(deltaYaw, deltaPitch) {
    if (typeof this.presentationRenderer.orbit !== "function") {
      throw new Error("active presentation renderer does not support orbit");
    }
    this.presentationRenderer.orbit(deltaYaw, deltaPitch);
  }

  zoom(delta) {
    if (typeof this.presentationRenderer.zoom !== "function") {
      throw new Error("active presentation renderer does not support zoom");
    }
    this.presentationRenderer.zoom(delta);
  }

  pan(deltaX, deltaY, deltaZ = 0) {
    const camera = this.presentationRenderer.camera;
    if (!camera || !Array.isArray(camera.target)) {
      throw new Error("active presentation renderer does not support pan");
    }
    camera.target = [
      camera.target[0] + finite(deltaX, "pan deltaX"),
      camera.target[1] + finite(deltaY, "pan deltaY"),
      camera.target[2] + finite(deltaZ, "pan deltaZ"),
    ];
  }

  focusEntity(entityId) {
    const entity = this.scene?.entities.find((item) => item.entity_id === entityId);
    if (!entity) throw new RangeError("unknown Construction scene entity");
    const camera = this.presentationRenderer.camera;
    if (camera && Array.isArray(camera.target)) camera.target = [...entity.position];
    this.selectedEntityId = entityId;
    return entity;
  }

  pick(x, y, radius = 18) {
    if (typeof this.presentationRenderer.pick !== "function") return null;
    const entityId = this.presentationRenderer.pick(x, y, radius);
    if (entityId) this.selectedEntityId = entityId;
    return entityId;
  }

  resetView() {
    this.showAllStoreys();
    this.collapseStoreys();
    this.selectedEntityId = null;
    this.overlayPass.setTimelineDay(1_000_000);
    if (this.presentationRenderer.camera) {
      this.presentationRenderer.camera.yaw = 0;
      this.presentationRenderer.camera.pitch = 0;
      this.presentationRenderer.camera.distance = 12;
      this.presentationRenderer.camera.target = [0, 0, 0];
    }
  }

  async present(options = {}) {
    if (![RENDERER_STATES.INITIALIZED, RENDERER_STATES.PRESENTED].includes(this.state)) {
      throw new Error("Construction scene renderer is not initialized");
    }
    const signal = options.signal;
    if (signal?.aborted || this.cancelled) throw new Error("Construction presentation cancelled");
    try {
      const baseReceipt =
        this.mode === "MESH"
          ? await this.presentationRenderer.present(options)
          : await this.gaussianRenderer.present({
              cameraPosition: this._cameraPosition(),
              signal,
            });
      if (signal?.aborted || this.cancelled) {
        await this._disposeOwnedResources();
        this.state = RENDERER_STATES.LOST;
        throw new Error("Construction presentation cancelled");
      }
      const meshReceipt =
        this.mode === "SPLATS" ? null : await this.meshPass.present({ signal });
      if (signal?.aborted || this.cancelled) {
        await this._disposeOwnedResources();
        this.state = RENDERER_STATES.LOST;
        throw new Error("Construction presentation cancelled");
      }
      const overlayReceipt = await this.overlayPass.present({ signal });
      if (signal?.aborted || this.cancelled) {
        await this._disposeOwnedResources();
        this.state = RENDERER_STATES.LOST;
        throw new Error("Construction presentation cancelled");
      }
      this.state = RENDERER_STATES.PRESENTED;
      return Object.freeze({
        version: CONSTRUCTION_SCENE_RENDERER_VERSION,
        renderer: this.presentationRenderer.kind,
        outcome: "PRESENTED",
        representation_mode: this.mode,
        scene_digest: this.scene.scene_digest,
        render_plan_digest: this.plan.render_plan_digest,
        selected_entity_id: this.selectedEntityId,
        base_receipt: baseReceipt,
        mesh_receipt: meshReceipt,
        overlay_receipt: overlayReceipt,
        source_asset_coordinates_immutable: true,
        exploded_view_is_presentation_only: true,
        ...AUTHORITY_ENVELOPE,
      });
    } catch (error) {
      await this._disposeOwnedResources();
      this.state = RENDERER_STATES.LOST;
      throw error;
    }
  }

  _cameraPosition() {
    const camera = this.presentationRenderer.camera;
    if (!camera) return [0, 0, 0];
    return [camera.target[0], camera.target[1], camera.target[2] + camera.distance];
  }

  async markDeviceLost() {
    if (this.state === RENDERER_STATES.DISPOSED) return this.status();
    this.cancelled = true;
    const errors = [];
    try {
      await this.overlayPass.dispose();
    } catch (error) {
      errors.push(error);
    }
    try {
      await this.meshPass.dispose();
    } catch (error) {
      errors.push(error);
    }
    try {
      if (this.gaussianOwnerActive) await this.gaussianRenderer.markDeviceLost();
      else await this.presentationRenderer.dispose();
    } catch (error) {
      errors.push(error);
    }
    this.state = RENDERER_STATES.LOST;
    const failure = aggregate(errors, "Construction device-loss cleanup failed");
    if (failure) throw failure;
    return this.status();
  }

  async _disposeOwnedResources() {
    const errors = [];
    for (const owner of [this.overlayPass, this.meshPass]) {
      try {
        await owner.dispose();
      } catch (error) {
        errors.push(error);
      }
    }
    try {
      if (this.gaussianOwnerActive) await this.gaussianRenderer.dispose();
      else await this.presentationRenderer.dispose();
    } catch (error) {
      errors.push(error);
    }
    return aggregate(errors, "Construction renderer cleanup failed");
  }

  async dispose() {
    if (this.state === RENDERER_STATES.DISPOSED) return this.status();
    this.cancelled = true;
    const failure = await this._disposeOwnedResources();
    this.scene = null;
    this.plan = null;
    this.assetFrames.clear();
    this.basePresentationTransforms.clear();
    this.presentationTransforms.clear();
    this.storeyFrames = Object.freeze([]);
    this.selectedEntityId = null;
    this.state = failure ? RENDERER_STATES.LOST : RENDERER_STATES.DISPOSED;
    if (failure) throw failure;
    return this.status();
  }

  status() {
    return Object.freeze({
      version: CONSTRUCTION_SCENE_RENDERER_VERSION,
      renderer: this.presentationRenderer.kind,
      state: this.state,
      representation_mode: this.mode,
      storey_count: this.storeyFrames.length,
      selected_entity_id: this.selectedEntityId,
      gaussian_owner_active: this.gaussianOwnerActive,
      source_asset_coordinates_immutable: true,
      exploded_view_is_presentation_only: true,
      ...AUTHORITY_ENVELOPE,
    });
  }
}

export function createConstructionWebGL2SceneRenderer({
  canvas,
  gl = null,
  drawMeshPass,
  drawOverlayPass = null,
  isGaussianVisible = null,
  maxVisibleSplats = 250_000,
  meshLimits = null,
  gaussianLimits = null,
} = {}) {
  const presentationRenderer = new WebGL2Renderer({ canvas, gl });
  let controller = null;
  let innerGaussianPass = null;
  const drawGaussianPass = async (resources, context) => {
    if (!innerGaussianPass) {
      if (!presentationRenderer.gl) throw new Error("WebGL2 context is unavailable for Gaussian pass");
      innerGaussianPass = createWebGL2GaussianPass({
        gl: presentationRenderer.gl,
        getViewProjection: () => viewProjection(presentationRenderer),
        getPresentationTransform: (assetId) => controller?.getAssetRenderTransform(assetId),
        isVisible: isGaussianVisible,
        maxVisibleSplats,
      });
    }
    return innerGaussianPass(resources, context);
  };
  controller = new ConstructionSceneRenderer({
    presentationRenderer,
    meshPass: new ConstructionMeshPass({ drawMeshPass, limits: meshLimits }),
    overlayPass: new ConstructionOverlayPass({ drawOverlayPass }),
    drawGaussianPass,
    gaussianLimits,
  });
  return controller;
}
