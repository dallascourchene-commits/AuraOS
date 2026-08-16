export const FST_ROUTING_LOW_CHURN = Object.freeze({
  id: "reference.fst-routing.low-churn",
  description:
    "Deterministic reference envelope shaped like repeated FST route selection; fixture only, not a production measurement.",
  consequenceClass: "REVERSIBLE_ROUTING",
  churnRegime: "LOW",
  churnRate: 0.02,
  payloadBytes: 64_000,
  proofComplexity: 18,
  reuseFactor: 12,
  sourceReadMs: 2,
  deadlineMs: 40,
  requestedEffect: "ROUTE_CANDIDATE",
  costWeights: {
    activeBytes: 0.01,
    retainedBytes: 0.006,
    sourceReads: 35,
    reconstructionWork: 15,
    invalidationRadius: 12,
    p95LatencyMs: 55,
  },
  v30Requirement: {
    obligationId: "fst-route-source-current",
    validityDomain: "fst-routing/reference/v1",
    semanticGeneration: "fst-sem-v1",
    sourceGeneration: "src-g1",
    requiredStatus: "REQUIRED",
    dependencies: ["fst-grammar", "route-owner"],
  },
});

export const MOBILE_KERNEL_HIGH_CHURN = Object.freeze({
  id: "reference.mobile-kernel.high-churn",
  description:
    "Deterministic mobile-kernel-shaped reference envelope with high source churn and fenceable effects; fixture only, not a production measurement.",
  consequenceClass: "FENCEABLE_MOBILE_EFFECT",
  churnRegime: "HIGH",
  churnRate: 0.88,
  payloadBytes: 180_000,
  proofComplexity: 12,
  reuseFactor: 1,
  sourceReadMs: 1,
  deadlineMs: 55,
  requestedEffect: "MOBILE_KERNEL_COMMIT",
  costWeights: {
    activeBytes: 0.012,
    retainedBytes: 0.010,
    sourceReads: 25,
    reconstructionWork: 8,
    invalidationRadius: 70,
    p95LatencyMs: 30,
  },
  v30Requirement: {
    obligationId: "mobile-kernel-current-owner",
    validityDomain: "mobile-kernel/reference/v1",
    semanticGeneration: "mobile-sem-v1",
    sourceGeneration: "src-g1",
    requiredStatus: "REQUIRED",
    dependencies: ["kernel-owner", "effect-fence"],
  },
});

export function createCanonicalOwnerAdapter({
  sourceGeneration = "src-g1",
  authorityGeneration = "auth-g1",
  sourceAvailability = "AVAILABLE",
} = {}) {
  return {
    async getCurrentState(workload) {
      return {
        ownerId: "canonical-owner.reference",
        ownerRoute: "owner://canonical/reference",
        sourceGeneration,
        authorityGeneration,
        sourceAvailability,
        provenanceRoot: `prov:${workload.id}:root`,
        liveObligations: [`duty:${workload.id}:provenance`, `duty:${workload.id}:repair`],
        lawfulResult: {
          status: sourceAvailability === "AVAILABLE" ? "PASS" : "UNKNOWN",
          value: sourceAvailability === "AVAILABLE" ? `lawful:${workload.id}` : null,
        },
      };
    },
    async verifyPermission({
      sourceGeneration: requestedSourceGeneration,
      authorityGeneration: requestedAuthorityGeneration,
    }) {
      return {
        ok:
          sourceAvailability === "AVAILABLE" &&
          requestedSourceGeneration === sourceGeneration &&
          requestedAuthorityGeneration === authorityGeneration,
        ownerId: "canonical-owner.reference",
      };
    },
  };
}
