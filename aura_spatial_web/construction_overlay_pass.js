import {
  AUTHORITY_ENVELOPE,
  validateSceneProjection,
} from "./renderer_adapter.js";

export const CONSTRUCTION_OVERLAY_PASS_VERSION = "AURA_CONSTRUCTION_OVERLAY_PASS_V1";
export const CONSTRUCTION_OVERLAY_LAYERS = Object.freeze([
  "floorPlans",
  "status",
  "trades",
  "blockers",
  "budgets",
  "inspections",
  "dependencies",
  "syntheticRules",
]);

function requireDisposer(value) {
  if (typeof value === "function") return value;
  if (value && typeof value.dispose === "function") return value.dispose.bind(value);
  throw new TypeError("Construction overlay draw pass must return a disposal handle");
}

function finiteDay(value) {
  const day = Number(value);
  if (!Number.isFinite(day) || day < -1_000_000 || day > 1_000_000) {
    throw new RangeError("Construction timeline day must be finite and bounded");
  }
  return day;
}

function finiteVector(value, length, label, fallback, { positive = false } = {}) {
  const candidate = value ?? fallback;
  if (
    !Array.isArray(candidate) ||
    candidate.length !== length ||
    candidate.some(
      (item) =>
        typeof item !== "number" ||
        !Number.isFinite(item) ||
        (positive && item <= 0),
    )
  ) {
    throw new TypeError(`${label} must be a finite ${length}-vector`);
  }
  return Object.freeze([...candidate]);
}

function canonicalTransform(value, label = "presentation_transform") {
  const source = value || {};
  return Object.freeze({
    translation: finiteVector(
      source.translation,
      3,
      `${label}.translation`,
      [0, 0, 0],
    ),
    rotation_xyzw: finiteVector(
      source.rotation_xyzw,
      4,
      `${label}.rotation_xyzw`,
      [0, 0, 0, 1],
    ),
    scale: finiteVector(source.scale, 3, `${label}.scale`, [1, 1, 1], {
      positive: true,
    }),
  });
}

function deepFreeze(value) {
  if (!value || typeof value !== "object" || Object.isFrozen(value)) return value;
  Object.freeze(value);
  for (const item of Object.values(value)) deepFreeze(item);
  return value;
}

function hasOverlayKind(record, kind) {
  return record.metadata?.overlay_kind === kind;
}

export class ConstructionOverlayPass {
  constructor({ drawOverlayPass = null, maxOverlayItems = 2048 } = {}) {
    if (drawOverlayPass !== null && typeof drawOverlayPass !== "function") {
      throw new TypeError("drawOverlayPass must be callable when supplied");
    }
    if (!Number.isInteger(maxOverlayItems) || maxOverlayItems < 1 || maxOverlayItems > 20_000) {
      throw new RangeError("maxOverlayItems must be an integer in [1, 20000]");
    }
    this.drawOverlayPass = drawOverlayPass;
    this.maxOverlayItems = maxOverlayItems;
    this.scene = null;
    this.layers = new Map(CONSTRUCTION_OVERLAY_LAYERS.map((name) => [name, true]));
    this.timelineDay = 1_000_000;
    this.visibleFrameIds = null;
    this.presentationTransforms = new Map();
    this.disposer = null;
    this.initialized = false;
    this.disposed = false;
  }

  initialize(scenePayload) {
    if (this.initialized || this.disposed) {
      throw new Error("Construction overlay pass may initialize only once");
    }
    validateSceneProjection(scenePayload);
    this.scene = deepFreeze(structuredClone(scenePayload));
    for (const frame of this.scene.frames) {
      this.presentationTransforms.set(
        frame.frame_id,
        canonicalTransform(frame, `frame ${frame.frame_id}`),
      );
    }
    this.initialized = true;
    return this.status();
  }

  setLayer(name, visible) {
    if (!this.layers.has(name)) throw new RangeError(`unknown Construction overlay layer: ${name}`);
    if (typeof visible !== "boolean") throw new TypeError("overlay visibility must be boolean");
    this.layers.set(name, visible);
  }

