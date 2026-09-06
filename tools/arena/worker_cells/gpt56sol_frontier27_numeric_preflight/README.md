# Frontier-27 numeric + invocation totality / transactional preflight donor

Non-owner D0 repair surface stacked on AGENT_01 / PR #825. AGENT_01 remains the canonical Frontier-27 owner.

Keeper laws:

- `GovernedNumericValidation => TotalDeterministicRejection`
- `IndividuallyFiniteInputs != FiniteDerivedMetric`
- `AggregateMetricFinite != OwnerAccumulationFinite`
- `RejectedCall => PersistentStateEquivalentToPreCall`
- `NumericPreflightTotal != InvocationPreflightTotal`
- `GovernedInputMaterialization => BoundedCardinality AND DeterministicOrdinaryExceptionTranslation`

The donor does not replace `FrontierOffload`. It bounds and freezes nested caller records, validates the governed numeric domain, proves consequential float products/divisions before mutation, and now also proves the owner's actual accumulation shape before owner execution.

For `LegacyOffload`, the donor replays the exact positive seconds/energy addition order used by the owner. For `FrontierOffload`, every actual prefetch/miss adds the same size-derived term, so the donor conservatively proves finiteness for the maximum possible bounded transfer count (`route IDs + prediction IDs`) before residency/counters can move. Two deterministic regressions demonstrate why aggregate finiteness is insufficient: a Legacy route-order case and an 11-transfer Frontier case both keep aggregate division finite while owner-style repeated additions reach `inf`.

Invocation materialization remains bounded while iterating rather than after `tuple(...)` has consumed the source. Ordinary exceptions raised by caller-controlled `iter()` or `next()` are translated to governed `ValueError`; `BaseException` process-control signals are intentionally not swallowed. The current donor defaults to 4,096 outer records and 4,096 expert IDs per record. Those ceilings, like the explicit 63-bit integer ceiling, are conservative donor policy rather than canonical Aura law.

The bounded-cardinality claim does not pretend a synchronous Python caller can prove wall-clock termination of an adversarial `next()` implementation that never returns. Such execution-time isolation remains a separate runtime/watchdog evidence plane.

R10.2 local frozen proof: three recreated stdlib-only virtual environments; 72/72 focused test executions; 300,000 randomized owner-order decisions; 33,000 numeric HyperScale cases; 90,000 invocation-materialization decisions; 30,000 invocation HS cases; zero oracle mismatches/false accepts/false holds/uncontrolled ordinary exceptions; Omega8 exactly one keeper; 13D zero hard-axis repairs. Campaign root `3d1a105d9975db34c993d79df12cd832697e1a2b6381fab9a85d208be5c1da60`.

D0 only: no physical energy/throughput claim, provider/model execution, canonical owner mutation, main merge/deploy authority, effect authority, semantic K27 authority, native/private Transformer KV access, Gate10, or numbered successor.
