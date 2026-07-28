"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");
const { PNG } = require("pngjs");

const BASE_URL = process.env.AURA_CONSTRUCTION_DEMO_URL || "http://127.0.0.1:8767/demo/construction";
const OUTPUT_DIR = process.env.AURA_RUNTIME_EVIDENCE_DIR || "/tmp/aura-construction-runtime";

function ensureDirectory(directory) {
  fs.mkdirSync(directory, { recursive: true });
}

async function snapshot(page, name) {
  const target = path.join(OUTPUT_DIR, `${name}.png`);
  await page.screenshot({ path: target, fullPage: true });
  return target;
}

function analyzePng(buffer) {
  const image = PNG.sync.read(buffer);
  let opaquePixels = 0;
  let chromaticPixels = 0;
  for (let offset = 0; offset < image.data.length; offset += 4) {
    const red = image.data[offset];
    const green = image.data[offset + 1];
    const blue = image.data[offset + 2];
    const alpha = image.data[offset + 3];
    if (alpha === 0) continue;
    opaquePixels += 1;
    const maximum = Math.max(red, green, blue);
    const minimum = Math.min(red, green, blue);
    if (maximum >= 45 && maximum - minimum >= 18) chromaticPixels += 1;
  }
  return {
    width: image.width,
    height: image.height,
    opaquePixels,
    chromaticPixels,
    chromaticRatio: opaquePixels ? chromaticPixels / opaquePixels : 0,
  };
}

async function snapshotCanvas(page, name) {
  const target = path.join(OUTPUT_DIR, `${name}.png`);
  // Capture the complete user-visible presentation composite: WebGL canvas,
  // SVG mesh overlay, HUD, and camera controls.
  const buffer = await page.locator(".viewport-wrap").screenshot({ path: target });
  return { path: target, ...analyzePng(buffer) };
}

async function inspectPage(page, label) {
  return page.evaluate((pageLabel) => {
    const modeButtons = [...document.querySelectorAll("button[data-mode]")].map((button) => ({
      mode: button.dataset.mode,
      disabled: button.disabled,
      active: button.classList.contains("active"),
      title: button.title,
    }));
    const canvas = document.querySelector("#construction-canvas");
    const gl = canvas?.getContext?.("webgl2");
    const sampleWebGl = () => {
      if (!canvas || !gl || gl.isContextLost?.()) {
        return { samples: 0, nonBackgroundSamples: 0, error: null };
      }
      const pixel = new Uint8Array(4);
      const columns = 32;
      const rows = 18;
      let samples = 0;
      let nonBackgroundSamples = 0;
      for (let row = 0; row < rows; row += 1) {
        for (let column = 0; column < columns; column += 1) {
          const x = Math.min(canvas.width - 1, Math.floor(((column + 0.5) / columns) * canvas.width));
          const y = Math.min(canvas.height - 1, Math.floor(((row + 0.5) / rows) * canvas.height));
          gl.readPixels(x, y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixel);
          samples += 1;
          const total = pixel[0] + pixel[1] + pixel[2];
          const spread = Math.max(pixel[0], pixel[1], pixel[2]) - Math.min(pixel[0], pixel[1], pixel[2]);
          if (pixel[3] > 0 && (total > 70 || spread > 20)) nonBackgroundSamples += 1;
        }
      }
      return {
        samples,
        nonBackgroundSamples,
        error: gl.getError?.() ?? null,
      };
    };
    return {
      label: pageLabel,
      sceneState: document.querySelector("#scene-state")?.textContent || null,
      tourStatus: document.querySelector("#tour-status")?.textContent || null,
      selectedCard: document.querySelector("#selected-card")?.textContent || null,
      intentLine: document.querySelector("#intent-line")?.textContent || null,
      storeyButtons: document.querySelectorAll("#storey-list button").length,
      modeButtons,
      canvas: canvas
        ? {
            clientWidth: canvas.clientWidth,
            clientHeight: canvas.clientHeight,
            width: canvas.width,
            height: canvas.height,
          }
        : null,
      webgl2Available: Boolean(gl),
      webglContextLost: Boolean(gl?.isContextLost?.()),
      visualEvidence: {
        webgl: sampleWebGl(),
        wireframeGroups: document.querySelectorAll(
          "#construction-mesh-overlay .construction-wireframe-storey",
        ).length,
        wireframeLines: document.querySelectorAll(
          "#construction-mesh-overlay .construction-wireframe-storey line",
        ).length,
      },
      bodyText: document.body.innerText.slice(0, 6000),
    };
  }, label);
}

