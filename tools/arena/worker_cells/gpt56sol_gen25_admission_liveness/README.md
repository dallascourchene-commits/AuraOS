# GEN25 Admission-Liveness Witness + Project006 Observation Bridge

D0-only Arena worker cell for distinguishing current command starvation from unrelated historical bus activity, stale/future receipts, inactive/unknown queue entries, incomplete host observation, or assumed service death. It also provides an observation-only bridge for the exact AWJ033 Project006 owner-host surface.

Keeper laws:
- `HistoricalBusSuccess != CurrentCommandAdmission`.
- `SameGeneration != SameExactHead`; generation and authoritative head digest are both bound.
- `QueuePresence != ActiveCurrentIngress`; only explicitly active queue states can create starvation pressure.
- Known active states: `AUTHORIZED_FOR_DISPATCH_WHEN_OWNER_BOUND`, `READY`.
- Known inactive states: `CANCELLED`, `HOLD`, `SUPERSEDED`, `DONE`, `TERMINAL`; unknown states require visibility instead of guessed activation.
- `ProcessAlive != ConsumerProgress`.
- `FutureReceipt != CurrentProgress`; command-bound receipts after the observation cut fail closed.
- `GenericReceiptDirectoryChurn != CanaryProgress`; only an exact canary command-bound receipt may contribute on the receipt plane.
- `QueuePresence != ACK_ACCEPTED_PRE_EFFECT != RESULT/ERROR != HostEffect`.
- `Project006RestartEligibility = ServiceInactiveOrMissingPID OR ActiveServiceAndObservedNoProgressAfterBoundedCanaryIteration`.
- Consumer progress is measured from state hash, cursor, last-scan, or exact canary command-bound receipt movement. Lease state is retained as advisory only; the current AWJ033 owner contract does not make it a restart prerequisite.
- The recovery receipt root commits to the exact current head, queue classes, and exact consumer-observation surface.
- This D0 witness never self-authorizes provider/model fanout.
- The Project006 bridge is read-only: it compiles service/hash/state/receipt inspection commands but never executes `systemctl restart`, the consumer, the canary, providers, or models.

Exact owner-host bindings are source-derived from the current AWJ033 R2 handoff:
- service `aura-project006.service`;
- consumer `/home/john_of_wick/.config/aura-drive/bin/aura_drive_swarm_consumer_v1.py`;
- state `/home/john_of_wick/.config/aura-drive/state/swarm_consumer_v1/consumer_state.json`;
- receipts `/home/john_of_wick/.config/aura-drive/state/swarm_consumer_v1/receipts`;
- head `GEN25 / d91e0a39358901c5`;
- existing execution-false canary `AWJ033-CURRENT-CONSUMER-WAKE-ADMISSION-DIAGNOSTIC-20260902T234505Z-R1`.

The bridge's read-only probe plan checks systemd state, hashes the installed consumer, reads the consumer state, inventories receipts, and locates receipts containing the exact canary command ID. It does not execute the owner-host recovery procedure. The owner-host handoff remains the authority for any actual restart or consumer iteration.

## Falsifier closure

Successive repairs closed: future-dated command receipts, incomplete observations, inactive/unknown queue starvation inflation, mandatory-lease drift from the actual owner contract, recovery receipts that did not bind exact host evidence, and generic receipt-directory churn being mistaken for canary progress. Proof is credited only after exact published-byte replay in fresh environments.
