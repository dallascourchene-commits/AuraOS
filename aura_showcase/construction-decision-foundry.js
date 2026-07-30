(() => {
  "use strict";

  const root = document.getElementById("construction-decision-foundry");
  if (!root) return;

  const statusNode = document.getElementById("construction-decision-status");
  const timeline = document.getElementById("construction-timeline");
  const overlayControls = document.getElementById("construction-overlay-controls");
  const selectionSummary = document.getElementById("construction-selection-summary");
  const evidencePins = document.getElementById("construction-evidence-pins");
  const candidatesNode = document.getElementById("construction-candidates");
  const decisionNode = document.getElementById("construction-decision-packet");
  const syncNode = document.getElementById("construction-render-sync");
  const designPane = document.getElementById("construction-design-pane");
  const asBuiltPane = document.getElementById("construction-as-built-pane");
  const asBuiltFrame = document.getElementById("construction-as-built-frame");
  const pascalMount = document.getElementById("construction-pascal-mount");
  const viewButtons = Array.from(root.querySelectorAll("[data-construction-view]"));
  const exportLinks = Array.from(root.querySelectorAll(".construction-export-controls a"));

  const AS_BUILT_SYNC_VERSION = "AURA_CONSTRUCTION_P3_AS_BUILT_SYNC_V1";
  const AS_BUILT_SYNC_TYPE = "AURA_CONSTRUCTION_P3_AS_BUILT_SYNC";
  const AS_BUILT_RECEIPT_TYPE = "AURA_CONSTRUCTION_P3_AS_BUILT_RECEIPT";
  const AS_BUILT_READY_TYPE = "AURA_CONSTRUCTION_P3_AS_BUILT_READY";
  const AS_BUILT_OVERLAY_MAP = Object.freeze({
    work_packages: "status",
    hazards: "blockers",
    geofences: "syntheticRules",
    inspections: "inspections",
    dependencies: "dependencies",
    crews: "trades",
    budget: "budgets",
    // schedule, material_staging, and waste_and_bin_zones are projected by
    // the compiler and rendered in the inspector/evidence panels, but the
    // as-built renderer has no distinct layer for them.  Mapping them to
    // shared layers would create aliasing where toggling one affects
    // another.  They are omitted from the renderer overlay set.
  });

  let projection = null;
  let requestQueue = Promise.resolve();
  let pascalQueue = Promise.resolve();
  let overlaysInitialized = false;
  let pascalFrame = null;
  let pascalSessionId = "";
  let pascalStorey = "";
  let pascalNode = "";
  let pascalActive = false;
  const pendingPascalReceipts = new Map();
  const enabledOverlays = new Set();

  function text(value) {
    return String(value ?? "");
  }

  function element(tag, className, content) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (content !== undefined) node.textContent = text(content);
    return node;
  }

  function p2Root() {
    return document.getElementById("pascal-construction-foundry");
  }

  function mountPascalSurface() {
    const retained = p2Root();
    if (retained && retained.parentElement !== pascalMount) {
      pascalMount.append(retained);
    }
  }

  function exactIdentityBody(current) {
    return {
      state_digest: current?.domain?.state_digest,
      runtime_packet_digest: current?.domain?.runtime_packet_digest,
      pascal_artifact_digest: current?.artifacts?.pascal_artifact_digest,
      coordinate_receipt_digest: current?.artifacts?.coordinate_receipt_digest,
      as_built_scene_digest: current?.artifacts?.as_built_scene_digest,
    };
  }

  async function requestProjection(changes = {}) {
    const current = projection;
    const body = {
      active_view: current?.presentation?.active_view || "DESIGN",
      selected_storey: current?.presentation?.selected_storey,
      selected_node: current?.presentation?.selected_node,
      selected_issue_id: current?.presentation?.selected_issue_id,
      selected_candidate_id: current?.presentation?.selected_candidate_id,
      selected_candidate_digest: current?.presentation?.selected_candidate_digest,
      timeline_day: current?.presentation?.timeline_day ?? 12,
      ...exactIdentityBody(current),
      ...changes,
    };
    Object.keys(body).forEach((key) => body[key] === undefined && delete body[key]);
    const response = await fetch("/api/construction/decision-lane/project", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      cache: "no-store",
      body: JSON.stringify(body),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok || result.ok !== true || !result.projection) {
      throw new Error(
        result.error || result.reason || `P3 projection failed with ${response.status}`,
      );
    }
    projection = result.projection;
    render();
    synchronizeAsBuilt();
    return projection;
  }

  function pascalControl(name) {
    return document.querySelector(`[data-pascal-action="${name}"]`);
  }

  function ensurePascalLaunch() {
    mountPascalSurface();
    const launch = pascalControl("launch");
    if (!pascalFrame && launch && !launch.disabled) launch.click();
  }

  function waitForPascalActive(deadline = Date.now() + 15000) {
    return new Promise((resolve, reject) => {
      const check = () => {
        pascalFrame = document.querySelector("[data-pascal-workbench-frame], .pascal-workbench-frame");
        if (pascalFrame && pascalSessionId && pascalActive) {
          resolve();
          return;
        }
        if (Date.now() >= deadline) {
          reject(new Error("P2 Pascal session did not become active for P3 synchronization"));
          return;
        }
        setTimeout(check, 60);
      };
      check();
    });
  }

  function waitForPascalRetention(commandDigest, deadline = Date.now() + 10000) {
    return new Promise((resolve, reject) => {
      const check = () => {
        const receipt = document.getElementById("pascal-foundry-receipt")?.textContent || "";
        if (receipt.includes(commandDigest)) {
          resolve();
          return;
        }
        if (Date.now() >= deadline) {
          reject(new Error("P2 did not retain the exact Pascal command receipt"));
          return;
        }
        setTimeout(check, 40);
      };
      check();
    });
  }

  async function issuePascalCommand(action, payload = {}) {
    ensurePascalLaunch();
    await waitForPascalActive();
    const response = await fetch(
      `/api/construction/pascal/session/${encodeURIComponent(pascalSessionId)}/command`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        cache: "no-store",
        body: JSON.stringify({ action, payload }),
      },
    );
    const result = await response.json().catch(() => ({}));
    if (!response.ok || result.ok !== true || !result.message) {
      throw new Error(
        result.error || result.reason || `Pascal synchronization failed with ${response.status}`,
      );
    }
    const commandDigest = result.message.message_digest;
    const childReceipt = new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        pendingPascalReceipts.delete(commandDigest);
        reject(new Error("Pascal child did not return the exact command receipt"));
      }, 10000);
      pendingPascalReceipts.set(commandDigest, {
        resolve: (actionName) => {
          clearTimeout(timeout);
          resolve(actionName);
        },
      });
    });
    pascalFrame.contentWindow.postMessage(
      { type: "AURA_PASCAL_BRIDGE_MESSAGE", message: result.message },
      location.origin,
    );
    const childAction = await childReceipt;
    if (childAction === "PRESENTATION_ERROR") {
      throw new Error("Pascal rejected the synchronized P3 command");
    }
    await waitForPascalRetention(commandDigest);
  }

  function synchronizePascalView(nextProjection) {
    const view = nextProjection.presentation.active_view;
    if (!["DESIGN", "FLOOR_PLAN", "COMPARE"].includes(view)) return;
    const action = view === "FLOOR_PLAN" ? "SET_VIEW_2D" : "SET_VIEW_3D";
    pascalQueue = pascalQueue
      .then(() => issuePascalCommand(action))
      .catch(showError);
  }

  function synchronizePascalIssue(nextProjection, pin) {
    pascalQueue = pascalQueue
      .then(async () => {
        if (pascalStorey !== pin.presentation_storey_id) {
          await issuePascalCommand("SET_STOREY", {
            storey_id: pin.presentation_storey_id,
          });
        }
        if (pascalNode !== pin.pascal_node_id) {
          await issuePascalCommand("SET_SELECTION", {
            node_id: pin.pascal_node_id,
          });
        }
      })
      .catch(showError);
  }

  function asBuiltOverlays() {
    return [...new Set(
      [...enabledOverlays]
        .map((name) => AS_BUILT_OVERLAY_MAP[name])
        .filter(Boolean),
    )].sort();
  }

  function synchronizeAsBuilt() {
    if (!projection || !asBuiltFrame.contentWindow) return;
    const selected = projection.presentation;
    asBuiltFrame.contentWindow.postMessage(
      {
        type: AS_BUILT_SYNC_TYPE,
        payload: {
          version: AS_BUILT_SYNC_VERSION,
          projection_digest: projection.projection_digest,
          state_digest: projection.domain.state_digest,
          as_built_scene_digest: projection.artifacts.as_built_scene_digest,
          as_built_frame_id: selected.as_built_frame_id,
          as_built_entity_id: selected.selected_issue_spatial_entity_id,
          selected_issue_id: selected.selected_issue_id,
          timeline_day: selected.timeline_day,
          overlays: asBuiltOverlays(),
        },
      },
      location.origin,
    );
  }

  function renderOverlays() {
    overlayControls.replaceChildren();
    const overlays = projection?.construction?.overlays || {};
    if (!overlaysInitialized) {
      Object.entries(overlays).forEach(([name, available]) => {
        if (available) enabledOverlays.add(name);
      });
      overlaysInitialized = true;
    }
    Object.entries(overlays).forEach(([name, available]) => {
      if (!available) return;
      const label = element("label", "construction-overlay-toggle");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = enabledOverlays.has(name);
      input.addEventListener("change", () => {
        if (input.checked) enabledOverlays.add(name);
        else enabledOverlays.delete(name);
        renderEvidence();
        synchronizeAsBuilt();
      });
      label.append(input, document.createTextNode(name.replaceAll("_", " ")));
      overlayControls.append(label);
    });
  }

  function renderEvidence() {
    selectionSummary.replaceChildren();
    evidencePins.replaceChildren();
    if (!projection) return;
    const selected = projection.presentation;
    const summary = element("dl", "construction-selection-dl");
    [
      ["View", selected.active_view],
      ["Pascal storey", selected.selected_storey],
      ["Pascal node", selected.selected_node],
      ["Pascal Aura target", selected.selected_target_ref],
      ["Construction issue", selected.selected_issue_id],
      ["Domain storey", selected.selected_domain_storey_id],
      ["As-built frame", selected.as_built_frame_id],
      ["Timeline day", selected.timeline_day],
      [
        "Truth class",
        selected.active_view === "AS_BUILT"
          ? selected.as_built_truth_class
          : selected.design_truth_class,
      ],
    ].forEach(([label, value]) => {
      summary.append(element("dt", null, label), element("dd", null, value));
    });
    selectionSummary.append(summary);

    const pins = projection.construction.evidence_pins;
    if (!pins.length) {
      evidencePins.append(
        element("p", "construction-muted", "No evidence pin is projected."),
      );
      return;
    }
    pins.forEach((pin) => {
      const card = element("button", "construction-pin");
      card.type = "button";
      card.append(
        element("strong", null, pin.work_package_id),
        element("span", null, pin.construction_scope_ref),
        element(
          "span",
          "construction-muted",
          `Pascal association: ${pin.pascal_aura_target_ref}`,
        ),
      );
      if (enabledOverlays.has("hazards") && pin.hazard_ids.length) {
        card.append(
          element("span", "construction-blocked", `Hazards: ${pin.hazard_ids.join(", ")}`),
        );
      }
      if (enabledOverlays.has("inspections") && pin.inspection_ids.length) {
        card.append(element("span", null, `Inspections: ${pin.inspection_ids.join(", ")}`));
      }
      if (pin.evidence_refs.length) {
        card.append(element("span", null, `Evidence refs: ${pin.evidence_refs.length}`));
      }
      card.append(
        element(
          "span",
          "construction-muted",
          "Presentation association only; authorized domain review remains external.",
        ),
      );
      card.setAttribute(
        "aria-pressed",
        String(projection.presentation.selected_issue_id === pin.work_package_id),
      );
      card.addEventListener("click", () => {
        requestQueue = requestQueue
          .then(() => requestProjection({
            selected_issue_id: pin.work_package_id,
            selected_storey: pin.presentation_storey_id,
            selected_node: pin.pascal_node_id,
          }))
          .then((next) => synchronizePascalIssue(next, pin))
          .catch(showError);
      });
      evidencePins.append(card);
    });
  }

  function candidateLabel(role) {
    return {
      HARD_BLOCKED: "Hard blocked",
      NEEDS_EVIDENCE: "Evidence incomplete",
      READY_FOR_HUMAN_REVIEW: "Ready for human review",
    }[role] || role;
  }

  function renderCandidates() {
    candidatesNode.replaceChildren();
    if (!projection) return;
    projection.coordination_candidates.forEach((candidate) => {
      const artifact = candidate.artifact;
      const card = element(
        "button",
        `construction-candidate construction-candidate-${candidate.role.toLowerCase()}`,
      );
      card.type = "button";
      card.dataset.candidateId = artifact.candidate_id;
      card.append(
        element("span", "construction-candidate-role", candidateLabel(candidate.role)),
        element("strong", null, artifact.title),
        element("span", null, artifact.summary),
        element("span", null, `Closure ${candidate.closure_count}/${candidate.closure_total}`),
        element(
          "span",
          null,
          `Schedule ${candidate.schedule_delta_hours} h · Budget CAD ${candidate.budget_delta_cad} · Idle ${candidate.idle_time_delta_hours} h`,
        ),
      );
      if (candidate.open_obligations.length) {
        card.append(
          element("span", "construction-muted", candidate.open_obligations.join(" · ")),
        );
      }
      card.setAttribute(
        "aria-pressed",
        String(projection.presentation.selected_candidate_id === artifact.candidate_id),
      );
      card.addEventListener("click", () => {
        requestQueue = requestQueue
          .then(() => requestProjection({
            selected_candidate_id: artifact.candidate_id,
            selected_candidate_digest: artifact.candidate_digest,
          }))
          .catch(showError);
      });
      candidatesNode.append(card);
    });
  }

  function updateExportLinks() {
    if (!projection) return;
    const params = new URLSearchParams({
      active_view: projection.presentation.active_view,
      selected_storey: projection.presentation.selected_storey,
      selected_node: projection.presentation.selected_node,
      selected_issue_id: projection.presentation.selected_issue_id,
      selected_candidate_id: projection.presentation.selected_candidate_id,
      selected_candidate_digest: projection.presentation.selected_candidate_digest,
      timeline_day: String(projection.presentation.timeline_day),
      state_digest: projection.domain.state_digest,
      runtime_packet_digest: projection.domain.runtime_packet_digest,
      pascal_artifact_digest: projection.artifacts.pascal_artifact_digest,
      coordinate_receipt_digest: projection.artifacts.coordinate_receipt_digest,
      as_built_scene_digest: projection.artifacts.as_built_scene_digest,
    });
    exportLinks.forEach((link) => {
      const base = link.getAttribute("href").split("?", 1)[0];
      link.href = `${base}?${params.toString()}`;
    });
  }

  function renderDecision() {
    decisionNode.replaceChildren();
    if (!projection) return;
    const decision = projection.domain_decision;
    const authority = projection.authority;
    const badge = element(
      "p",
      "construction-review-badge",
      "Recommended for authorized human review",
    );
    const list = element("dl", "construction-decision-dl");
    [
      ["Status", decision.status],
      ["Candidate", decision.candidate_id],
      ["Physical work authorized", authority.physical_work_authorized],
      ["Professional approval", authority.professional_approval],
      ["Payment released", authority.payment_released],
      ["Access granted", authority.access_granted],
      ["Automatic execution", authority.automatic_execution],
      ["Construction event appended", authority.construction_event_appended],
      ["Human review required", authority.human_review_required],
    ].forEach(([label, value]) => {
      list.append(element("dt", null, label), element("dd", null, value));
    });
    const digest = element("code", "construction-digest", projection.projection_digest);
    decisionNode.append(
      badge,
      list,
      element("p", "construction-muted", "Projection digest"),
      digest,
    );
  }

  function renderStage() {
    const view = projection.presentation.active_view;
    const designVisible = ["DESIGN", "FLOOR_PLAN", "COMPARE"].includes(view);
    const asBuiltVisible = ["AS_BUILT", "COMPARE"].includes(view);
    designPane.hidden = !designVisible;
    asBuiltPane.hidden = !asBuiltVisible;
    root.dataset.presentationMode = view.toLowerCase().replace("_", "-");
    ensurePascalLaunch();
  }

  function render() {
    if (!projection) return;
    statusNode.textContent = `${projection.presentation.active_view} · ${projection.presentation.selected_issue_id} · projection ${projection.projection_digest.slice(0, 12)}`;
    timeline.value = String(projection.presentation.timeline_day);
    viewButtons.forEach((button) => {
      const active = button.dataset.constructionView === projection.presentation.active_view;
      button.setAttribute("aria-pressed", String(active));
    });
    renderStage();
    renderOverlays();
    renderEvidence();
    renderCandidates();
    renderDecision();
    updateExportLinks();
  }

  function showError(error) {
    statusNode.textContent = `P3 failed closed: ${String(error.message || error)}`;
    root.dataset.error = "true";
  }

  viewButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const activeView = button.dataset.constructionView;
      requestQueue = requestQueue
        .then(() => requestProjection({ active_view: activeView }))
        .then((next) => synchronizePascalView(next))
        .catch(showError);
    });
  });

  timeline.addEventListener("change", () => {
    requestQueue = requestQueue
      .then(() => requestProjection({ timeline_day: Number(timeline.value) }))
      .catch(showError);
  });

  window.addEventListener("message", (event) => {
    if (event.origin !== location.origin) return;
    const envelope = event.data;
    if (!envelope || typeof envelope !== "object") return;

    if (event.source === asBuiltFrame.contentWindow) {
      if (envelope.type === AS_BUILT_READY_TYPE) {
        syncNode.textContent = "Aura as-built renderer ready; awaiting exact P3 projection.";
        synchronizeAsBuilt();
        return;
      }
      if (envelope.type === AS_BUILT_RECEIPT_TYPE) {
        const receipt = envelope.payload || {};
        if (receipt.ok === false) {
          syncNode.textContent = `Aura as-built synchronization failed closed: ${text(receipt.error)}`;
          return;
        }
        if (projection && receipt.projection_digest === projection.projection_digest) {
          syncNode.textContent = `Synchronized ${receipt.as_built_frame_id} · day ${receipt.timeline_day} · client receipt only`;
        }
        return;
      }
    }

    pascalFrame = document.querySelector("[data-pascal-workbench-frame], .pascal-workbench-frame");
    if (!pascalFrame || event.source !== pascalFrame.contentWindow) return;
    if (envelope.type !== "AURA_PASCAL_BRIDGE_MESSAGE") return;
    const message = envelope.message;
    if (!message || typeof message !== "object" || !message.payload) return;
    if (typeof message.session_id === "string") pascalSessionId = message.session_id;
    if (["LOAD_RECEIPT", "VIEW_STATE", "SELECTION_CHANGED"].includes(message.action)) {
      pascalActive = true;
    }
    if (typeof message.payload.storey_id === "string") {
      pascalStorey = message.payload.storey_id;
    }
    if (typeof message.payload.node_id === "string") {
      pascalNode = message.payload.node_id;
    }
    const commandDigest = message.payload.command_message_digest;
    if (typeof commandDigest === "string" && pendingPascalReceipts.has(commandDigest)) {
      const pendingReceipt = pendingPascalReceipts.get(commandDigest);
      pendingPascalReceipts.delete(commandDigest);
      pendingReceipt.resolve(message.action);
    }
    if (
      ["LOAD_RECEIPT", "VIEW_STATE", "SELECTION_CHANGED"].includes(message.action)
      && pascalStorey
      && pascalNode
    ) {
      // Pascal-originated selection changes must clear the stale issue ID
      // so the server derives the matching Construction work package from
      // the new Pascal target instead of rejecting the mismatched pair.
      requestQueue = requestQueue
        .then(() => requestProjection({
          selected_storey: pascalStorey,
          selected_node: pascalNode,
          selected_issue_id: null,
        }))
        .catch(showError);
    }
  });

  asBuiltFrame.addEventListener("load", () => {
    syncNode.textContent = "Aura as-built renderer loaded; verifying exact packet.";
    synchronizeAsBuilt();
  });

  mountPascalSurface();
  requestQueue = requestQueue
    .then(() => fetch("/api/construction/decision-lane", {
      credentials: "same-origin",
      cache: "no-store",
    }))
    .then(async (response) => {
      const result = await response.json().catch(() => ({}));
      if (!response.ok || result.ok !== true || !result.projection) {
        throw new Error(
          result.error || result.reason || `P3 load failed with ${response.status}`,
        );
      }
      projection = result.projection;
      render();
      synchronizeAsBuilt();
    })
    .catch(showError);
})();
