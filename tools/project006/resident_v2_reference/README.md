# Project006 Resident V2 IPC — staged reference

Status: **reference implementation / G4 Stage-9 candidate / not target-host integration**.

This directory implements the Lane-A contract for `PROJECT006-RESIDENT-DEEPSEEK-WORKERCRYSTAL-BB-POC-001` without guessing the source path of the currently running P11 service.

## Boundary

- Resident uses **AF_UNIX only**.
- Provider URLs, provider credentials, HTTP clients, DNS/IP endpoints, and external networking do not belong in Resident.
- External provider networking belongs in the separately owned Provider Dispatcher Sidecar.
- Work enters Resident as bounded references/digests (`capsule_id`, `capsule_digest`, `route_ref`, source/dependency refs), not secrets.
- The authoritative consequence processor accepts the **connected AF_UNIX socket**, not a caller-supplied UID or peer object. It derives the current peer UID from Linux/WSL `SO_PEERCRED` inside the trusted processing seam.
- Trusted processing time is sampled after the complete frame is received; callers cannot provide the consequence timestamp.
- Generation/currentness/authority/issue-expiry are checked at use time.
- State transitions, replay checks, capacity checks, cancellation authorization, receipt caching, and effect-ledger insertion execute under one ResidentState transaction lock.
- Consequence replay is idempotent only for an identical live digest **and the same authorized peer UID**; conflicting or foreign-peer replay fails closed.

## Independent-review repairs represented in G4

G4 consumes the predecessor Gate-10 HOLD and current PR review findings without claiming its own certification:

1. **Transport-bound authority.** `_process_request(raw, state, sock)` derives `SO_PEERCRED` itself. The prior arbitrary-UID/sealed-PeerIdentity minting surface is removed.
2. **Atomic state transitions.** One state-owned re-entrant lock serializes pruning, replay resolution, authorization-dependent state lookup, capacity checks, mutations, receipt construction, and accepted-effect insertion.
3. **Use-time currentness.** Processing time is sampled after frame receipt, preventing a partial/slow frame from using a stale pre-read timestamp to pass expiry or work-deadline checks.
4. **Replay reauthorization.** Accepted consequence records bind the authorizing peer UID; replay from another peer returns `REPLAY_PEER_MISMATCH` without reapplying the effect.
5. **Immutable cache boundary.** Cached receipts are stored as independent canonical JSON values and replay returns a fresh clone, so caller mutation cannot corrupt retained evidence.
6. **Bounded work tombstones.** Active-work capacity counts only `ACCEPTED` work; terminal records carry `terminal_at_ms` and are bounded/reclaimed while live accepted-effect history prevents unsafe capsule reuse.
7. **Bounded frame liveness.** One absolute receive deadline covers header and body reads; timeout is typed as `FRAME_RECEIVE_TIMEOUT`; `ConnectionGate` remains fail-closed and finite.
8. **Schema fail-closed hardening.** Malformed/non-string message types, invalid Unicode, oversized object keys, network-endpoint aliases, and all non-empty extension objects fail closed through typed validation.
9. **Historical P11 preserved.** This remains additive reference code; no live-P11/source-binding, deployment, reboot-persistence, provider connectivity, or production claim is minted here.

## Frame

`4-byte big-endian unsigned length || canonical UTF-8 JSON`

Hard body ceiling: 256 KiB.

Protocol: `AURA_RESIDENT_IPC_V2`.

Default absolute receive deadline: 2 seconds per frame in the reference implementation. Deployment may choose another positive bound only through an explicit current policy/configuration.

## Tests

```bash
cd tools/project006/resident_v2_reference
python -m unittest -v test_resident_v2_ipc.py
```

The G4 suite contains **46 focused adversarial tests**. In addition to inherited framing/currentness/cancellation/resource tests, G4 covers transport-only authority arguments, foreign-peer replay, cached-receipt mutation, concurrent capacity and duplicate-effect races, terminal-record reclamation, post-frame time sampling, malformed message-type handling, Unicode/key bounds, and non-empty extension rejection.

Exact functional CI evidence at commit `e1af6de2fe0831a083ea01417590ea8492cea567`:

- `Project006 Resident V2 Reference` run `32335590247`: **SUCCESS**.
- Python 3.10 job: compile + exact Resident V2 adversarial suite **SUCCESS**.
- Python 3.12 job: compile + exact Resident V2 adversarial suite **SUCCESS**.
- `Verify source anchors` at the same functional head: **SUCCESS**.
- The CODEMAP synchronization workflow at that functional cut reported generated topology drift; repository automation then produced a CODEMAP-only child. That topology child is evidence synchronization, not an independent functional change.

The CI success is execution evidence, **not author self-certification**. Final Gate-10 review must bind the eventual frozen head/current CODEMAP child and be performed by a worker that did not author G4.

## Claim ceiling

This branch does **not** claim:

- that these files are integrated into the currently running P11 Resident;
- target ThinkPad/WSL V2 deployment;
- reboot persistence;
- provider/DeepSeek connectivity;
- WorkerCrystal scaling results;
- crash-safe durable exactly-once execution;
- production security or performance superiority;
- independent Gate-10 approval of G4.

The exact live P11 source-generation/path remains a source-binding prerequisite. Transplant/integration must occur only after that binding is positively recovered and collision-checked. G4 must be frozen at one exact current head and independently reviewed by a worker that did not author these changes.
