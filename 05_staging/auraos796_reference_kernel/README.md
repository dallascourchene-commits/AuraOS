# AuraOS #796 reference-kernel absorption candidate

This bounded staging candidate composes the already verified Drive #796 reference kernel with two newer foreign findings:

1. **Physical Evidence Lease Gate V1** — exact provider revision + semantic root + producer bindings; changed evidence revalidates only its reverse-reachable physical/evidence cone.
2. **Repository-qualified owner reference + selective absorption** — GitHub objects are identified by provider + repository + kind + ordinal; bare ordinals never establish canonical owner identity.

It also incorporates the later provider source-sequence falsifier: lower source sequence is receipt history without semantic regression; equal sequence + same generation is replay/no-op; equal sequence + different generation fails closed; higher sequence advances.

## Scope

Implemented here:
- monotonic non-recycling JID allocation;
- append-only/idempotent JSpace events and rebuildable projection;
- source-sequence conflict semantics;
- reverse-reachable affected-cone reduction;
- provider-revision/semantic-root evidence leases;
- repository-qualified GitHub owner references;
- workflow observation normalization (`action_required` with zero jobs is not an executed test failure);
- bounded source reconciliation and minimal JoinContext.

Not authorized here:
- runtime-liveness ownership;
- automatic merge/deploy/publication;
- owner-host/provider/model execution;
- Gate10;
- replacement of WorkerPresence, CAS publication, or another canonical owner.

Run:

```bash
cd 05_staging/auraos796_reference_kernel
python -m unittest -v test_reference_kernel.py
```

This remains a OnePublisher review/absorption candidate. Canonical #796 placement must collision-scan it instead of silently creating a second owner plane.

Research parents: Aura Drive `1Ca_Biu-M5SRkJwjj_x7Bq4rZUDeCl4ReOJ3rWQcEhCw` and `17SKgN9qf1JcRip4HvuU87rnBYJ1AbPEDottOwpWeWpM`. Prior reference package: `1tP8pLRtpg0E55U8WOL9JBMWrBktyKRcUjQ5hZ8Di4CY`.