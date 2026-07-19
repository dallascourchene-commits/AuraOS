import { AUTHORITY_ENVELOPE } from "./renderer_adapter.js";

const CLASSES = new Set(["MEASURED", "CALCULATED", "ESTIMATED", "UNAVAILABLE"]);
const RENDERERS = new Set(["WEBXR", "WEBGPU", "WEBGL2", "ACCESSIBLE_2D", "HEADLESS"]);
const METRIC_NAME = /^[A-Za-z][A-Za-z0-9_.:-]{0,127}$/;
const DIGEST = /^[0-9a-f]{64}$/;
const MAX_PACKET_BYTES = 64 * 1024;

export function compileTelemetryPacket({
  scene_digest,
  render_plan_digest,
  device_profile_digest,
  renderer,
  fixture_digest,
  metrics,
}) {
  for (const digest of [scene_digest, render_plan_digest, device_profile_digest, fixture_digest]) {
    if (!DIGEST.test(String(digest || ""))) {
      throw new TypeError("telemetry digests must be lowercase sha256");
    }
  }
  if (!RENDERERS.has(renderer)) throw new TypeError("unsupported telemetry renderer");
  if (!metrics || typeof metrics !== "object" || Array.isArray(metrics)) {
    throw new TypeError("telemetry metrics must be an object");
  }
  const names = Object.keys(metrics).sort();
  if (names.length > 64) throw new RangeError("telemetry metric ceiling exceeded");
  const normalized = {};
  for (const name of names) {
    if (!METRIC_NAME.test(name)) throw new TypeError(`invalid telemetry metric name: ${name}`);
    const metric = metrics[name];
    if (
      !metric ||
      typeof metric !== "object" ||
      Array.isArray(metric) ||
      Object.keys(metric).sort().join(",") !== "evidence_class,method,unit,value" ||
      !CLASSES.has(metric.evidence_class)
    ) {
      throw new TypeError(`invalid telemetry metric: ${name}`);
    }
    const value = metric.value;
    if (metric.evidence_class === "UNAVAILABLE") {
      if (value !== null) throw new TypeError(`metric ${name} must be null when unavailable`);
    } else if (typeof value !== "number" || !Number.isFinite(value)) {
      throw new TypeError(`metric ${name} must be finite`);
    }
    normalized[name] = Object.freeze({
      value,
      unit: String(metric.unit || "").slice(0, 64),
      evidence_class: metric.evidence_class,
      method: String(metric.method || "").slice(0, 256),
    });
  }
  const packet = {
    version: "AURA_SPATIAL_BROWSER_TELEMETRY_V1",
    scene_digest,
    render_plan_digest,
    device_profile_digest,
    fixture_digest,
    renderer,
    metrics: Object.freeze(normalized),
    ...AUTHORITY_ENVELOPE,
  };
  if (new TextEncoder().encode(JSON.stringify(packet)).length > MAX_PACKET_BYTES) {
    throw new RangeError("telemetry packet byte ceiling exceeded");
  }
  return Object.freeze(packet);
}
