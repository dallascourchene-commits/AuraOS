import { createConstructionWebGL2SceneRenderer } from "./construction_scene_renderer.js";

const GAUSSIAN_REPRESENTATION_DIGEST =
  "5e4620fc5ea92315714eaf3bfe0247f4a18f6ed51997efb9c5c389d20536d7b7";
const LAYERS = Object.freeze([
  ["floorPlans", "Floor plans"],
  ["status", "Work status"],
  ["trades", "Trades"],
  ["blockers", "Blockers"],
  ["budgets", "Budgets"],
  ["inspections", "Inspections"],
  ["dependencies", "Dependencies"],
  ["syntheticRules", "Synthetic rules"],
]);

const $ = (selector) => document.querySelector(selector);
const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
const state = {
  packet: null,
  renderer: null,
  overlayModel: null,
  tourIndex: 0,
  playing: false,
  paused: false,
  disposed: false,
};

function resizeCanvas() {
  const canvas = $("#construction-canvas");
  const ratio = Math.min(2, globalThis.devicePixelRatio || 1);
  const width = Math.max(1, Math.floor(canvas.clientWidth * ratio));
  const height = Math.max(1, Math.floor(canvas.clientHeight * ratio));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
}

function meshPayloads(scene) {
  return scene.assets
    .filter((asset) => asset.asset_type === "MESH")
    .map((asset) => ({
      asset_id: asset.asset_id,
      source_digest: asset.content_digest.split(":", 2).at(-1),
      decoded_byte_length: Math.max(1, asset.byte_length),
      resource: Object.freeze({ asset_id: asset.asset_id, bounds: [asset.bounds_min, asset.bounds_max] }),
    }));
}

function gaussianGeometry() {
  const positions = [];
  for (const x of [-8, -4, 0, 4, 8]) {
    for (const z of [-8, -4, 0, 4, 8]) positions.push([x, 2, z]);
  }
  return {
    positions,
    rotations_xyzw: positions.map(() => [0, 0, 0, 1]),
    scales_xyz: positions.map(() => [1.2, 0.18, 1.2]),
    opacities: positions.map(() => 0.68),
    sh_coefficients: positions.map(() => [0, 0, 0]),
    colors_rgba: positions.map(() => [210, 80, 255, 190]),
  };
}

function gaussianPayloads(scene) {
  const geometry = gaussianGeometry();
  return scene.assets
    .filter((asset) => asset.asset_type === "GAUSSIAN_SPLAT")
    .map((asset) => ({
      asset_id: asset.asset_id,
      source_digest: asset.content_digest.split(":", 2).at(-1),
      derived_asset_digest: asset.metadata.import_receipt_digest,
      representation_digest: GAUSSIAN_REPRESENTATION_DIGEST,
      sh_degree: 0,
      color_space: "SPZ_INTERNAL_WIDE_RGB",
      ...geometry,
    }));
}

function classForStatus(status) {
  return ["BLOCKED", "DELAYED", "REWORK_REQUIRED"].includes(status) ? "blocked" : "ready";
}

