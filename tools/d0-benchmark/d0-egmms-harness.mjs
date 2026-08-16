import { createHash } from "node:crypto";

export const EGMMS_BUNDLE_SHA256 =
  "c9f6c13f23decb0b53d1a567dd4f9b72fd01d24b67db115472ae760e4ddc21f6";

export const MODE_IDS = Object.freeze({
  FULL_CONTEXT_FULL_PROOF: "FULL_CONTEXT_FULL_PROOF",
  CONVENTIONAL_VERSIONED_MEMOIZATION: "CONVENTIONAL_VERSIONED_MEMOIZATION",
  PERSISTENT_REACTIVATION_KERNEL: "PERSISTENT_REACTIVATION_KERNEL",
  DERIVATIVE_RECONSTRUCTION: "DERIVATIVE_RECONSTRUCTION",
  OWNER_GATED_NEAR_STATELESS: "OWNER_GATED_NEAR_STATELESS",
});

const POLARITIES = new Set(["PASS", "FAIL", "UNKNOWN"]);

function sortValue(value) {
  if (Array.isArray(value)) return value.map(sortValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value).sort().map((key) => [key, sortValue(value[key])]),
    );
  }
  return value;
}

export function stableStringify(value) {
  return JSON.stringify(sortValue(value));
}

export function digest(value) {
  return createHash("sha256").update(stableStringify(value)).digest("hex");
}

function sameArray(a = [], b = []) {
  return stableStringify([...a].sort()) === stableStringify([...b].sort());
}

function explicitUnknownOrBlock(value) {
  return value && (value.status === "UNKNOWN" || value.status === "BLOCK");
}

/**
 * J56/V30 receipt validation.
 *
 * A receipt is a reusable evidence fragment, not inherited closure or authority.
 * Exact semantic/domain/generation compatibility is required for a used receipt.
 */
export function verifyV30Receipt(receipt, expected) {
  if (!receipt || typeof receipt !== "object") {
    return { valid: false, reason: "missing-receipt" };
  }
  if (!POLARITIES.has(receipt.polarity)) {
    return { valid: false, reason: "invalid-polarity" };
  }
  if (receipt.polarity === "UNKNOWN") {
    return { valid: false, reason: "unknown-never-admits" };
  }

  const exact = [
    ["obligationId", expected.obligationId],
    ["validityDomain", expected.validityDomain],
    ["semanticGeneration", expected.semanticGeneration],
    ["sourceGeneration", expected.sourceGeneration],
  ];
  for (const [field, expectedValue] of exact) {
    if (receipt[field] !== expectedValue) {
      return { valid: false, reason: `${field}-mismatch` };
    }
  }

  if (receipt.invalidated || receipt.revoked || receipt.counterevidence) {
    return { valid: false, reason: "receipt-invalidated" };
  }
  if (receipt.negativeSpace !== "TYPED_COMPLETE") {
    return { valid: false, reason: "negative-space-not-complete" };
  }
  if (!receipt.sourceLocator || !receipt.reopenPath) {
    return { valid: false, reason: "source-reopen-path-missing" };
  }
  if (receipt.requiredStatus !== expected.requiredStatus) {
    return { valid: false, reason: "required-status-mismatch" };
  }
  if (!sameArray(receipt.dependencies, expected.dependencies)) {
    return { valid: false, reason: "dependency-mismatch" };
  }
  return { valid: true, reason: "exact-current-v30-domain" };
}

function cost(metrics, weights) {
  const m = metrics;
  const w = {
    activeBytes: 1,
    retainedBytes: 0.5,
    sourceReads: 150,
    reconstructionWork: 20,
    invalidationRadius: 10,
    p95LatencyMs: 100,
    ...weights,
  };
  return (
    m.activeBytes * w.activeBytes +
    m.retainedBytes * w.retainedBytes +
    m.sourceReads * w.sourceReads +
    m.reconstructionWork * w.reconstructionWork +
    m.invalidationRadius * w.invalidationRadius +
    m.p95LatencyMs * w.p95LatencyMs
  );
}

