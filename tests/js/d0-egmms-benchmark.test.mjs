import assert from "node:assert/strict";
import test from "node:test";

import {
  EGMMS_BUNDLE_SHA256,
  MODE_IDS,
  runD0Benchmark,
  verifyModeSelectionReceipt,
} from "../../tools/d0-benchmark/d0-egmms-harness.mjs";
import {
  createReferenceModeAdapter,
  createReferenceModeAdapters,
} from "../../tools/d0-benchmark/reference-modes.mjs";
import {
  FST_ROUTING_LOW_CHURN,
  MOBILE_KERNEL_HIGH_CHURN,
  createCanonicalOwnerAdapter,
} from "../../tools/d0-benchmark/reference-workloads.mjs";

const owner = createCanonicalOwnerAdapter();

test("D0 receipt binds the exact EGMMS synthesis bundle digest", async () => {
  const receipt = await runD0Benchmark({
    workload: FST_ROUTING_LOW_CHURN,
    modes: createReferenceModeAdapters(),
    ownerAdapter: owner,
  });
  assert.equal(
    receipt.egmmsBundleSha256,
    "c9f6c13f23decb0b53d1a567dd4f9b72fd01d24b67db115472ae760e4ddc21f6",
  );
  assert.equal(receipt.egmmsBundleSha256, EGMMS_BUNDLE_SHA256);
});

test("all reference modes pass hard safety gates before cost comparison", async () => {
  const receipt = await runD0Benchmark({
    workload: FST_ROUTING_LOW_CHURN,
    modes: createReferenceModeAdapters(),
    ownerAdapter: owner,
  });
  assert.equal(receipt.evaluatedModes.length, 5);
  for (const evaluated of receipt.evaluatedModes) {
    assert.equal(evaluated.safe, true, evaluated.mode);
    assert.equal(
      evaluated.safetyGates.every((gate) => gate.pass),
      true,
      evaluated.mode,
    );
  }
});

test("distinct churn/consequence envelopes produce distinct local mode selections", async () => {
  const fst = await runD0Benchmark({
    workload: FST_ROUTING_LOW_CHURN,
    modes: createReferenceModeAdapters(),
    ownerAdapter: owner,
  });
  const mobile = await runD0Benchmark({
    workload: MOBILE_KERNEL_HIGH_CHURN,
    modes: createReferenceModeAdapters(),
    ownerAdapter: owner,
  });
  assert.notEqual(fst.selectedMode, mobile.selectedMode);
});

test("a cheaper mode with stale source contamination is never selectable", async () => {
  const stale = createReferenceModeAdapter(
    MODE_IDS.OWNER_GATED_NEAR_STATELESS,
    (result) => ({
      observedSourceGeneration: "stale-g0",
      staleSourceEscape: true,
      metrics: {
        ...result.metrics,
        activeBytes: 0,
        retainedBytes: 0,
        sourceReads: 0,
        reconstructionWork: 0,
        invalidationRadius: 0,
        p95LatencyMs: 0,
      },
    }),
  );
  const receipt = await runD0Benchmark({
    workload: MOBILE_KERNEL_HIGH_CHURN,
    modes: [
      stale,
      createReferenceModeAdapter(MODE_IDS.PERSISTENT_REACTIVATION_KERNEL),
    ],
    ownerAdapter: owner,
  });
  assert.notEqual(receipt.selectedMode, MODE_IDS.OWNER_GATED_NEAR_STATELESS);
  const evaluated = receipt.evaluatedModes.find(
    (entry) => entry.mode === MODE_IDS.OWNER_GATED_NEAR_STATELESS,
  );
  assert.equal(evaluated.safe, false);
  assert.equal(evaluated.lifecycleCost, Infinity);
});

test("UNKNOWN V30 receipt is never promoted to admission", async () => {
  const unknown = createReferenceModeAdapter(
    MODE_IDS.CONVENTIONAL_VERSIONED_MEMOIZATION,
    (result) => ({
      v30Receipts: result.v30Receipts.map((receipt) => ({
        ...receipt,
        polarity: "UNKNOWN",
      })),
    }),
  );
  const receipt = await runD0Benchmark({
    workload: FST_ROUTING_LOW_CHURN,
    modes: [
      unknown,
      createReferenceModeAdapter(MODE_IDS.FULL_CONTEXT_FULL_PROOF),
    ],
    ownerAdapter: owner,
  });
  const evaluated = receipt.evaluatedModes.find(
    (entry) => entry.mode === MODE_IDS.CONVENTIONAL_VERSIONED_MEMOIZATION,
  );
  assert.equal(evaluated.safe, false);
  assert.match(
    JSON.stringify(evaluated.safetyGates),
    /unknown-never-admits|unknown-laundering/,
  );
});

