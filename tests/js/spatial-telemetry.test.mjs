import test from "node:test";
import assert from "node:assert/strict";

import { compileTelemetryPacket } from "../../aura_spatial_web/telemetry.js";

function packet(overrides = {}) {
  return {
    scene_digest: "a".repeat(64),
    render_plan_digest: "b".repeat(64),
    device_profile_digest: "c".repeat(64),
    fixture_digest: "d".repeat(64),
    renderer: "WEBGL2",
    metrics: {
      frame_ms: {
        value: 12.5,
        unit: "ms",
        evidence_class: "MEASURED",
        method: "performance.now",
      },
      gpu_bytes: {
        value: null,
        unit: "bytes",
        evidence_class: "UNAVAILABLE",
        method: "API unavailable",
      },
    },
    ...overrides,
  };
}

test("telemetry binds evidence classes and digests", () => {
  const result = compileTelemetryPacket(packet());
  assert.equal(result.metrics.gpu_bytes.value, null);
  assert.equal(result.renderer_authority, false);
});

test("telemetry rejects non-finite and contradictory evidence", () => {
  assert.throws(
    () =>
      compileTelemetryPacket(
        packet({ metrics: { frame_ms: { value: Number.NaN, unit: "ms", evidence_class: "MEASURED", method: "clock" } } }),
      ),
    /finite/,
  );
  assert.throws(
    () =>
      compileTelemetryPacket(
        packet({ metrics: { unavailable: { value: 1, unit: "", evidence_class: "UNAVAILABLE", method: "none" } } }),
      ),
    /null/,
  );
  assert.throws(() => compileTelemetryPacket(packet({ renderer: "UNKNOWN" })), /renderer/);
});
