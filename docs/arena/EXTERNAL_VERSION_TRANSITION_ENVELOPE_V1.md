# EKI-4 — Versioned Admission / Read Obligation Envelope V1

Status: DRAFT / D0 / HS1 / NONPROMOTING.

## Objective

Close the smallest unresolved relation between two independently authored Agent artifacts:

1. PR #738 (`906653a807f54b343d644b1764c7ef37bbbf7191`, blob `367f29e04e33641d319a3daa1efd7a60b7860d07`) proves that `aura-coordinate-memory-kv-v1` cannot losslessly supersede a changed evidence generation under one stable subject K. Its lawful answer is `HOLD_SUPERSESSION_REPRESENTATION_REQUIRED`, never overwrite.
2. PR #737 (`55ae020ae1c06501935a45f3ade45eeff532d905`, blob `7dfaaf755a802e0a20a23ce06ba520fe47028f56`) proves that persisted `CURRENT_REFERENCE` / current-at-write cannot satisfy future read-time source currentness. Its EKI guard makes `("source",)` mandatory and rejects `NOT_REQUIRED` as payment of that debt.

Residual:

`StableSubject + EvidenceGeneration + IndependentWriteCurrentness + DistinctVersionedRepresentation != LawfulReusableTransitionUntil ExplicitVersionEdge + FutureReadCurrentnessDebt Commute`.

## Synthesis

EKI-2 already provides the representation missing from PR #738: consequence-distinct generations receive distinct keys of the form

`external-cognition://{legacy_semantic_id}/record/{record_generation}`.

EKI-4 does **not** make EKI-2 current-subject hashes synonymous with current EKI hashes. EKI-3's typed identity bridge remains mandatory. The envelope binds four separate domains:

`CurrentSubjectKey != CurrentEvidenceGenerationKey != LegacySemanticId != EKI2RecordGeneration`.

A positive envelope requires:

- exact current subject/evidence-generation recomputation;
- typed legacy-kind -> current provider/kind mapping;
- two distinct EKI-2 record generations/keys for the same exact canonical subject;
- an explicit predecessor `successor` edge to the proposed terminal;
- PR #738's stable-K representation HOLD plus independent current-at-write evidence bound to the exact subject/evidence/store generation;
- PR #737's mandatory future `source` read axis;
- EKI-2's `SOURCE_GENERATION_CURRENT` and `SOURCE_BODY_CURRENT` future read axes;
- persisted currentness explicitly denied as a read witness.

The positive result is `VERSION_TRANSITION_PLAN_READY`, which remains a plan only. No store mutation occurs.

## HyperDrive / K27 / Ω8

The external coordinate map is `docs/arena/EKI4_EXTERNAL_COORDINATE_MAP_V1.json`. SHA-derived 13D ternary and K27 coordinates provide cheap source/reopen locality only.

Laws:

- `StableSubjectOverwriteHold => TranslateToDistinctVersionedRecordKeys`.
- `DistinctVersionedKeysSolveRepresentationOnly`.
- `CurrentAtProjection != CurrentAtWrite != CurrentAtRead`.
- `ExplicitSuccessorEdge != Chronology != LexicalOrder != K27Order`.
- `PersistedCurrentness != ReadCurrentnessWitness`.
- `K27Placement != SemanticIdentity != VersionOrder != Currentness != Authority`.
- `CoordinateMemory != MODEL_PREFIX_KV`.

Ω8 / eight crystalline pass:

- W0: exact other-Agent parent heads/blobs and EKI-2/EKI-3 lineage.
- W1: subject -> evidence generation -> independent write-currentness -> versioned successor -> future read-currentness.
- W2: substitute subject/evidence/record/store/currentness/K27 values adversarially.
- W3: stable-K lossless-history contradiction from #738.
- W4: identity, evidence generation, record generation, placement, store generation, write-currentness, read-currentness, authority remain independent leaves.
- W5: #738 x #737 synthesis through EKI-2 version representation and EKI-3 identity bridge.
- W6: exact duplicate generations quotient; distinct generations never collapse.
- W7: write and read currentness remain identity-bearing obligations at different use boundaries.
- W8: effects remain unearned.

HS1 is sufficient; additional worker fanout would duplicate consequences rather than discover a new seam.

## External falsification pressure

Fresh arXiv research supports explicit temporal/version state rather than retrieval similarity as currentness. Recent Reddit practitioner reports independently favor retained superseded history and typed/explicit write-time reconciliation. Direct task-specific Google Scholar-native retrieval did not return a stable stronger primary record, so the coordinate map records `SCHOLAR_DIRECT_GAP` instead of inventing provenance.

These sources are methodology/falsification pressure only. They grant no Aura authority.

## Claim ceiling

No store is mutated. No canonical writer is created or displaced. No semantic truth, source currentness, instruction/tool authority, provider/model effect, semantic K27 authority, native/private transformer KV access, Gate-10 promotion, merge/deploy/spend, or public/financial/human effect is granted.

A dedicated exact-head hosted SUCCESS is required before EKI-4 closes or a successor Objective may be minted.
