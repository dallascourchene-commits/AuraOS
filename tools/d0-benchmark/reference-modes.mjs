import { MODE_IDS } from "./d0-egmms-harness.mjs";

function exactReceipt(canonical, workload) {
  const r = workload.v30Requirement;
  return {
    obligationId: r.obligationId,
    polarity: "PASS",
    validityDomain: r.validityDomain,
    semanticGeneration: r.semanticGeneration,
    sourceGeneration: canonical.sourceGeneration,
    requiredStatus: r.requiredStatus,
    dependencies: [...r.dependencies],
    invalidated: false,
    revoked: false,
    counterevidence: false,
    negativeSpace: "TYPED_COMPLETE",
    sourceLocator: canonical.ownerRoute,
    reopenPath: `owner:${canonical.ownerId}:reprove`,
    used: true,
  };
}

function baseResult(workload, canonical, metrics) {
  return {
    lawfulResult: canonical.lawfulResult,
    restartResult: canonical.lawfulResult,
    observedSourceGeneration: canonical.sourceGeneration,
    authorityGeneration: canonical.authorityGeneration,
    provenanceRoot: canonical.provenanceRoot,
    liveObligations: [...canonical.liveObligations],
    invalidationFanoutComplete: true,
    staleSourceEscape: false,
    fenced: false,
    v30Receipts: [exactReceipt(canonical, workload)],
    metrics,
  };
}

function metricsFor(id, w) {
  const bytes = w.payloadBytes;
  const proof = w.proofComplexity;
  const churn = w.churnRate;
  const reuse = w.reuseFactor;
  const read = w.sourceReadMs;

  switch (id) {
    case MODE_IDS.FULL_CONTEXT_FULL_PROOF:
      return {
        activeBytes: Math.round(bytes * 2.0),
        retainedBytes: Math.round(bytes * 1.2),
        sourceReads: 1,
        reconstructionWork: proof * 0.05,
        invalidationRadius: Math.max(1, Math.round(churn * 2)),
        p95LatencyMs: 2 + proof * 0.10,
      };
    case MODE_IDS.CONVENTIONAL_VERSIONED_MEMOIZATION:
      return {
        activeBytes: Math.round(bytes * 0.65),
        retainedBytes: Math.round(bytes * 0.75),
        sourceReads: 1 + Math.ceil(churn * 6),
        reconstructionWork: proof * (0.10 + churn * 0.35),
        invalidationRadius: 1 + Math.ceil(churn * 20),
        p95LatencyMs: 2 + read * (1 + churn * 2),
      };
    case MODE_IDS.PERSISTENT_REACTIVATION_KERNEL:
      return {
        activeBytes: Math.round(bytes * 0.16),
        retainedBytes: Math.round(bytes * 0.18),
        sourceReads: Math.max(1, Math.ceil(3 / Math.max(1, reuse))),
        reconstructionWork: proof * 0.22,
        invalidationRadius: 1 + Math.ceil(churn * 8),
        p95LatencyMs: 3 + read * 0.75,
      };
    case MODE_IDS.DERIVATIVE_RECONSTRUCTION:
      return {
        activeBytes: Math.round(bytes * 0.08),
        retainedBytes: Math.round(bytes * 0.07),
        sourceReads: 2 + Math.ceil(churn * 2),
        reconstructionWork: proof * 0.38,
        invalidationRadius: 1 + Math.ceil(churn * 4),
        p95LatencyMs: 3 + read * 1.8 + proof * 0.08,
      };
    case MODE_IDS.OWNER_GATED_NEAR_STATELESS:
      return {
        activeBytes: Math.max(256, Math.round(bytes * 0.015)),
        retainedBytes: Math.max(128, Math.round(bytes * 0.008)),
        sourceReads: 3,
        reconstructionWork: proof * 0.55,
        invalidationRadius: 1,
        p95LatencyMs: 3 + read * 3 + proof * 0.12,
      };
    default:
      throw new TypeError(`unknown mode: ${id}`);
  }
}

export function createReferenceModeAdapter(id, overrides = {}) {
  return {
    id,
    async run({ workload, canonical }) {
      const result = baseResult(workload, canonical, metricsFor(id, workload));
      const applied =
        typeof overrides === "function"
          ? overrides(result, { workload, canonical })
          : overrides;
      return { ...result, ...applied };
    },
  };
}

export function createReferenceModeAdapters() {
  return Object.values(MODE_IDS).map((id) => createReferenceModeAdapter(id));
}
