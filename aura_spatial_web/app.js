import { Accessible2DRenderer, renderAccessibleScene } from "./accessibility.js";
import { HeadlessRenderer } from "./headless_renderer.js";
import {
  compileBrowserInteraction,
  toServerInteractionRequest,
} from "./interaction_adapter.js";
import { decodeSceneEnvelope } from "./scene_decoder.js";
import { WebGL2Renderer } from "./webgl2_renderer.js";
import { WebGPUShadowRenderer } from "./webgpu_renderer.js";
import { WebXRSessionAdapter } from "./webxr_session.js";

export function selectBrowserPresentationRenderer(plan) {
  const admitted = [plan.selected_renderer, ...plan.fallback_renderers];
  if (plan.selected_renderer === "WEBXR") {
    for (const renderer of ["WEBGL2", "ACCESSIBLE_2D", "HEADLESS"]) {
      if (admitted.includes(renderer)) return renderer;
    }
    throw new Error("WEBXR plan has no admitted non-immersive presentation fallback");
  }
  return plan.selected_renderer;
}

export async function bootSpatialApp({
  envelope,
  sessionId,
  canvas,
  accessibleContainer,
  sendInteraction = async () => {},
  gpu,
  xr,
}) {
  if (typeof sendInteraction !== "function") throw new TypeError("sendInteraction must be callable");
  const decoded = decodeSceneEnvelope(envelope);
  const { scene, render_plan: plan } = decoded;
  const onInteraction = async (input) =>
    sendInteraction(
      toServerInteractionRequest(
        compileBrowserInteraction({
          session_id: sessionId,
          scene_id: scene.scene_id,
          scene_digest: scene.scene_digest,
          actor_ref: "human:local",
          ...input,
        }),
      ),
    );

  const presentationRenderer = selectBrowserPresentationRenderer(plan);
  if (presentationRenderer !== "ACCESSIBLE_2D") {
    renderAccessibleScene(accessibleContainer, envelope.scene, onInteraction);
  }
  let renderer;
  if (presentationRenderer === "WEBGL2") {
    renderer = new WebGL2Renderer({ canvas });
  } else if (presentationRenderer === "WEBGPU") {
    renderer = new WebGPUShadowRenderer({ gpu });
  } else if (presentationRenderer === "ACCESSIBLE_2D") {
    renderer = new Accessible2DRenderer({
      container: accessibleContainer,
      onInteraction,
    });
  } else {
    renderer = new HeadlessRenderer();
  }

  await renderer.initialize(envelope.scene, envelope.render_plan);
  const receipt = renderer.present();
  const xrSession = new WebXRSessionAdapter({ xr });
  return Object.freeze({
    scene,
    plan,
    presentation_renderer: presentationRenderer,
    renderer,
    xrSession,
    receipt,
    onInteraction,
    dispose: async () => {
      await xrSession.end();
      return renderer.dispose();
    },
  });
}
