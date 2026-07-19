import { bootSpatialApp } from "./app.js";
import { compileTelemetryPacket } from "./telemetry.js";

const ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$/;
const form = document.querySelector("#session-form");
const input = document.querySelector("#session-id");
const status = document.querySelector("#spatial-status");
const canvas = document.querySelector("#spatial-canvas");
const accessibleContainer = document.querySelector("#accessible-scene");
const xrButton = document.querySelector("#enter-xr");
let activeApp = null;

function setStatus(message, state = "ready") {
  status.textContent = message;
  status.dataset.state = state;
}

async function fetchJson(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || `Spatial request failed with ${response.status}`);
  }
  return payload;
}

async function loadSession(sessionId) {
  if (!ID.test(sessionId)) throw new TypeError("Session ID is not a canonical path segment");
  setStatus("Loading bounded spatial projection…", "loading");
  await activeApp?.dispose?.();
  activeApp = null;
  const [capabilities, projection] = await Promise.all([
    fetchJson("/api/spatial/capabilities"),
    fetchJson(`/api/spatial/projections/${sessionId}`),
  ]);
  const started = performance.now();
  activeApp = await bootSpatialApp({
    envelope: { scene: projection.scene, render_plan: projection.render_plan },
    sessionId,
    canvas,
    accessibleContainer,
    sendInteraction: (request) =>
      fetchJson("/api/spatial/interactions", {
        method: "POST",
        body: JSON.stringify(request),
      }),
    gpu: navigator.gpu,
    xr: navigator.xr,
  });
  const frameMs = performance.now() - started;
  const telemetry = compileTelemetryPacket({
    scene_digest: projection.scene.scene_digest,
    render_plan_digest: projection.render_plan.render_plan_digest,
    device_profile_digest: projection.render_plan.device_profile_digest,
    fixture_digest: capabilities.browser_fixture_digest,
    renderer: activeApp.presentation_renderer,
    metrics: {
      initial_present_ms: {
        value: frameMs,
        unit: "ms",
        evidence_class: "MEASURED",
        method: "performance.now",
      },
    },
  });
  await fetchJson("/api/spatial/telemetry", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, packet: telemetry }),
  });
  const xrAdmitted = [
    projection.render_plan.selected_renderer,
    ...projection.render_plan.fallback_renderers,
  ].includes("WEBXR");
  xrButton.disabled = !xrAdmitted;
  xrButton.hidden = !xrAdmitted;
  setStatus(
    `Presenting ${projection.scene.entities.length} entities with ${activeApp.presentation_renderer}.`,
  );
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const sessionId = input.value.trim();
  try {
    history.replaceState(null, "", `#session=${encodeURIComponent(sessionId)}`);
    await loadSession(sessionId);
  } catch (error) {
    setStatus(String(error?.message || error), "error");
  }
});

xrButton.addEventListener("click", async () => {
  try {
    if (!activeApp) throw new Error("Load a spatial session before entering XR");
    await activeApp.xrSession.start({
      userActivation: true,
      scene: activeApp.scene,
      renderPlan: activeApp.plan,
    });
    setStatus("WebXR session active. Raw sensor frames are not retained.");
  } catch (error) {
    setStatus(String(error?.message || error), "error");
  }
});

const initial = new URLSearchParams(location.hash.slice(1)).get("session");
if (initial) {
  input.value = initial;
  loadSession(initial).catch((error) => setStatus(String(error?.message || error), "error"));
}