async function waitForInitialState(page) {
  await page.waitForFunction(() => {
    const value = document.querySelector("#scene-state")?.textContent || "";
    return value !== "Loading" && value.length > 0;
  }, null, { timeout: 30_000 });
}

function assertVisiblePresentation(receipt, mode) {
  const screenshot = receipt.canvasScreenshot;
  if (
    !screenshot ||
    screenshot.width < 1 ||
    screenshot.height < 1 ||
    screenshot.chromaticPixels < 25
  ) {
    throw new Error(`${mode} presentation produced no verified user-visible canvas pixels`);
  }
  if (["MESH", "HYBRID"].includes(mode) && receipt.visualEvidence.wireframeLines < 12) {
    throw new Error(`${mode} presentation produced no verified wireframe geometry`);
  }
}

async function exerciseManualControls(page, receipts) {
  const controls = [
    "#orbit-left",
    "#orbit-right",
    "#zoom-in",
    "#zoom-out",
    "#explode",
    "#collapse",
    "#show-all",
  ];
  for (const selector of controls) {
    await page.click(selector);
    await page.waitForTimeout(100);
    receipts.push(await inspectPage(page, `after-${selector.slice(1)}`));
  }
  const firstStorey = page.locator("#storey-list button").first();
  if ((await firstStorey.count()) < 1) {
    throw new Error("Construction browser rendered no storey controls");
  }
  await firstStorey.click();
  await page.waitForTimeout(100);
  receipts.push(await inspectPage(page, "after-first-storey"));
}

async function exerciseRepresentationControls(page, receipts) {
  for (const mode of ["MESH", "SPLATS", "HYBRID"]) {
    const button = page.locator(`button[data-mode="${mode}"]`);
    const disabled = await button.isDisabled();
    receipts.push({ label: `mode-${mode}-before-click`, disabled });
    if (disabled) {
      throw new Error(`${mode} representation control is disabled`);
    }
    await button.click();
    await page.waitForTimeout(150);
    const receipt = await inspectPage(page, `after-mode-${mode}`);
    receipt.canvasScreenshot = await snapshotCanvas(page, `mode-${mode}-canvas`);
    receipts.push(receipt);
    if (!String(receipt.sceneState || "").startsWith(`${mode} · PRESENTED`)) {
      throw new Error(`${mode} representation did not become active`);
    }
    assertVisiblePresentation(receipt, mode);
  }
}

