(() => {
  "use strict";

  const root = document.getElementById("pascal-construction-foundry");
  if (!root) return;
  const statusNode = document.getElementById("pascal-foundry-status");
  const receiptNode = document.getElementById("pascal-foundry-receipt");
  const host = document.getElementById("pascal-workbench-host");
  const buttons = new Map(
    Array.from(root.querySelectorAll("[data-pascal-action]"), (button) => [button.dataset.pascalAction, button])
  );

  let iframe = null;
  let session = null;
  let fixture = null;
  let pending = false;
  let storeyIndex = 0;
  let dimensionsVisible = true;
  let eventQueue = Promise.resolve();

  function setStatus(text, detail) {
    statusNode.textContent = text;
    if (detail !== undefined) receiptNode.textContent = JSON.stringify(detail, null, 2);
  }

  function setControls(active) {
    ["2d", "3d", "storey", "dimensions", "reset", "dissolve"].forEach((name) => {
      const button = buttons.get(name);
      if (button) button.disabled = !active || pending;
    });
    const launch = buttons.get("launch");
    if (launch) launch.disabled = Boolean(iframe) || pending;
  }

  async function request(path, payload) {
    const response = await fetch(path, {
      method: payload === undefined ? "GET" : "POST",
      headers: payload === undefined ? {} : { "Content-Type": "application/json" },
      body: payload === undefined ? undefined : JSON.stringify(payload),
      cache: "no-store",
      credentials: "same-origin",
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok || body.ok === false) {
      throw new Error(body.error || body.reason || `Pascal API failed with ${response.status}`);
    }
    return body;
  }

  function workbenchUrl(start) {
    const current = start.session;
    const query = new URLSearchParams({
      session_id: current.session_id,
      expected_origin: location.origin,
      spatial_scene_digest: current.spatial_scene_digest,
      render_plan_digest: current.render_plan_digest,
      pascal_artifact_digest: current.pascal_artifact_digest,
      coordinate_receipt_digest: current.coordinate_receipt_digest,
      state_binding_digest: current.state_binding_digest,
    });
    return `${start.workbench_path}?${query.toString()}`;
  }

  async function launch() {
    if (iframe || pending) return;
    pending = true;
    setControls(false);
    setStatus("Issuing exact local Pascal presentation session...");
    try {
      fixture = await request("/api/construction/pascal/session/start", {});
      session = fixture.session;
      storeyIndex = 0;
      dimensionsVisible = true;
      iframe = document.createElement("iframe");
      iframe.className = "pascal-workbench-frame";
      iframe.title = "Aura Pascal Construction workbench";
      iframe.sandbox = fixture.sandbox;
      iframe.referrerPolicy = "no-referrer";
      iframe.src = workbenchUrl(fixture);
      host.replaceChildren(iframe);
      setStatus("Pascal iframe created; waiting for exact READY receipt.", session);
    } catch (error) {
      iframe = null;
      session = null;
      fixture = null;
      setStatus(`Pascal launch failed closed: ${String(error.message || error)}`);
    } finally {
      pending = false;
      setControls(Boolean(iframe && session && session.state === "ACTIVE"));
    }
  }

  async function sendCommand(action, payload = {}) {
    if (!iframe || !session || pending) return;
    pending = true;
    setControls(false);
    try {
      const result = await request(
        `/api/construction/pascal/session/${encodeURIComponent(session.session_id)}/command`,
        { action, payload },
      );
      session = result.session;
      iframe.contentWindow.postMessage(
        { type: "AURA_PASCAL_BRIDGE_MESSAGE", message: result.message },
        location.origin,
      );
      setStatus(`Issued ${action}; waiting for exact child receipt.`, result);
    } catch (error) {
      pending = false;
      setControls(Boolean(iframe && session && session.state === "ACTIVE"));
      setStatus(`Pascal command failed closed: ${String(error.message || error)}`);
    }
  }

  async function acceptChildMessage(message) {
    if (!session) return;
    const result = await request(
      `/api/construction/pascal/session/${encodeURIComponent(session.session_id)}/event`,
      { message },
    );
    session = result.session;
    const action = message.action;
    setStatus(`Retained ${action}.`, result);

    if (action === "READY") {
      await sendCommand("LOAD_ARTIFACT", {
        scene: fixture.scene,
        artifact_manifest: fixture.artifact_manifest,
        initial_view: "2D",
        dimensions_visible: true,
      });
      return;
    }
    if (["LOAD_RECEIPT", "VIEW_STATE", "SELECTION_CHANGED", "PRESENTATION_ERROR"].includes(action)) {
      pending = false;
      setControls(Boolean(iframe && session.state === "ACTIVE"));
      return;
    }
    if (action === "DISSOLUTION_RECEIPT") {
      pending = true;
      if (iframe) iframe.remove();
      iframe = null;
      const finalized = await request(
        `/api/construction/pascal/session/${encodeURIComponent(session.session_id)}/dissolution/finalize`,
        { iframe_removed: true },
      );
      session = finalized.session;
      pending = false;
      setControls(false);
      setStatus("Pascal renderer, storage, listeners, and iframe dissolved.", finalized);
    }
  }

  function onWindowMessage(event) {
    if (event.origin !== location.origin || !iframe || event.source !== iframe.contentWindow) return;
    const envelope = event.data;
    if (!envelope || typeof envelope !== "object") return;
    if (envelope.type === "AURA_PASCAL_BRIDGE_MESSAGE") {
      eventQueue = eventQueue
        .then(() => acceptChildMessage(envelope.message))
        .catch((error) => {
          pending = false;
          setControls(Boolean(iframe && session && session.state === "ACTIVE"));
          setStatus(`Pascal receipt failed closed: ${String(error.message || error)}`);
        });
      return;
    }
    if (
      envelope.type === "AURA_PASCAL_SELECTION_REQUEST"
      && session
      && envelope.session_id === session.session_id
      && typeof envelope.node_id === "string"
    ) {
      eventQueue = eventQueue.then(() => sendCommand("SET_SELECTION", { node_id: envelope.node_id }));
    }
  }

  buttons.get("launch")?.addEventListener("click", launch);
  buttons.get("2d")?.addEventListener("click", () => sendCommand("SET_VIEW_2D"));
  buttons.get("3d")?.addEventListener("click", () => sendCommand("SET_VIEW_3D"));
  buttons.get("storey")?.addEventListener("click", () => {
    if (!fixture) return;
    const storeys = fixture.artifact_manifest.storey_ids;
    storeyIndex = (storeyIndex + 1) % storeys.length;
    sendCommand("SET_STOREY", { storey_id: storeys[storeyIndex] });
  });
  buttons.get("dimensions")?.addEventListener("click", () => {
    dimensionsVisible = !dimensionsVisible;
    sendCommand("SET_DIMENSIONS", { visible: dimensionsVisible });
  });
  buttons.get("reset")?.addEventListener("click", () => sendCommand("RESET_CAMERA"));
  buttons.get("dissolve")?.addEventListener("click", () => sendCommand("DISSOLVE"));
  window.addEventListener("message", onWindowMessage);

  const style = document.createElement("style");
  style.textContent = `
    .pascal-controls { display: flex; flex-wrap: wrap; gap: .55rem; margin: .8rem 0; }
    .pascal-controls button { min-width: 5rem; }
    .pascal-stage-card { min-height: 30rem; }
    .pascal-workbench-host { min-height: 28rem; border: 1px solid rgba(126,200,255,.25); border-radius: 12px; overflow: hidden; background: #071018; }
    .pascal-workbench-frame { width: 100%; min-height: 28rem; height: 64vh; border: 0; display: block; background: #071018; }
  `;
  document.head.appendChild(style);
  setControls(false);

  request("/api/construction/pascal/manifest")
    .then((result) => setStatus("Pinned Pascal presentation organ is available.", result))
    .catch((error) => setStatus(`Pascal is unavailable; PR 1 remains active. ${String(error.message || error)}`));
})();
