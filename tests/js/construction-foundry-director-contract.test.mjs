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