function gate(name, pass, details = null) {
  return { name, pass: Boolean(pass), ...(details ? { details } : {}) };
}

export async function evaluateModeSafety({
  workload,
  modeRun,
  canonical,
  ownerAdapter,
}) {
  const usedReceipts = (modeRun.v30Receipts ?? []).filter((receipt) => receipt.used);
  const receiptChecks = usedReceipts.map((receipt) => ({
    receiptDigest: digest(receipt),
    polarity: receipt.polarity,
    ...verifyV30Receipt(receipt, workload.v30Requirement),
  }));

  const permission = await ownerAdapter.verifyPermission({
    workload,
    requestedEffect: workload.requestedEffect,
    sourceGeneration: canonical.sourceGeneration,
    authorityGeneration: canonical.authorityGeneration,
  });

  const restartEquivalent =
    stableStringify(modeRun.restartResult) === stableStringify(canonical.lawfulResult) ||
    (canonical.sourceAvailability !== "AVAILABLE" &&
      explicitUnknownOrBlock(modeRun.restartResult));

  const gates = [
    gate(
      "stale-source-pass-escape",
      modeRun.observedSourceGeneration === canonical.sourceGeneration &&
        !modeRun.staleSourceEscape,
      {
        observed: modeRun.observedSourceGeneration,
        canonical: canonical.sourceGeneration,
      },
    ),
    gate(
      "v30-receipt-validity",
      receiptChecks.every((check) => check.valid),
      { checks: receiptChecks },
    ),
    gate(
      "unknown-laundering",
      !(modeRun.v30Receipts ?? []).some(
        (receipt) => receipt.used && receipt.polarity === "UNKNOWN",
      ),
    ),
    gate(
      "authority-provenance-live-duties",
      permission.ok &&
        modeRun.authorityGeneration === canonical.authorityGeneration &&
        modeRun.provenanceRoot === canonical.provenanceRoot &&
        sameArray(modeRun.liveObligations, canonical.liveObligations),
      {
        permissionVerified: permission.ok,
        ownerId: permission.ownerId,
        authorityGeneration: canonical.authorityGeneration,
      },
    ),
    gate("generated-state-deletion-reproducibility", restartEquivalent),
    gate("invalidation-fanout-complete", modeRun.invalidationFanoutComplete === true),
    gate(
      "consequence-deadline-or-fence",
      modeRun.metrics.p95LatencyMs <= workload.deadlineMs || modeRun.fenced === true,
      {
        p95LatencyMs: modeRun.metrics.p95LatencyMs,
        deadlineMs: workload.deadlineMs,
        fenced: Boolean(modeRun.fenced),
      },
    ),
  ];

  return {
    safe: gates.every((entry) => entry.pass),
    gates,
    receiptChecks,
    permission: {
      ok: permission.ok,
      ownerId: permission.ownerId,
      authorityGeneration: canonical.authorityGeneration,
    },
  };
}

