import { AUTHORITY_ENVELOPE } from "./renderer_adapter.js";

const REFERENCE_SPACES = new Set(["local", "local-floor"]);

export class WebXRSessionAdapter {
  constructor({ xr = globalThis.navigator?.xr } = {}) {
    this.xr = xr;
    this.session = null;
    this.sceneDigest = null;
    this.state = "IDLE";
  }

  async capability() {
    if (!this.xr?.isSessionSupported) return false;
    try {
      return Boolean(await this.xr.isSessionSupported("immersive-vr"));
    } catch {
      return false;
    }
  }

  async start({
    userActivation,
    scene,
    renderPlan,
    referenceSpaceType = "local-floor",
  }) {
    if (this.session) throw new Error("a WebXR session is already active");
    if (userActivation !== true) {
      throw new Error("WebXR requires an explicit observed user gesture");
    }
    if (!REFERENCE_SPACES.has(referenceSpaceType)) {
      throw new Error("unsupported WebXR reference space");
    }
    if (
      renderPlan.selected_renderer !== "WEBXR" &&
      !renderPlan.fallback_renderers?.includes("WEBXR")
    ) {
      throw new Error("WEBXR is not admitted by the render plan");
    }
    if (scene.scene_digest !== renderPlan.scene_digest) {
      throw new Error("stale scene/render-plan binding");
    }
    if (!(await this.capability())) throw new Error("WebXR unavailable");
    this.session = await this.xr.requestSession("immersive-vr", {
      requiredFeatures: [],
      optionalFeatures: [referenceSpaceType],
    });
    this.sceneDigest = scene.scene_digest;
    this.state = "ACTIVE";
    this.session.addEventListener?.("end", () => {
      this.state = "ENDED";
      this.session = null;
      this.sceneDigest = null;
    });
    return Object.freeze({
      state: this.state,
      mode: "immersive-vr",
      reference_space: referenceSpaceType,
      scene_digest: this.sceneDigest,
      raw_sensor_data_retained: false,
      ...AUTHORITY_ENVELOPE,
    });
  }

  async end() {
    const active = this.session;
    this.session = null;
    this.sceneDigest = null;
    if (active) await active.end();
    this.state = "ENDED";
    return Object.freeze({
      state: this.state,
      raw_sensor_data_retained: false,
      ...AUTHORITY_ENVELOPE,
    });
  }
}
