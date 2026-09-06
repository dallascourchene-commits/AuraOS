# Atomic Absorption R3 — Resource-Lease CAS

Additive D0 worker surface around `atomic_absorption.py` v1.1.

Keeper law:

`PublishWithRuntimeResources => ExactOwnerHeadCAS AND ExactLeaseRegistryCAS AND AtomicManifest AND ValidCurrentLeases AND ResourceModeCompatibility AND NoActiveLeaseConflict AND NoProposalResourceConflict AND AuthorityNonWidening`

Corollaries:
- clean Git/worktree state does not prove runtime isolation;
- a WRITE requirement needs an EXCLUSIVE current lease;
- SHARED_READ leases may coexist only with other SHARED_READ leases;
- missing, expired, future, holder-mismatched, or mode-mismatched lease evidence cannot create publication readiness;
- owner-head movement or lease-registry movement after planning yields zero writes;
- exact resource bindings are folded into each proposal receipt before R1.1 consequence quotienting, so same-consequence/different-resource evidence is divergent rather than silently deduplicated;
- resource coordinates/lease identifiers never grant truth, currentness, or effect authority.

External pressure: MemTX (arXiv:2607.23929), CoAgent (arXiv:2606.15376), and recent practitioner reports that git worktrees isolate files but not shared databases/ports/services.

D0 only. This planner/simulator does not acquire/release OS leases, mutate services, merge PRs, deploy, call models/providers, or pass Gate10.
