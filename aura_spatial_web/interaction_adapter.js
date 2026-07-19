import { AUTHORITY_ENVELOPE } from "./renderer_adapter.js";

const ID = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$/;
const DIGEST = /^[0-9a-f]{64}$/;
const INPUTS = new Set(["MOUSE", "TOUCH", "KEYBOARD", "RAY", "CONTROLLER"]);
const BLOCKED_KEY = /(authority|approval|automatic|commit|merge|mutation|promotion|lease|verifier|prototype|constructor|__proto__)/i;
const MAX_METADATA_BYTES = 16 * 1024;
const MAX_METADATA_DEPTH = 6;

const SLOTS = Object.freeze({
  SELECT: { DIR: "scene", ASP: "inspect", CLASS: "spatial_selection", SUBJ: "domain_projection", VOICE: "select", STEM: "bind_selection" },
  DESELECT: { DIR: "scene", ASP: "inspect", CLASS: "spatial_selection", SUBJ: "domain_projection", VOICE: "deselect", STEM: "release_selection" },
  EXPAND: { DIR: "scene", ASP: "navigate", CLASS: "bounded_projection", SUBJ: "domain_neighborhood", VOICE: "expand", STEM: "request_neighborhood" },
  CONTRACT: { DIR: "scene", ASP: "navigate", CLASS: "bounded_projection", SUBJ: "domain_neighborhood", VOICE: "contract", STEM: "reduce_neighborhood" },
  FOCUS: { DIR: "scene", ASP: "navigate", CLASS: "spatial_focus", SUBJ: "domain_projection", VOICE: "focus", STEM: "center_view" },
  OPEN_SOURCE: { DIR: "repository", ASP: "inspect", CLASS: "exact_source_navigation", SUBJ: "selected_entity_source", VOICE: "open", STEM: "resolve_source_anchor" },
  PREPARE_REPAIR_REQUEST: { DIR: "forge", ASP: "prepare", CLASS: "governed_repair_request", SUBJ: "selected_entity_source", VOICE: "propose", STEM: "compile_review_handoff" },
});

function identifier(value, label) {
  const text = String(value || "");
  if (!ID.test(text)) throw new TypeError(`${label} is invalid`);
  return text;
}

function sanitizeMetadata(value, depth = 0) {
  if (depth > MAX_METADATA_DEPTH) throw new RangeError("metadata nesting ceiling exceeded");
  if (value === null || typeof value === "boolean" || typeof value === "string") return value;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new TypeError("metadata numbers must be finite");
    return value;
  }
  if (Array.isArray(value)) {
    if (value.length > 128) throw new RangeError("metadata array ceiling exceeded");
    return value.map((item) => sanitizeMetadata(item, depth + 1));
  }
  if (!value || typeof value !== "object" || Object.getPrototypeOf(value) !== Object.prototype) {
    throw new TypeError("metadata must contain plain JSON values");
  }
  const output = {};
  const keys = Object.keys(value).sort();
  if (keys.length > 128) throw new RangeError("metadata key ceiling exceeded");
  for (const key of keys) {
    if (BLOCKED_KEY.test(key)) throw new TypeError(`metadata authority alias rejected: ${key}`);
    output[key] = sanitizeMetadata(value[key], depth + 1);
  }
  return output;
}

export function compileBrowserInteraction({
  session_id,
  scene_id,
  scene_digest,
  action,
  target_entity_ids,
  actor_ref = "human:local",
  input_source,
  metadata = {},
}) {
  if (!SLOTS[action]) throw new TypeError("unsupported spatial action");
  if (!INPUTS.has(input_source)) throw new TypeError("unsupported browser input source");
  const sessionId = identifier(session_id, "session_id");
  const sceneId = identifier(scene_id, "scene_id");
  if (!DIGEST.test(String(scene_digest || ""))) {
    throw new TypeError("scene_digest must be lowercase sha256");
  }
  const actorRef = identifier(actor_ref, "actor_ref");
  if (!Array.isArray(target_entity_ids) || target_entity_ids.length < 1 || target_entity_ids.length > 128) {
    throw new RangeError("target_entity_ids must be a bounded non-empty array");
  }
  const targets = [...new Set(target_entity_ids.map((value) => identifier(value, "target_entity_id")))].sort();
  if (!metadata || typeof metadata !== "object" || Array.isArray(metadata) || Object.getPrototypeOf(metadata) !== Object.prototype) {
    throw new TypeError("metadata must be a plain object");
  }
  const safeMetadata = sanitizeMetadata(metadata);
  const serializedMetadata = JSON.stringify(safeMetadata);
  if (new TextEncoder().encode(serializedMetadata).length > MAX_METADATA_BYTES) {
    throw new RangeError("metadata byte ceiling exceeded");
  }
  return Object.freeze({
    version: "AURA_SPATIAL_BROWSER_INTERACTION_V1",
    session_id: sessionId,
    scene_id: sceneId,
    scene_digest,
    action,
    target_entity_ids: Object.freeze(targets),
    actor_ref: actorRef,
    input_source,
    intent_slots: Object.freeze({ ...SLOTS[action] }),
    metadata: Object.freeze({
      ...safeMetadata,
      input_source,
      renderer_input_is_authority: false,
    }),
    review_only: true,
    requires_forge: action === "PREPARE_REPAIR_REQUEST",
    ...AUTHORITY_ENVELOPE,
  });
}

export function toServerInteractionRequest(packet) {
  const {
    renderer_input_is_authority: _browserAuthoritySentinel,
    ...serverMetadata
  } = packet.metadata;
  return Object.freeze({
    session_id: packet.session_id,
    action: packet.action,
    target_entity_ids: [...packet.target_entity_ids],
    actor_ref: packet.actor_ref,
    metadata: {
      ...serverMetadata,
      browser_scene_id: packet.scene_id,
      browser_scene_digest: packet.scene_digest,
    },
  });
}
