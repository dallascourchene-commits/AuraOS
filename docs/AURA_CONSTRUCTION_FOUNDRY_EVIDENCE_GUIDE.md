# Construction + Pascal Spatial Foundry Evidence Guide

## Evidence classes

| Evidence | Meaning | Not authority for |
|---|---|---|
| Git head/tree | Exact reviewed source identity | correctness by itself |
| Pascal lock/manifest/coordinate receipt | Exact local package, asset, scene, and transform chain | survey or Construction truth |
| Browser screenshots | User-visible current-run presentation | pixel attestation against a hostile browser |
| Director receipts | Admitted sequence, chapter, effect, evidence, and unchanged Construction digest | skipped or unexecuted chapters |
| Runtime Profile V2 proof | Positive, negative, preservation, fault, freshness, verifier, and cleanliness obligations | production deployment or merge |
| Attempt Archive | Durable failed/successful repair attempt evidence | automatic retry or promotion |
| U7 current reproof | Current P0/P1/reproof and human-disposition binding | Construction approval or automatic learning |
| Cleanup receipt | Bounded resource release and terminal lifecycle | proof of unrelated process cleanup |

## Required current-run artifacts

The V1 profile requires seventeen screenshots named `00-bilateral-intent.png` through `16-dissolved.png`, plus:

```text
browser-evidence.json
construction-foundry-projection.json
incident-replay-packet.json
runtime-profile-v2-proof.json
repair-attempt.json
preview-rollback-receipt.json
u7-current-reproof.json
attempt-archive-index.json
cleanup-receipt.json
```

The Runtime Harness additionally emits readiness, probe, server output, server termination, verification-command, and runtime-harness receipts. The V2 bilateral adapter separately emits the bilateral-Waboose receipt after V1 succeeds.

## Freshness rules

- Use a new external output directory for every run.
- Reject a dirty checkout.
- Bind the confirmation, V2 profile, verifier source, Git head, and source tree before execution.
- Treat every missing or stale artifact as unproved.
- Do not copy prior screenshots or receipts into a current run.
- Verify that Waboose does not mutate runtime traces.
- Verify that the repository identity is unchanged after execution.

## Network rules

All runtime serving is loopback-only. Pascal and the Foundry use retained local assets. Any request outside the declared loopback origin is a hard failure. A browser-policy block must appear in the failure evidence and cannot be transformed into a passing receipt.

## Review disposition

A complete proof may yield `RUNTIME_VERIFIED` and `READY_FOR_HUMAN_REVIEW`. Those dispositions do not grant merge, deployment, physical-work, professional, payment, access, or learning-promotion authority.
