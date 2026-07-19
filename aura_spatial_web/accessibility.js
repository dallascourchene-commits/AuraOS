import {
  AUTHORITY_ENVELOPE,
  RendererAdapter,
  RENDERER_STATES,
  validateSceneProjection,
} from "./renderer_adapter.js";

function accessibleModelFromValidated(scene) {
  const inbound = new Map();
  const outbound = new Map();
  for (const link of scene.links) {
    outbound.set(link.source_entity_id, (outbound.get(link.source_entity_id) || 0) + 1);
    inbound.set(link.target_entity_id, (inbound.get(link.target_entity_id) || 0) + 1);
  }
  return Object.freeze({
    scene_id: scene.scene_id,
    scene_digest: scene.scene_digest,
    rows: Object.freeze(
      scene.entities.map((entity) =>
        Object.freeze({
          entity_id: entity.entity_id,
          label: entity.label,
          entity_type: entity.entity_type,
          selectable: entity.selectable,
          inbound_links: inbound.get(entity.entity_id) || 0,
          outbound_links: outbound.get(entity.entity_id) || 0,
          source_refs: entity.source_refs,
        }),
      ),
    ),
    ...AUTHORITY_ENVELOPE,
  });
}

export function buildAccessibleSceneModel(scenePayload) {
  return accessibleModelFromValidated(validateSceneProjection(scenePayload));
}

function renderAccessibleModel(container, model, onInteraction) {
  if (!container || typeof container.replaceChildren !== "function") {
    throw new TypeError("container must be a DOM element");
  }
  if (typeof onInteraction !== "function") throw new TypeError("onInteraction must be callable");
  const doc = container.ownerDocument || globalThis.document;
  if (!doc?.createElement) throw new TypeError("a DOM document is required");
  const table = doc.createElement("table");
  table.setAttribute("role", "grid");
  table.setAttribute("aria-label", `Spatial scene ${model.scene_id}`);
  const head = doc.createElement("thead");
  head.innerHTML = "<tr><th>Entity</th><th>Type</th><th>Links</th><th>Source</th></tr>";
  table.append(head);
  const body = doc.createElement("tbody");
  for (const row of model.rows) {
    const tr = doc.createElement("tr");
    tr.tabIndex = row.selectable ? 0 : -1;
    tr.dataset.entityId = row.entity_id;
    const source = row.source_refs[0] || "unavailable";
    tr.innerHTML = `<td>${escapeHtml(row.label)}</td><td>${escapeHtml(row.entity_type)}</td><td>${row.inbound_links + row.outbound_links}</td><td>${escapeHtml(source)}</td>`;
    const activate = () => {
      if (row.selectable) {
        return onInteraction(
          Object.freeze({
            action: "SELECT",
            target_entity_ids: [row.entity_id],
            input_source: "KEYBOARD",
            ...AUTHORITY_ENVELOPE,
          }),
        );
      }
      return undefined;
    };
    tr.addEventListener("click", activate);
    tr.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        activate();
      }
    });
    body.append(tr);
  }
  table.append(body);
  container.replaceChildren(table);
}

export function renderAccessibleScene(container, scenePayload, onInteraction = () => {}) {
  const model = buildAccessibleSceneModel(scenePayload);
  renderAccessibleModel(container, model, onInteraction);
  return model;
}

export class Accessible2DRenderer extends RendererAdapter {
  constructor({ container, onInteraction = () => {} } = {}) {
    super("ACCESSIBLE_2D");
    this.container = container;
    this.onInteraction = onInteraction;
    this.model = null;
  }

  present() {
    if (this.state !== RENDERER_STATES.INITIALIZED) {
      throw new Error("accessible renderer is not initialized");
    }
    this.model = accessibleModelFromValidated(this.scene);
    renderAccessibleModel(this.container, this.model, this.onInteraction);
    this.markPresented();
    return Object.freeze({
      renderer: "ACCESSIBLE_2D",
      outcome: "PRESENTED",
      evidence_class: "CALCULATED",
      scene_digest: this.scene.scene_digest,
      render_plan_digest: this.plan.render_plan_digest,
      entity_count: this.scene.entities.length,
      link_count: this.scene.links.length,
      ...AUTHORITY_ENVELOPE,
    });
  }

  dispose() {
    this.container?.replaceChildren?.();
    this.model = null;
    return super.dispose();
  }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) =>
    ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "'": "&#39;",
      '"': "&quot;",
    })[character],
  );
}
