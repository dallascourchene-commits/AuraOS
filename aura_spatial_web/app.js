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

const PRESENTATION_RENDERERS = new Set([
  "WEBGL2",
  "WEBGPU",
  "ACCESSIBLE_2D",
  "HEADLESS",
]);

const DEFAULT_RENDERER_FACTORIES = Object.freeze({
  WEBGL2: ({ canvas }) => new WebGL2Renderer({ canvas }),
  WEBGPU: ({ gpu }) => new WebGPUShadowRenderer({ gpu }),
  ACCESSIBLE_2D: ({ accessibleContainer, onInteraction }) =>
    new Accessible2DRenderer({
      container: accessibleContainer,
      onInteraction,
    }),
  HEADLESS: () => new HeadlessRenderer(),
});

export function browserPresentationRendererCandidates(plan) {
  const admitted = [plan.selected_renderer, ...plan.fallback_renderers];
  const ordered =
    plan.selected_renderer === "WEBXR"
      ? ["WEBGL2", "WEBGPU", "ACCESSIBLE_2D", "HEADLESS"]
      : admitted;
  const candidates = [
    ...new Set(ordered.filter((renderer) => admitted.includes(renderer))),
  ].filter((renderer) => PRESENTATION_RENDERERS.has(renderer));
  if (candidates.length === 0) {
    throw new Error("render plan has no admitted non-immersive presentation fallback");
  }
  return Object.freeze(candidates);
}

export function selectBrowserPresentationRenderer(plan) {
  return browserPresentationRendererCandidates(plan)[0];
}

async function disposeFailedRenderer(renderer) {
  try {
    await renderer?.dispose?.();
  } catch {
    // Initialization failure evidence is retained in the final aggregate error.
  }
}

export async function bootSpatialApp({
  envelope,
  sessionId,
  canvas,
  accessibleContainer,
  sendInteraction = async () => {},
  gpu,
  xr,
  rendererFactories = DEFAULT_RENDERER_FACTORIES,
}) {
  if (typeof sendInteraction !== "function") throw new TypeError("sendInteraction must be callable");
  if (!rendererFactories || typeof rendererFactories !== "object") {
    throw new TypeError("rendererFactories must be an object");
  }
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

  let renderer = null;
  let presentationRenderer = null;
  let receipt = null;
  const failures = [];
  for (const candidate of browserPresentationRendererCandidates(plan)) {
    const factory = rendererFactories[candidate];
    if (typeof factory !== "function") {
      failures.push(`${candidate}: renderer factory unavailable`);
      continue;
    }
    const attempted = factory({
      canvas,
      accessibleContainer,
      onInteraction,
      gpu,
    });
    try {
      await attempted.initialize(envelope.scene, envelope.render_plan);
      receipt = attempted.present();
      renderer = attempted;
      presentationRenderer = candidate;
      break;
    } catch (error) {
      await disposeFailedRenderer(attempted);
      failures.push(`${candidate}: ${String(error?.message || error)}`);
    }
  }
  if (!renderer || !presentationRenderer || !receipt) {
    throw new Error(`No admitted presentation renderer initialized: ${failures.join("; ")}`);
  }

  try {
    if (presentationRenderer !== "ACCESSIBLE_2D") {
      renderAccessibleScene(accessibleContainer, envelope.scene, onInteraction);
    }
  } catch (error) {
    await renderer.dispose();
    throw error;
  }

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
