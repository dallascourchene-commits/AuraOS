import {
  AUTHORITY_ENVELOPE,
  RENDERER_STATES,
  validateRenderPlan,
  validateSceneProjection,
} from "./renderer_adapter.js";

export const CONSTRUCTION_OVERLAY_PASS_VERSION =
  "AURA_CONSTRUCTION_OVERLAY_PASS_V1";

const MAX_OVERLAYS = 4_096;
const STATUS_STYLES = Object.freeze({
  ACTIVE: Object.freeze({ class_name: "active", icon: "▶", priority: 40 }),
  AWAITING_INSPECTION: Object.freeze({ class_name: "inspection", icon: "⌕", priority: 70 }),
  AWAITING_PROFESSIONAL_RELEASE: Object.freeze({ class_name: "professional", icon: "◆", priority: 80 }),
  BLOCKED: Object.freeze({ class_name: "blocked", icon: "⛔", priority: 100 }),
  COMPLETED: Object.freeze({ class_name: "completed", icon: "✓", priority: 20 }),
  DELAYED: Object.freeze({ class_name: "delayed", icon: "◷", priority: 90 }),
  NOT_STARTED: Object.freeze({ class_name: "not-started", icon: "○", priority: 10 }),
  READY_FOR_REVIEW: Object.freeze({ class_name: "review", icon: "◎", priority: 60 }),
  REWORK_REQUIRED: Object.freeze({ class_name: "rework", icon: "↻", priority: 95 }),
});

function requireDisposer(value) {
  if (typeof value === "function") return value;
  if (value && typeof value.dispose === "function") return value.dispose.bind(value);
  throw new TypeError("construction overlay draw pass must return a disposer");
}

function boundedText(value, label, maximum = 512) {
  const text = String(value ?? "").trim();
  if (!text || new TextEncoder().encode(text).length > maximum) {
    throw new TypeError(`${label} must be non-empty bounded text`);
  }
  return text;
}

function overlayKind(entity) {
  const metadata = entity.metadata || {};
  if (typeof metadata.status === "string" && STATUS_STYLES[metadata.status]) {
    return Object.freeze({ kind: "WORK_STATUS", status: metadata.status });
  }
  if (metadata.admissible === true || metadata.admissible === false) {
    return Object.freeze({
      kind: "PROPOSAL",
      status: metadata.admissible ? "ADMISSIBLE" : "BLOCKED",
    });
  }
  if (typeof metadata.inspection_status === "string") {
    return Object.freeze({ kind: "INSPECTION", status: metadata.inspection_status });
  }
  if (typeof metadata.release_status === "string") {
    return Object.freeze({ kind: "PROFESSIONAL_RELEASE", status: metadata.release_status });
  }
  if (metadata.truth_class === "SYNTHETIC_DEMO_RULE") {
    return Object.freeze({ kind: "SYNTHETIC_RULE", status: "NON_AUTHORITATIVE" });
  }
  if (metadata.synthetic_projection === true && metadata.currency === "CAD") {
    return Object.freeze({ kind: "BUDGET", status: "SYNTHETIC_PROJECTION" });
  }
  if (metadata.synthetic_projection === true && Number.isFinite(metadata.start_hour)) {
    return Object.freeze({ kind: "TIMELINE", status: String(metadata.status || "PROJECTED") });
  }
  return null;
}

function buildOverlay(entity) {
  const classification = overlayKind(entity);
  if (!classification) return null;
  const style = STATUS_STYLES[classification.status] || Object.freeze({
    class_name: classification.kind.toLowerCase().replaceAll("_", "-"),
    icon: "•",
    priority: 50,
  });
  return Object.freeze({
    overlay_id: `overlay:${entity.entity_id}`,
    entity_id: entity.entity_id,
    frame_id: entity.frame_id,
    label: boundedText(entity.label, "overlay label"),
    position: Object.freeze([...entity.position]),
    kind: classification.kind,
    status: classification.status,
    class_name: style.class_name,
    icon: style.icon,
    priority: style.priority,
    selectable: entity.selectable === true,
    metadata: Object.freeze({
      proposal_only: true,
      human_review_required: true,
      person_level_data_included: false,
    }),
  });
}

export class ConstructionOverlayPass {
  constructor({ drawOverlays, hitTest = null } = {}) {
    if (typeof drawOverlays !== "function") {
      throw new TypeError("ConstructionOverlayPass requires drawOverlays");
    }
    if (hitTest !== null && typeof hitTest !== "function") {
      throw new TypeError("hitTest must be callable when supplied");
    }
    this.drawOverlays = drawOverlays;
    this.hitTest = hitTest;
    this.state = RENDERER_STATES.NEW;
    this.scene = null;
    this.plan = null;
    this.overlays = Object.freeze([]);
    this.enabledKinds = new Set([
      "WORK_STATUS",
      "PROPOSAL",
      "INSPECTION",
      "PROFESSIONAL_RELEASE",
      "SYNTHETIC_RULE",
      "BUDGET",
      "TIMELINE",
    ]);
    this.selectedEntityId = null;
    this.disposers = new Set();
    this.cancelled = false;
  }

