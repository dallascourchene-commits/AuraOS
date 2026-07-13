# Aura Model Cognome Refactor — MR-0 / MR-1 Status

**Branch:** `refactor/model-cognome-adaptive-router`  
**Base:** merged `main` commit `9742cc7a05adbf70b910584962c05c8e23afdb2b`  
**Scope:** topology-grounded inventory, canonical contracts, DIKWP provenance, and a local-first Cognome store.  
**Live adaptive routing:** deliberately not enabled in this slice.

## Reuse-before-invention inventory

| Existing Aura subsystem | Authority retained | Cognome relationship |
|---|---|---|
| `aura_capability_connectome.py` | Advisory capability graph; never patch authority | Remains Aura's internal capability graph. The next phase will add a stable graph digest and detailed path packet. |
| `aura_capability_resolver.py` | Reuse gate over CODEMAP, topology, affordances, lanes, plugins, workspaces, and Arena tools | Will provide the admitted capability path used to construct `TaskContext`. |
| `aura_model_probe_ledger.py` | Existing black-box provider/model/role observations and AuraFusion compatibility score | Preserved as a deterministic migration source. Imported rows remain `BEHAVIORAL_SURROGATE` / `INFERRED` evidence. |
| `aura_usage_normalizer.py` | Canonical usage normalization; unknown values remain `None` | Measurement fields exist in `ModelObservation`; runtime wiring remains deferred to telemetry MR-2. |
| `aura_pricing_registry.py` | Versioned pricing and provider-billed precedence | Price snapshots can be stored without replacing the registry. |
| `aura_empirical_cost_ledger.py` | Existing WAL cost and verification ledger | Retained as a linked authority store rather than merged or replaced. |
| `aura_fusion.py` | Existing panel and judge path | No competing panel implementation was introduced. |
| `aura_router.py` / `aura_llm_egress.py` | Public router compatibility and canonical model-egress boundary | Unchanged; no live model route changed. |
| ArenaExperience / OutcomeVector / Crucible | Governed outcomes and proposal-only learning | Unchanged; active policy mutation remains denied. |

## Implemented

### Canonical Cognome contracts

- Deterministic canonical JSON, BLAKE2 digests, and stable record IDs.
- Versioned endpoint identity with separate requested alias, returned model, fingerprint, access class, and lifecycle state.
- `TaskContext`, `RouteDecision`, `ModelObservation`, `ModelCapabilityEdge`, and split-isolated `CapabilityPosterior` contracts.
- Event IDs include event time, preventing distinct route or observation events from colliding.
- `ZERO_MODEL` cannot select a model profile.
- Probability, latency, cost, count, enum, and posterior invariants fail closed.
- Closed and gray-box endpoints cannot store `MECHANISTIC_OPEN_WEIGHT` evidence.
- Raw objective text is not retained in `TaskContext`.

### Local-first SQLite store

The public facade remains `aura_model_cognome_store.py`; implementation is split into bounded modules:

- `aura_model_cognome_store_schema.py`
- `aura_model_cognome_store_records.py`
- `aura_model_cognome_store_io.py`

The store provides:

- default `Aura_Memory/model_cognome.db`;
- WAL mode, `synchronous=NORMAL`, and foreign keys;
- explicit V1→V2 migration, including posterior split isolation;
- idempotent writes and deterministic outbox events;
- recursive credential, raw-prompt, and private-reasoning redaction;
- storage-boundary evidence-claim enforcement;
- deterministic legacy Model Probe Ledger import;
- task-bucket and Capability Connectome graph-digest candidate admission;
- verified-evidence requirements for validated model-capability edges;
- endpoint drift events that can quarantine or retire candidates;
- independent TRAIN / VALIDATION / SHADOW posteriors;
- explicit approval for `PAIRED_LIVE` experiment records;
- local export/import bundles with authority validation;
- no required cloud dependency.

### DIKWP provenance

- Append-only Data, Information, Knowledge, Wisdom, and Purpose envelopes.
- One correlation ID per chain.
- Required causal parent stages and source existence checks.
- Parent timestamps cannot follow child timestamps.
- Cyclic provenance is rejected.
- Wisdom must cite both Knowledge and the exact Purpose envelope whose digest it pins.
- Wisdom remains proposal-only.

### Portable schema and focused tests

- `schemas/model_cognome_v1.schema.json` dispatches typed records and pins authority invariants.
- Focused tests cover contracts, migration, storage, redaction, drift, split isolation, DIKWP, outbox behavior, explicit live-experiment approval, and bundle round trips.

Local validation of the hardened implementation:

```text
29 passed
```

Repository-native Python 3.10 and 3.12 checks are the merge authority. Known unrelated baseline failures remain documented separately in PR CI.

## Deferred to the next phases

- Stable Capability Connectome graph digest and detailed path packet.
- First-class Connectome results in `aura_capability_resolver.py`.
- The model↔capability bridge over validated evidence.
- Canonical usage, pricing, cost-ledger, latency, and ArenaExperience linkage.
- Shadow-only adaptive route evaluation.
- Live `ZERO_MODEL`, `DIRECT`, `CASCADE`, and `PANEL` execution.
- Endpoint probe suites and optional open-weight Jacobian Lens adapter.
- Crucible route-policy candidates and cloud/federation adapters.

## Authority invariants

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
closed_model_mechanistic_claims: denied
private_chain_of_thought_storage: denied
raw_prompt_storage_by_default: denied
active_route_policy_mutation: denied
learning_status: proposal_only
automatic_commit: false
automatic_push: false
automatic_merge: false
automatic_policy_promotion: false
```
