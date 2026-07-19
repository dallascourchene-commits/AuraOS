import test from "node:test";
import assert from "node:assert/strict";

import {
  compileBrowserInteraction,
  toServerInteractionRequest,
} from "../../aura_spatial_web/interaction_adapter.js";

function packet(overrides = {}) {
  return {
    session_id: "spatial-session:test",
    scene_id: "scene:test",
    scene_digest: "a".repeat(64),
    action: "SELECT",
    target_entity_ids: ["entity:b", "entity:a", "entity:a"],
    input_source: "MOUSE",
    ...overrides,
  };
}

test("browser interaction compiles six-slot review-only intent", () => {
  const result = compileBrowserInteraction(packet());
  assert.deepEqual(Object.keys(result.intent_slots), [
    "DIR",
    "ASP",
    "CLASS",
    "SUBJ",
    "VOICE",
    "STEM",
  ]);
  assert.deepEqual(result.target_entity_ids, ["entity:a", "entity:b"]);
  assert.equal(result.review_only, true);
  const serverRequest = toServerInteractionRequest(result);
  assert.equal(result.metadata.renderer_input_is_authority, false);
  assert.equal("renderer_input_is_authority" in serverRequest.metadata, false);
  assert.equal(serverRequest.metadata.input_source, "MOUSE");
});

test("browser metadata cannot smuggle authority at any depth", () => {
  assert.throws(
    () => compileBrowserInteraction(packet({ metadata: { nested: { automaticMerge: true } } })),
    /authority/,
  );
  assert.throws(() => compileBrowserInteraction(packet({ metadata: null })), /metadata/);
  assert.throws(
    () => compileBrowserInteraction(packet({ scene_digest: "not-a-digest" })),
    /sha256/,
  );
});
