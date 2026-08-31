# EKI-3 — Cross-Generation Subject Identity + Version-Lineage Bridge V1

Status: DRAFT / D0 / HS1 / NONPROMOTING

## Earned predecessor

EKI-2 exact head `b13ba81aa671693828e4fd97bd5b222db5d49d94` earned terminal hosted SUCCESS in `Aura External Knowledge Store Writer V1` run `33420122351` on 2026-08-31. The exact-head Ubuntu job proved writer→independent-reader composition and the Windows job proved PowerShell/provider fail-closed behavior.

## Exactly two other-Agent artifacts used to mint this Objective

1. **PR #728 — WP03 ExternalCognitionResolveAdapterV1**
   - exact semantic head `9865c42f3ada2520141bd2fe30a439ce160ce2f8`
   - reader blob `53de9d551c81a0eb495eb180294c0aba5eb359d0`
   - dedicated run `33416056653` SUCCESS
   - reusable law: lookup is by exact semantic K; superseded rows are history-only; currentness, principal and evidence-domain validation are external; `MODEL_PREFIX_KV` is a different responsibility owner.

2. **PR #735 — current EKI→WP03 CoordinateMemoryCandidateV2**
   - exact green semantic head `89a66cdb972d3eab19c9408356b7061d1529947d`
   - candidate blob `fed7003630487af41586ce07a00b83b8fbf66835`
   - dedicated run `33417664825` SUCCESS
   - reusable law: stable `subject_key` is distinct from mutable `evidence_generation_key`; K27 XYZ is routing placement only; projection/candidate readiness does not grant persistent write authority.

## Collision discovered after EKI-2 closure

The EKI-2 writer and current EKI owner do not share one digest namespace.

Legacy EKI-2 identity:

`LegacySemanticId = SHA256({domain=AURA-EKI-EXTERNAL-SEMANTIC-ID-v1, source_kind, canonical_id})`

Current EKI subject identity:

`CurrentSubjectKey = SHA256({domain=AURA-EXTERNAL-SUBJECT-v1, provider, source_kind, canonical_id})`

Therefore:

`LegacySemanticId != CurrentSubjectKey`

and neither digest may be substituted for the other merely because both refer to the same external subject.

## Objective

Materialize the smallest typed bridge that can:

1. validate an exact current-owner subject descriptor and its current `subject_key`;
2. validate the one-to-one legacy-kind→current-(provider,kind) type relation where such a relation is unambiguous;
3. recompute the legacy EKI-2 semantic identity from the exact canonical subject coordinates;
4. bind every matching EKI-2 row to its exact record-generation key;
5. follow only explicit `successor` edges to produce one ordered, lossless version lineage;
6. refuse disconnected, branching, cross-subject, malformed or URI-drifted lineages rather than infer a latest record;
7. require external currentness before returning the explicit lineage terminal as a current record candidate;
8. hand the exact terminal record key to the independently owned PR #728 reader for final candidate validation.

## Residual equation

`CurrentStableSubject + EKI2VersionedRows + PR728ExactKeyReader != LawfulCurrentRecordUntil TypedIdentityBridge + ExplicitSuccessorLineage + ExternalCurrentness Commute`

## Invariants

`LegacySemanticId != CurrentSubjectKey`.

`CanonicalSubjectCoordinates -> {LegacySemanticId, CurrentSubjectKey}` only through explicit typed recipes.

`ExplicitSuccessorTerminal != ChronologicallyLatest != SourceCurrent`.

`K27Placement != SemanticIdentity != VersionOrder != Currentness != Authority`.

`PersistedCURRENTLabel != CurrentnessWitness`.

`LineageResolution != WriteAuthority != EffectAuthority`.

`CoordinateMemory != MODEL_PREFIX_KV`.

`SourceBoundExternalMap != NativePrivateTransformerKV`.

## External Different-J coordinate memory

`EKI3_EXTERNAL_COORDINATE_MAP_V1.json` records a bounded reopen map for current research pressure. It is deliberately a source-coordinate index, not a truth store or native model cache.

