# Project006 Resident V2 IPC — staged reference

Status: **reference implementation / Gate-10 repair candidate / not target-host integration**.

This directory implements the Lane-A contract for `PROJECT006-RESIDENT-DEEPSEEK-WORKERCRYSTAL-BB-POC-001` without guessing the source path of the currently running P11 service.

## Boundary

- Resident uses **AF_UNIX only**.
- Provider URLs, provider credentials, HTTP clients, DNS/IP endpoints, and external networking do not belong in Resident.
- External provider networking belongs in the separately owned Provider Dispatcher Sidecar.
- Work enters Resident as bounded references/digests (`capsule_id`, `capsule_digest`, `route_ref`, source/dependency refs), not secrets.
- Linux/WSL consequence authorization receives an opaque `PeerIdentity` minted from the connected socket's `SO_PEERCRED` witness; there is no public raw-UID `process_request` authorization entry point.
- Generation/currentness/authority/issue-expiry are checked at use time.
- Consequence-bearing request replay is idempotent only for an identical live request digest; conflicting reuse fails closed.

## Independent-review repairs represented in this candidate

This generation incorporates the independent Gate-10 HOLD/REPAIR findings and the subsequent independent PR security-review finding:

1. **Rejected-request flood isolation.** Rejected and read-only requests do not consume the consequence/idempotency ledger. Accepted consequence-bearing receipts are bounded and reclaimed when request expiry passes or generation/currentness/authority rebases.
2. **Bounded frame liveness.** One absolute receive deadline covers header and body reads. Timeout is typed as `FRAME_RECEIVE_TIMEOUT`. Server wrappers use a fail-closed finite `ConnectionGate`.
3. **Cancellation authorization.** `WORK_CANCEL` may be performed only by the capsule-creating peer identity or configured Resident owner identity in this Linux/WSL reference profile. Knowledge of `authority_ref` alone is insufficient.
4. **Transport-bound peer identity.** Consequence processing accepts an opaque sealed `PeerIdentity`; the production serving seam mints it only from the active AF_UNIX connection via `SO_PEERCRED`. A caller-supplied integer UID is not an authorization input.
5. **Historical P11 preserved.** This remains additive reference code; no live-P11/source-binding, deployment, reboot-persistence or provider claim is minted here.

## Frame

`4-byte big-endian unsigned length || canonical UTF-8 JSON`

Hard body ceiling: 256 KiB.

Protocol: `AURA_RESIDENT_IPC_V2`.

Default absolute receive deadline: 2 seconds per frame in the reference implementation. Deployment may choose another positive bound only through an explicit current policy/configuration.

## Tests

```bash
cd tools/project006/resident_v2_reference
python3 test_resident_v2_ipc.py
```

The author-side second-repair candidate passed **37/37 focused tests before the final GitHub write**, including rejected-flood serviceability, expiry reclamation, slow-client timeout, bounded connection capacity, creator/owner cancellation authorization, cross-capsule rejection, forged peer-identity rejection, AF_UNIX peer credentials, framing, replay/collision, currentness/authority and no-IP/no-HTTP surface checks.

That author-side run is **not an independent Gate-10 review and is not claimed as an exact-head rerun**. Final Gate-10 evidence must bind one frozen Git head, enumerate every changed path, and independently execute/review that exact generation. Older 22/22, 23/23, 28/28 and 36/36 snapshots are historical/superseded for final evidence.

## Claim ceiling

This branch does **not** claim:

- that these files are integrated into the currently running P11 Resident;
- target ThinkPad/WSL V2 deployment;
- reboot persistence;
- provider/DeepSeek connectivity;
- WorkerCrystal scaling results;
- crash-safe durable exactly-once execution;
- production security or performance superiority;
- independent Gate-10 approval of this repair generation.

The exact live P11 source-generation/path remains a source-binding prerequisite. Transplant/integration must occur only after that binding is positively recovered and collision-checked. The repaired generation must be reviewed by a worker that did not author these changes.
