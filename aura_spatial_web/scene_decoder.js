import { validateRenderPlan, validateSceneProjection } from "./renderer_adapter.js";

export const MAX_SCENE_JSON_BYTES = 4 * 1024 * 1024;

export function decodeSceneEnvelope(input, maximumBytes = MAX_SCENE_JSON_BYTES) {
  if (!Number.isInteger(maximumBytes) || maximumBytes < 1 || maximumBytes > MAX_SCENE_JSON_BYTES) {
    throw new RangeError("maximumBytes is outside the admitted scene ceiling");
  }
  let value = input;
  if (typeof input === "string") {
    if (new TextEncoder().encode(input).length > maximumBytes) {
      throw new RangeError("scene envelope exceeds byte ceiling");
    }
    value = JSON.parse(input);
  } else {
    try {
      if (new TextEncoder().encode(JSON.stringify(input)).length > maximumBytes) {
        throw new RangeError("scene envelope exceeds byte ceiling");
      }
    } catch (error) {
      if (error instanceof RangeError) throw error;
      throw new TypeError("scene envelope must be JSON serializable");
    }
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("scene envelope must be an object");
  }
  const keys = Object.keys(value).sort();
  if (keys.join(",") !== "render_plan,scene") {
    throw new TypeError("scene envelope keys mismatch");
  }
  const scene = validateSceneProjection(value.scene);
  const renderPlan = validateRenderPlan(value.render_plan, scene);
  return Object.freeze({ scene, render_plan: renderPlan });
}