function renderOverlayModel(model) {
  state.overlayModel = model;
  const status = model.status.slice(0, 14).map((item) =>
    `<div class="${classForStatus(item.status)}"><strong>${escapeHtml(item.label)}</strong>${escapeHtml(item.status)}</div>`,
  );
  $("#status-list").innerHTML = status.join("") || "<div>No visible work status</div>";
  $("#blocker-list").innerHTML = model.blockers.slice(0, 10).map((item) =>
    `<div class="blocked"><strong>${escapeHtml(item.relation)}</strong>${escapeHtml(item.source_entity_id)} → ${escapeHtml(item.target_entity_id)}</div>`,
  ).join("") || "<div>No visible blockers</div>";
  $("#budget-list").innerHTML = model.budgets.slice(0, 8).map((item) =>
    `<div><strong>${escapeHtml(item.label)}</strong>Committed ${money(item.committed_cad)} · Forecast ${money(item.forecast_cad)} · Actual ${money(item.actual_cad)}</div>`,
  ).join("") || "<div>No visible budget lines</div>";
  return () => {};
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function money(value) {
  return new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD", maximumFractionDigits: 0 })
    .format(Number(value || 0));
}

function storeyEntities() {
  return state.packet.scene.entities
    .filter((item) => item.entity_type === "ASSET_INSTANCE")
    .sort((left, right) => left.frame_id.localeCompare(right.frame_id));
}

function buildControls() {
  const storeys = storeyEntities();
  $("#storey-list").innerHTML = storeys.map((item, index) =>
    `<button data-frame="${escapeHtml(item.frame_id)}"><span>${escapeHtml(item.label)}</span><small>${index + 1}</small></button>`,
  ).join("");
  $("#storey-list").addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-frame]");
    if (!button || state.disposed) return;
    state.renderer.isolateStorey(button.dataset.frame);
    $("#intent-line").textContent = `Isolate ${button.textContent.trim()}.`;
    await present();
  });

  $("#layer-list").innerHTML = LAYERS.map(([name, label]) =>
    `<label><input type="checkbox" data-layer="${name}" checked> ${label}</label>`,
  ).join("");
  $("#layer-list").addEventListener("change", async (event) => {
    const input = event.target.closest("input[data-layer]");
    if (!input || state.disposed) return;
    state.renderer.toggleOverlay(input.dataset.layer, input.checked);
    await present();
  });

  document.querySelectorAll("button[data-mode]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (state.disposed) return;
      state.renderer.setRepresentationMode(button.dataset.mode);
      document.querySelectorAll("button[data-mode]").forEach((item) => item.classList.toggle("active", item === button));
      await present();
    });
  });

  $("#timeline").addEventListener("input", async (event) => {
    const day = Number(event.target.value);
    $("#timeline-value").value = String(day);
    if (state.disposed) return;
    state.renderer.setTimelineDay(day);
    await present();
  });

  const actions = {
    "#orbit-left": () => state.renderer.orbit(-0.18, 0),
    "#orbit-right": () => state.renderer.orbit(0.18, 0),
    "#zoom-in": () => state.renderer.zoom(-1.2),
    "#zoom-out": () => state.renderer.zoom(1.2),
    "#explode": () => state.renderer.explodeStoreys(4),
    "#collapse": () => state.renderer.collapseStoreys(),
    "#show-all": () => state.renderer.showAllStoreys(),
    "#reset": () => state.renderer.resetView(),
  };
  for (const [selector, action] of Object.entries(actions)) {
    $(selector).addEventListener("click", async () => {
      if (state.disposed) return globalThis.location.reload();
      action();
      await present();
    });
  }

  $("#construction-canvas").addEventListener("click", async (event) => {
    if (state.disposed) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const entityId = state.renderer.pick(event.clientX - rect.left, event.clientY - rect.top);
    if (entityId) showEntity(entityId);
    await present();
  });

  $("#play-tour").addEventListener("click", () => playTour());
  $("#pause-tour").addEventListener("click", () => {
    state.paused = true;
    $("#tour-status").textContent = "Paused";
  });
  $("#next-step").addEventListener("click", () => runNextStep());
  $("#dissolve").addEventListener("click", () => dissolve());
}

async function present() {
  if (!state.renderer || state.disposed) return;
  resizeCanvas();
  const receipt = await state.renderer.present();
  $("#scene-state").textContent = `${receipt.representation_mode} · ${receipt.outcome}`;
}

function showEntity(entityId) {
  const entity = state.packet.scene.entities.find((item) => item.entity_id === entityId);
  if (!entity) return;
  $("#selected-card").innerHTML = `
    <strong>${escapeHtml(entity.label)}</strong><br>
    ${escapeHtml(entity.entity_type)}<br>
    <small>${escapeHtml(entity.frame_id)}</small>`;
}

function focusEntity(predicate) {
  const entity = state.packet.scene.entities.find(predicate);
  if (!entity) return null;
  state.renderer.focusEntity(entity.entity_id);
  showEntity(entity.entity_id);
  return entity;
}

function updateComparison(entity) {
  if (!entity) return;
  const metadata = entity.metadata || {};
  $("#comparison-title").textContent = entity.label;
  $("#metric-time").textContent = `${Number(metadata.projected_time_delta_hours || 0)} h`;
  $("#metric-cost").textContent = money(metadata.projected_cost_delta_cad || 0);
  $("#metric-idle").textContent = `${Number(metadata.projected_idle_delta_hours || 0)} h`;
  $("#metric-authority").textContent = metadata.admissible === false ? "Hard blocked" : "Human review";
}

