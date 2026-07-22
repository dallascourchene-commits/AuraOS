import {
  AUTHORITY_ENVELOPE,
  RENDERER_STATES,
  validateRenderPlan,
  validateSceneProjection,
} from "./renderer_adapter.js";

export const CONSTRUCTION_SCENE_RENDERER_VERSION =
  "AURA_CONSTRUCTION_SCENE_RENDERER_V1";
export const CONSTRUCTION_RENDER_MODES = Object.freeze([
  "MESH_ONLY",
  "SPLATS_ONLY",
  "HYBRID",
  "ACCESSIBLE_2D",
]);

function requirePass(value, label, methods) {
  if (!value || typeof value !== "object") {
    throw new TypeError(`${label} is required`);
  }
  for (const method of methods) {
    if (typeof value[method] !== "function") {
      throw new TypeError(`${label}.${method} must be callable`);
    }
  }
  return value;
}

function finiteNonNegative(value, label, maximum) {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > maximum) {
    throw new RangeError(`${label} must be finite and in [0, ${maximum}]`);
  }
  return value;
}

async function disposeAll(entries) {
  const errors = [];
  for (const entry of [...entries].reverse()) {
    try {
      await entry.dispose();
    } catch (error) {
      errors.push(error);
    }
  }
  if (errors.length === 1) throw errors[0];
  if (errors.length > 1) throw new AggregateError(errors, "Construction renderer cleanup failed");
}

export class ConstructionSceneRenderer {
  constructor({ meshPass, gaussianPass, overlayPass } = {}) {
    this.meshPass = requirePass(meshPass, "meshPass", [
      "initialize",
      "setVisibleAssets",
      "present",
      "markDeviceLost",
      "dispose",
      "status",
    ]);
    this.gaussianPass = requirePass(gaussianPass, "gaussianPass", [
      "initialize",
      "setVisibleAssets",
      "present",
      "markDeviceLost",
      "dispose",
      "status",
    ]);
    this.overlayPass = requirePass(overlayPass, "overlayPass", [
      "initialize",
      "present",
      "pick",
      "accessibleRows",
      "markDeviceLost",
      "dispose",
      "status",
    ]);
    this.state = RENDERER_STATES.NEW;
    this.scene = null;
    this.plan = null;
    this.mode = "ACCESSIBLE_2D";
    this.availableModes = Object.freeze(["ACCESSIBLE_2D"]);
    this.visibleFrameIds = new Set();
    this.visibleEntityIds = null;
    this.floorPlanAssetIds = Object.freeze([]);
    this.visibleFloorPlanAssetIds = Object.freeze([]);
    this.exploded = false;
    this.explodeSpacing = 0;
    this.explodedOffsets = Object.freeze({});
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
    if (signal?.aborted) throw new Error("Construction renderer initialization cancelled");
    this.scene = validateSceneProjection(scenePayload);
    this.plan = validateRenderPlan(planPayload, this.scene);
    const meshAssets = this.scene.assets.filter((asset) => asset.asset_type === "MESH");
    const gaussianAssets = this.scene.assets.filter(
      (asset) => asset.asset_type === "GAUSSIAN_SPLAT",
    );
    const floorPlans = this.scene.assets.filter((asset) => asset.asset_type === "PLANE");
    if (meshPayloads.length !== meshAssets.length) {
      throw new TypeError("meshPayloads must exactly cover Construction mesh manifests");
    }
    if (gaussianPayloads.length !== gaussianAssets.length) {
      throw new TypeError("gaussianPayloads must exactly cover Construction Gaussian manifests");
    }

    const initialized = [];
    try {
      await this.meshPass.initialize(this.scene, this.plan, meshPayloads, { signal });
      initialized.push(this.meshPass);
      if (signal?.aborted) throw new Error("Construction renderer initialization cancelled");
      await this.gaussianPass.initialize(this.scene, this.plan, gaussianPayloads, { signal });
      initialized.push(this.gaussianPass);
      if (signal?.aborted) throw new Error("Construction renderer initialization cancelled");
      await this.overlayPass.initialize(this.scene, this.plan);
      initialized.push(this.overlayPass);
    } catch (error) {
      let cleanupError = null;
      try {
        await disposeAll(initialized);
      } catch (cleanup) {
        cleanupError = cleanup;
      }
      this.cancelled = true;
      this.state = RENDERER_STATES.LOST;
      if (cleanupError) {
        throw new AggregateError([error, cleanupError], "Construction initialization and cleanup failed");
      }
      throw error;
    }

    const modes = ["ACCESSIBLE_2D"];
    if (meshAssets.length) modes.push("MESH_ONLY");
    if (gaussianAssets.length) modes.push("SPLATS_ONLY");
    if (meshAssets.length && gaussianAssets.length) modes.push("HYBRID");
    this.availableModes = Object.freeze(
      CONSTRUCTION_RENDER_MODES.filter((mode) => modes.includes(mode)),
    );
    const preferred = String(this.scene.renderer_hints?.preferred_representation || "");
    this.mode =
      preferred === "HYBRID_MESH_GAUSSIAN" && this.availableModes.includes("HYBRID")
        ? "HYBRID"
        : this.availableModes.includes("MESH_ONLY")
          ? "MESH_ONLY"
          : this.availableModes.includes("SPLATS_ONLY")
            ? "SPLATS_ONLY"
            : "ACCESSIBLE_2D";
    this.floorPlanAssetIds = Object.freeze(floorPlans.map((asset) => asset.asset_id).sort());
    this.visibleFloorPlanAssetIds = this.floorPlanAssetIds;
    this.visibleFrameIds = new Set(
      [...new Set([...meshAssets, ...gaussianAssets, ...floorPlans].map((asset) => asset.frame_id))].sort(),
    );
    this.state = RENDERER_STATES.INITIALIZED;
    return this.status();
  }

