# GEN25 Admission-Liveness Witness

D0-only Arena worker cell for distinguishing command admission starvation from unrelated historical bus activity or assumed service death.

Keeper laws:
- `HistoricalBusSuccess != CurrentCommandAdmission`.
- `SameGeneration != SameExactHead`; generation and authoritative head digest are both bound.
- `ProcessAlive != ConsumerProgress`.
- `QueuePresence != ACK_ACCEPTED_PRE_EFFECT != RESULT/ERROR != HostEffect`.
- `FutureReceipt != CurrentProgress`; command-bound receipts later than the observation cut fail closed.
- `ObservedConsumerState => CompleteTypedServiceAndLeaseSurface` before restart budgeting.
- `StarvationPressure = ActiveCurrentIngress AND MissingCommandBoundTypedProgress AND AgeThreshold`; this does not prove host death.
- This D0 witness never self-authorizes provider/model fanout. It may prove local admission progress, but provider dispatch remains a separate owner/effect decision.
- A restart is never authorized from silence alone; it is at most one restart after direct host observation shows an inactive/stale service/lease.

The worker does not execute services, providers, models, or network effects. It compiles a minimal owner-host recovery cone.
