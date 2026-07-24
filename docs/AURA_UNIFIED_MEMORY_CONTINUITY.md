# AuraOS Unified Memory and Continuity Integration

> **Status:** bounded V1 integration contract  
> **Primary owner:** existing AuraOS intent, Architect, Model Cognome, Relationship Experience, QDKT, Crucible, and continuity owners  
> **Implementation:** `aura_unified_memory_continuity.py`  
> **Focused verification:** `tests/test_aura_unified_memory_continuity.py`  
> **Waboose request:** `.aura/waboose_requests/unified_memory_continuity.v1.json`

## 1. Purpose

This integration joins Manufactured Functional Memory Saturation and Continuity Sensitivity into one governed lifecycle:

```text
canonical human intent
  → minimum-sufficient active memory
  → canonical Act Capsule envelope
  → model-relative execution packet
  → committed P0 prediction
  → bounded execution
  → independently observed P1
  → prediction-error and continuity receipt
  → compact Continuity Delta
  → current-reproof eligibility
  → existing Relationship Experience / QDKT owners
  → human or community disposition
```

It does **not** create a universal memory database, continuity fabric, model-personality engine, truth store, router, verifier, policy engine, publication lane, or promotion authority.

## 2. Canonical ownership remains unchanged

| Concern | Existing canonical owner retained |
|---|---|
| Human objective and Purpose | Intent ingestion, FST/LEXC, and existing intent contracts |
| Atomic executable work | `aura_architect_loop.ActCapsule` |
| Exact model identity and empirical behavior | Model Cognome and Provider Registry |
| Repository and relationship evidence | CODEMAP, Connectome, Relational Index, Atlas, Compass |
| Architecture challenge and implementation | Council V3, Surgeon, Forge, bounded workers |
| Adversarial review | Coding Waboose |
| Runtime proof | Runtime Refactor Harness |
| Relationship lesson eligibility | Relationship Experience |
| Governed observations | QDKT |
| Replay and proposed learning | Crucible |
| Compact continuity | ST3GG, J-Space, State Ledger, Temporal Persistence, Attempt Archive |
| Human-readable evidence | Observatory and Luminance projections |
| Final disposition | required human or community authority |

The new module is a deterministic compatibility and compilation layer over those owners.

## 3. Core contracts

### 3.1 `IntentPacket`

`AURA_INTENT_PACKET_V1` freezes:

- objective;
- Purpose;
- user meaning;
- mode;
- Arena;
- constraints and prohibitions;
- authority envelope;
- acceptance criteria;
- required evidence;
- risk, cost, context, privacy, and freshness bounds;
- output contract;
- stable `intent_digest`.

The digest remains stable when a different model-specific prompt is compiled.

### 3.2 `SemanticLedger`

`AURA_SEMANTIC_LEDGER_V1` records operational definitions that can alter execution. Each term states:

- what it means;
- what it does not mean;
- exact source references;
- freshness.

The Act Capsule compiler fails closed when a required semantic term is absent.

### 3.3 `ArenaEvidenceSlice`

`AURA_ARENA_EVIDENCE_SLICE_V1` is the minimum causal evidence needed for one Act Capsule.

Each evidence item carries:

- exact evidence reference;
- causal reason it can change the next action, verification, or escalation;
- truth class;
- canonical owner;
- source digest;
- freshness;
- whether it is required.

`compile_arena_evidence_slice(...)` applies two deterministic rules:

1. **Saturation:** every required reference must be present and current.
2. **Noise removal:** non-required evidence is excluded and retained only as a reference.

This compiles active memory; it does not persist a new memory store.

### 3.4 `ActCapsuleEnvelope`

`AURA_ACT_CAPSULE_ENVELOPE_V2` wraps—without replacing—the existing `aura_architect_loop.ActCapsule`.

Before binding, the adapter requires a complete canonical `ActCapsule` round-trip, the current `AURA_ACT_CAPSULE_V1` version, an objective identical to the `IntentPacket`, and target file/symbol membership inside the declared edit scope.

It binds the canonical Act Capsule to:

- `IntentPacket`;
- `SemanticLedger`;
- `ArenaEvidenceSlice`;
- exact repository head;
- allowed files, symbols, tools, and effects;
- prohibited effects;
- invariants;
- acceptance bundle;
- repair budget;
- legal outcomes;
- mandatory P0;
- continuity requirements.

The legacy Act Capsule record and digest remain embedded for exact compatibility.

### 3.5 `ModelExecutionPacket`

`AURA_MODEL_EXECUTION_PACKET_V1` is disposable and recompilable.

It binds:

- the unchanged intent and Act Capsule digests;
- exact repository head, working-tree digest, and current source digest;
- exact provider/model profile and provider configuration;
- selected worker role and task slice;
- prompt structure;
- evidence placement and context order;
- examples and available tools, restricted to the canonical Act Capsule allowance;
- reasoning budget and output schema;
- uncertainty, stop, retry, and escalation rules;
- cross-model disagreement references;
- required verification depth.

A stale, expired, unknown, or mismatched model profile fails closed. Evidence outside the active Arena slice, role drift, or tool-scope expansion also fails closed. Cross-model disagreement increases verification depth; it never becomes voting authority.

### 3.6 `PredictionPacket` and `P1Observation`

`AURA_PREDICTION_PACKET_V1` commits P0 before action:

- current state digest;
- proposed transition;
- expected state delta;
- expected evidence;
- expected cost;
- expected risk;
- exact Act Capsule, ModelExecutionPacket, and model-profile digests;
- exact repository head and source digest inherited from the active evidence slice;
- producer identity;
- commit timestamp and immutable P0 digest.

All canonical JSON mappings are recursively frozen. A frozen dataclass cannot be bypassed by mutating a nested cost, example, observation, or embedded Act Capsule mapping after its digest is committed. Aggregate records are also bounded by the shared canonical packet-size limit.

