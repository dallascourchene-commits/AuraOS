# Provider Observation → Evidence Slice Bridge V2 (O6R)

This worker repairs the O6 bridge after the Evidence-Slice DAG moved from O3/v1 to O3R2/v2.

## Keeper laws

- `ProviderObserved != ProviderAttested`.
- `ProviderAttested != SemanticWitnessAdmission != SemanticTruth != EffectAuthority`.
- `ChangedProviderPaths -> ExactEvidenceInvalidationSeeds -> CurrentDAGPlan`.
- `CurrentDAGPlan => ExactDAGGeneration ∧ ExactDAGSchema ∧ ExactAdmissionSurfaceRoot ∧ ExactChangedRootBinding`.
- A provider attestation can establish provider-evidence status only. It cannot admit semantic witnesses for reuse.
- A semantic AdmissionSet can admit exact witness roots for reuse only. It cannot establish provider provenance.

## Current parent generation

Evidence-Slice DAG O3R2: `8d97a5f0fb0efefedf3daa2e36161c5eecc93fb1`, schema `AURA-EVIDENCE-SLICE-DAG-v2`.

The O3R2 plan surface adds `admission_surface_root`; reusable witness validity is externally admitted through exact witness roots and verifier generations. V2 consumes and binds that surface without authenticating or minting the upstream semantic receipt.

## Authority ceiling

D0 control-plane composition only. No provider/source provenance, semantic truth, automatic proof reuse/admission, model execution, hosted PASS, physical performance, merge/deploy authority, native/private transformer KV, effect authority, canonical promotion, or Gate10 is created by this worker.
