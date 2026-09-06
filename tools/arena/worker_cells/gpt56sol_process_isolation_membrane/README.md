# Process-Isolation Membrane — implementation-bound repair

## Objective

Close the process-global patching blocker without allowing a spawned worker receipt to survive a same-name implementation change.

The original blocker remains:

`RegisteredModulePatch -> DedicatedProcess OR HOLD`.

The repair adds:

`IsolationReceiptCurrent => ExactFactorySpec AND ExactFactoryModuleBytes AND ParentWorkerIdentityParity AND ValidReceipt AND D0`.

`SameFactoryName != SameFactoryImplementation`.

`HistoricalIsolationReceipt != CurrentIsolationAdmission`.

A registered process-global module may still be patched only inside a dedicated spawned worker. The service keeps patch-sensitive state resident there and exposes bounded method RPC. Parent and worker now independently derive an exact identity for the factory module file. If the module bytes move between parent preflight and worker resolution, construction fails closed as `FACTORY_IDENTITY_DRIFT`. The worker receipt binds the exact factory identity and module-byte SHA-256 and verifies its own canonical receipt root.

## Scope and claim ceiling

This is a D0 process-isolation/currentness primitive. It proves only parity of the directly named factory module file within the current service construction. It does **not** authenticate provider/source truth, prove transitive package provenance, establish immutable filesystems, close explicit shared-memory/FD channels, execute AirLLM/GLM, establish physical performance, grant merge/deploy/effect authority, or Gate10.

PR #835 remains owner-blocked until its AirLLM security path adopts an isolation architecture (or removes process-global mutation) and is freshly reproved.

## J59 / HyperScale lineage

J59 requires reusable results to retain provenance, generation/currentness, source descent, unresolved gaps, and reopen triggers; source movement should reopen the minimum affected neighborhood rather than silently survive under an unchanged address. The factory implementation root is the smallest currentness binding needed here. Cardinality remains falsification geometry, not novelty.

## Shared-memory / provenance pressure

The modern shared-memory firewall independently preserves the same distinction: repeated/same-lineage state does not create fresh corroboration, and stale/source/domain movement must remain explicit. Recent MAP-Graph and governed-shared-memory research similarly treats ancestry/currentness and stale propagation as execution-time control concerns. These are design pressure only, not Arena parent authority.

## Verification target

- focused unit tests for process isolation, factory identity, receipt integrity, and fail-closed RPC;
- independent factory-currentness differential;
- HS1000 stale-factory mutations;
- registered-parent patch attacks;
- resident worker RPC campaign;
- exhaustive Omega8 and sampled 13D noncompensation checks;
- three freshly recreated stdlib-only virtual environments on frozen bytes.