`AURA_P1_OBSERVATION_V1` may be created only when the caller supplies the unchanged P0 digest and the record still recomputes to that digest. It binds:

- exact prediction identity;
- repository head and source digest;
- observed state delta and evidence;
- observed cost and risk;
- unresolved surprise;
- producer and independent verifier identities;
- verifier evidence;
- observation timestamp.

The observation must use the exact repository head and source digest committed in P0. The P0 producer cannot act as the independent P1 observer.

### 3.7 `ContinuitySensitivityReceipt`

`AURA_CONTINUITY_SENSITIVITY_RECEIPT_V1` deterministically interprets the P0/P1 delta.

It records:

- prediction-error class and exact deltas;
- consequence dimensions;
- protected pathways;
- mutation budget;
- replay burden;
- raw evidence references;
- missing measurements;
- replacement candidates;
- uncertainty and freshness;
- model, prompt/runtime, source, Purpose, and repository identity;
- independent verifier and human-disposition references.

It is proposal-only, is not a truth owner, and has no patch, VSA, promotion, publication, or merge authority.

### 3.8 `ContinuityDelta`

`AURA_CONTINUITY_DELTA_V2` is the compact post-act handoff. It updates active structural continuity and navigation references but is explicitly **not** a durable lesson.

### 3.9 Learning-to-reproof decisions

`evaluate_learning_to_reproof(...)` admits a candidate only when all required gates are satisfied:

- exact current source identity;
- exact current repository head;
- current continuity receipt;
- independent verification matching the verifier bound into the continuity receipt;
- complete verifier evidence and an explicit human/community disposition reference;
- required Crucible replay/current reproof;
- replacement and invalidation handling;
- required human or community disposition.

Failure returns exact blockers and a legal outcome rather than silently promoting the candidate.

`relationship_experience_kwargs(...)` prepares validated arguments for the existing `RelationshipExperienceObservation.create(...)` owner. It requires the continuity receipt and independent verifier to remain in the evidence bundle, enforces the canonical owner’s privacy classes, and does not persist an observation itself.

### 3.10 QDKT consequential admission

`evaluate_qdkt_consequential_admission(...)` accepts the typed continuity receipt, typed learning-to-reproof decision, and canonical `RelationshipExperienceObservation`. It keeps consequential QDKT admission closed until those records agree on repository/source/relationship identity, the current-reproof decision is eligible, raw continuity evidence remains complete, and the required human/community disposition is present.

The result remains proposal-only and has no crystallization, patch, policy, or promotion authority.

## 4. Authority invariants

All contracts preserve:

```yaml
planning_proposes: true
verification_proves: true
human_or_community_authority_disposes: true

automatic_fix: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
automatic_promotion: false

model_vote_authority: false
semantic_similarity_authority: false
vsa_patch_authority: false
continuity_receipt_truth_authority: false
```

Unknown, stale, malformed, non-finite, self-verified, mismatched, incomplete, or unauthorized records fail closed.

## 5. Focused use

```python
from aura_unified_memory_continuity import (
    ArenaEvidenceItem,
    AuthorityEnvelope,
    IntentPacket,
    IntentMode,
    SemanticDefinition,
    SemanticLedger,
    compile_act_capsule_envelope,
    compile_arena_evidence_slice,
    compile_model_execution_packet,
    commit_prediction,
    observe_prediction,
    derive_continuity_sensitivity_receipt,
    compile_continuity_delta,
    evaluate_learning_to_reproof,
)
```

The expected operator sequence is:

1. freeze the canonical `IntentPacket`;
2. resolve execution-changing terms in the `SemanticLedger`;
3. compile the minimum-sufficient `ArenaEvidenceSlice`;
4. wrap the existing canonical Act Capsule;
5. compile a packet for the exact current model profile;
6. commit P0;
7. execute only within the Act Capsule lease;
8. observe P1 independently;
9. derive the continuity receipt;
10. compile a Continuity Delta;
11. run Waboose, deterministic tests, and required runtime proof;
12. run Crucible/current reproof;
13. evaluate Relationship Experience and QDKT eligibility;
14. return evidence for human/community disposition.

## 6. Verification

Focused regression coverage includes:

- actual existing `ActCapsule` compatibility;
- actual Model Cognome endpoint identity;
- actual Relationship Experience integration arguments;
- full vertical lifecycle;
- canonical-owner preservation;
- stable canonical intent across distinct model packets;
- disagreement-driven verification depth;
- stale model-profile rejection;
- saturation and semantic-ledger failures;
- immutable P0 and ordered P1;
- independent-verifier enforcement;
- exact head/source binding;
- non-finite-number rejection;
- current-reproof, replacement, invalidation, and human-disposition gates;
- QDKT admission gates;
- Continuity Delta non-promotion;
- authority flags remaining false.

Run:

```bash
python -m pytest -q tests/test_aura_unified_memory_continuity.py
python aura_coding_waboose_cli.py run \
  --request .aura/waboose_requests/unified_memory_continuity.v1.json
```

Use the Architecture Harness and current CODEMAP before widening this vertical slice.

## 7. Deferred work

This V1 deliberately does not:

- add a persistence database;
- alter the canonical `ActCapsule` schema in place;
- modify Model Cognome storage;
- auto-write Relationship Experience or QDKT records;
- auto-run Council, Forge, Crucible, or runtime profiles;
- auto-update ST3GG, J-Space, State Ledger, Temporal Persistence, or Attempt Archive;
- auto-promote any lesson;
- grant publication or merge authority.

Further integration must be driven by exact current architecture evidence, bounded Act Capsules, Waboose findings, focused tests, current reproof, and required human/community approval.
