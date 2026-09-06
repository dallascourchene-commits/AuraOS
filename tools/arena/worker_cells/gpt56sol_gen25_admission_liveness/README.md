# GEN25 Admission-Liveness Witness

D0-only Arena worker cell for distinguishing command admission starvation from unrelated historical bus activity, stale/future receipts, inactive queue entries, incomplete host observation, or assumed service death.

Keeper laws:
- `HistoricalBusSuccess != CurrentCommandAdmission`.
- `SameGeneration != SameExactHead`; generation and authoritative head digest are both bound.
- `ProcessAlive != ConsumerProgress`.
- `QueuePresence != ActiveCurrentIngress`; only explicitly active queue states can create starvation pressure.
- `FutureReceipt != CurrentProgress`; a command-bound receipt observed after `now_s` fails closed.
- `QueuePresence != ACK_ACCEPTED_PRE_EFFECT != RESULT/ERROR != HostEffect`.
- `StarvationPressure = ActiveCurrentIngress AND MissingCommandBoundTypedProgress AND AgeThreshold`; inactive/cancelled/superseded commands cannot create starvation pressure.
- `ObservationFlag != CompleteHostObservation`; restart planning requires direct service-active and lease-current facts.
- This D0 witness never self-authorizes provider/model fanout. It may prove local admission progress, but provider dispatch remains a separate owner/effect decision.
- A restart is never authorized from silence alone; it is at most one restart after complete direct host observation shows an inactive/stale service or lease.

Known active queue states in this worker are `AUTHORIZED_FOR_DISPATCH_WHEN_OWNER_BOUND` and `READY`. Known inactive states are `CANCELLED`, `HOLD`, `SUPERSEDED`, `DONE`, and `TERMINAL`. Unknown queue states fail to `HOST_VISIBILITY_REQUIRED` rather than being guessed active or inactive.

The worker does not execute services, providers, models, or network effects. It compiles a minimal owner-host recovery cone.

## Falsifier closure

The original branch passed its own campaign but admitted three boundary defects. A concurrent v2 repair closed future-dated receipt admission and incomplete consumer-observation handling. v3 preserves those stricter checks and closes the remaining queue-semantic gap: inactive or unknown queue entries can no longer manufacture active-ingress starvation.

Proof is credited only after exact published-byte replay in fresh environments; see the PR body and durable Arena repair receipt for the current hashes and campaign root.
