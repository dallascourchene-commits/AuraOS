(() => {
  "use strict";

  const BUILD_REF = "aura-adopt-zf01a-static-v1";
  const ROUTE_ID = "zf01a-local-image-title-card";
  const RECIPE_ID = "aura-adopt-zf01-title-card-v1";
  const RECIPE_SHA256 = "a95b233ff6019fa6a32cc72715c2ba528b80d7d97258e8e6087948d426d3449d";
  const MAX_BYTES = 8 * 1024 * 1024;
  const STAGES = [
    "DISCOVER", "TRUST", "OPEN_INSTALL", "PERMISSION", "STORAGE_CHOICE",
    "OPTIONAL_ACCOUNT", "OPTIONAL_KEY", "INPUT", "CAPABILITY_RESOLVE",
    "EXECUTE", "VERIFY_ACCEPT", "SAVE_REOPEN", "SHARE_OR_REUSE"
  ];

  const $ = (id) => document.getElementById(id);
  const input = $("image-input");
  const titleInput = $("title-input");
  const renderButton = $("render-button");
  const downloadButton = $("download-button");
  const receiptButton = $("receipt-button");
  const acceptOutput = $("accept-output");
  const status = $("status");
  const badge = $("capability-badge");
  const canvas = $("output-canvas");
  const ctx = canvas.getContext("2d");

  const state = {
    startedAtMs: performance.now(),
    stepCount: 0,
    renderedBlob: null,
    renderedBlobBytes: null,
    inputBytes: null,
    inputType: null,
    saved: false,
    accepted: false,
    capabilityResult: null,
    stageEvents: new Map()
  };

  function stage(stageName, disposition, reason = "") {
    if (!STAGES.includes(stageName)) throw new Error(`unknown stage ${stageName}`);
    state.stageEvents.set(stageName, { stage: stageName, disposition, reason });
  }

  function markBaselineStages() {
    stage("DISCOVER", "COMPLETE", "static route opened");
    stage("TRUST", "COMPLETE", `build=${BUILD_REF}; recipe_sha256=${RECIPE_SHA256}`);
    stage("OPEN_INSTALL", "NOT_APPLICABLE", "zero-install browser route");
    stage("PERMISSION", "NOT_APPLICABLE", "user-selected File input; no persistent permission requested");
    stage("STORAGE_CHOICE", "NOT_APPLICABLE", "browser download remains user-controlled");
    stage("OPTIONAL_ACCOUNT", "NOT_APPLICABLE", "no account required for first value");
    stage("OPTIONAL_KEY", "NOT_APPLICABLE", "no API key required for first value");
    stage("SHARE_OR_REUSE", "NOT_APPLICABLE", "sharing is outside first-value witness; reusable recipe identity emitted");
  }

  function capabilities() {
    const missing = [];
    if (!("File" in window) || !("FileReader" in window)) missing.push("FILE_API");
    if (!("Blob" in window) || !("URL" in window) || typeof URL.createObjectURL !== "function") missing.push("BLOB_URL");
    if (!(canvas instanceof HTMLCanvasElement) || !ctx) missing.push("CANVAS_2D");
    if (!("download" in document.createElement("a"))) missing.push("DOWNLOAD_ATTRIBUTE");
    return {
      route: "ZERO_INSTALL_WEB_PWA",
      supported: missing.length === 0,
      missing,
      next_route: missing.length ? "DOWNLOAD_APP_OR_ASSISTED_PATH" : "NONE"
    };
  }

  function setCapabilityUI() {
    const result = capabilities();
    state.capabilityResult = result;
    stage("CAPABILITY_RESOLVE", result.supported ? "COMPLETE" : "REFUSED", result.missing.join(",") || "minimum browser capabilities present");
    if (result.supported) {
      badge.textContent = "READY";
      status.textContent = "Ready. Choose an image to create locally.";
      renderButton.disabled = false;
    } else {
      badge.textContent = "UNAVAILABLE";
      status.textContent = `BROWSER_CAPABILITY_UNAVAILABLE: ${result.missing.join(", ")}. Next route: ${result.next_route}.`;
      renderButton.disabled = true;
    }
    return result;
  }

  function coverRect(sourceWidth, sourceHeight, destWidth, destHeight) {
    const scale = Math.max(destWidth / sourceWidth, destHeight / sourceHeight);
    const width = sourceWidth * scale;
    const height = sourceHeight * scale;
    return { x: (destWidth - width) / 2, y: (destHeight - height) / 2, width, height };
  }

  function drawTitleCard(image, title) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#111";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    const rect = coverRect(image.naturalWidth || image.width, image.naturalHeight || image.height, canvas.width, canvas.height);
    ctx.drawImage(image, rect.x, rect.y, rect.width, rect.height);

    const overlayHeight = 176;
    const gradient = ctx.createLinearGradient(0, canvas.height - overlayHeight - 72, 0, canvas.height);
    gradient.addColorStop(0, "rgba(0,0,0,0)");
    gradient.addColorStop(0.32, "rgba(0,0,0,.70)");
    gradient.addColorStop(1, "rgba(0,0,0,.92)");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, canvas.height - overlayHeight - 72, canvas.width, overlayHeight + 72);

    ctx.fillStyle = "#fff";
    ctx.textBaseline = "alphabetic";
    ctx.font = "700 54px system-ui";
    const safeTitle = String(title || "Untitled").trim().slice(0, 80) || "Untitled";
    ctx.fillText(safeTitle, 48, canvas.height - 76, canvas.width - 96);
    ctx.font = "600 24px system-ui";
    ctx.globalAlpha = 0.78;
    ctx.fillText("Made with Aura", 48, canvas.height - 34);
    ctx.globalAlpha = 1;
  }

  function canvasBlob() {
    return new Promise((resolve, reject) => {
      canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error("CANVAS_ENCODE_FAILED")), "image/png");
    });
  }

  function loadImageFromUrl(url) {
    return new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error("IMAGE_DECODE_FAILED"));
      image.src = url;
    });
  }

  async function renderFile(file, title) {
    if (!state.capabilityResult?.supported) throw new Error("BROWSER_CAPABILITY_UNAVAILABLE");
    if (!file) throw new Error("INPUT_REQUIRED");
    if (!file.type.startsWith("image/")) throw new Error("INPUT_MEDIA_TYPE_UNSUPPORTED");
    if (file.size > MAX_BYTES) throw new Error("INPUT_TOO_LARGE");
    state.inputBytes = file.size;
    state.inputType = file.type || "UNKNOWN";
    stage("INPUT", "COMPLETE", `local image selected; type=${state.inputType}; bytes=${state.inputBytes}`);

    const url = URL.createObjectURL(file);
    try {
      const image = await loadImageFromUrl(url);
      drawTitleCard(image, title);
      state.renderedBlob = await canvasBlob();
      state.renderedBlobBytes = state.renderedBlob.size;
      stage("EXECUTE", "COMPLETE", `local Canvas 2D render; output_bytes=${state.renderedBlobBytes}`);
      state.saved = false;
      state.accepted = false;
      acceptOutput.checked = false;
      acceptOutput.disabled = false;
      downloadButton.disabled = true;
      receiptButton.disabled = true;
      status.textContent = "Preview ready. Mark it useful to accept the output.";
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.rel = "noopener";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  function stableFingerprint(payload) {
    const text = JSON.stringify(payload, Object.keys(payload).sort());
    let h = 2166136261;
    for (let i = 0; i < text.length; i += 1) {
      h ^= text.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return `zf01-fnv1a-${(h >>> 0).toString(16).padStart(8, "0")}`;
  }

  function stageArray() {
    return STAGES.map((name) => state.stageEvents.get(name) || { stage: name, disposition: "UNKNOWN", reason: "not observed" });
  }

  function routeReceipt() {
    const events = stageArray();
    const consequence = {
      route_id: ROUTE_ID,
      build_ref: BUILD_REF,
      recipe_id: RECIPE_ID,
      recipe_sha256: RECIPE_SHA256,
      entry_surface: "ZERO_INSTALL_WEB_PWA",
      input_type: state.inputType || "UNKNOWN",
      input_bytes: state.inputBytes ?? "UNKNOWN",
      output_type: "image/png",
      output_bytes: state.renderedBlobBytes ?? "UNKNOWN",
      accepted_value: state.accepted,
      saved: state.saved,
      stages: events.map(({ stage: s, disposition, reason }) => ({ stage: s, disposition, reason }))
    };
    return {
      schema: "AdoptionFrictionReceiptV1",
      compatibility_status: "PROVISIONAL_ZF01_SUPERSET_AWAIT_ZF00B_REDUCER",
      route_id: ROUTE_ID,
      build_ref: BUILD_REF,
      recipe_ref: `${RECIPE_ID}@${RECIPE_SHA256}`,
      privacy_mode: "LOCAL_ONLY_NO_TELEMETRY_NO_CONTENT_IN_RECEIPT",
      starting_state: "BROWSER_OPEN_NO_ACCOUNT_NO_KEY",
      stage_events: events,
      step_count: state.stepCount,
      permissions_requested: 0,
      mandatory_account: false,
      mandatory_api_key: false,
      install_actions: 0,
      downloaded_dependency_bytes: 0,
      retained_dependency_bytes: 0,
      input_bytes: state.inputBytes ?? "UNKNOWN",
      output_bytes: state.renderedBlobBytes ?? "UNKNOWN",
      wall_time_to_receipt_ms: Math.round(performance.now() - state.startedAtMs),
      provider_cost_microunits: 0,
      provider_calls: 0,
      retries: 0,
      accepted_value_criterion: "user explicitly marks rendered local PNG as useful",
      accepted_value_result: state.accepted,
      saved_result: state.saved,
      capability_result: state.capabilityResult,
      friction_vector: {
        steps: state.stepCount,
        install_actions: 0,
        account_actions: 0,
        key_actions: 0,
        persistent_permission_actions: 0,
        downloaded_dependency_bytes: 0,
        provider_cost_microunits: 0
      },
      consequence_fingerprint: stableFingerprint(consequence),
      evidence_class: "LOCAL_BROWSER_WITNESS",
      authority: {
        upload_authorized: false,
        provider_authorized: false,
        telemetry_authorized: false,
        public_deployment_proven: false,
        background_execution_proven: false
      }
    };
  }

  async function runSelfTest() {
    try {
      if (!setCapabilityUI().supported) throw new Error("BROWSER_CAPABILITY_UNAVAILABLE");
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360"><rect width="640" height="360" fill="#2b2b2b"/><circle cx="320" cy="180" r="96" fill="#ddd"/></svg>`;
      const image = await loadImageFromUrl(`data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`);
      drawTitleCard(image, "Aura first value");
      state.inputBytes = new Blob([svg]).size;
      state.inputType = "image/svg+xml";
      stage("INPUT", "COMPLETE", "synthetic local fixture");
      state.renderedBlob = await canvasBlob();
      state.renderedBlobBytes = state.renderedBlob.size;
      stage("EXECUTE", "COMPLETE", `selftest Canvas render; output_bytes=${state.renderedBlobBytes}`);
      state.accepted = state.renderedBlob.size > 0 && canvas.width === 1280 && canvas.height === 720;
      stage("VERIFY_ACCEPT", state.accepted ? "COMPLETE" : "REFUSED", "selftest acceptance: nonempty PNG at exact dimensions");
      state.saved = true;
      stage("SAVE_REOPEN", "COMPLETE", "selftest save path simulated without external effect");
      const receipt = routeReceipt();
      if (!state.accepted || receipt.provider_calls !== 0 || receipt.install_actions !== 0) throw new Error("SELFTEST_ACCEPTANCE_FAILED");
      document.body.dataset.selftest = "PASS";
      document.body.dataset.selftestReceipt = receipt.consequence_fingerprint;
      status.textContent = "SELFTEST PASS";
    } catch (error) {
      document.body.dataset.selftest = "FAIL";
      document.body.dataset.selftestError = String(error?.message || error);
      status.textContent = `SELFTEST FAIL: ${error?.message || error}`;
    }
  }

  markBaselineStages();
  setCapabilityUI();

  renderButton.addEventListener("click", async () => {
    state.stepCount += 1;
    renderButton.disabled = true;
    try {
      await renderFile(input.files?.[0], titleInput.value);
    } catch (error) {
      status.textContent = String(error?.message || error);
      stage("EXECUTE", "REFUSED", String(error?.message || error));
    } finally {
      renderButton.disabled = !state.capabilityResult?.supported;
    }
  });

  acceptOutput.addEventListener("change", () => {
    state.stepCount += 1;
    state.accepted = acceptOutput.checked && Boolean(state.renderedBlob);
    stage("VERIFY_ACCEPT", state.accepted ? "COMPLETE" : "REFUSED", state.accepted ? "user explicitly accepted preview" : "output not accepted");
    downloadButton.disabled = !state.accepted;
    receiptButton.disabled = !(state.accepted && state.saved);
  });

  downloadButton.addEventListener("click", () => {
    if (!state.renderedBlob || !state.accepted) return;
    state.stepCount += 1;
    downloadBlob(state.renderedBlob, "aura-title-card.png");
    state.saved = true;
    stage("SAVE_REOPEN", "COMPLETE", "PNG download initiated by user");
    receiptButton.disabled = false;
    status.textContent = "Saved locally. You can also download the route receipt.";
  });

  receiptButton.addEventListener("click", () => {
    state.stepCount += 1;
    const receipt = routeReceipt();
    const blob = new Blob([`${JSON.stringify(receipt, null, 2)}\n`], { type: "application/json" });
    downloadBlob(blob, "aura-adoption-friction-receipt.json");
  });

  if (new URLSearchParams(location.search).get("selftest") === "1") runSelfTest();

  window.AuraZF01 = Object.freeze({ capabilities, routeReceipt, recipeId: RECIPE_ID, recipeSha256: RECIPE_SHA256 });
})();
