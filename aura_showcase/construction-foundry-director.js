(() => {
  "use strict";

  function shouldPaceAfterChapter(chapter) {
    return Boolean(chapter && chapter.consequential !== true);
  }

  function waitForP3View(activeView, options = {}) {
    if (typeof activeView !== "string" || !activeView.trim()) {
      return Promise.reject(new TypeError("activeView must be a non-empty string"));
    }
    const normalizedView = activeView.trim().toUpperCase();
    const getControl = options.getControl
      || ((view) => document.querySelector(`[data-construction-view="${view}"]`));
    const getStage = options.getStage
      || (() => document.getElementById("construction-decision-foundry"));
    const now = options.now || Date.now;
    const schedule = options.schedule || setTimeout;
    const timeoutMs = options.timeoutMs ?? 15000;
    const pollMs = options.pollMs ?? 40;
    if (
      typeof getControl !== "function"
      || typeof getStage !== "function"
      || typeof now !== "function"
      || typeof schedule !== "function"
      || !Number.isFinite(timeoutMs)
      || timeoutMs < 0
      || !Number.isFinite(pollMs)
      || pollMs < 0
    ) {
      return Promise.reject(new TypeError("P3 presentation wait contract is invalid"));
    }
    const expectedMode = normalizedView.toLowerCase().replaceAll("_", "-");
    const deadline = now() + timeoutMs;
    return new Promise((resolve, reject) => {
      const check = () => {
        const target = getControl(normalizedView);
        const stage = getStage();
        if (
          target?.getAttribute?.("aria-pressed") === "true"
          && stage?.dataset?.presentationMode === expectedMode
        ) {
          resolve({ activeView: normalizedView, presentationMode: expectedMode });
          return;
        }
        if (now() >= deadline) {
          reject(new Error(`P3 did not retain the exact ${normalizedView} presentation receipt`));
          return;
        }
        schedule(check, pollMs);
      };
      check();
    });
  }

  async function settleDirective(effect, render) {
    if (typeof effect !== "function" || typeof render !== "function") {
      throw new TypeError("directive effect and render must be functions");
    }
    try {
      return await effect();
    } finally {
      render();
    }
  }

  if (globalThis.__AURA_CONSTRUCTION_DIRECTOR_TEST__ === true) {
    globalThis.AuraConstructionDirectorTestHooks = Object.freeze({
      settleDirective,
      shouldPaceAfterChapter,
      waitForP3View,
    });
    return;
  }

  const root = document.getElementById("construction-foundry-director");
  if (!root) return;

  const statusNode = document.getElementById("construction-director-status");
  const currentNode = document.getElementById("construction-director-current");
  const notesNode = document.getElementById("construction-director-notes");
  const receiptNode = document.getElementById("construction-director-receipt");
  const chapterSelect = document.getElementById("construction-director-chapters");
  const controls = Array.from(root.querySelectorAll("[data-director-control]"));

  let projection = null;
  let identityHandle = "";
  let manifest = null;
  let session = null;
  let requestQueue = Promise.resolve();
  let playGeneration = 0;

  function text(value) {
    return String(value ?? "");
  }

  function exactIdentityBody() {
    if (!projection) throw new Error("P3 exact identities are not loaded");
    return {
      state_digest: projection.domain?.state_digest,
      runtime_packet_digest: projection.domain?.runtime_packet_digest,
      pascal_artifact_digest: projection.artifacts?.pascal_artifact_digest,
      coordinate_receipt_digest: projection.artifacts?.coordinate_receipt_digest,
      as_built_scene_digest: projection.artifacts?.as_built_scene_digest,
    };
  }

  async function jsonRequest(path, options = {}) {
    const response = await fetch(path, {
      credentials: "same-origin",
      cache: "no-store",
      ...options,
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok || result.ok !== true) {
      throw new Error(result.error || result.reason || `P4 request failed with ${response.status}`);
    }
    return result;
  }

  async function loadProjection() {
    const result = await jsonRequest("/api/construction/decision-lane");
    if (!result.projection) throw new Error("P3 projection was not returned");
    projection = result.projection;
  }

  async function loadIdentity() {
    const result = await jsonRequest("/api/showcase/live-repair/identity/current");
    if (typeof result.identity_handle !== "string" || !result.identity_handle) {
      throw new Error("P4 server did not issue a trusted identity handle");
    }
    identityHandle = result.identity_handle;
  }

  function chapterById(chapterId) {
    return manifest?.chapters?.find((chapter) => chapter.chapter_id === chapterId) || null;
  }

  function selectedChapter() {
    return chapterById(session?.selected_chapter_id) || chapterById(session?.next_chapter_id);
  }

  async function applyDirective(chapter, receipt = null) {
    const directive = receipt?.effect_receipt?.ui_directive || chapter?.ui_directive || {};
    try {
      if (directive.active_view) {
        const target = document.querySelector(`[data-construction-view="${directive.active_view}"]`);
        if (!target || target.disabled) {
          throw new Error(`P3 ${directive.active_view} control is unavailable`);
        }
        if (target.getAttribute("aria-pressed") !== "true") target.click();
        await waitForP3View(directive.active_view);
      }
      if (directive.panel === "coordination_candidates") {
        document.getElementById("construction-candidates")?.scrollIntoView({ block: "nearest" });
      }
    } catch (error) {
      // The session has already advanced on the server; render the current
      // state so the UI stays consistent before re-throwing the error.
      render();
      throw error;
    }
  }

  function renderChapter(chapter) {
    currentNode.replaceChildren();
    notesNode.replaceChildren();
    if (!chapter) {
      currentNode.textContent = "No chapter is selected.";
      return;
    }
    const heading = document.createElement("h3");
    heading.textContent = `${chapter.order + 1}. ${chapter.title}`;
    const route = document.createElement("p");
    route.textContent = `${chapter.from_state} -> ${chapter.to_state} · ${chapter.effect}`;
    const slots = document.createElement("code");
    slots.textContent = Object.entries(chapter.six_slot_packet)
      .map(([key, value]) => `${key}:${value}`)
      .join(" · ");
    currentNode.append(heading, route, slots);
    const list = document.createElement("ul");
    (chapter.presenter_notes || []).forEach((note) => {
      const item = document.createElement("li");
      item.textContent = text(note);
      list.append(item);
    });
    notesNode.append(list);
  }

  function renderChapterOptions() {
    if (!manifest || !session) return;
    if (chapterSelect.options.length !== manifest.chapters.length) {
      chapterSelect.replaceChildren();
      manifest.chapters.forEach((chapter) => {
        const option = document.createElement("option");
        option.value = chapter.chapter_id;
        option.textContent = `${chapter.order + 1}. ${chapter.title}`;
        chapterSelect.append(option);
      });
    }
    Array.from(chapterSelect.options).forEach((option) => {
      const chapter = chapterById(option.value);
      option.disabled = !chapter || chapter.order > session.executed_index;
    });
  }

  function render() {
    if (!manifest || !session) return;
    statusNode.textContent = session.dissolved
      ? "Tour dissolved. Restart creates a fresh exact confirmation and session."
      : `${session.current_state} · ${session.executed_index + 1}/${manifest.chapters.length} chapters proven${session.playing ? " · playing" : ""}`;
    const chapter = selectedChapter();
    renderChapter(chapter);
    renderChapterOptions();
    chapterSelect.value = session.selected_chapter_id || "";
    controls.forEach((button) => {
      const action = button.dataset.directorControl;
      if (action === "RESTART") {
        button.disabled = !session.dissolved;
      } else if (action === "RESYNC") {
        button.disabled = !session.p3_sync_pending;
      } else {
        button.disabled = false;
      }
    });
  }

  async function startSession() {
    await loadProjection();
    await loadIdentity();
    const result = await jsonRequest("/api/construction/director/session/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identity_handle: identityHandle, ...exactIdentityBody() }),
    });
    manifest = result.manifest;
    session = result.session;
    render();
  }

  async function syncP3Presentation(receipt) {
    // Runs the full prepare → project → confirm → acknowledge sequence
    // using jsonRequest for consistent error handling and response validation.
    // Under Trust Model A, the browser is the trusted presentation agent.
    const chapter = chapterById(receipt.chapter_id);
    const chapterId = receipt?.chapter_id || null;
    const activeView = chapter?.ui_directive?.active_view || null;

    // Step 1: Ask P4 to resolve the bilateral identity and return the
    // binding values needed for P3 presentation retention.
    const prepareResult = await jsonRequest(
      `/api/construction/director/session/${encodeURIComponent(session.session_id)}/prepare-p3-sync`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...exactIdentityBody(projection),
          identity_handle: identityHandle,
        }),
      },
    );

    // Step 2: Call P3 project with the resolved bindings + nonce.
    // P3 records the retained presentation state as a side effect.
    const projectResult = await jsonRequest(
      "/api/construction/decision-lane/project",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...exactIdentityBody(projection),
          identity_handle: identityHandle,
          identity_digest: prepareResult.identity_digest,
          active_view: prepareResult.active_view,
          director_session_id: prepareResult.director_session_id,
          director_receipt_digest: prepareResult.director_receipt_digest,
          chapter_id: prepareResult.chapter_id,
          sync_nonce: prepareResult.sync_nonce,
        }),
      },
    );

    const projectionDigest = projectResult.projection_digest || null;
    const presentationRevision = projectResult.presentation_revision || null;

    // Step 3: Call confirm-presentation to transition PROJECTED →
    // RENDER_CONFIRMED.  The render_capability is NOT accepted from
    // the request body — P3 looks it up from the server-side sync
    // record and uses it internally to bind the receipt_digest.
    const confirmResult = await jsonRequest(
      "/api/construction/decision-lane/confirm-presentation",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          director_session_id: prepareResult.director_session_id,
          director_receipt_digest: prepareResult.director_receipt_digest,
          chapter_id: prepareResult.chapter_id,
          active_view: prepareResult.active_view,
          identity_digest: prepareResult.identity_digest,
          projection_digest: projectionDigest,
          presentation_revision: presentationRevision,
        }),
      },
    );

    const presentationReceiptDigest = confirmResult.presentation_receipt_digest || null;

    // Step 4: Request P4 acknowledgement — validates the confirmed
    // P3 record via lookup only (does NOT create it).
    const ackResult = await jsonRequest(
      `/api/construction/director/session/${encodeURIComponent(session.session_id)}/ack-p3-sync`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...exactIdentityBody(projection),
          identity_handle: identityHandle,
          presentation_receipt: {
            chapter_id: prepareResult.chapter_id,
            active_view: prepareResult.active_view,
            receipt_digest: presentationReceiptDigest,
          },
        }),
      },
    );

    if (ackResult.session) {
      session = ackResult.session;
    }
  }

  async function control(action, chapterId = "") {
    if (!session) throw new Error("P4 Director session is not active");
    const result = await jsonRequest(
      `/api/construction/director/session/${encodeURIComponent(session.session_id)}/control`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          control: action,
          chapter_id: chapterId || undefined,
          identity_handle: identityHandle,
          ...exactIdentityBody(),
        }),
      },
    );
    if (result.restarted_from_session_id) {
      identityHandle = result.identity_summary.identity_handle;
      manifest = result.manifest;
      session = result.session;
      receiptNode.textContent = "Fresh exact identity and confirmation issued for restart.";
      render();
      return result;
    }
    session = result.session;
    let syncFailed = false;
    let syncError = "";
    await settleDirective(async () => {
      if (result.receipt) {
        receiptNode.textContent = JSON.stringify(result.receipt, null, 2);
        lastCommittedReceipt = result.receipt;
        const chapter = chapterById(result.receipt.chapter_id);
        await applyDirective(chapter, result.receipt);
        // Acknowledge P3 sync to the server so progression is unblocked.
        if (result.session && result.session.p3_sync_pending) {
          await syncP3Presentation(result.receipt);
        }
      } else {
        await applyDirective(selectedChapter());
      }
    }, render).catch((err) => { syncFailed = true; syncError = String(err?.message || err); });
    if (syncFailed) {
      statusNode.textContent = `P3 presentation sync failed: ${syncError || "unknown error"}. Click RESYNC to retry without losing progress.`;
    }
    return result;
  }

  let lastCommittedReceipt = null;

  async function resync() {
    if (!session) throw new Error("P4 Director session is not active");
    if (!session.p3_sync_pending) {
      statusNode.textContent = "No pending P3 sync — resync not needed.";
      return;
    }
    if (!lastCommittedReceipt) {
      throw new Error("No committed receipt available to re-sync against");
    }
    statusNode.textContent = "Re-syncing P3 presentation…";
    let syncError = "";
    await settleDirective(async () => {
      await syncP3Presentation(lastCommittedReceipt);
    }, render).catch((err) => { syncError = String(err?.message || err); });
    if (syncError) {
      statusNode.textContent = `P3 re-sync failed: ${syncError}. Click RESYNC to retry.`;
    } else {
      statusNode.textContent = "P3 presentation sync completed.";
    }
  }

  async function play() {
    const generation = ++playGeneration;
    await control("PLAY");
    while (generation === playGeneration && session && !session.dissolved) {
      // Halt autoplay if P3 sync is pending — the sync-failure message
      // in the status node must not be clobbered by a doomed NEXT.
      if (session.p3_sync_pending) {
        playGeneration += 1;  // stop the loop
        break;
      }
      const result = await control("NEXT");
      // Check again after control returns — a presentation chapter may
      // have set p3_sync_pending during this call.
      if (session && session.p3_sync_pending) {
        playGeneration += 1;
        break;
      }
      const chapter = result.receipt ? chapterById(result.receipt.chapter_id) : null;
      if (shouldPaceAfterChapter(chapter)) {
        await new Promise((resolve) => setTimeout(resolve, 650));
      }
    }
  }

  function enqueue(work) {
    requestQueue = requestQueue
      .then(work)
      .catch((error) => {
        playGeneration += 1;
        statusNode.textContent = `P4 stopped safely: ${error.message}`;
        receiptNode.textContent = JSON.stringify({ ok: false, error: error.message }, null, 2);
      });
    return requestQueue;
  }

  controls.forEach((button) => {
    button.addEventListener("click", () => {
      const action = button.dataset.directorControl;
      if (action === "PLAY") enqueue(play);
      else if (action === "PAUSE") {
        playGeneration += 1;
        enqueue(() => control("PAUSE"));
      } else if (action === "RESYNC") {
        playGeneration += 1;
        enqueue(resync);
      } else {
        playGeneration += 1;
        enqueue(() => control(action));
      }
    });
  });

  chapterSelect.addEventListener("change", () => {
    playGeneration += 1;
    enqueue(() => control("JUMP", chapterSelect.value));
  });

  enqueue(async () => {
    const status = await jsonRequest("/api/construction/director/status");
    if (status.available !== true) throw new Error(status.reason || "P4 Director is unavailable");
    await startSession();
  });
})();