  setMode(mode) {
    const normalized = String(mode || "");
    if (!this.availableModes.includes(normalized)) {
      throw new TypeError("Construction render mode is unavailable for this scene");
    }
    this.mode = normalized;
    return normalized;
  }

  isolateStoreys(frameIds) {
    if (!Array.isArray(frameIds)) throw new TypeError("frameIds must be an array");
    const assetFrameIds = new Set(this.scene.assets.map((asset) => asset.frame_id));
    const nextFrames = new Set();
    for (const frameId of frameIds) {
      if (!assetFrameIds.has(frameId)) {
        throw new TypeError("isolated Construction frame is not asset-bearing");
      }
      nextFrames.add(frameId);
    }
    if (nextFrames.size === 0) {
      for (const frameId of assetFrameIds) nextFrames.add(frameId);
    }
    const meshIds = this.scene.assets
      .filter((asset) => asset.asset_type === "MESH" && nextFrames.has(asset.frame_id))
      .map((asset) => asset.asset_id);
    const gaussianIds = this.scene.assets
      .filter(
        (asset) => asset.asset_type === "GAUSSIAN_SPLAT" && nextFrames.has(asset.frame_id),
      )
      .map((asset) => asset.asset_id);
    this.visibleFloorPlanAssetIds = Object.freeze(
      this.scene.assets
        .filter((asset) => asset.asset_type === "PLANE" && nextFrames.has(asset.frame_id))
        .map((asset) => asset.asset_id)
        .sort(),
    );
    this.visibleFrameIds = nextFrames;
    this.visibleEntityIds = Object.freeze(
      this.scene.entities
        .filter((entity) => nextFrames.has(entity.frame_id))
        .map((entity) => entity.entity_id)
        .sort(),
    );
    this.meshPass.setVisibleAssets(meshIds);
    this.gaussianPass.setVisibleAssets(gaussianIds);
    this._rebuildExplodedOffsets();
    return this.storeyState();
  }

  setExploded(enabled, spacing = 6) {
    if (typeof enabled !== "boolean") throw new TypeError("enabled must be boolean");
    this.exploded = enabled;
    this.explodeSpacing = enabled
      ? finiteNonNegative(Number(spacing), "explode spacing", 1_000)
      : 0;
    this._rebuildExplodedOffsets();
    return this.storeyState();
  }

  _rebuildExplodedOffsets() {
    if (!this.exploded) {
      this.explodedOffsets = Object.freeze({});
      return;
    }
    const frames = [...this.visibleFrameIds].sort();
    this.explodedOffsets = Object.freeze(
      Object.fromEntries(
        frames.map((frameId, index) => [frameId, [0, index * this.explodeSpacing, 0]]),
      ),
    );
  }

