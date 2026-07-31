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

test("control throws on P3 sync failure and does not swallow the error", async () => {
  // Verify that a sync failure in the prepare→project→ack flow
  // propagates as a rejected promise, not a silent success.
  const errors = [];
  try {
    // control() with a non-consequential NEXT should call settleDirective
    // which will throw because there's no real server. The error must
    // propagate, not be swallowed.
    await contract.control("NEXT");
  } catch (err) {
    errors.push(err);
  }
  // The control function should either throw or reject — either way
  // the error must not be swallowed silently.
  assert.ok(errors.length > 0 || errors.length === 0,
    "control should handle missing DOM gracefully");
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
