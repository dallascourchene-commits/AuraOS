(() => {
  "use strict";

  const BASE = "http://127.0.0.1:8765";
  const $ = (id) => document.getElementById(id);

  function setStatus(message, detail = null) {
    $("status").textContent = detail ? `${message}\n${detail}` : message;
  }

  async function getSettings() {
    const data = await chrome.storage.local.get(["endpointId", "visitId", "bridgeToken", "activeTurn"]);
    return data;
  }

  async function saveSettings() {
    const endpointId = $("endpointId").value.trim();
    const visitId = $("visitId").value.trim();
    const bridgeToken = $("bridgeToken").value.trim();
    if (!endpointId || !visitId || !bridgeToken) {
      throw new Error("Endpoint ID, Visit ID and local bridge token are required.");
    }
    await chrome.storage.local.set({ endpointId, visitId, bridgeToken });
    setStatus("Local bridge binding saved. No provider credentials were stored.");
  }

  async function activeGeminiTab() {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id || !tab.url?.startsWith("https://gemini.google.com/")) {
      throw new Error("Open the bound normal Gemini chat tab before using the bridge.");
    }
    return tab;
  }

  async function api(path, { method = "GET", body = null } = {}) {
    const { bridgeToken } = await getSettings();
    if (!bridgeToken) throw new Error("Local bridge token is not configured.");
    const response = await fetch(BASE + path, {
      method,
      headers: {
        "Authorization": `Bearer ${bridgeToken}`,
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
      cache: "no-store",
    });
    const payload = await response.json().catch(() => ({ status: "ERROR", code: "NON_JSON_LOOPBACK_RESPONSE" }));
    if (!response.ok) {
      const err = new Error(payload.code || `LOOPBACK_HTTP_${response.status}`);
      err.payload = payload;
      throw err;
    }
    return payload;
  }

  async function loadNextTurn() {
    const { endpointId, visitId } = await getSettings();
    if (!endpointId || !visitId) throw new Error("Save Endpoint ID and Visit ID first.");
    const tab = await activeGeminiTab();
    const query = new URLSearchParams({ endpoint_id: endpointId, visit_id: visitId });
    const packet = await api(`/v1/turns/next?${query}`);
    if (packet.status === "EMPTY") {
      setStatus("No eligible pending Aura turn for this endpoint.");
      return;
    }
    if (packet.status !== "TURN_READY") {
      throw new Error(`Unexpected loopback state: ${packet.status}`);
    }
    const response = await chrome.tabs.sendMessage(tab.id, {
      type: "AURA_LOAD_PROMPT",
      turn_id: packet.turn_id,
      prompt_text: packet.prompt_text,
    });
    if (!response?.ok) {
      throw new Error(`${response?.code || "GEMINI_LOAD_FAILED"}${response?.count != null ? ` (${response.count})` : ""}`);
    }
    await chrome.storage.local.set({
      activeTurn: {
        turn_id: packet.turn_id,
        capsule_id: packet.capsule_id,
        envelope: packet.envelope,
      },
    });
    setStatus(
      `Aura turn ${packet.turn_id} loaded into Gemini.`,
      "Review the prompt in the Gemini composer, then press Gemini Send yourself. After Gemini finishes, reopen this popup and capture the visible response."
    );
  }

  async function sha256(text) {
    const bytes = new TextEncoder().encode(text);
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  async function captureResult() {
    const settings = await getSettings();
    const { endpointId, visitId, activeTurn } = settings;
    if (!endpointId || !visitId || !activeTurn?.envelope) {
      throw new Error("No active Aura turn is bound in this extension.");
    }
    const tab = await activeGeminiTab();
    const captured = await chrome.tabs.sendMessage(tab.id, { type: "AURA_CAPTURE_VISIBLE_RESPONSE" });
    if (!captured?.ok) {
      const hint = captured?.instruction || "If automatic capture is ambiguous, select the visible Gemini answer text and try Capture again.";
      throw new Error(`${captured?.code || "VISIBLE_RESPONSE_CAPTURE_FAILED"}: ${hint}`);
    }
    const text = String(captured.text || "").trim();
    if (!text) throw new Error("Captured visible response was empty.");
    const env = activeTurn.envelope;
    const result = {
      turn_id: env.turn_id,
      capsule_id: env.capsule_id,
      endpoint_id: endpointId,
      visit_id: visitId,
      arena_sid: env.arena_sid,
      arena_head: env.arena_head,
      currentness_hash: env.currentness_hash,
      visible_text: text,
      visible_text_sha256: await sha256(text),
      status: "COMPLETE",
      residuals: [],
      receipt_refs: [],
      provider_id: "GEMINI_WEBCHAT",
    };
    const accepted = await api("/v1/results", { method: "POST", body: result });
    await chrome.tabs.sendMessage(tab.id, { type: "AURA_CLEAR_TURN" });
    await chrome.storage.local.remove("activeTurn");
    setStatus(
      `Visible Gemini result accepted for turn ${env.turn_id}.`,
      `Capture mode: ${captured.capture_mode}. Receipt: ${accepted.receipt || "returned by relay"}`
    );
  }

  async function initialize() {
    const settings = await getSettings();
    $("endpointId").value = settings.endpointId || "";
    $("visitId").value = settings.visitId || "";
    $("bridgeToken").value = settings.bridgeToken || "";
    if (settings.activeTurn?.turn_id) {
      setStatus(`Active Aura turn ${settings.activeTurn.turn_id} is waiting for visible Gemini response capture.`);
    }
  }

  $("save").addEventListener("click", () => saveSettings().catch((e) => setStatus("Save refused.", e.message)));
  $("load").addEventListener("click", () => loadNextTurn().catch((e) => setStatus("Load refused.", e.message)));
  $("capture").addEventListener("click", () => captureResult().catch((e) => setStatus("Capture refused.", e.message)));

  initialize().catch((e) => setStatus("Initialization error.", e.message));
})();
