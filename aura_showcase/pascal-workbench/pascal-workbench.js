(() => {
  "use strict";

  const BRIDGE_VERSION = "AURA_PASCAL_PRESENTATION_BRIDGE_V1";
  const GRAMMAR_VERSION = "AURA_PASCAL_PRESENTATION_WFST_EXTENSION_V1";
  const SESSION_VERSION = "AURA_PASCAL_PRESENTATION_SESSION_V1";
  const MAX_SAFE_INTEGER = Number.MAX_SAFE_INTEGER;
  const params = new URLSearchParams(location.search);
  const identity = Object.freeze({
    sessionId: params.get("session_id") || "",
    expectedOrigin: params.get("expected_origin") || "",
    spatialSceneDigest: params.get("spatial_scene_digest") || "",
    renderPlanDigest: params.get("render_plan_digest") || "",
    pascalArtifactDigest: params.get("pascal_artifact_digest") || "",
    coordinateReceiptDigest: params.get("coordinate_receipt_digest") || "",
    initialStateBindingDigest: params.get("state_binding_digest") || "",
  });
  const hex64 = /^[0-9a-f]{64}$/;
  const idPattern = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$/;

  if (
    !idPattern.test(identity.sessionId)
    || identity.expectedOrigin !== location.origin
    || !hex64.test(identity.spatialSceneDigest)
    || !hex64.test(identity.renderPlanDigest)
    || !hex64.test(identity.pascalArtifactDigest)
    || !hex64.test(identity.coordinateReceiptDigest)
    || !hex64.test(identity.initialStateBindingDigest)
  ) {
    document.body.textContent = "Pascal workbench identity is invalid or not same-origin.";
    return;
  }

  const canvas = document.getElementById("pascal-canvas");
  const context = canvas.getContext("2d", { alpha: false });
  const title = document.getElementById("scene-title");
  const viewBadge = document.getElementById("view-badge");
  const storeyBadge = document.getElementById("storey-badge");
  const selectionLabel = document.getElementById("selection-label");
  const networkLabel = document.getElementById("network-label");
  const emptyState = document.getElementById("empty-state");

  let state = "CREATED";
  let childSequence = 1;
  let expectedParentSequence = 1;
  let externalRequests = 0;
  let scene = null;
  let manifest = null;
  let activeView = "UNSET";
  let selectedStorey = "";
  let selectedNodeId = "";
  let dimensionsVisible = true;
  let disposed = false;
  const seenNonces = new Set();
  const hitRegions = [];
  let focusedRegionIndex = -1;

  const nativeFetch = window.fetch;
  const NativeWebSocket = window.WebSocket;
  const nativeXhrOpen = window.XMLHttpRequest && window.XMLHttpRequest.prototype.open;

  function noteExternalRequest(label) {
    externalRequests += 1;
    networkLabel.textContent = `External requests: ${externalRequests}`;
    throw new Error(`${label} disabled in Pascal workbench`);
  }

  window.fetch = (...args) => Promise.reject(
    new Error(`Network disabled in Pascal workbench: ${String(args[0])}`)
  ).finally(() => {
    externalRequests += 1;
    networkLabel.textContent = `External requests: ${externalRequests}`;
  });
  if (window.WebSocket) {
    window.WebSocket = function BlockedWebSocket() {
      noteExternalRequest("WebSocket");
    };
  }
  if (nativeXhrOpen) {
    window.XMLHttpRequest.prototype.open = function blockedOpen() {
      noteExternalRequest("XMLHttpRequest");
    };
  }

  function concatBytes(chunks) {
    const length = chunks.reduce((total, chunk) => total + chunk.length, 0);
    const output = new Uint8Array(length);
    let offset = 0;
    chunks.forEach((chunk) => {
      output.set(chunk, offset);
      offset += chunk.length;
    });
    return output;
  }

  function ascii(text) {
    return new TextEncoder().encode(text);
  }

  function bridgeEncode(value, depth = 0) {
    if (depth > 16) throw new Error("bridge value exceeds MAX_BRIDGE_DEPTH=16");
    if (value === null) return ascii("n");
    if (typeof value === "boolean") return ascii(value ? "b1" : "b0");
    if (typeof value === "number") {
      if (!Number.isFinite(value)) throw new Error("bridge numbers must be finite");
      if (Number.isInteger(value) && Math.abs(value) <= MAX_SAFE_INTEGER) {
        return ascii(`i${Object.is(value, -0) ? 0 : value};`);
      }
      const buffer = new ArrayBuffer(8);
      new DataView(buffer).setFloat64(0, value, false);
      const hex = Array.from(new Uint8Array(buffer), (item) => (
        item.toString(16).padStart(2, "0")
      )).join("");
      return ascii(`f${hex};`);
    }
    if (typeof value === "string") {
      const encoded = new TextEncoder().encode(value);
      return concatBytes([ascii(`s${encoded.length}:`), encoded]);
    }
    if (Array.isArray(value)) {
      return concatBytes([
        ascii("["),
        ...value.map((item) => bridgeEncode(item, depth + 1)),
        ascii("]"),
      ]);
    }
    if (value && typeof value === "object") {
      const chunks = [ascii("{")];
      Object.keys(value).sort().forEach((key) => {
        if (!/^[\x20-\x7e]{1,256}$/.test(key)) {
          throw new Error("bridge object keys must be bounded printable ASCII strings");
        }
        chunks.push(bridgeEncode(key, depth + 1));
        chunks.push(bridgeEncode(value[key], depth + 1));
      });
      chunks.push(ascii("}"));
      return concatBytes(chunks);
    }
    throw new Error(`bridge value is not JSON-compatible: ${typeof value}`);
  }

  async function digestBytes(bytes) {
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(digest), (item) => (
      item.toString(16).padStart(2, "0")
    )).join("");
  }

  async function bridgeSha256(value) {
    return digestBytes(bridgeEncode(value));
  }

  function canonicalize(value) {
    if (Array.isArray(value)) return value.map(canonicalize);
    if (value && typeof value === "object") {
      const output = {};
      Object.keys(value).sort().forEach((key) => {
        output[key] = canonicalize(value[key]);
      });
      return output;
    }
    return value;
  }

  async function ordinarySha256(value) {
    const text = typeof value === "string"
      ? value
      : JSON.stringify(canonicalize(value));
    return digestBytes(new TextEncoder().encode(text));
  }

  function randomHex(bytes = 12) {
    const values = new Uint8Array(bytes);
    crypto.getRandomValues(values);
    return Array.from(values, (item) => item.toString(16).padStart(2, "0")).join("");
  }

  async function stateBindingDigest() {
    return bridgeSha256({
      grammar_version: GRAMMAR_VERSION,
      session_version: SESSION_VERSION,
      session_id: identity.sessionId,
      state,
      spatial_scene_digest: identity.spatialSceneDigest,
      render_plan_digest: identity.renderPlanDigest,
      pascal_artifact_digest: identity.pascalArtifactDigest,
      coordinate_receipt_digest: identity.coordinateReceiptDigest,
      expected_origin: identity.expectedOrigin,
      projection_only: true,
      execution_authority: false,
      construction_truth: false,
    });
  }

  function nextChildState(action) {
    if (action === "READY") return "READY";
    if (action === "LOAD_RECEIPT") return "ACTIVE";
    if (action === "DISSOLUTION_RECEIPT") return "DISSOLVED";
    return state;
  }

  async function sendEvent(action, payload) {
    if (disposed && action !== "DISSOLUTION_RECEIPT") return;
    const body = {
      message_id: `PBM-${randomHex()}`,
      session_id: identity.sessionId,
      sequence: childSequence,
      nonce: `N-${randomHex()}`,
      spatial_scene_digest: identity.spatialSceneDigest,
      render_plan_digest: identity.renderPlanDigest,
      pascal_artifact_digest: identity.pascalArtifactDigest,
      coordinate_receipt_digest: identity.coordinateReceiptDigest,
      state_binding_digest: await stateBindingDigest(),
      sent_at: new Date().toISOString(),
      direction: "PASCAL_TO_PARENT",
      action,
      payload,
      version: BRIDGE_VERSION,
    };
    const message = { ...body, message_digest: await bridgeSha256(body) };
    parent.postMessage(
      { type: "AURA_PASCAL_BRIDGE_MESSAGE", message },
      identity.expectedOrigin,
    );
    childSequence += 1;
    state = nextChildState(action);
  }

  function validateMessageShape(message) {
    const expected = [
      "message_id", "session_id", "sequence", "nonce", "spatial_scene_digest",
      "render_plan_digest", "pascal_artifact_digest", "coordinate_receipt_digest",
      "state_binding_digest", "sent_at", "direction", "action", "payload",
      "message_digest", "version",
    ].sort();
    return message && typeof message === "object"
      && !Array.isArray(message)
      && Object.keys(message).sort().join("|") === expected.join("|");
  }

  async function validateParentMessage(message, event) {
    if (event.origin !== identity.expectedOrigin || event.source !== parent) {
      throw new Error("wrong origin or parent");
    }
    if (!validateMessageShape(message)) throw new Error("bridge keys mismatch");
    if (
      message.version !== BRIDGE_VERSION
      || message.direction !== "PARENT_TO_PASCAL"
    ) throw new Error("wrong bridge version or direction");
    if (
      typeof message.sent_at !== "string"
      || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$/.test(message.sent_at)
    ) throw new Error("invalid bridge timestamp");
    if (message.session_id !== identity.sessionId) throw new Error("wrong session");
    if (message.sequence !== expectedParentSequence) {
      throw new Error("stale or skipped sequence");
    }
    if (!idPattern.test(message.nonce) || seenNonces.has(message.nonce)) {
      throw new Error("nonce replay");
    }
    if (
      message.spatial_scene_digest !== identity.spatialSceneDigest
      || message.render_plan_digest !== identity.renderPlanDigest
      || message.pascal_artifact_digest !== identity.pascalArtifactDigest
      || message.coordinate_receipt_digest !== identity.coordinateReceiptDigest
    ) throw new Error("stale bridge identity");
    if (message.state_binding_digest !== await stateBindingDigest()) {
      throw new Error("stale state binding");
    }
    const body = { ...message };
    delete body.message_digest;
    if (message.message_digest !== await bridgeSha256(body)) {
      throw new Error("message digest mismatch");
    }
  }

  function activeStorey() {
    return scene && scene.storeys.find((item) => item.id === selectedStorey);
  }

  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    const ratio = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
    const width = Math.max(320, Math.round(rect.width * ratio));
    const height = Math.max(240, Math.round(rect.height * ratio));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
  }

  function updateLabels() {
    viewBadge.textContent = activeView;
    storeyBadge.textContent = selectedStorey || "No storey";
    selectionLabel.textContent = `Selection: ${selectedNodeId || "none"}`;
    networkLabel.textContent = `External requests: ${externalRequests}`;
  }

  function drawGrid(width, height) {
    context.strokeStyle = "rgba(126, 200, 255, 0.08)";
    context.lineWidth = 1;
    for (let x = 0; x <= width; x += 40) {
      context.beginPath();
      context.moveTo(x, 0);
      context.lineTo(x, height);
      context.stroke();
    }
    for (let y = 0; y <= height; y += 40) {
      context.beginPath();
      context.moveTo(0, y);
      context.lineTo(width, y);
      context.stroke();
    }
  }

  function roomColor(nodeId, selected) {
    const hash = Array.from(nodeId).reduce(
      (sum, char) => (sum * 31 + char.charCodeAt(0)) >>> 0,
      0,
    );
    const lightness = selected ? 68 : 38 + (hash % 14);
    return `hsl(${185 + (hash % 55)} 58% ${lightness}%)`;
  }

  function draw2D(storey, scale, offsetX, offsetY) {
    hitRegions.length = 0;
    storey.rooms.forEach((room) => {
      const x = offsetX + room.x * scale;
      const y = offsetY + room.y * scale;
      const width = room.width * scale;
      const depth = room.depth * scale;
      const selected = room.node_id === selectedNodeId;
      context.fillStyle = roomColor(room.node_id, selected);
      context.globalAlpha = selected ? 0.92 : 0.58;
      context.fillRect(x, y, width, depth);
      context.globalAlpha = 1;
      context.strokeStyle = selected ? "#f8fdff" : "#7ec8ff";
      context.lineWidth = selected ? 4 : 2;
      context.strokeRect(x, y, width, depth);
      context.fillStyle = "#eff9ff";
      context.font = `${Math.max(12, Math.round(scale * 0.52))}px system-ui`;
      context.fillText(room.label, x + 8, y + 22);
      if (dimensionsVisible) {
        context.fillStyle = "#a9d8f4";
        context.font = `${Math.max(10, Math.round(scale * 0.4))}px ui-monospace`;
        context.fillText(`${room.width}m × ${room.depth}m`, x + 8, y + depth - 10);
      }
      hitRegions.push({ nodeId: room.node_id, x, y, width, height: depth });
    });
    context.strokeStyle = "#d7efff";
    context.lineWidth = 5;
    storey.walls.forEach((wall) => {
      context.beginPath();
      context.moveTo(offsetX + wall.x1 * scale, offsetY + wall.y1 * scale);
      context.lineTo(offsetX + wall.x2 * scale, offsetY + wall.y2 * scale);
      context.stroke();
    });
  }

  function isoPoint(x, y, z, scale, originX, originY) {
    return {
      x: originX + (x - y) * scale * 0.72,
      y: originY + (x + y) * scale * 0.36 - z * scale,
    };
  }

  function polygon(points, fill, stroke) {
    context.beginPath();
    points.forEach((point, index) => {
      if (index) context.lineTo(point.x, point.y);
      else context.moveTo(point.x, point.y);
    });
    context.closePath();
    context.fillStyle = fill;
    context.fill();
    context.strokeStyle = stroke;
    context.lineWidth = 2;
    context.stroke();
  }

  function draw3D(storey, scale, originX, originY) {
    hitRegions.length = 0;
    const rooms = [...storey.rooms].sort(
      (a, b) => (a.x + a.y) - (b.x + b.y),
    );
    rooms.forEach((room) => {
      const height = 2.8;
      const base = [
        isoPoint(room.x, room.y, 0, scale, originX, originY),
        isoPoint(room.x + room.width, room.y, 0, scale, originX, originY),
        isoPoint(room.x + room.width, room.y + room.depth, 0, scale, originX, originY),
        isoPoint(room.x, room.y + room.depth, 0, scale, originX, originY),
      ];
      const top = [
        isoPoint(room.x, room.y, height, scale, originX, originY),
        isoPoint(room.x + room.width, room.y, height, scale, originX, originY),
        isoPoint(room.x + room.width, room.y + room.depth, height, scale, originX, originY),
        isoPoint(room.x, room.y + room.depth, height, scale, originX, originY),
      ];
      const selected = room.node_id === selectedNodeId;
      const topColor = roomColor(room.node_id, selected);
      polygon([base[0], base[1], top[1], top[0]], "rgba(22, 66, 88, .85)", "#6ab6dd");
      polygon([base[1], base[2], top[2], top[1]], "rgba(13, 48, 67, .9)", "#6ab6dd");
      polygon(top, topColor, selected ? "#ffffff" : "#9bdcff");
      context.fillStyle = "#eff9ff";
      context.font = `${Math.max(11, Math.round(scale * 0.44))}px system-ui`;
      context.fillText(room.label, top[0].x + 4, top[0].y - 6);
      if (dimensionsVisible) {
        context.fillStyle = "#a9d8f4";
        context.font = `${Math.max(9, Math.round(scale * 0.34))}px ui-monospace`;
        context.fillText(
          `${room.width}m × ${room.depth}m × ${height}m`,
          top[0].x + 4,
          top[0].y + 10,
        );
      }
      const xs = top.map((point) => point.x);
      const ys = top.concat(base).map((point) => point.y);
      hitRegions.push({
        nodeId: room.node_id,
        x: Math.min(...xs),
        y: Math.min(...ys),
        width: Math.max(...xs) - Math.min(...xs),
        height: Math.max(...ys) - Math.min(...ys),
      });
    });
  }

  async function render() {
    if (!scene || disposed) return "";
    resizeCanvas();
    const width = canvas.width;
    const height = canvas.height;
    context.fillStyle = "#071018";
    context.fillRect(0, 0, width, height);
    drawGrid(width, height);
    const storey = activeStorey();
    if (!storey) throw new Error("selected storey missing from scene");
    const scale = Math.min(
      width / (storey.width + 8),
      height / (storey.depth + 8),
    );
    if (activeView === "3D") {
      draw3D(storey, scale * 0.75, width * 0.48, height * 0.3);
    } else {
      draw2D(
        storey,
        scale,
        (width - storey.width * scale) / 2,
        (height - storey.depth * scale) / 2,
      );
    }
    emptyState.hidden = true;
    updateLabels();
    return ordinarySha256({
      scene_digest: identity.spatialSceneDigest,
      view: activeView,
      storey_id: selectedStorey,
      node_id: selectedNodeId,
      dimensions_visible: dimensionsVisible,
      canvas: [width, height],
      external_requests: externalRequests,
    });
  }

  function viewPayload(commandDigest, extra = {}) {
    return {
      command_message_digest: commandDigest,
      view: activeView,
      storey_id: selectedStorey,
      node_id: selectedNodeId,
      dimensions_visible: dimensionsVisible,
      ...extra,
    };
  }

  async function renderReceipt(commandDigest) {
    const frameDigest = await render();
    const storey = activeStorey();
    await sendEvent("RENDER_RECEIPT", {
      command_message_digest: commandDigest,
      frame_digest: frameDigest,
      renderer_kind: activeView === "3D"
        ? "CANVAS_ISOMETRIC_3D"
        : "CANVAS_FLOORPLAN_2D",
      node_count: storey.rooms.length + storey.walls.length,
      external_requests: externalRequests,
    });
  }

  async function deleteSessionDatabase() {
    if (!window.indexedDB) return true;
    return new Promise((resolve) => {
      const request = indexedDB.deleteDatabase(`aura-pascal-${identity.sessionId}`);
      request.onsuccess = () => resolve(true);
      request.onerror = () => resolve(false);
      request.onblocked = () => resolve(false);
    });
  }

  function requireActive(action) {
    if (state !== "ACTIVE") {
      throw new Error(`${action} not admitted outside ACTIVE`);
    }
  }

  async function loadArtifact(message) {
    if (state !== "READY") throw new Error("LOAD_ARTIFACT not admitted");
    const payload = message.payload || {};
    if (!payload.scene || !payload.artifact_manifest) {
      throw new Error("load payload incomplete");
    }
    if (payload.artifact_manifest.artifact_digest !== identity.pascalArtifactDigest) {
      throw new Error("artifact digest mismatch");
    }
    const nextScene = payload.scene;
    const nextManifest = payload.artifact_manifest;
    const nextStorey = nextManifest.storey_ids[0];
    const nextNode = nextManifest.root_node_id;
    const nextView = payload.initial_view === "3D" ? "3D" : "2D";
    const nextDimensions = payload.dimensions_visible !== false;
    if (!nextScene.storeys.some((item) => item.id === nextStorey)) {
      throw new Error("initial storey missing");
    }
    scene = nextScene;
    manifest = nextManifest;
    selectedStorey = nextStorey;
    selectedNodeId = nextNode;
    activeView = nextView;
    dimensionsVisible = nextDimensions;
    title.textContent = scene.label || "Pascal Construction Fixture";
    await render();
    await sendEvent("LOAD_RECEIPT", {
      command_message_digest: message.message_digest,
      loaded: true,
      view: activeView,
      storey_id: selectedStorey,
      node_id: selectedNodeId,
      dimensions_visible: dimensionsVisible,
      node_count: manifest.node_bindings.length,
      external_requests: externalRequests,
    });
    await renderReceipt(message.message_digest);
  }

  async function setView(message, view) {
    requireActive(message.action);
    activeView = view;
    await render();
    await sendEvent("VIEW_STATE", viewPayload(message.message_digest));
    await renderReceipt(message.message_digest);
  }

  async function setStorey(message) {
    requireActive(message.action);
    const storeyId = message.payload && message.payload.storey_id;
    if (!manifest.storey_ids.includes(storeyId)) throw new Error("unadmitted storey");
    const storeyBinding = manifest.node_bindings.find(
      (item) => item.storey_id === storeyId && item.selectable,
    );
    if (!storeyBinding) throw new Error("storey has no selectable node");
    selectedStorey = storeyId;
    selectedNodeId = storeyBinding.node_id;
    await render();
    await sendEvent("VIEW_STATE", viewPayload(message.message_digest));
    await renderReceipt(message.message_digest);
  }

  async function setSelection(message) {
    requireActive(message.action);
    const nodeId = message.payload && message.payload.node_id;
    const binding = manifest.node_bindings.find((item) => item.node_id === nodeId);
    if (!binding || !binding.selectable || binding.storey_id !== selectedStorey) {
      throw new Error("unadmitted or hidden selection");
    }
    selectedNodeId = binding.node_id;
    await render();
    await sendEvent("SELECTION_CHANGED", {
      command_message_digest: message.message_digest,
      node_id: selectedNodeId,
    });
    await renderReceipt(message.message_digest);
  }

  async function setDimensions(message) {
    requireActive(message.action);
    const visible = message.payload && message.payload.visible;
    if (typeof visible !== "boolean") {
      throw new Error("dimension visibility must be boolean");
    }
    dimensionsVisible = visible;
    await render();
    await sendEvent("VIEW_STATE", viewPayload(message.message_digest));
    await renderReceipt(message.message_digest);
  }

  async function resetCamera(message) {
    requireActive(message.action);
    await render();
    await sendEvent(
      "VIEW_STATE",
      viewPayload(message.message_digest, { camera_reset: true }),
    );
    await renderReceipt(message.message_digest);
  }

  function restoreNetworkGuards() {
    window.fetch = nativeFetch;
    if (NativeWebSocket) window.WebSocket = NativeWebSocket;
    if (nativeXhrOpen) window.XMLHttpRequest.prototype.open = nativeXhrOpen;
  }

  async function dissolve(message) {
    requireActive(message.action);
    const indexeddbDeleted = await deleteSessionDatabase();
    window.removeEventListener("message", onMessage);
    window.removeEventListener("resize", onResize);
    canvas.removeEventListener("click", onCanvasClick);
    canvas.removeEventListener("keydown", onCanvasKeyDown);
    restoreNetworkGuards();
    context.clearRect(0, 0, canvas.width, canvas.height);
    scene = null;
    manifest = null;
    hitRegions.length = 0;
    disposed = true;
    await sendEvent("DISSOLUTION_RECEIPT", {
      command_message_digest: message.message_digest,
      renderer_released: true,
      listeners_released: true,
      timers_released: true,
      buffers_cleared: true,
      indexeddb_deleted: indexeddbDeleted,
      network_guards_restored: true,
      external_requests: externalRequests,
    });
  }

  const commandHandlers = Object.freeze({
    LOAD_ARTIFACT: loadArtifact,
    SET_VIEW_2D: (message) => setView(message, "2D"),
    SET_VIEW_3D: (message) => setView(message, "3D"),
    SET_STOREY: setStorey,
    SET_SELECTION: setSelection,
    SET_DIMENSIONS: setDimensions,
    RESET_CAMERA: resetCamera,
    DISSOLVE: dissolve,
  });

  async function handleCommand(message) {
    if (!Object.prototype.hasOwnProperty.call(commandHandlers, message.action)) {
      throw new Error(`unknown parent action ${message.action}`);
    }
    const handler = commandHandlers[message.action];
    await handler(message);
  }

  async function onMessage(event) {
    const envelope = event.data;
    if (!envelope || envelope.type !== "AURA_PASCAL_BRIDGE_MESSAGE") return;
    const message = envelope.message;
    let validated = false;
    try {
      await validateParentMessage(message, event);
      validated = true;
      await handleCommand(message);
      seenNonces.add(message.nonce);
      expectedParentSequence += 1;
    } catch (error) {
      const payload = {
        error: String((error && error.message) || error),
        validated_command: validated,
      };
      if (validated) {
        seenNonces.add(message.nonce);
        expectedParentSequence += 1;
        payload.command_message_digest = message.message_digest;
      } else {
        payload.rejected_sequence = (
          message && Number.isInteger(message.sequence)
            ? message.sequence
            : expectedParentSequence
        );
      }
      await sendEvent("PRESENTATION_ERROR", payload);
    }
  }

  function selectRegionByNodeId(nodeId) {
    if (nodeId === selectedNodeId) return;
    parent.postMessage(
      {
        type: "AURA_PASCAL_SELECTION_REQUEST",
        session_id: identity.sessionId,
        node_id: nodeId,
      },
      identity.expectedOrigin,
    );
  }

  async function onCanvasClick(event) {
    if (state !== "ACTIVE" || !scene || disposed) return;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = (event.clientX - rect.left) * scaleX;
    const y = (event.clientY - rect.top) * scaleY;
    const hit = [...hitRegions].reverse().find(
      (item) => (
        x >= item.x
        && x <= item.x + item.width
        && y >= item.y
        && y <= item.y + item.height
      ),
    );
    if (hit) {
      selectRegionByNodeId(hit.nodeId);
    }
  }

  function onCanvasKeyDown(event) {
    if (state !== "ACTIVE" || !scene || disposed || hitRegions.length === 0) return;

    if (event.key === "Tab") {
      event.preventDefault();
      if (event.shiftKey) {
        focusedRegionIndex = focusedRegionIndex <= 0
          ? hitRegions.length - 1
          : focusedRegionIndex - 1;
      } else {
        focusedRegionIndex = (focusedRegionIndex + 1) % hitRegions.length;
      }
      highlightFocusedRegion();
      return;
    }

    if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
      event.preventDefault();
      focusedRegionIndex = focusedRegionIndex <= 0
        ? hitRegions.length - 1
        : focusedRegionIndex - 1;
      highlightFocusedRegion();
      return;
    }

    if (event.key === "ArrowDown" || event.key === "ArrowRight") {
      event.preventDefault();
      focusedRegionIndex = (focusedRegionIndex + 1) % hitRegions.length;
      highlightFocusedRegion();
      return;
    }

    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (focusedRegionIndex >= 0 && focusedRegionIndex < hitRegions.length) {
        selectRegionByNodeId(hitRegions[focusedRegionIndex].nodeId);
      }
      return;
    }
  }

  function highlightFocusedRegion() {
    if (focusedRegionIndex < 0 || focusedRegionIndex >= hitRegions.length) return;
    const region = hitRegions[focusedRegionIndex];
    context.strokeStyle = "#ffdd00";
    context.lineWidth = 3;
    context.setLineDash([8, 4]);
    context.strokeRect(region.x, region.y, region.width, region.height);
    context.setLineDash([]);
  }

  function onResize() {
    if (scene && !disposed) {
      render().catch(() => {});
    }
  }

  window.addEventListener("message", onMessage);
  canvas.addEventListener("click", onCanvasClick);
  canvas.addEventListener("keydown", onCanvasKeyDown);
  window.addEventListener("resize", onResize);

  (async () => {
    const initial = await stateBindingDigest();
    if (initial !== identity.initialStateBindingDigest) {
      throw new Error("initial state binding mismatch");
    }
    await sendEvent("READY", {
      renderer_kind: "LOCAL_CANVAS_PASCAL_COMPATIBILITY",
      external_requests: externalRequests,
      working_copy_only: true,
    });
  })().catch((error) => {
    disposed = true;
    window.removeEventListener("message", onMessage);
    window.removeEventListener("resize", onResize);
    canvas.removeEventListener("click", onCanvasClick);
    canvas.removeEventListener("keydown", onCanvasKeyDown);
    document.body.textContent = (
      `Pascal workbench failed closed: ${String((error && error.message) || error)}`
    );
  });
})();