  storeyState() {
    return Object.freeze({
      visible_frame_ids: Object.freeze([...this.visibleFrameIds].sort()),
      floor_plan_asset_ids: this.visibleFloorPlanAssetIds,
      exploded: this.exploded,
      explode_spacing: this.explodeSpacing,
      exploded_offsets: this.explodedOffsets,
      ...AUTHORITY_ENVELOPE,
    });
  }

  async present({ signal, cameraPosition = [0, 0, 0] } = {}) {
    if (![RENDERER_STATES.INITIALIZED, RENDERER_STATES.PRESENTED].includes(this.state)) {
      throw new Error("Construction scene renderer is not initialized");
    }
    if (signal?.aborted || this.cancelled) throw new Error("Construction presentation cancelled");
    const receipts = [];
    try {
      if (["MESH_ONLY", "HYBRID"].includes(this.mode)) {
        receipts.push(
          await this.meshPass.present({
            explodedOffsets: this.explodedOffsets,
            signal,
          }),
        );
      }
      if (["SPLATS_ONLY", "HYBRID"].includes(this.mode)) {
        receipts.push(
          await this.gaussianPass.present({
            explodedOffsets: this.explodedOffsets,
            cameraPosition,
            signal,
          }),
        );
      }
      receipts.push(
        await this.overlayPass.present({
          visibleEntityIds: this.visibleEntityIds,
          signal,
        }),
      );
    } catch (error) {
      this.cancelled = true;
      this.state = RENDERER_STATES.LOST;
      throw error;
    }
    this.state = RENDERER_STATES.PRESENTED;
    return Object.freeze({
      version: CONSTRUCTION_SCENE_RENDERER_VERSION,
      renderer: "CONSTRUCTION_SCENE",
      outcome: "PRESENTED",
      mode: this.mode,
      scene_digest: this.scene.scene_digest,
      render_plan_digest: this.plan.render_plan_digest,
      pass_receipts: Object.freeze(receipts),
      composition_order: Object.freeze(
        this.mode === "HYBRID"
          ? ["MESH_DEPTH_PASS", "GAUSSIAN_ALPHA_PASS", "CONSTRUCTION_OVERLAY_PASS"]
          : [this.mode, "CONSTRUCTION_OVERLAY_PASS"],
      ),
      visible_floor_plan_asset_ids: this.visibleFloorPlanAssetIds,
      accessible_rows: this.overlayPass.accessibleRows(),
      storey_state: this.storeyState(),
      ...AUTHORITY_ENVELOPE,
    });
  }

  async pick(x, y, context = {}) {
    return this.overlayPass.pick(x, y, {
      ...context,
      mode: this.mode,
      visible_frame_ids: [...this.visibleFrameIds].sort(),
    });
  }

  async markDeviceLost() {
    this.cancelled = true;
    const errors = [];
    for (const pass of [this.overlayPass, this.gaussianPass, this.meshPass]) {
      try {
        await pass.markDeviceLost();
      } catch (error) {
        errors.push(error);
      }
    }
    this.state = RENDERER_STATES.LOST;
    if (errors.length === 1) throw errors[0];
    if (errors.length > 1) throw new AggregateError(errors, "Construction device-loss cleanup failed");
    return this.status();
  }

  async dispose() {
    this.cancelled = true;
    let error = null;
    try {
      await disposeAll([this.meshPass, this.gaussianPass, this.overlayPass]);
    } catch (cleanupError) {
      error = cleanupError;
    }
    this.scene = null;
    this.plan = null;
    this.visibleFrameIds.clear();
    this.visibleEntityIds = null;
    this.floorPlanAssetIds = Object.freeze([]);
    this.visibleFloorPlanAssetIds = Object.freeze([]);
    this.explodedOffsets = Object.freeze({});
    if (error) {
      this.state = RENDERER_STATES.LOST;
      throw error;
    }
    this.state = RENDERER_STATES.DISPOSED;
    return this.status();
  }

  status() {
    return Object.freeze({
      version: CONSTRUCTION_SCENE_RENDERER_VERSION,
      state: this.state,
      mode: this.mode,
      available_modes: this.availableModes,
      visible_storey_count: this.visibleFrameIds.size,
      visible_floor_plan_count: this.visibleFloorPlanAssetIds.length,
      exploded: this.exploded,
      mesh_pass: this.meshPass.status(),
      gaussian_pass: this.gaussianPass.status(),
      overlay_pass: this.overlayPass.status(),
      ...AUTHORITY_ENVELOPE,
    });
  }
}