async function exerciseBilateralRendererContract(page) {
  return page.evaluate(async () => {
    const GAUSSIAN_REPRESENTATION_DIGEST =
      "5e4620fc5ea92315714eaf3bfe0247f4a18f6ed51997efb9c5c389d20536d7b7";
    const [
      { ConstructionSceneRenderer },
      { ConstructionMeshPass },
      { ConstructionOverlayPass },
      { GaussianRenderer },
      { RENDERER_STATES, validateRenderPlan, validateSceneProjection },
    ] = await Promise.all([
      import("/aura_spatial_web/construction_scene_renderer.js"),
      import("/aura_spatial_web/construction_mesh_pass.js"),
      import("/aura_spatial_web/construction_overlay_pass.js"),
      import("/aura_spatial_web/gaussian_renderer.js"),
      import("/aura_spatial_web/renderer_adapter.js"),
    ]);

    const response = await fetch("/api/construction-demo", { cache: "no-store" });
    if (!response.ok) throw new Error(`bilateral packet failed: ${response.status}`);
    const packet = await response.json();
    const sourceSnapshot = JSON.stringify(packet.scene);

    const gaussianGeometry = () => {
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
    };
    const meshPayloads = (scene) =>
      scene.assets
        .filter((asset) => asset.asset_type === "MESH")
        .map((asset) => ({
          asset_id: asset.asset_id,
          source_digest: asset.content_digest.split(":", 2).at(-1),
          decoded_byte_length: Math.max(1, asset.byte_length),
          resource: Object.freeze({ asset_id: asset.asset_id }),
        }));
    const gaussianPayloads = (scene, { staleDigest = false } = {}) => {
      const geometry = gaussianGeometry();
      return scene.assets
        .filter((asset) => asset.asset_type === "GAUSSIAN_SPLAT")
        .map((asset, index) => ({
          asset_id: asset.asset_id,
          source_digest:
            staleDigest && index === 0
              ? "0".repeat(64)
              : asset.content_digest.split(":", 2).at(-1),
          derived_asset_digest: asset.metadata.import_receipt_digest,
          representation_digest: GAUSSIAN_REPRESENTATION_DIGEST,
          sh_degree: 0,
          color_space: "SPZ_INTERNAL_WIDE_RGB",
          ...geometry,
        }));
    };

    class ProbePresentationRenderer {
      constructor({ initializeDelayMs = 0, pickEntityId = null } = {}) {
        this.kind = "HEADLESS";
        this.state = RENDERER_STATES.NEW;
        this.camera = { yaw: 0, pitch: 0, distance: 12, target: [0, 0, 0] };
        this.initializeDelayMs = initializeDelayMs;
        this.pickEntityId = pickEntityId;
        this.disposed = 0;
        this.scene = null;
        this.plan = null;
      }

      async initialize(scenePayload, planPayload, { signal } = {}) {
        if (this.initializeDelayMs) {
          await new Promise((resolve, reject) => {
            const timeoutId = setTimeout(resolve, this.initializeDelayMs);
            signal?.addEventListener(
              "abort",
              () => {
                clearTimeout(timeoutId);
                reject(new Error("Probe presentation initialization cancelled"));
              },
              { once: true },
            );
          });
        }
        if (signal?.aborted) throw new Error("Probe presentation initialization cancelled");
        this.scene = validateSceneProjection(scenePayload);
        this.plan = validateRenderPlan(planPayload, this.scene);
        this.state = RENDERER_STATES.INITIALIZED;
        return this.status();
      }

      async present() {
        this.state = RENDERER_STATES.PRESENTED;
        return Object.freeze({
          renderer: this.kind,
          outcome: "PRESENTED",
          scene_digest: this.scene.scene_digest,
          render_plan_digest: this.plan.render_plan_digest,
        });
      }

      pick() {
        return this.pickEntityId;
      }

      orbit(deltaYaw, deltaPitch) {
        this.camera.yaw += deltaYaw;
        this.camera.pitch += deltaPitch;
      }

      zoom(delta) {
        this.camera.distance += delta;
      }

      async dispose() {
        if (this.state === RENDERER_STATES.DISPOSED) return this.status();
        this.disposed += 1;
        this.scene = null;
        this.plan = null;
        this.state = RENDERER_STATES.DISPOSED;
        return this.status();
      }

      status() {
        return Object.freeze({ renderer: this.kind, state: this.state });
      }
    }

    const createRenderer = async ({
      scene = packet.scene,
      plan = packet.render_plan,
      initializeDelayMs = 0,
      pickEntityId = null,
      signal = undefined,
      staleGaussianDigest = false,
      restoreState = null,
      initializationTimeoutMs = 60_000,
    } = {}) => {
      const presentation = new ProbePresentationRenderer({
        initializeDelayMs,
        pickEntityId,
      });
      const renderer = new ConstructionSceneRenderer({
        presentationRenderer: presentation,
        meshPass: new ConstructionMeshPass({
          drawMeshPass: async () => () => {},
        }),
        overlayPass: new ConstructionOverlayPass({
          drawOverlayPass: async () => () => {},
        }),
        gaussianRenderer: new GaussianRenderer({
          presentationRenderer: presentation,
          drawGaussianPass: async () => () => {},
          now: () => 0,
        }),
        initializationTimeoutMs,
      });
      await renderer.initialize(scene, plan, {
        meshPayloads: meshPayloads(scene),
        gaussianPayloads: gaussianPayloads(scene, {
          staleDigest: staleGaussianDigest,
        }),
        signal,
        restoreState,
      });
      return { renderer, presentation };
    };

    const storeyFrames = packet.scene.entities
      .filter((item) => item.entity_type === "ASSET_INSTANCE")
      .map((item) => item.frame_id)
      .filter((value, index, values) => values.indexOf(value) === index)
      .sort();
    const storeyWithIssue = storeyFrames.find((frameId) => {
      const blueprintCount = packet.scene.assets.filter(
        (asset) => asset.asset_type === "PLANE" && asset.frame_id === frameId,
      ).length;
      const issueCount = packet.scene.entities.filter(
        (entity) =>
          entity.frame_id === frameId &&
          entity.entity_type !== "ASSET_INSTANCE" &&
          entity.selectable !== false,
      ).length;
      return blueprintCount === 1 && issueCount > 0;
    });
    const otherStorey = storeyFrames.find((frameId) => frameId !== storeyWithIssue);
    if (!storeyWithIssue || !otherStorey) {
      throw new Error("bilateral proof requires two admitted storeys and one selectable issue");
    }
    const selectedIssue = packet.scene.entities.find(
      (entity) =>
        entity.frame_id === storeyWithIssue &&
        entity.entity_type !== "ASSET_INSTANCE" &&
        entity.selectable !== false,
    );
    const hiddenStoreyEntity = packet.scene.entities.find(
      (entity) =>
        entity.frame_id === otherStorey &&
        entity.entity_type === "ASSET_INSTANCE" &&
        entity.selectable !== false,
    );
    if (!selectedIssue || !hiddenStoreyEntity) {
      throw new Error("bilateral proof requires one visible issue and one hidden storey");
    }

    const primary = await createRenderer({ pickEntityId: hiddenStoreyEntity.entity_id });
    const { renderer, presentation } = primary;
    renderer.isolateStorey(storeyWithIssue);
    renderer.focusEntity(selectedIssue.entity_id);
    const initialInspector = renderer.inspectorState();
    const modeReceipts = [];
    for (const mode of ["MESH", "SPLATS", "HYBRID", "MESH", "HYBRID"]) {
      renderer.setRepresentationMode(mode);
      modeReceipts.push(await renderer.present());
    }
    const inspectorStable = modeReceipts.every(
      (receipt) => JSON.stringify(receipt.inspector_state) === JSON.stringify(initialInspector),
    );
    const selectedStoreyStable = modeReceipts.every(
      (receipt) => receipt.selected_storey_frame_id === storeyWithIssue,
    );
    const selectedIssueStable = modeReceipts.every(
      (receipt) => receipt.selected_entity_id === selectedIssue.entity_id,
    );
    const blueprintStable = modeReceipts.every(
      (receipt) =>
        receipt.inspector_state.blueprint?.asset_id === initialInspector.blueprint?.asset_id &&
        receipt.inspector_state.blueprint?.content_digest ===
          initialInspector.blueprint?.content_digest,
    );
    const annotationSetStable = modeReceipts.every(
      (receipt) =>
        JSON.stringify(receipt.inspector_state.annotation_entity_ids) ===
        JSON.stringify(initialInspector.annotation_entity_ids),
    );
    const representationSequenceStable =
      modeReceipts.map((receipt) => receipt.representation_mode).join(",") ===
      "MESH,SPLATS,HYBRID,MESH,HYBRID";

    renderer.showAllStoreys();
    const showAllReceipt = await renderer.present();
    const showAllRetainedSelection =
      showAllReceipt.selected_storey_frame_id === storeyWithIssue &&
      showAllReceipt.selected_entity_id === selectedIssue.entity_id;
    renderer.isolateStorey(storeyWithIssue);
    const hiddenPick = renderer.pick(0, 0);
    const hiddenStoreyPickRejected =
      hiddenPick === null && renderer.status().selected_entity_id === selectedIssue.entity_id;
    let hiddenStoreyFocusRejected = false;
    try {
      renderer.focusEntity(hiddenStoreyEntity.entity_id);
    } catch (error) {
      hiddenStoreyFocusRejected = String(error?.message || error).includes(
        "hidden Construction scene entity is not selectable",
      );
    }

    let missingBlueprintExplicit = false;
    const missingBlueprintPresentation = new ProbePresentationRenderer();
    const missingBlueprintRenderer = new ConstructionSceneRenderer({
      presentationRenderer: missingBlueprintPresentation,
      meshPass: new ConstructionMeshPass({ drawMeshPass: async () => () => {} }),
      overlayPass: new ConstructionOverlayPass(),
    });
    const missingBlueprintScene = {
      ...packet.scene,
      assets: [
        ...packet.scene.assets.filter(
          (asset) => !(asset.asset_type === "PLANE" && asset.frame_id === otherStorey),
        ),
        {
          ...packet.scene.assets.find(
            (asset) =>
              asset.asset_type === "PLANE" &&
              asset.frame_id === storeyWithIssue,
          ),
          asset_id: "asset:unrelated-plan",
          frame_id: otherStorey,
        },
      ],
    };
    try {
      await missingBlueprintRenderer.initialize(
        missingBlueprintScene,
        packet.render_plan,
        {
          meshPayloads: meshPayloads(missingBlueprintScene),
          gaussianPayloads: gaussianPayloads(missingBlueprintScene),
        },
      );
    } catch (error) {
      missingBlueprintExplicit = String(error?.message || error).includes(
        "requires exactly one canonically bound blueprint; status MISSING, found 0",
      );
      if (!missingBlueprintExplicit) {
        throw new Error(
          `missing-blueprint fixture failed outside the canonical binding check: ${String(
            error?.message || error,
          )}`,
        );
      }
    }
    if (!missingBlueprintExplicit) {
      throw new Error("missing-blueprint fixture unexpectedly initialized");
    }

    let ambiguousBlueprintExplicit = false;
    const canonicalBlueprint = packet.scene.assets.find(
      (asset) =>
        asset.asset_type === "PLANE" &&
        asset.frame_id === otherStorey,
    );
    if (!canonicalBlueprint) {
      throw new Error(
        "bilateral proof requires a canonically bound blueprint on the hidden storey",
      );
    }
    const ambiguousBlueprintId = "asset:ambiguous-plan";
    const ambiguousBlueprintRenderer = new ConstructionSceneRenderer({
      presentationRenderer: new ProbePresentationRenderer(),
      meshPass: new ConstructionMeshPass({ drawMeshPass: async () => () => {} }),
      overlayPass: new ConstructionOverlayPass(),
    });
    const validatedScene = validateSceneProjection(packet.scene);
    ambiguousBlueprintRenderer.scene = {
      ...validatedScene,
      assets: [
        ...validatedScene.assets,
        Object.freeze({
          ...canonicalBlueprint,
          asset_id: ambiguousBlueprintId,
        }),
      ],
      entities: validatedScene.entities.map((entity) =>
        entity.entity_type === "ASSET_INSTANCE" && entity.frame_id === otherStorey
          ? Object.freeze({
              ...entity,
              asset_ids: Object.freeze([...entity.asset_ids, ambiguousBlueprintId].sort()),
            })
          : entity,
      ),
    };
    ambiguousBlueprintRenderer.storeyFrames = Object.freeze([...storeyFrames]);
    ambiguousBlueprintRenderer.selectedStoreyFrameId = otherStorey;
    try {
      ambiguousBlueprintRenderer.isolateStorey(otherStorey);
    } catch (error) {
      const inspector = ambiguousBlueprintRenderer.inspectorState();
      const status = ambiguousBlueprintRenderer.status();
      ambiguousBlueprintExplicit =
        String(error?.message || error).includes(
          "requires exactly one canonically bound blueprint; status AMBIGUOUS, found 2",
        ) &&
        inspector.blueprint === null &&
        inspector.blueprint_resolution.status === "AMBIGUOUS" &&
        status.inspector_state.blueprint_resolution.status === "AMBIGUOUS";
    }

    let invalidDigestExplicit = false;
    try {
      await createRenderer({ staleGaussianDigest: true });
    } catch (error) {
      invalidDigestExplicit = String(error?.message || error).includes(
        "source digest is stale or ambiguous",
      );
    }

    let preInitializationSwitchRejected = false;
    let delayedAssetBounded = false;
    const delayedPresentation = new ProbePresentationRenderer({ initializeDelayMs: 100 });
    const delayedRenderer = new ConstructionSceneRenderer({
      presentationRenderer: delayedPresentation,
      meshPass: new ConstructionMeshPass({ drawMeshPass: async () => () => {} }),
      overlayPass: new ConstructionOverlayPass(),
      gaussianRenderer: new GaussianRenderer({
        presentationRenderer: delayedPresentation,
        drawGaussianPass: async () => () => {},
        now: () => 0,
      }),
      initializationTimeoutMs: 20,
    });
    const delayedStart = performance.now();
    const delayedInitialization = delayedRenderer.initialize(
      packet.scene,
      packet.render_plan,
      {
        meshPayloads: meshPayloads(packet.scene),
        gaussianPayloads: gaussianPayloads(packet.scene),
      },
    );
    try {
      delayedRenderer.setRepresentationMode("MESH");
    } catch (error) {
      preInitializationSwitchRejected = String(error?.message || error).includes(
        "cannot change before initialization completes",
      );
    }
    try {
      await delayedInitialization;
    } catch (error) {
      delayedAssetBounded =
        String(error?.message || error).includes("timed out after 20 ms") &&
        delayedRenderer.status().state === RENDERER_STATES.LOST &&
        delayedPresentation.disposed === 1 &&
        performance.now() - delayedStart < 500;
    }

    let cancellationExplicit = false;
    let cancellationCleanupTerminal = false;
    const cancellation = await createRenderer();
    const controller = new AbortController();
    controller.abort();
    try {
      await cancellation.renderer.present({ signal: controller.signal });
    } catch (error) {
      cancellationExplicit = String(error?.message || error).includes("cancelled");
    }
    const cancellationStatus = await cancellation.renderer.dispose();
    cancellationCleanupTerminal = cancellationStatus.state === RENDERER_STATES.DISPOSED;

    const deviceLoss = await createRenderer();
    const contextLossTarget = new EventTarget();
    deviceLoss.renderer.bindContextLoss(contextLossTarget);
    const contextLossEvent = new Event("webglcontextlost", { cancelable: true });
    contextLossTarget.dispatchEvent(contextLossEvent);
    await new Promise((resolve) => setTimeout(resolve, 0));
    const deviceLossStatus = deviceLoss.renderer.status();
    const deviceLossTerminal =
      contextLossEvent.defaultPrevented &&
      deviceLossStatus.state === RENDERER_STATES.LOST;
    const deviceLossDisposeStatus = await deviceLoss.renderer.dispose();
    const deviceLossCleanupTerminal =
      [RENDERER_STATES.DISPOSED, RENDERER_STATES.LOST].includes(
        deviceLossDisposeStatus.state,
      );

    const continuityReceipt = renderer.continuityState();
    const primaryDisposeStatus = await renderer.dispose();
    const dissolveTerminal =
      primaryDisposeStatus.state === RENDERER_STATES.DISPOSED &&
      primaryDisposeStatus.selected_storey_frame_id === null &&
      primaryDisposeStatus.selected_entity_id === null &&
      presentation.disposed === 1;

    const relaunched = await createRenderer({ restoreState: continuityReceipt });
    const restoredStatus = relaunched.renderer.status();
    const relaunchReceipt = await relaunched.renderer.present();
    const relaunchSucceeded =
      restoredStatus.selected_storey_frame_id === storeyWithIssue &&
      restoredStatus.selected_entity_id === selectedIssue.entity_id &&
      restoredStatus.representation_mode === "HYBRID" &&
      relaunchReceipt.outcome === "PRESENTED" &&
      relaunchReceipt.selected_storey_frame_id === storeyWithIssue &&
      relaunchReceipt.inspector_state.blueprint?.asset_id ===
        initialInspector.blueprint?.asset_id;
    await relaunched.renderer.dispose();

    const sourceGeometryUnchanged = JSON.stringify(packet.scene) === sourceSnapshot;
    const authorityReceipts = [...modeReceipts, showAllReceipt, relaunchReceipt];
    const physicalWorkAuthorized = authorityReceipts.some(
      (receipt) => receipt.physical_work_authority !== false,
    );
    const professionalAuthority = authorityReceipts.some(
      (receipt) => receipt.professional_authority !== false,
    );
    const automaticMerge = authorityReceipts.some(
      (receipt) => receipt.automatic_merge !== false,
    );
    const productionMutation = authorityReceipts.some(
      (receipt) => receipt.production_mutation !== false,
    );
    const authorityDenialsObserved =
      !physicalWorkAuthorized &&
      !professionalAuthority &&
      !automaticMerge &&
      !productionMutation;
    const conditions = {
      inspectorStable,
      selectedStoreyStable,
      selectedIssueStable,
      blueprintStable,
      annotationSetStable,
      representationSequenceStable,
      showAllRetainedSelection,
      hiddenStoreyPickRejected,
      hiddenStoreyFocusRejected,
      missingBlueprintExplicit,
      ambiguousBlueprintExplicit,
      invalidDigestExplicit,
      preInitializationSwitchRejected,
      delayedAssetBounded,
      cancellationExplicit,
      cancellationCleanupTerminal,
      deviceLossTerminal,
      deviceLossCleanupTerminal,
      dissolveTerminal,
      relaunchSucceeded,
      sourceGeometryUnchanged,
      authorityDenialsObserved,
    };
    return Object.freeze({
      version: "AURA_CONSTRUCTION_BILATERAL_BROWSER_PROOF_V1",
      ok: Object.values(conditions).every(Boolean),
      selectedStoreyFrameId: storeyWithIssue,
      selectedIssueEntityId: selectedIssue.entity_id,
      hiddenStoreyFrameId: otherStorey,
      hiddenStoreyEntityId: hiddenStoreyEntity.entity_id,
      blueprintAssetId: initialInspector.blueprint?.asset_id || null,
      blueprintDigest: initialInspector.blueprint?.content_digest || null,
      annotationEntityIds: initialInspector.annotation_entity_ids,
      modeSequence: modeReceipts.map((receipt) => receipt.representation_mode),
      ...conditions,
      physicalWorkAuthorized,
      professionalAuthority,
      automaticMerge,
      productionMutation,
      humanReviewRequired: true,
    });
  });
}