  initialize(scenePayload, planPayload) {
    if (this.state !== RENDERER_STATES.NEW) {
      throw new Error("Construction overlay pass may initialize only once");
    }
    this.scene = validateSceneProjection(scenePayload);
    this.plan = validateRenderPlan(planPayload, this.scene);
    const overlays = this.scene.entities
      .map(buildOverlay)
      .filter(Boolean)
      .sort((left, right) =>
        right.priority - left.priority || left.overlay_id.localeCompare(right.overlay_id),
      );
    if (overlays.length > MAX_OVERLAYS) {
      throw new RangeError("Construction overlay count exceeds its boundary");
    }
    this.overlays = Object.freeze(overlays);
    this.state = RENDERER_STATES.INITIALIZED;
    return this.status();
  }

  setLayerEnabled(kind, enabled) {
    const normalized = boundedText(kind, "overlay kind", 64);
    if (typeof enabled !== "boolean") throw new TypeError("enabled must be boolean");
    if (!this.overlays.some((overlay) => overlay.kind === normalized)) {
      throw new TypeError("overlay kind is not present in the scene");
    }
    if (enabled) this.enabledKinds.add(normalized);
    else this.enabledKinds.delete(normalized);
    return Object.freeze([...this.enabledKinds].sort());
  }

  select(entityId) {
    if (entityId === null) {
      this.selectedEntityId = null;
      return null;
    }
    const normalized = boundedText(entityId, "selected entity", 192);
    if (!this.scene?.entities.some((entity) => entity.entity_id === normalized && entity.selectable)) {
      throw new TypeError("selected entity is not admitted or selectable");
    }
    this.selectedEntityId = normalized;
    return normalized;
  }

  async pick(x, y, context = {}) {
    if (!this.hitTest) return null;
    if (![x, y].every((value) => typeof value === "number" && Number.isFinite(value))) {
      throw new TypeError("overlay pick coordinates must be finite");
    }
    const visible = this.visibleOverlays();
    const selected = await this.hitTest(x, y, visible, Object.freeze({
      ...context,
      scene_digest: this.scene.scene_digest,
      render_plan_digest: this.plan.render_plan_digest,
      ...AUTHORITY_ENVELOPE,
    }));
    if (selected === null || selected === undefined) return null;
    const overlay = visible.find((item) => item.entity_id === selected || item.overlay_id === selected);
    if (!overlay || !overlay.selectable) throw new TypeError("hitTest returned an inadmissible overlay");
    this.selectedEntityId = overlay.entity_id;
    return overlay.entity_id;
  }

  visibleOverlays(visibleEntityIds = null) {
    const visibleEntities = visibleEntityIds === null
      ? null
      : new Set(Array.isArray(visibleEntityIds) ? visibleEntityIds : (() => {
          throw new TypeError("visibleEntityIds must be an array when supplied");
        })());
    return Object.freeze(
      this.overlays.filter(
        (overlay) =>
          this.enabledKinds.has(overlay.kind) &&
          (visibleEntities === null || visibleEntities.has(overlay.entity_id)),
      ),
    );
  }

  async present({ visibleEntityIds = null, signal } = {}) {
    if (![RENDERER_STATES.INITIALIZED, RENDERER_STATES.PRESENTED].includes(this.state)) {
      throw new Error("Construction overlay pass is not initialized");
    }
    if (signal?.aborted || this.cancelled) throw new Error("Construction overlay presentation cancelled");
    const visible = this.visibleOverlays(visibleEntityIds);
    try {
      const disposer = requireDisposer(
        await this.drawOverlays(
          visible,
          Object.freeze({
            selected_entity_id: this.selectedEntityId,
            scene_digest: this.scene.scene_digest,
            render_plan_digest: this.plan.render_plan_digest,
            signal,
            ...AUTHORITY_ENVELOPE,
          }),
        ),
      );
      this.disposers.add(disposer);
    } catch (error) {
      await this._releaseDrawResources();
      this.cancelled = true;
      this.state = RENDERER_STATES.LOST;
      throw error;
    }
    this.state = RENDERER_STATES.PRESENTED;
    return Object.freeze({
      version: CONSTRUCTION_OVERLAY_PASS_VERSION,
      outcome: "PRESENTED",
      scene_digest: this.scene.scene_digest,
      render_plan_digest: this.plan.render_plan_digest,
      overlay_count: visible.length,
      selected_entity_id: this.selectedEntityId,
      enabled_kinds: Object.freeze([...this.enabledKinds].sort()),
      ...AUTHORITY_ENVELOPE,
    });
  }

  accessibleRows() {
    return Object.freeze(
      this.visibleOverlays().map((overlay) =>
        Object.freeze({
          entity_id: overlay.entity_id,
          label: overlay.label,
          kind: overlay.kind,
          status: overlay.status,
          selected: overlay.entity_id === this.selectedEntityId,
          human_review_required: true,
        }),
      ),
    );
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
    let error = null;
    try {
      await this._releaseDrawResources();
    } catch (cleanupError) {
      error = cleanupError;
    }
    this.overlays = Object.freeze([]);
    this.enabledKinds.clear();
    this.selectedEntityId = null;
    this.scene = null;
    this.plan = null;
    if (error) {
      this.state = RENDERER_STATES.LOST;
      throw error;
    }
    this.state = RENDERER_STATES.DISPOSED;
    return this.status();
  }

  status() {
    return Object.freeze({
      version: CONSTRUCTION_OVERLAY_PASS_VERSION,
      state: this.state,
      overlay_count: this.overlays.length,
      enabled_kind_count: this.enabledKinds.size,
      disposer_count: this.disposers.size,
      selected_entity_id: this.selectedEntityId,
      ...AUTHORITY_ENVELOPE,
    });
  }
}
