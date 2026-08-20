# Project006 Resident V2 IPC — staged reference

Status: **reference implementation / not target-host integration**.

This directory implements the Lane-A contract for `PROJECT006-RESIDENT-DEEPSEEK-WORKERCRYSTAL-BB-POC-001` without guessing the source path of the currently running P11 service.

## Boundary

- Resident uses **AF_UNIX only**.
- Provider URLs, provider credentials, HTTP clients, DNS/IP endpoints, and external networking do not belong in Resident.
- External provider networking belongs in the separately owned Provider Dispatcher Sidecar.
- Work enters Resident as bounded references/digests (`capsule_id`, `capsule_digest`, `route_ref`, source/dependency refs), not secrets.
- Normal and admin operations are separate; the Linux/WSL reference uses `SO_PEERCRED` UID witnessing for its minimum admin check.
- Generation/currentness/expiry are checked at use time.
- `request_id` replay is idempotent only for an identical request digest; conflicting reuse fails closed.

## Frame

`4-byte big-endian unsigned length || canonical UTF-8 JSON`

Hard body ceiling: 256 KiB.

Protocol: `AURA_RESIDENT_IPC_V2`.

## Tests

```bash
cd tools/project006/resident_v2_reference
python3 test_resident_v2_ipc.py
```

The source/test byte-equivalent branch snapshot was rerun locally before this README was written: **22/22 PASS**. A 10,000-case mutation fuzz pass against the reference parser/validator produced zero unexpected exception classes.

## Claim ceiling

This branch does **not** claim:

- that these files are integrated into the currently running P11 Resident;
- target ThinkPad/WSL V2 deployment;
- reboot persistence;
- provider/DeepSeek connectivity;
- WorkerCrystal scaling results;
- crash-safe durable exactly-once execution;
- production security or performance superiority.

The exact live P11 source-generation/path remains a source-binding prerequisite. Transplant/integration must occur only after that binding is positively recovered and collision-checked.