async function exerciseTour(page, receipts) {
  await page.click("#play-tour");
  await page.waitForFunction(() => {
    const text = document.querySelector("#tour-status")?.textContent || "";
    return text === "Tour complete" || text.includes("Presentation stopped") || text.includes("Renderer released");
  }, null, { timeout: 90_000 });
  receipts.push(await inspectPage(page, "after-tour"));
}

async function main() {
  ensureDirectory(OUTPUT_DIR);
  const consoleMessages = [];
  const pageErrors = [];
  const requestFailures = [];
  const receipts = [];
  let bilateral = {
    version: "AURA_CONSTRUCTION_BILATERAL_BROWSER_PROOF_V1",
    ok: false,
    error: "bilateral proof not run",
    productionMutation: false,
    automaticMerge: false,
    physicalWorkAuthorized: false,
    professionalAuthority: false,
  };

  let browser = null;
  let page = null;
  let exitCode = 0;
  try {
    browser = await chromium.launch({
      headless: true,
      args: [
        "--enable-webgl",
        "--ignore-gpu-blocklist",
        "--use-gl=swiftshader",
        "--enable-unsafe-swiftshader",
        "--disable-gpu-sandbox",
      ],
    });
    const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
    page = await context.newPage();
    page.on("console", (message) => consoleMessages.push({ type: message.type(), text: message.text() }));
    page.on("pageerror", (error) => pageErrors.push({ name: error.name, message: error.message, stack: error.stack }));
    page.on("requestfailed", (request) => requestFailures.push({ url: request.url(), failure: request.failure() }));

    await page.goto(BASE_URL, { waitUntil: "networkidle", timeout: 45_000 });
    await waitForInitialState(page);
    const initial = await inspectPage(page, "initial");
    receipts.push(initial);
    if (!initial.webgl2Available || initial.webglContextLost) {
      throw new Error("Construction browser requires an intact WebGL2 context");
    }
    if (!initial.canvas || initial.canvas.width < 1 || initial.canvas.height < 1) {
      throw new Error("Construction browser canvas has invalid dimensions");
    }
    if (initial.storeyButtons < 1) {
      throw new Error("Construction browser rendered no storey controls");
    }
    initial.canvasScreenshot = await snapshotCanvas(page, "initial-canvas");
    assertVisiblePresentation(initial, "HYBRID");
    await snapshot(page, "initial");

    await exerciseManualControls(page, receipts);
    await exerciseRepresentationControls(page, receipts);
    try {
      bilateral = await exerciseBilateralRendererContract(page);
      receipts.push({
        label: "bilateral-renderer-contract",
        ok: bilateral.ok,
        selectedStoreyFrameId: bilateral.selectedStoreyFrameId,
        selectedIssueEntityId: bilateral.selectedIssueEntityId,
        blueprintAssetId: bilateral.blueprintAssetId,
        blueprintDigest: bilateral.blueprintDigest,
        modeSequence: bilateral.modeSequence,
      });
    } catch (error) {
      bilateral = {
        ...bilateral,
        error: String(error?.message || error),
      };
    }
    await exerciseTour(page, receipts);
    await snapshot(page, "after-tour");

    const finalState = receipts.at(-1);
    const finalTourStatus = String(finalState?.tourStatus || "");
    const finalSceneState = String(finalState?.sceneState || "");
    const tourFinished =
      finalSceneState === "Dissolved" && finalTourStatus.includes("Renderer released");
    const unexpectedContextLoss = receipts.some(
      (receipt) =>
        receipt.webglContextLost === true &&
        String(receipt.sceneState || "") !== "Dissolved",
    );
    const failed =
      bilateral.ok !== true ||
      pageErrors.length > 0 ||
      requestFailures.length > 0 ||
      consoleMessages.some((message) => message.type === "error") ||
      receipts.some((receipt) => receipt.webgl2Available === false) ||
      unexpectedContextLoss ||
      receipts.some((receipt) => String(receipt.sceneState || "").toLowerCase().includes("failed")) ||
      !tourFinished ||
      finalTourStatus.includes("Presentation stopped");
    if (failed) exitCode = 1;
  } catch (error) {
    exitCode = 1;
    pageErrors.push({ name: error.name, message: error.message, stack: error.stack });
    if (page) {
      try {
        receipts.push(await inspectPage(page, "exception"));
        await snapshot(page, "exception");
      } catch (_) {
        // Preserve the original browser failure.
      }
    }
  } finally {
    if (browser) {
      try {
        await browser.close();
      } catch (error) {
        exitCode = 1;
        pageErrors.push({ name: error.name, message: error.message, stack: error.stack });
      }
    }
    const evidence = {
      version: "AURA_CONSTRUCTION_BROWSER_PROBE_V1",
      url: BASE_URL,
      receipts,
      bilateral,
      consoleMessages,
      pageErrors,
      requestFailures,
      ok: exitCode === 0,
      productionMutation: bilateral.productionMutation,
      automaticPatch: false,
      automaticMerge: bilateral.automaticMerge,
      physicalWorkAuthorized: bilateral.physicalWorkAuthorized,
      professionalAuthority: bilateral.professionalAuthority,
      humanReviewRequired: true,
    };
    fs.writeFileSync(path.join(OUTPUT_DIR, "browser-evidence.json"), JSON.stringify(evidence, null, 2));
    process.stdout.write(`${JSON.stringify(evidence, null, 2)}\n`);
  }
  process.exitCode = exitCode;
}

main();
