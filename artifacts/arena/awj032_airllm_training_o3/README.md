# AWJ032 O3 — Proof-carrying delegated-training operation bridge

State: D0 / nonpromoting / Gate10=false.

## Two fresh foreign parents
1. J235/O1 FrontDoor→Workcell→Stable Operation — Drive `17e4p6j8ajXLa95MxRoHiy5-DVdG3s_3-fyzT-NRPIks`, receipt `8060cceb39815ccf5073bb4f9049ad1f12d0fb09987b1418c974447c197d1fcb`. Keeper: stable semantic operation identity excludes volatile workcell/currentness/navigation/progress state; public work card is not execution evidence.
2. O17 Runtime-Native Delegated Training — Drive `1hNElhJANXg-9Q2Oq4RDzHeLfeIDx0a43XnIiqpK7ehk`, receipt `7067a7cd0a75e075418098e0dbaf430d42803b3c7023bdbe1254e8be2dbc37d3`. Keeper: delegated worker capsule is not a training permit; worker result is proposal-only and must be host-revalidated.

## Objective
Compose R1 current admission with a stable training-operation root, host-private current workcell lease, bounded delegated-training capsule, durable attempt identity, proposal-only worker result, and authenticated recovery verdict. Benign workcell/currentness reissue preserves the semantic training operation; source/intent/contract/payload/base/config/tokenizer/runtime/adapter identity movement rotates or holds the semantic operation.

## Hard laws
- `PublicWorkCard != ExecutionEvidence`.
- `DelegatedWorkerCapsule != TrainingExecutionPermit`.
- `WorkerProposal != CheckpointMutationAuthority != DeploymentAuthority`.
- `CurrentAdmission + CurrentWorkcell + StableOperation + DurableAttempt + ProposalBinding` are jointly required for D0 host-review admission.
- `UNKNOWN recovery => HOLD_RECONCILE_UNKNOWN`; only authenticated `NOT_STARTED` is a retry candidate; `COMPLETED => RETURN_ONLY`.
- K27/cache/navigation/currentness cannot compensate for a missing proof role.
- GLM-5.3 streamed training remains `HOLD_PORT_REQUIRED`.

## Proof
27 focused tests x 3 freshly recreated stdlib virtual environments = **81/81 PASS**. Each proof reran 30,000 frozen delegation states: 0 unsafe O3 admissions and 0 oracle mismatches. Across the three environments this is 90,000 campaign executions. Counterfactual simple gates on the same frozen campaign would admit 20,361 invalid states for admission-only, 16,135 for admission+workcell-only, and 958 when durable-attempt evidence alone is omitted. Twelve modeled hard-guard deletions were killed, survivors 0.

Omega8: 6,561 states, exactly one keeper. Factored 13D: 1,594,323 states, exactly one keeper, hard-invalid contextual repairs 0. HS1000: exactly 1,000 search/falsification cells -> eight consequence groups; cardinality breakthrough credit 0.

Receipt root `fb9a49dc713b295a73326636cc14534cf9affd9fc103eb66fa61e724ea86a316`. Three proof JSONs byte-identical, SHA-256 `04acc55d436a878f42f5559cbe70afb5443cf1bc7a237f705af598201fdfb303`.

## External counterplane
Attesting Outputs and Delegation Ancestry (arXiv:2608.30387) pressures deployer-side output binding plus authorization of delegation edges. The Provenance Paradox / LDP (arXiv:2603.18043) pressures explicit delegation contracts and claimed-vs-attested identity. Current practitioner reports independently pressure durable idempotency/reconciliation and treating `UNKNOWN` as a first-class state. External evidence is methodology pressure only, not Aura authority.

## Authority ceiling
No real delegated worker execution, model training/generation, tensor-payload read, checkpoint mutation, provider spend, deployment, main merge, public release, or Gate10 promotion is performed or authorized by O3.
