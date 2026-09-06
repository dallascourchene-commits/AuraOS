# Frontier-27 numeric + invocation totality / transactional preflight donor

Non-owner D0 repair surface stacked on AGENT_01 / PR #825. AGENT_01 remains the canonical Frontier-27 owner.

Keeper laws:

- `GovernedNumericValidation => TotalDeterministicRejection`
- `IndividuallyFiniteInputs != FiniteDerivedMetric`
- `RejectedCall => PersistentStateEquivalentToPreCall`
- `NumericPreflightTotal != InvocationPreflightTotal`
- `GovernedInputMaterialization => BoundedCardinality AND DeterministicOrdinaryExceptionTranslation`

The donor does not replace `FrontierOffload`. It bounds and freezes nested caller records, validates the governed numeric domain, proves consequential float products/divisions before mutation, snapshots residency/counters, invokes the canonical owner, and restores exact state if the owner raises or emits a non-finite governed metric.

Invocation materialization is bounded while iterating rather than after `tuple(...)` has consumed the source. Ordinary exceptions raised by caller-controlled `iter()` or `next()` are translated to governed `ValueError`; `BaseException` process-control signals are intentionally not swallowed. The current donor defaults to 4,096 outer records and 4,096 expert IDs per record. Those ceilings, like the explicit 63-bit integer ceiling, are conservative donor policy rather than canonical Aura law.

The bounded-cardinality claim does not pretend a synchronous Python caller can prove wall-clock termination of an adversarial `next()` implementation that never returns. Such execution-time isolation remains a separate runtime/watchdog evidence plane.

D0 only: no physical energy/throughput claim, provider/model execution, canonical owner mutation, merge/deploy authority, effect authority, semantic K27 authority, native/private Transformer KV access, or Gate10.