  setTimelineDay(day) {
    this.timelineDay = finiteDay(day);
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
      throw new RangeError("unknown Construction overlay frame");
    }
    this.presentationTransforms.set(
      frameId,
      canonicalTransform(transform, `frame ${frameId} presentation_transform`),
    );
  }

  resetPresentationTransforms() {
    if (!this.scene) return;
    for (const frame of this.scene.frames) {
      this.presentationTransforms.set(
        frame.frame_id,
        canonicalTransform(frame, `frame ${frame.frame_id}`),
      );
    }
  }

  _frameVisible(frameId) {
    return this.visibleFrameIds === null || this.visibleFrameIds.has(frameId);
  }

  buildModel() {
    if (!this.initialized || this.disposed) {
      throw new Error("Construction overlay pass is not initialized");
    }
    const entities = this.scene.entities.filter((item) => this._frameVisible(item.frame_id));
    const entitiesById = new Map(entities.map((item) => [item.entity_id, item]));
    const entityIds = new Set(entitiesById.keys());
    const links = this.scene.links.filter(
      (item) => entityIds.has(item.source_entity_id) && entityIds.has(item.target_entity_id),
    );
    const withinTimeline = (item) => {
      const day = item.metadata?.day ?? item.metadata?.planned_start_day ?? -Infinity;
      return typeof day !== "number" || day <= this.timelineDay;
    };
    const presentationTransform = (frameId) =>
      this.presentationTransforms.get(frameId) || canonicalTransform(null);
    const model = {
      version: CONSTRUCTION_OVERLAY_PASS_VERSION,
      timeline_day: this.timelineDay,
      presentation_transforms: Object.freeze(
        Object.fromEntries(
          [...this.presentationTransforms.entries()].sort(([left], [right]) =>
            left.localeCompare(right),
          ),
        ),
      ),
      floor_plans: this.layers.get("floorPlans")
        ? this.scene.assets
            .filter((item) => item.asset_type === "PLANE" && this._frameVisible(item.frame_id))
            .map((item) => ({
              asset_id: item.asset_id,
              frame_id: item.frame_id,
              content_digest: item.content_digest,
              source_transform_immutable: true,
              presentation_transform: presentationTransform(item.frame_id),
            }))
        : [],
      status: this.layers.get("status")
        ? entities
            .filter((item) => item.metadata?.status_overlay && withinTimeline(item))
            .map((item) => ({
              entity_id: item.entity_id,
              frame_id: item.frame_id,
              status: item.metadata.status_overlay,
              label: item.label,
              presentation_transform: presentationTransform(item.frame_id),
            }))
        : [],
      trades: this.layers.get("trades")
        ? entities
            .filter((item) => hasOverlayKind(item, "TRADE"))
            .map((item) => ({
              entity_id: item.entity_id,
              frame_id: item.frame_id,
              label: item.label,
              presentation_transform: presentationTransform(item.frame_id),
            }))
        : [],
      blockers: this.layers.get("blockers")
        ? links
            .filter((item) => ["BLOCKED_BY", "HAS_BLOCKED_PROPOSAL"].includes(item.relation))
            .map((item) => ({
              link_id: item.link_id,
              source_entity_id: item.source_entity_id,
              target_entity_id: item.target_entity_id,
              relation: item.relation,
            }))
        : [],
      budgets: this.layers.get("budgets")
        ? entities
            .filter((item) => hasOverlayKind(item, "BUDGET"))
            .map((item) => ({
              entity_id: item.entity_id,
              frame_id: item.frame_id,
              label: item.label,
              committed_cad: item.metadata?.committed_cad ?? 0,
              forecast_cad: item.metadata?.forecast_cad ?? 0,
              actual_cad: item.metadata?.actual_cad ?? 0,
              truth_class: item.metadata?.truth_class || "",
              presentation_transform: presentationTransform(item.frame_id),
            }))
        : [],
      inspections: this.layers.get("inspections")
        ? entities
            .filter((item) => hasOverlayKind(item, "INSPECTION"))
            .map((item) => ({
              entity_id: item.entity_id,
              frame_id: item.frame_id,
              label: item.label,
              status: item.metadata?.status_overlay || "UNKNOWN",
              scheduled_day: item.metadata?.scheduled_day ?? null,
              presentation_transform: presentationTransform(item.frame_id),
            }))
        : [],
      dependencies: this.layers.get("dependencies")
        ? links
            .filter((item) => item.relation === "DEPENDS_ON")
            .map((item) => ({
              link_id: item.link_id,
              source_entity_id: item.source_entity_id,
              target_entity_id: item.target_entity_id,
            }))
        : [],
      synthetic_rules: this.layers.get("syntheticRules")
        ? entities
            .filter((item) => hasOverlayKind(item, "SYNTHETIC_RULE"))
            .map((item) => ({
              entity_id: item.entity_id,
              frame_id: item.frame_id,
              label: item.label,
              requirement: item.metadata?.requirement || "",
              truth_class: item.metadata?.truth_class || "",
              legal_authority: false,
              regulatory_authority: false,
              presentation_transform: presentationTransform(item.frame_id),
            }))
        : [],
      source_geometry_mutated: false,
      person_level_data_included: false,
      ...AUTHORITY_ENVELOPE,
    };
    const itemCount = CONSTRUCTION_OVERLAY_LAYERS.reduce(
      (total, name) =>
        total +
        model[
          name === "floorPlans"
            ? "floor_plans"
            : name === "syntheticRules"
              ? "synthetic_rules"
              : name
        ].length,
      0,
    );
    if (itemCount > this.maxOverlayItems) {
      throw new RangeError("Construction overlay item budget exceeded");
    }
    return deepFreeze(model);
  }

  async present({ signal } = {}) {
    if (signal?.aborted) throw new Error("Construction overlay presentation cancelled");
    await this.releaseDrawResources();
    const model = this.buildModel();
    if (this.drawOverlayPass) {
      this.disposer = requireDisposer(
        await this.drawOverlayPass(model, Object.freeze({ signal, ...AUTHORITY_ENVELOPE })),
      );
      if (signal?.aborted) {
        await this.releaseDrawResources();
        throw new Error("Construction overlay presentation cancelled");
      }
    }
    return Object.freeze({
      version: CONSTRUCTION_OVERLAY_PASS_VERSION,
      outcome: "PRESENTED",
      model,
      drawn: Boolean(this.drawOverlayPass),
      source_geometry_mutated: false,
      ...AUTHORITY_ENVELOPE,
    });
  }

  async releaseDrawResources() {
    if (!this.disposer) return;
    const dispose = this.disposer;
    this.disposer = null;
    await dispose();
  }

  async dispose() {
    if (this.disposed) return this.status();
    try {
      await this.releaseDrawResources();
    } finally {
      this.scene = null;
      this.visibleFrameIds = null;
      this.presentationTransforms.clear();
      this.initialized = false;
      this.disposed = true;
    }
    return this.status();
  }

  status() {
    return Object.freeze({
      version: CONSTRUCTION_OVERLAY_PASS_VERSION,
      initialized: this.initialized,
      disposed: this.disposed,
      timeline_day: this.timelineDay,
      layers: Object.freeze(Object.fromEntries(this.layers)),
      active_disposer_count: this.disposer ? 1 : 0,
      source_geometry_mutated: false,
      ...AUTHORITY_ENVELOPE,
    });
  }
}
