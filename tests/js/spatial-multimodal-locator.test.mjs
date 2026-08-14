import test from "node:test";
import assert from "node:assert/strict";

import {
  compileWorkOrderLocator,
  toServerLocatorRequest,
} from "../../aura_spatial_web/multimodal_locator_adapter.js";

function request(input_source, overrides = {}) {
  return {
    session_id: "spatial-session:multimodal",
    query_text: "Hey Aura, where are work orders?",
    input_source,
    ...overrides,
  };
}

test("voice and hand compile to the same semantic work-order coordinate", () => {
  const voice = compileWorkOrderLocator(request("VOICE"));
  const hand = compileWorkOrderLocator(request("HAND", { query_text: "Show work-orders" }));

  assert.deepEqual(voice.coordinate_request, hand.coordinate_request);
  assert.deepEqual(voice.coordinate_request, {
    domain: "WORK",
    object_class: "WORK_ORDER",
    resolution: "L0",
    currentness: "CURRENT",
    authority: "VIEW_NO_EFFECT",
    presentation: "SURFACE_ADAPTIVE",
  });
  assert.equal(voice.renderer_authority, false);
  assert.equal(voice.execution_authority, false);
  assert.equal(voice.patch_authority, false);
  assert.equal(voice.production_mutation, false);
  assert.equal(voice.automatic_merge, false);
  assert.equal(voice.metadata.renderer_input_is_authority, false);
});

test("server locator request strips renderer authority sentinel", () => {
  const compiled = compileWorkOrderLocator(request("TOUCH"));
  const server = toServerLocatorRequest(compiled);

  assert.equal(server.review_only, true);
  assert.equal(server.coordinate_request.resolution, "L0");
  assert.equal("renderer_input_is_authority" in server, false);
  assert.equal("metadata" in server, false);
  assert.equal("execution_authority" in server, false);
});

test("locator rejects authority-like or otherwise unknown request keys", () => {
  assert.throws(
    () => compileWorkOrderLocator(request("VOICE", { automatic_merge: true })),
    /unsupported locator request key/,
  );
  assert.throws(
    () => compileWorkOrderLocator(request("HAND", { authority: "ADMIN" })),
    /unsupported locator request key/,
  );
});

test("locator is bounded to the first supported semantic coordinate", () => {
  assert.throws(
    () => compileWorkOrderLocator(request("VOICE", { query_text: "Where are research projects?" })),
    /unsupported locator query/,
  );
  assert.throws(
    () => compileWorkOrderLocator(request("DEVICE_POSE")),
    /unsupported multimodal input source/,
  );
});