Primary research pressure:
- arXiv:2606.27472, *Supersede: Diagnosing and Training the Memory-Update Gap in LLM Agents* — current-value maintenance is a distinct failure mode and is not repaired merely by enlarging memory.
- arXiv:2606.26511, *Temporal Validity in Retrieval Memory* — stale and current facts can be embedding-near; explicit deterministic supersession materially reduces stale-fact failures in the reported benchmark.
- arXiv:2510.08109, *VersionRAG* — version sequences/change boundaries are modeled explicitly for evolving documents.

Community falsification pressure:
- Reddit r/LocalLLM, 2026-06-20, discussion of stale facts converges on write-time supersession/contradiction handling rather than similarity alone.
- Reddit r/Rag, 2026-06-16, production document-update discussion explicitly recommends temporal versioning and `superseded_by` state.

Direct task-specific Google Scholar-native retrieval on 2026-08-31 did not return a stable stronger primary record. This remains `SCHOLAR_DIRECT_GAP`; no Scholar provenance/currentness edge is invented.

## Triadic / Creation Process

Thesis: #735 proves stable subject identity must survive evidence-generation changes.

Antithesis: #728 requires exact row K, while EKI-2 intentionally gives each consequence-relevant record generation a distinct K.

Synthesis: retain both identity planes and add a typed descriptor bridge plus explicit successor-lineage resolver; never collapse one digest domain into the other.

Creation path:
`freeze EKI2 exact green -> bind #728 + #735 -> collision scan identity recipes -> derive typed mapping -> parse exact snapshot -> validate each record-generation binding -> follow explicit successors -> challenge disconnected/branch/cross-subject/URI drift -> require external currentness -> compose exact terminal with #728 -> hosted proof -> recurse`.

## Ω8 / eight crystalline walk allocation

- W0 / I3: exact EKI-2 head + exact #728/#735 artifacts + immutable source-coordinate map.
- W1 / S6: current subject descriptor → legacy identity → matching version rows → explicit successor chain → terminal candidate → PR728 read.
- W2 / C8: provider/kind/canonical-id/URI/hash/store/K27/currentness/responsibility substitutions.
- W3 / Antiprism: identity-domain collision discovered after EKI-2 proof; reopen only this smallest cone.
- W4 / Toroid: semantic identity, evidence generation, record generation, placement, store generation, currentness, authority and transformer-KV ownership remain independently invalidatable.
- W5 / Diamond: exact #728 × exact #735 other-Agent synthesis over the newly green EKI-2 substrate.
- W6 / K27: only exact duplicate subject descriptors collapse; coordinates never collapse identity/version/currentness.
- W7 / 13D Crystal: source/currentness/identity/reopen dimensions remain identity-bearing where consequence changes.
- W8: no effect fanout earned.

HyperScale classification: **HS1**. A single coupled identity/lineage cone is sufficient; duplicating workers would add evidence mass without adding a distinct consequence path.

## Hosted closure criterion

One exact child head must:

1. compile the EKI-3 bridge;
2. pass the focused adversarial battery;
3. blob-verify exact PR #728 and #735 parent artifacts;
4. validate the bounded external coordinate map and its nonauthority flags;
5. resolve a two-version current-subject fixture through EKI-3;
6. hand the exact terminal key to PR #728 and receive `FOUND_VERIFIED`;
7. hand the predecessor to PR #728 and receive `SUPERSEDED_HISTORY_ONLY`;
8. emit the full claim ceiling with no native/private transformer KV access.

Only terminal hosted SUCCESS closes EKI-3 and permits minting the next Objective.

## Claim ceiling

No canonical EKI owner replacement. No schema migration. No persistent-store write/mutation. No source currentness minted from persistence, timestamps, coordinates, hash order or successor-terminal status. No semantic truth/instruction/tool/provider/model authority. No K27 semantic authority. No native/private/hidden transformer KV access. No Gate-10, merge, deploy, spend, public, financial or human effect.
