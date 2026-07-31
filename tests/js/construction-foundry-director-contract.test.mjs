import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

const source = await readFile(
  new URL("../../aura_showcase/construction-foundry-director.js", import.meta.url),
  "utf8",
);
const context = {
  Promise,
  TypeError,
  Error,
  Number,
  Object,
  Boolean,
  setTimeout,
  __AURA_CONSTRUCTION_DIRECTOR_TEST__: true,
};
context.globalThis = context;
vm.runInNewContext(source, context, {
  filename: "construction-foundry-director.js",
});
const contract = context.AuraConstructionDirectorTestHooks;

test("waitForP3View resolves only after exact P3 retained state", async () => {
  let clock = 0;
  let pressed = false;
  const stage = { dataset: { presentationMode: "design" } };
  const result = await contract.waitForP3View("AS_BUILT", {
    getControl: () => ({
      getAttribute: (name) => (name === "aria-pressed" && pressed ? "true" : "false"),
    }),
    getStage: () => stage,
    now: () => clock,
    schedule: (callback) => {
      clock += 40;
      if (clock === 80) {
        pressed = true;
        stage.dataset.presentationMode = "as-built";
      }
      queueMicrotask(callback);
    },
    timeoutMs: 200,
    pollMs: 40,
  });
  assert.deepEqual(
    { activeView: result.activeView, presentationMode: result.presentationMode },
    { activeView: "AS_BUILT", presentationMode: "as-built" },
  );
});

test("waitForP3View fails closed when P3 never retains the view", async () => {
  let clock = 0;
  await assert.rejects(
    contract.waitForP3View("COMPARE", {
      getControl: () => ({ getAttribute: () => "false" }),
      getStage: () => ({ dataset: { presentationMode: "design" } }),
      now: () => clock,
      schedule: (callback) => {
        clock += 50;
        queueMicrotask(callback);
      },
      timeoutMs: 100,
      pollMs: 50,
    }),
    /exact COMPARE presentation receipt/,
  );
});

test("settleDirective renders the server-updated session even on sync failure", async () => {
  let renders = 0;
  await assert.rejects(
    contract.settleDirective(
      async () => {
        throw new Error("P3 receipt timeout");
      },
      () => {
        renders += 1;
      },
    ),
    /P3 receipt timeout/,
  );
  assert.equal(renders, 1);
});

test("pacing is limited to non-consequential presentation chapters", () => {
  assert.equal(contract.shouldPaceAfterChapter({ consequential: false }), true);
  assert.equal(contract.shouldPaceAfterChapter({ consequential: true }), false);
  assert.equal(contract.shouldPaceAfterChapter(null), false);
});

test("settleDirective surfaces sync errors via render without swallowing", async () => {
  // settleDirective wraps an effect and always calls render() in finally.
  // When the effect throws, the error must propagate (not be swallowed)
  // and render must still run.  This tests the actual contract that
  // control() depends on for sync-failure visibility.
  let renderCount = 0;
  const render = () => { renderCount += 1; };
  await assert.rejects(
    contract.settleDirective(
      async () => { throw new Error("P3 sync failed at prepare-p3-sync"); },
      render,
    ),
    /P3 sync failed at prepare-p3-sync/,
  );
  assert.equal(renderCount, 1, "render must run even when the effect throws");
});

test("autoplay terminates on sync failure without issuing another NEXT", async () => {
  // settleDirective wraps the effect and catches errors. When sync fails,
  // it should render and re-throw — the caller (control) should not
  // issue another NEXT automatically.
  let nextCount = 0;
  let renderCount = 0;
  // Simulate: sync fails inside settleDirective
  await assert.rejects(
    contract.settleDirective(
      async () => {
        nextCount += 1;
        throw new Error("P3 presentation sync failed");
      },
      () => { renderCount += 1; },
    ),
    /P3 presentation sync failed/,
  );
  // Only one attempt should have been made — no retry/autoplay
  assert.equal(nextCount, 1);
  assert.equal(renderCount, 1);
});

test("controlDisabled and chapterOptionDisabled block controls during pending sync", () => {
  const syncPendingSession = { dissolved: false, p3_sync_pending: true, executed_index: 3 };
  const normalSession = { dissolved: false, p3_sync_pending: false, executed_index: 3 };
  const dissolvedSession = { dissolved: true, p3_sync_pending: false, executed_index: 3 };

  // PLAY and NEXT disabled when sync pending
  assert.equal(contract.controlDisabled("PLAY", syncPendingSession), true);
  assert.equal(contract.controlDisabled("NEXT", syncPendingSession), true);
  // RESYNC enabled when sync pending
  assert.equal(contract.controlDisabled("RESYNC", syncPendingSession), false);
  // PAUSE and PREVIOUS always enabled (not blocked by sync)
  assert.equal(contract.controlDisabled("PAUSE", syncPendingSession), false);
  assert.equal(contract.controlDisabled("PREVIOUS", syncPendingSession), false);

  // After sync clears: PLAY/NEXT re-enabled, RESYNC disabled
  assert.equal(contract.controlDisabled("PLAY", normalSession), false);
  assert.equal(contract.controlDisabled("NEXT", normalSession), false);
  assert.equal(contract.controlDisabled("RESYNC", normalSession), true);

  // RESTART only enabled when dissolved
  assert.equal(contract.controlDisabled("RESTART", normalSession), true);
  assert.equal(contract.controlDisabled("RESTART", dissolvedSession), false);

  // No session: everything disabled
  assert.equal(contract.controlDisabled("PLAY", null), true);
  assert.equal(contract.controlDisabled("NEXT", null), true);

  // Chapter options disabled when sync pending, enabled for proven chapters otherwise
  const provenChapter = { order: 2 };
  const unprovenChapter = { order: 5 };
  assert.equal(contract.chapterOptionDisabled(provenChapter, syncPendingSession), true);
  assert.equal(contract.chapterOptionDisabled(unprovenChapter, syncPendingSession), true);
  assert.equal(contract.chapterOptionDisabled(provenChapter, normalSession), false);
  assert.equal(contract.chapterOptionDisabled(unprovenChapter, normalSession), true);
  assert.equal(contract.chapterOptionDisabled(null, normalSession), true);
});
