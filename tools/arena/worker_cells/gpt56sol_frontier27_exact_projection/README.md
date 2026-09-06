# Frontier-27 R11 exact projection donor

Additive D0 residual stacked above PR #858 R10.2. It does not edit the canonical Frontier-27 owner or the R10.2 donor files.

Keeper laws:
- `WorstCaseFinite != ExactOwnerAdmission`
- `SafetySurrogateCanRejectValidOwnerExecution`
- `PerDimensionBounded != AggregateResourceBounded`
- `AggregatePotentialMetric != ExactTransferredMetric`
- `ExactPreStateProjection + ExactRealExecutionEquality => SemanticsPreservingAdmissionCandidate`

The adapter applies a shared aggregate expert-ID budget while records are consumed, reuses R10.2 bounded materialization, aggregate-byte policy and window guards, deliberately does not reuse the aggregate potential seconds/energy surrogate, clones the exact Frontier residency/counters, dry-runs `FrontierOffload.run` on that clone, requires finite projected metrics, then runs the same canonical method on the real owner and requires exact result + persistent-state equality. Any post-projection divergence rolls back the real residency/counters.

D0 only. A synchronous `next()` call that itself never returns remains outside this layer and requires watchdog/process isolation. No canonical adoption, provider/model execution, physical performance truth, effect authority, Gate10, semantic K27 authority, or native/private Transformer KV is claimed.
