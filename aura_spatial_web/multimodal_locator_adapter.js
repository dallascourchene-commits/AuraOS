import { AUTHORITY_ENVELOPE } from "./renderer_adapter.js";

const ID = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$/;
const CONTROL = /[\u0000-\u001f\u007f]/;
const INPUT_SOURCES = new Set([
  "VOICE",
  "TEXT",
  "KEYBOARD",
  "MOUSE",
  "TOUCH",
  "HAND",
  "GAZE",
  "RAY",
  "CONTROLLER",
]);
const REQUEST_KEYS = new Set([
  "session_id",
  "query_text",
  "input_source",
  "actor_ref",
  "frame_ref",
  "objective_ref",
]);
const WORK_ORDER_QUERY = /\bwork[\s-]*orders?\b/i;
const MAX_QUERY_CHARS = 512;

const WORK_ORDER_COORDINATE = Object.freeze({
  domain: "WORK",
  object_class: "WORK_ORDER",
  resolution: "L0",
  currentness: "CURRENT",
  authority: "VIEW_NO_EFFECT",
  presentation: "SURFACE_ADAPTIVE",
});

const WORK_ORDER_INTENT_SLOTS = Object.freeze({
  DIR: "work",
  ASP: "locate",
  CLASS: "work_order",
  SUBJ: "current_work_orders",
  VOICE: "query",
  STEM: "resolve_coordinate",
});

function identifier(value, label, { optional = false } = {}) {
  if (optional && (value === undefined || value === null || value === "")) return null;
  const text = String(value || "");
  if (!ID.test(text)) throw new TypeError(`${label} is invalid`);
  return text;
}

function queryText(value) {
  if (typeof value !== "string") throw new TypeError("query_text must be a string");
  const text = value.trim().replace(/\s+/g, " ");
  if (!text || text.length > MAX_QUERY_CHARS || CONTROL.test(text)) {
    throw new TypeError("query_text is invalid");
  }
  if (!WORK_ORDER_QUERY.test(text)) {
    throw new TypeError("unsupported locator query");
  }
  return text;
}

function exactKeys(packet) {
  if (!packet || typeof packet !== "object" || Array.isArray(packet) || Object.getPrototypeOf(packet) !== Object.prototype) {
    throw new TypeError("locator request must be a plain object");
  }
  for (const key of Object.keys(packet)) {
    if (!REQUEST_KEYS.has(key)) throw new TypeError(`unsupported locator request key: ${key}`);
  }
}

export function compileWorkOrderLocator(packet) {
  exactKeys(packet);
  const {
    session_id,
    query_text,
    input_source,
    actor_ref = "human:local",
    frame_ref,
    objective_ref,
  } = packet;

  const sessionId = identifier(session_id, "session_id");
  const actorRef = identifier(actor_ref, "actor_ref");
  const frameRef = identifier(frame_ref, "frame_ref", { optional: true });
  const objectiveRef = identifier(objective_ref, "objective_ref", { optional: true });
  const query = queryText(query_text);
  if (!INPUT_SOURCES.has(input_source)) throw new TypeError("unsupported multimodal input source");

  return Object.freeze({
    version: "AURA_MULTIMODAL_LOCATOR_V1",
    session_id: sessionId,
    actor_ref: actorRef,
    query_text: query,
    input_source,
    coordinate_request: WORK_ORDER_COORDINATE,
    intent_slots: WORK_ORDER_INTENT_SLOTS,
    context: Object.freeze({
      frame_ref: frameRef,
      objective_ref: objectiveRef,
    }),
    metadata: Object.freeze({
      input_source,
      renderer_input_is_authority: false,
    }),
    review_only: true,
    requires_coordinate_resolution: true,
    requires_effect_authority: false,
    ...AUTHORITY_ENVELOPE,
  });
}

export function toServerLocatorRequest(packet) {
  if (!packet || packet.version !== "AURA_MULTIMODAL_LOCATOR_V1") {
    throw new TypeError("invalid multimodal locator packet");
  }
  return Object.freeze({
    session_id: packet.session_id,
    actor_ref: packet.actor_ref,
    query_text: packet.query_text,
    input_source: packet.input_source,
    coordinate_request: { ...packet.coordinate_request },
    intent_slots: { ...packet.intent_slots },
    context: { ...packet.context },
    review_only: true,
  });
}