export async function runD0Benchmark({
  workload,
  modes,
  ownerAdapter,
  policyGeneration = "d0-policy-v1",
}) {
  if (!workload?.id) throw new TypeError("workload.id is required");
  if (!Array.isArray(modes) || modes.length === 0) {
    throw new TypeError("at least one memory mode is required");
  }

  const canonical = await ownerAdapter.getCurrentState(workload);
  const evaluatedModes = [];

  for (const mode of modes) {
    const modeRun = await mode.run({ workload, canonical, ownerAdapter });
    const safety = await evaluateModeSafety({
      workload,
      modeRun,
      canonical,
      ownerAdapter,
    });
    const lifecycleCost = safety.safe
      ? cost(modeRun.metrics, workload.costWeights)
      : Number.POSITIVE_INFINITY;

    evaluatedModes.push({
      mode: mode.id,
      safe: safety.safe,
      safetyGates: safety.gates,
      metrics: modeRun.metrics,
      lifecycleCost,
      sourceCurrentness: {
        observed: modeRun.observedSourceGeneration,
        canonical: canonical.sourceGeneration,
      },
      v30ReceiptVerification: safety.receiptChecks,
      canonicalOwnerVerification: safety.permission,
    });
  }

  const admissible = evaluatedModes
    .filter((entry) => entry.safe)
    .sort((a, b) =>
      a.lifecycleCost === b.lifecycleCost
        ? a.mode.localeCompare(b.mode)
        : a.lifecycleCost - b.lifecycleCost,
    );

  const selected = admissible[0] ?? null;
  const receiptBase = {
    schemaVersion: "aura.d0.mode-selection.v1",
    egmmsBundleSha256: EGMMS_BUNDLE_SHA256,
    policyGeneration,
    workload: {
      id: workload.id,
      digest: digest(workload),
      consequenceClass: workload.consequenceClass,
      churnRegime: workload.churnRegime,
      deadlineMs: workload.deadlineMs,
    },
    sourceCurrentness: {
      sourceGeneration: canonical.sourceGeneration,
      authorityGeneration: canonical.authorityGeneration,
      sourceAvailability: canonical.sourceAvailability,
    },
    evaluatedModes,
    selectedMode: selected?.mode ?? "BLOCK",
    selectedLifecycleCost: selected?.lifecycleCost ?? null,
    canonicalOwnerVerification: {
      ownerId: canonical.ownerId,
      provenanceRoot: canonical.provenanceRoot,
      liveObligations: canonical.liveObligations,
      authorityGeneration: canonical.authorityGeneration,
    },
    fallback: {
      kind: "CURRENT_OWNER",
      ownerId: canonical.ownerId,
      route: canonical.ownerRoute,
      requiresFreshRead: true,
    },
    advisoryOnly: true,
  };
  const receiptDigest = digest(receiptBase);

  return {
    ...receiptBase,
    receiptDigest,
  };
}

export async function verifyModeSelectionReceipt(receipt, { workload, ownerAdapter }) {
  if (receipt.egmmsBundleSha256 !== EGMMS_BUNDLE_SHA256) {
    return { valid: false, reason: "egmms-bundle-digest-mismatch" };
  }
  const { receiptDigest, ...unsigned } = receipt;
  if (digest(unsigned) !== receiptDigest) {
    return { valid: false, reason: "receipt-digest-mismatch" };
  }

  const canonical = await ownerAdapter.getCurrentState(workload);
  if (
    receipt.canonicalOwnerVerification.ownerId !== canonical.ownerId ||
    receipt.sourceCurrentness.sourceGeneration !== canonical.sourceGeneration ||
    receipt.sourceCurrentness.authorityGeneration !== canonical.authorityGeneration ||
    receipt.canonicalOwnerVerification.provenanceRoot !== canonical.provenanceRoot ||
    !sameArray(
      receipt.canonicalOwnerVerification.liveObligations,
      canonical.liveObligations,
    )
  ) {
    return { valid: false, reason: "canonical-owner-state-mismatch" };
  }

  const permission = await ownerAdapter.verifyPermission({
    workload,
    requestedEffect: workload.requestedEffect,
    sourceGeneration: canonical.sourceGeneration,
    authorityGeneration: canonical.authorityGeneration,
  });
  if (!permission.ok) {
    return { valid: false, reason: "canonical-owner-permission-failed" };
  }
  if (receipt.fallback?.kind !== "CURRENT_OWNER" || !receipt.fallback.requiresFreshRead) {
    return { valid: false, reason: "source-rooted-fallback-missing" };
  }
  if (receipt.advisoryOnly !== true) {
    return { valid: false, reason: "selector-must-remain-advisory" };
  }
  return { valid: true, reason: "verified-against-current-owner" };
}
