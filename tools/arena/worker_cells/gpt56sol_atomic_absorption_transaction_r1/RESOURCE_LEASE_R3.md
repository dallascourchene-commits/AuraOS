# Atomic Absorption R3 — Resource-Lease CAS + Commit-Time Revalidation

Additive D0 worker surface around the Atomic Absorption publication boundary.

Keeper law:

`PublishWithRuntimeResources => CanonicalPlanAuthentication AND ExactOwnerHeadCAS AND ExactLeaseRegistryCAS AND CommitTimeLeaseLiveness AND AtomicManifest AND ResourceModeCompatibility AND NoActiveLeaseConflict AND NoProposalResourceConflict AND AuthorityNonWidening`

Corollaries:
- clean Git/worktree state does not prove runtime isolation;
- a WRITE requirement needs an EXCLUSIVE live lease; SHARED_READ may coexist only with SHARED_READ;
- missing, expired, future, released, holder-mismatched, lineage-mismatched, or mode-mismatched lease evidence cannot create readiness;
- `LeaseRegistryRootAtT0 == LeaseRegistryRootAtT1` does **not** imply `LeaseLiveAtT1`; wall-clock aging is an independent currentness axis;
- a resource plan records `evaluated_at_s`; commit first reconstructs that exact original plan from authoritative owner/registry/proposals, then re-runs resource admission at `now_s` immediately before consequence;
- caller-constructed or mutated `ResourcePublicationPlan` values fail closed even if marked `READY`;
- owner-head movement or lease-registry movement after planning yields zero writes;
- exact resource bindings are folded into proposal receipts before semantic quotienting, so same-consequence/different-resource evidence remains divergent;
- resource coordinates, lease IDs, registry roots, plan objects, and K27 coordinates never grant truth, currentness, or effect authority.

External design pressure: dependency-scoped PlanFence-style validation, row-level invalidation contracts, transactional agent memory, and explicit multi-agent concurrency control all point toward revalidating only consequence-relevant state immediately before action. These references are design pressure, not authority.

D0 only. This planner/simulator does not acquire/release OS leases, mutate services, merge PRs, deploy, call models/providers, or pass Gate10.
