# Aura Model Cognome Refactor — MR-0 / MR-1 Start

**Branch:** `refactor/model-cognome-adaptive-router`  
**Base:** merged `main` commit `9742cc7a05adbf70b910584962c05c8e23afdb2b`  
**Scope:** topology-grounded inventory plus canonical schemas and a local store.  
**Live adaptive routing:** deliberately not enabled in this slice.

## Reuse-before-invention inventory

| Existing Aura subsystem | Authority retained | Cognome relationship |
|---|---|---|
| `aura_capability_connectome.py` | Advisory capability graph; never patch authority | Remains Aura's internal capability graph. A later bridge will cite exact capability IDs and a stable graph digest. |
| `aura_capability_resolver.py` | Reuse gate over CODEMAP, topology, affordances, lanes, plugins, workspaces, and Arena tools | Will provide the admitted capability path used to construct `TaskContext`. |
| `aura_model_probe_ledger.py` | Existing black-box provider/model/role observations and AuraFusion compatibility score | Preserved as the migration source. The V1 store imports rows as `BEHAVIORAL_SURROGATE` / `INFERRED` evidence rather than treating the old aggregate score as routing authority. |
| `aura_usage_normalizer.py` | Canonical usage normalization; unknown values remain `None` | Its measurement classes are represented in `ModelObservation`; field-level wiring is deferred to telemetry integration. |
| `aura_pricing_registry.py` | Versioned pricing and provider-billed precedence | `price_snapshots` is included in the Cognome schema; runtime wiring is deferred. |
| `aura_empirical_cost_ledger.py` | Existing WAL cost/verification ledger | Retained as an authoritative linked store; Cognome uses stable IDs instead of replacing it. |
| `aura_fusion.py` | Existing panel and judge path | PANEL admission remains deferred; no competing Fusion implementation is introduced. |
| `aura_router.py` / `aura_llm_egress.py` | Public router compatibility and canonical model-egress boundary | Unchanged in MR-1. No live route behavior changes are introduced. |
| ArenaExperience / OutcomeVector / Crucible | Governed outcomes and proposal-only learning | Unchanged in MR-1. Policy learning remains proposal-only and deferred. |

## Implemented in this first slice

### `aura_model_cognome.py`

- Stable canonical JSON, BLAKE2 digests, and stable record IDs.
- Versioned endpoint identity and endpoint lifecycle states.
- `TaskContext`, `RouteDecision`, `ModelObservation`, `ModelCapabilityEdge`, and `CapabilityPosterior` contracts.
- Explicit `OPEN_WEIGHT`, `GRAY_BOX`, and `BLACK_BOX` access classes.
- A hard claim boundary that rejects mechanistic J-space labels for non-open-weight endpoints.
- No raw objective text is stored in `TaskContext`; only its digest is retained.

### `aura_model_cognome_store.py`

- Local default `Aura_Memory/model_cognome.db`.
- SQLite WAL mode, `synchronous=NORMAL`, and foreign keys.
- Core V1 tables for endpoints, fingerprints, task contexts, decisions, observations, model-capability edges, posteriors, latency distributions, price snapshots, comparisons, drift, DIKWP envelopes, outbox events, and migrations.
- Idempotent record writes with conflict detection.
- Recursive credential, raw-prompt, and private-reasoning redaction.
- Legacy `aura_model_probe_ledger.jsonl` import with deterministic source digests.
- Imported closed-model evidence is labelled `BEHAVIORAL_SURROGATE` and `INFERRED`.
- Candidate queries require validated support for every requested capability ID.
- Local JSON export bundles; no cloud dependency.

### `aura_dikwp_router_pipeline.py`

- Append-only Data, Information, Knowledge, Wisdom, and Purpose envelopes.
- Provenance requirements for Information, Knowledge, and Wisdom.
- Purpose digest pinning for Wisdom.
- Consequential-chain validation.
- Wisdom remains proposal-only.

### Portable schema and focused tests

- `schemas/model_cognome_v1.schema.json`
- `tests/test_aura_model_cognome.py`
- `tests/test_aura_model_cognome_store.py`
- `tests/test_aura_dikwp_router_pipeline.py`

Local focused validation before upload:

```text
14 passed
```

## Deferred with reason

- Capability Connectome graph-digest/path-detail changes: next additive integration step, after repository-native tests confirm current affordance shapes.
- `aura_capability_resolver.py` first-class Connectome packet: requires the stable graph digest above.
- Live `AdaptiveModelRouter`: explicitly excluded from MR-1.
- `ZERO_MODEL`, `DIRECT`, `CASCADE`, and `PANEL`: schemas exist, execution policy does not.
- Usage/pricing/latency wiring: belongs to unified telemetry MR-2.
- Endpoint probing and Jacobian Lens adapter: belongs to profiling MR-6.
- Crucible policy candidates: belongs to proposal-only learning MR-7.
- Cloud/federation adapters: local mode must remain sufficient first.

## Authority invariants

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
closed_model_mechanistic_claims: denied
private_chain_of_thought_storage: denied
raw_prompt_storage_by_default: denied
active_route_policy_mutation: denied
automatic_commit: false
automatic_push: false
automatic_merge: false
automatic_policy_promotion: false
```