test("incomplete invalidation fanout is a correctness failure", async () => {
  const broken = createReferenceModeAdapter(
    MODE_IDS.DERIVATIVE_RECONSTRUCTION,
    { invalidationFanoutComplete: false },
  );
  const receipt = await runD0Benchmark({
    workload: FST_ROUTING_LOW_CHURN,
    modes: [
      broken,
      createReferenceModeAdapter(MODE_IDS.FULL_CONTEXT_FULL_PROOF),
    ],
    ownerAdapter: owner,
  });
  const evaluated = receipt.evaluatedModes.find(
    (entry) => entry.mode === MODE_IDS.DERIVATIVE_RECONSTRUCTION,
  );
  assert.equal(evaluated.safe, false);
  assert.equal(
    evaluated.safetyGates.find(
      (gate) => gate.name === "invalidation-fanout-complete",
    ).pass,
    false,
  );
});

test("generated-state deletion must reproduce the canonical lawful result", async () => {
  const broken = createReferenceModeAdapter(
    MODE_IDS.PERSISTENT_REACTIVATION_KERNEL,
    { restartResult: { status: "PASS", value: "different-after-restart" } },
  );
  const receipt = await runD0Benchmark({
    workload: FST_ROUTING_LOW_CHURN,
    modes: [
      broken,
      createReferenceModeAdapter(MODE_IDS.FULL_CONTEXT_FULL_PROOF),
    ],
    ownerAdapter: owner,
  });
  const evaluated = receipt.evaluatedModes.find(
    (entry) => entry.mode === MODE_IDS.PERSISTENT_REACTIVATION_KERNEL,
  );
  assert.equal(evaluated.safe, false);
});

test("loss of a live repair/provenance duty disqualifies the mode", async () => {
  const broken = createReferenceModeAdapter(
    MODE_IDS.OWNER_GATED_NEAR_STATELESS,
    { liveObligations: [] },
  );
  const receipt = await runD0Benchmark({
    workload: MOBILE_KERNEL_HIGH_CHURN,
    modes: [
      broken,
      createReferenceModeAdapter(MODE_IDS.FULL_CONTEXT_FULL_PROOF),
    ],
    ownerAdapter: owner,
  });
  const evaluated = receipt.evaluatedModes.find(
    (entry) => entry.mode === MODE_IDS.OWNER_GATED_NEAR_STATELESS,
  );
  assert.equal(evaluated.safe, false);
});

test("receipt independently verifies against current canonical owner permissions", async () => {
  const receipt = await runD0Benchmark({
    workload: MOBILE_KERNEL_HIGH_CHURN,
    modes: createReferenceModeAdapters(),
    ownerAdapter: owner,
  });
  const verification = await verifyModeSelectionReceipt(receipt, {
    workload: MOBILE_KERNEL_HIGH_CHURN,
    ownerAdapter: owner,
  });
  assert.deepEqual(verification, {
    valid: true,
    reason: "verified-against-current-owner",
  });
  assert.equal(receipt.fallback.kind, "CURRENT_OWNER");
  assert.equal(receipt.fallback.requiresFreshRead, true);
  assert.equal(receipt.advisoryOnly, true);
});

test("receipt digest detects selector-record tampering", async () => {
  const receipt = await runD0Benchmark({
    workload: FST_ROUTING_LOW_CHURN,
    modes: createReferenceModeAdapters(),
    ownerAdapter: owner,
  });
  receipt.selectedMode = MODE_IDS.OWNER_GATED_NEAR_STATELESS;
  const verification = await verifyModeSelectionReceipt(receipt, {
    workload: FST_ROUTING_LOW_CHURN,
    ownerAdapter: owner,
  });
  assert.equal(verification.valid, false);
  assert.equal(verification.reason, "receipt-digest-mismatch");
});

test("irreversible-deadline overrun fails unless an enforceable fence is present", async () => {
  const workload = {
    ...MOBILE_KERNEL_HIGH_CHURN,
    id: "reference.mobile-kernel.irreversible-tight",
    consequenceClass: "IRREVERSIBLE",
    deadlineMs: 1,
  };
  const unfenced = createReferenceModeAdapter(
    MODE_IDS.OWNER_GATED_NEAR_STATELESS,
  );
  const fenced = createReferenceModeAdapter(
    MODE_IDS.DERIVATIVE_RECONSTRUCTION,
    { fenced: true },
  );
  const receipt = await runD0Benchmark({
    workload,
    modes: [unfenced, fenced],
    ownerAdapter: owner,
  });
  const near = receipt.evaluatedModes.find(
    (entry) => entry.mode === MODE_IDS.OWNER_GATED_NEAR_STATELESS,
  );
  const derivative = receipt.evaluatedModes.find(
    (entry) => entry.mode === MODE_IDS.DERIVATIVE_RECONSTRUCTION,
  );
  assert.equal(near.safe, false);
  assert.equal(derivative.safe, true);
  assert.equal(receipt.selectedMode, MODE_IDS.DERIVATIVE_RECONSTRUCTION);
});