async function applyStep(step) {
  if (state.disposed && step.action !== "DISSOLVE") return;
  if ($("#evidence-dialog").open) $("#evidence-dialog").close();
  $("#tour-status").textContent = `${step.step_id} · ${step.title}`;
  $("#intent-line").textContent = step.title;
  switch (step.action) {
    case "SHOW_ATTRIBUTION":
      $("#evidence-content").textContent = state.packet.attribution;
      $("#evidence-dialog").showModal();
      break;
    case "SHOW_ALL":
      state.renderer.showAllStoreys();
      state.renderer.collapseStoreys();
      state.renderer.setRepresentationMode("HYBRID");
      break;
    case "ORBIT":
      state.renderer.orbit(Number(step.value || 0.5), -0.08);
      break;
    case "EXPLODE":
      state.renderer.explodeStoreys(Number(step.value || 4));
      break;
    case "TOGGLE_LAYER":
      state.renderer.toggleOverlay(step.target, step.value !== "off");
      const layerInput = document.querySelector(`input[data-layer="${step.target}"]`);
      if (layerInput) layerInput.checked = step.value !== "off";
      break;
    case "TIMELINE": {
      const end = Number(step.value || 12);
      for (let day = 0; day <= end && !state.paused; day += 2) {
        state.renderer.setTimelineDay(day);
        $("#timeline").value = String(day);
        $("#timeline-value").value = String(day);
        await present();
        await sleep(180);
      }
      break;
    }
    case "FOCUS_STATUS":
      focusEntity((item) => item.metadata?.status_overlay === step.target);
      break;
    case "FOCUS_BLOCKED_ALTERNATIVE": {
      const entity = focusEntity((item) => item.metadata?.admissible === false);
      updateComparison(entity);
      break;
    }
    case "FOCUS_RECOMMENDED_ALTERNATIVE": {
      const entity = focusEntity((item) => item.metadata?.recommended_for_human_review === true);
      updateComparison(entity);
      break;
    }
    case "SHOW_OBSERVATORY":
      $("#evidence-content").textContent = JSON.stringify({
        scene_digest: state.packet.scene.scene_digest,
        fixture_digest: state.packet.fixture_digest,
        blockers: state.overlayModel?.blockers || [],
        inspections: state.overlayModel?.inspections || [],
        synthetic_rules: state.overlayModel?.synthetic_rules || [],
        read_only: true,
      }, null, 2);
      $("#evidence-dialog").showModal();
      break;
    case "SHOW_DECISION_PACKET":
      $("#evidence-content").textContent = JSON.stringify({
        decision: "await authorized human Construction review",
        recommended_alternative_id: state.packet.recommended_alternative_id,
        physical_work_authorized: false,
        payment_released: false,
        automatic_execution: false,
        human_review_required: true,
      }, null, 2);
      $("#evidence-dialog").showModal();
      break;
    case "DISSOLVE":
      await dissolve();
      return;
    default:
      throw new Error(`Unknown Construction director action: ${step.action}`);
  }
  await present();
}

async function runNextStep() {
  const steps = state.packet?.tour_steps || [];
  if (!steps.length || state.tourIndex >= steps.length) return;
  const step = steps[state.tourIndex++];
  await applyStep(step);
}

async function playTour() {
  if (state.playing || state.disposed) return;
  state.playing = true;
  state.paused = false;
  try {
    while (state.tourIndex < state.packet.tour_steps.length && !state.paused && !state.disposed) {
      const step = state.packet.tour_steps[state.tourIndex++];
      await applyStep(step);
      if (!state.paused && !state.disposed) await sleep(Math.min(4000, Math.max(250, step.duration_ms)));
    }
  } finally {
    state.playing = false;
    if (!state.disposed && state.tourIndex >= state.packet.tour_steps.length) {
      $("#tour-status").textContent = "Tour complete";
    }
  }
}

async function dissolve() {
  if (!state.renderer || state.disposed) return;
  await state.renderer.dispose();
  state.disposed = true;
  $("#scene-state").textContent = "Dissolved";
  $("#tour-status").textContent = "Renderer released · zero active presentation resources";
  $("#intent-line").textContent = "Arena dissolved. Source geometry remained immutable.";
  document.querySelectorAll("button, input").forEach((control) => {
    if (control.id !== "reset") control.disabled = true;
  });
}

async function main() {
  const response = await fetch("/api/construction-demo", { cache: "no-store" });
  if (!response.ok) throw new Error(`Construction demo packet failed: ${response.status}`);
  state.packet = await response.json();
  $("#attribution").textContent = state.packet.attribution;
  resizeCanvas();
  const canvas = $("#construction-canvas");
  state.renderer = createConstructionWebGL2SceneRenderer({
    canvas,
    drawMeshPass: async () => () => {},
    drawOverlayPass: async (model) => renderOverlayModel(model),
    maxVisibleSplats: 250_000,
  });
  await state.renderer.initialize(state.packet.scene, state.packet.render_plan, {
    meshPayloads: meshPayloads(state.packet.scene),
    gaussianPayloads: gaussianPayloads(state.packet.scene),
  });
  buildControls();
  await present();
  $("#scene-state").textContent = state.packet.fallback_asset_pack ? "Fallback pack ready" : "Asset pack ready";
  const requestedTour = new URLSearchParams(globalThis.location.search).get("tour");
  if (requestedTour) {
    await sleep(650);
    playTour();
  }
}

window.addEventListener("resize", () => {
  resizeCanvas();
  present().catch(() => {});
});
window.addEventListener("beforeunload", () => state.renderer?.dispose?.());

main().catch((error) => {
  console.error(error);
  $("#scene-state").textContent = "Failed";
  $("#selected-card").textContent = error instanceof Error ? error.message : String(error);
  $("#tour-status").textContent = "Construction demo initialization failed closed";
});
