# Provider Observation -> Evidence Slice Invalidation Bridge V1

D0 composition membrane rebased from:

1. AGENT_10 Provider-Bound Efficiency Rebind V1 — provider-neutral carrier movement must be bound to exact parent/child/generator/changed paths and cannot compensate for efficiency-projection drift.
2. Evidence-Slice DAG Minimum Recompute O3 — exact changed evidence roots wake only their dependency-closed descendants; unrelated current/verified witnesses may survive.

## New seam

A provider-visible source movement is not automatically an attested provenance statement. This bridge removes a naked `provider_observation_verified` boolean from the recovery path by carrying a recoverable provider observation envelope with evidence URI, payload digest, verifier identity/generation, and explicit status:

`OBSERVED | ATTESTED | CONTESTED | EXPIRED | INDETERMINATE`.

Only `ATTESTED` may seed a downstream evidence-slice invalidation request. The bridge then maps exact changed paths to evidence-node IDs and requires the independent Evidence-Slice DAG owner's returned plan to bind the exact graph root and exact mapped changed-root set.

`ProviderObserved != ProviderAttested`.
`ProviderAttested != SemanticTruth != EffectAuthority`.
`ChangedPaths -> ExactEvidenceInvalidationSeeds -> DependencyClosedReproofByDAGOwner`.
`UnmappedPath | NonNeutralPath | UnacceptedVerifier | NonAttestedStatus | GraphOrChangedRootMismatch => HOLD`.

This worker does not recompute the DAG closure and does not reimplement either parent owner. It validates the cross-owner handoff.

## External pressure

SLSA v1.2 distinguishes source-control observation from Source Provenance issued by the source-control system, and describes Source Provenance as contemporaneous evidence about how a revision came to exist. in-toto supplies a standard attestation framework; Sigstore separates signing from verification and binds keyless signatures to identities/transparency evidence. Recent agent-provenance research likewise separates final-result correctness from process/evidence provenance.

Direct task-specific Google Scholar retrieval produced no stable Scholar-native result in this pass (`SCHOLAR_DIRECT_GAP`). Reddit material is practitioner pressure only.

## Claim ceiling

No cryptographic/provider truth is minted by this local module. `ATTESTED` is an externally established evidence state consumed by the bridge; if the provider is merely observable, the correct result is `HOLD_PROVIDER_EVIDENCE`. No model/provider execution, physical performance claim, merge/deploy authority, private/native transformer KV access, effect authority, or Gate10.

## Final falsification receipt

After a failed-first taxonomy test (duplicate path binding was safely rejected but routed to the wrong HOLD owner), the classifier alone was repaired and all three virtual environments were recreated.

Final credited proof on frozen bytes:
- 30/30 tests per environment = 90/90 PASS total;
- 100,000 independently spelled transition/bridge decisions per environment = 300,000 total, 0 oracle mismatches;
- identical oracle root `0e9860d36fafa9512c6014c267c72cfa012a4d599938d4893653cd0c41aa7e5a`;
- identical campaign root `11955f49f389e4ab6d67e3c6e34ad00481c028cbe2de9d6b590c481031e3cdea`;
- identical valid synthetic attested receipt root `d05453f8e202cafcf6bd8dcc89018f1f48a698dc74774ddfd99dc2f389e6e2a8`;
- Omega8: all 6,561 states, exactly one `REPROVE_MINIMUM_SLICE` keeper;
- 13D: all 243 trailing contexts explicitly applied against one hard-invalid core, zero repairs;
- HS1000: 1,000 mutation challenges, zero false slice admissions.

Connected GitHub PR #834 observation snapshot:
- payload SHA256 `dcdb372c7516c79f078e3988c74f3f7e66325dd90533bdb66eeca091bbc7b3f9`;
- observation root `1633ddd4cdc57f1fbda56dd9f535e50c4d676c4d07a9567bc89ec5ac0791a6d9`;
- bridge receipt root `841c2f25f756901b80167fe600a92b74a5c80bb8bbd5b3e323361bcaf88ac394`;
- decision `HOLD_PROVIDER_EVIDENCE` because the connected provider surface was observed, not cryptographically/source-provenance attested.
