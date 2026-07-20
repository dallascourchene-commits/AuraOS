# Aura Architecture Relationship Atlas (AARA)

> **Canonical name:** Aura Architecture Relationship Atlas, abbreviated AARA or simply Relationship Atlas.

The Relationship Atlas is Aura's living architectural relationship intelligence plane. It continuously classifies, compares, and projects every relational connection across Aura's self-understanding models without becoming the duplicate owner of the underlying source facts.

## The Core Distinction

| Layer | Responsibility |
|---|---|
| **Relational Anatomy Index** | What participants and structural relations exist ahead of time (Aura's anatomy). |
| **Emergent Properties System** | What new combinations may be possible (Aura's discovery organ). |
| **Relationship Atlas** | What every architectural relationship currently means (Aura's living relationship intelligence). |
| **Relational Synthesis Capsule** | The temporary operational configuration activated JIT for one bounded objective. |

## Architecture

```text
CODEMAP / exact source / manifests / schemas / tests / runtime state
    → CodeTopoAnchor exact structural graph
    → complete atomic-function inventory
    → Capability Connectome and Resolver advisory capability anatomy
    → AOT Relational Anatomy Index
    → Architecture Relationship Atlas classification and motif plane
    → JIT objective-specific Relational Synthesis Capsule
    → Arena-specific Planning Board / Breadboard / ephemeral organ
    → bounded execution, investigation, or explanation
    → exact verification and human or community decision
    → relational experience receipt and current reproof
```

The Atlas is a **compiled, evidence-bound status and intelligence plane** over Aura's existing self-models. Every exact Atlas claim points back to its canonical owner. Every inferred classification remains visibly advisory. Every candidate connection remains ungrounded until exact owners and verifiers establish it.

## 8 Orthogonal Dimensions of a Relationship

Every relationship is classified along these eight dimensions, avoiding lossy flattening into simple enums:

1. **Structural Status**: `EXACTLY_WIRED`, `DECLARED_WIRED`, `UNWIRED`, `PARTIALLY_WIRED`, `TEMPORARILY_WIRED`, `STALE_WIRING`, `UNRESOLVED`.
2. **Semantic Relationship**: `DIRECTLY_RELATED`, `OVERLAPPING`, `COMPLEMENTARY`, `AUXILIARY`, `ADJACENT`, `REDUNDANT`, `COMPETING`, `UNRELATED`, `CONTRADICTED`.
3. **Wiring Disposition**: `REQUIRED`, `RECOMMENDED`, `OPTIONAL`, `CANDIDATE`, `DEFERRED`, `NOT_NEEDED`, `PROHIBITED`.
4. **Readiness**: `READY`, `NEEDS_GROUNDING`, `NEEDS_MISSING_ROLE`, `NEEDS_SCHEMA`, `NEEDS_TEST`, `NEEDS_VERIFIER`, `NEEDS_AUTHORITY`, `NEEDS_CONSENT`, `NEEDS_LEASE`, `NEEDS_RESEARCH`, `TOO_RISKY`, `DREAM_ONLY`.
5. **Lifecycle**: `PERSISTENT`, `OBJECTIVE_SCOPED`, `LEASED`, `EPHEMERAL`, `DORMANT`, `DEPRECATED`, `DISSOLVED`.
6. **Truth Class**: `EXACT_SOURCE`, `EXACT_SCHEMA`, `EXACT_TEST`, `EXACT_MANIFEST`, `EXACT_RUNTIME`, `ADVISORY_CONNECTOME`, `ADVISORY_AFFINITY`, `INFERRED_MOTIF`, `UNRESOLVED`.
7. **Authority Posture**: `READ_ONLY`, `ADVISORY_ONLY`, `PROPOSAL_ONLY`, `VERIFIER_REQUIRED`, `HUMAN_AUTHORIZATION_REQUIRED`, `COMMUNITY_AUTHORIZATION_REQUIRED`, `MUTATION_LEASE_REQUIRED`, `EXECUTION_ALLOWED`, `EXECUTION_PROHIBITED`.
8. **Proof Status**: `OPEN`, `SATISFIED`, `CONTRADICTED`, `DEFERRED`.

### Derived High-Level Labels

The dimensions generate user-facing labels:

- **`EXPLICITLY_WIRED`**: `structural_status=EXACTLY_WIRED`, `truth_class ∈ exact`, `freshness=CURRENT`.
- **`OVERLAPPING_UNWIRED`**: `structural_status=UNWIRED`, `semantic_relationship=OVERLAPPING`.
- **`AUXILIARY_ADJACENT`**: `semantic_relationship ∈ {AUXILIARY, ADJACENT}`.
- **`POTENTIAL_WIRING`**: `wiring_disposition=CANDIDATE`, `readiness ∉ {TOO_RISKY}`.
- **`MISSING_PIECE`**: `readiness=NEEDS_MISSING_ROLE`, `motif_completion_ratio > threshold`.
- **`CONTRADICTED_OR_INCOMPATIBLE`**: `semantic_relationship=CONTRADICTED` or `proof_status=CONTRADICTED`.
- **`SHOULD_NOT_BE_WIRED`**: `wiring_disposition=PROHIBITED`, `prohibition_evidence` present.

## Operational Profiles

The Atlas supports three scan profiles controlling discovery depth:

| Profile | Features enabled |
|---|---|
| **MINIMAL** | Exact relations, declared relations, applicable prohibitions, one-hop missing roles. No overlap/auxiliary/candidate/motif scan. |
| **STANDARD** | Adds overlap detection, auxiliary/adjacent detection, candidate discovery, and motif search. |
| **DEEP** | Adds redundancy/competition analysis and cross-Arena candidate generation. |

All profiles remain bounded and read-only unless a separate authorized workflow acts on the output.

## Prohibitions and Rejected-Wiring Registry

The Atlas preserves negative knowledge to prevent the discovery organ from repeatedly proposing unsafe or prohibited paths. All seven builtin prohibition patterns are evaluated during every build:

| Pattern | Family | Description |
|---|---|---|
| `affinity_mutation_block` | authority | VSA/affinity similarity must never authorize mutation. |
| `self_verification_block` | security | A producer must not verify its own results without independent corroboration. |
| `agent_self_upgrade_block` | truth_ownership | External agents cannot self-upgrade candidate relations to exact. |
| `circular_authorization_block` | recursion | Circular authority paths are forbidden. |
| `ephemeral_lease_leak_block` | lifecycle | Ephemeral leases must not persist beyond TTL. |
| `research_production_coupling_block` | domain | Direct coupling of production mutation to unverified research is prohibited. |
| `cross_arena_coupling_block` | domain | Direct un-adapted coupling between isolated Arenas is prohibited. |

## Higher-Order Motif Registry

The Atlas maintains a registry of reusable role-labelled motifs for missing-configuration detection:

| Motif | Required Roles | Expected Capability |
|---|---|---|
| `input_to_authority` | external_input, parser, schema_validator, authority_guard, verifier | admitted_governed_operation |
| `state_lifecycle` | state_read, transformation, state_write, persistence, restore, invalidation | safe_state_management |
| `review_packet_integrity` | focal_symbol, dependency_closure, exact_endpoints, source_slices, verifier | verifiable_review_packet |
| `external_agent_lease` | objective, route, lease, temporary_identity, verifier, dissolution | governed_external_agent_task |
| `learning_to_reproof` | finding, grounding, crucible_proposal, validation, current_reproof | verified_empirical_learning |
| `spatial_explanation` | participant, assessment, scene_projection, drill_down | grounded_visual_orientation |
| `cross_arena_adapter` | source_arena, export_schema, privacy_filter, adapter, destination_arena | sovereign_arena_federation |

## Generated Artifacts

```text
.aura/RELATIONSHIP_ATLAS.json          — compiled snapshot
.aura/RELATIONSHIP_ATLAS_RECEIPT.json  — build receipt
.aura/RELATIONSHIP_ATLAS.md            — human-readable index
.aura/RELATIONSHIP_ATLAS_DELTA.json    — delta from previous build (if exists)
```

Generated artifacts are caches and navigation outputs. They are not source truth and must exclude themselves from scanning.

## Data Contracts

### `AtlasParticipantRef`

References an existing Relational Participant rather than duplicating it. Contains: `participant_id`, `participant_digest`, `participant_type`, `canonical_owner`, `canonical_ref`, `freshness`.

### `AtlasRelationshipAssessment`

A multidimensional assessment of one architectural relationship. Every claim references a canonical owner. Contains all 8 dimensions plus `participant_refs`, `role_bindings`, `relation_types`, `canonical_owner_refs`, `evidence_refs`, `missing_roles`, `required_adapters`, `authority_constraints`, `temporal_conditions`, `expected_benefits`, `risks`, `prohibited_effects`, `relationships_to_preserve`, `confidence`, `freshness`, `boundary`, `assessment_digest`.

### `MissingRelationalConfiguration`

Identifies a missing participant or relation in an otherwise coherent higher-order configuration. Contains: `configuration_id`, `motif_type`, `objective_family`, `bound_roles`, `missing_roles`, `completion_ratio`, `candidate_participants_by_role`, `hard_blockers`, `required_evidence`, `required_verifiers`, `required_authority`, `expected_capability`, `risk_class`.

### `RelationshipProhibition`

A first-class prohibition record. Contains: `prohibition_id`, `pattern`, `participant_types`, `relation_types`, `prohibition_family`, `reason`, `canonical_rule_refs`, `evidence_refs`, `exceptions`, `current_reproof_required`.

### `AtlasSnapshot`

The full AOT compiled view. Contains all assessments, missing configurations, prohibitions, reverse indexes, boundary, and a content-addressed `snapshot_digest`.

### `AtlasDeltaReceipt`

Records changes between two snapshots: added/removed exact relations, reclassified relationships, new/resolved candidates, new/resolved missing roles, stale assessments.

## Python API

```python
from aura_relationship_atlas import (
    build_relationship_atlas,
    validate_relationship_atlas,
    relationship_assessment,
    relationships_for_participant,
    relationships_for_objective,
    find_overlapping_unwired,
    find_auxiliary_adjacent,
    find_missing_configurations,
    find_candidate_wirings,
    find_prohibited_wirings,
    explain_relationship,
    diff_relationship_atlases,
    compile_atlas_projection,
)

# Build with STANDARD profile (default)
snapshot = build_relationship_atlas(repo_root=Path("."), profile="STANDARD")

# Validate invariants
report = validate_relationship_atlas(snapshot)

# Query relationships
related = relationships_for_participant("relp_...", snapshot)
overlaps = find_overlapping_unwired(snapshot)
candidates = find_candidate_wirings(snapshot)
missing = find_missing_configurations(snapshot)
prohibitions = find_prohibited_wirings(snapshot)

# Compile a bounded projection for visualization
projection = compile_atlas_projection(
    focal_participant_ids=["relp_..."],
    snapshot=snapshot,
)

# Diff two snapshots
delta = diff_relationship_atlases(previous_snapshot, current_snapshot)
```

## Command Line Interface

```bash
# Build snapshot from relational index (STANDARD profile by default)
python -m aura_relationship_atlas build
python -m aura_relationship_atlas build --profile MINIMAL
python -m aura_relationship_atlas build --profile DEEP

# Show atlas snapshot summary and build receipt
python -m aura_relationship_atlas status

# Validate atlas invariants
python -m aura_relationship_atlas validate

# Query relationship assessments for a participant
python -m aura_relationship_atlas query --participant <id>

# List overlapping unwired relationships
python -m aura_relationship_atlas overlaps

# List candidate wirings (non-prohibited)
python -m aura_relationship_atlas candidates

# List missing configuration motifs
python -m aura_relationship_atlas missing

# List active prohibitions
python -m aura_relationship_atlas prohibited

# Explain the full relationship assessment details
python -m aura_relationship_atlas explain --assessment <id>

# Compute deltas between snapshots
python -m aura_relationship_atlas diff --previous <path_to_previous.json>

# Refresh atlas after changed paths
python -m aura_relationship_atlas refresh --changed <path1> <path2>
```

CLI output is bounded by default. Full source disclosure remains opt-in and authority-controlled.

## Canonical Invariants

```yaml
relationship_atlas_is_compiled_view: true
relationship_atlas_is_truth_owner: false
relationship_atlas_is_patch_authority: false
relationship_atlas_is_execution_authority: false
exact_relationships_require_current_canonical_evidence: true
advisory_relationships_remain_advisory: true
candidate_relationships_cannot_self_promote: true
missing_roles_are_explicit: true
intentional_non_wiring_is_explicit: true
prohibited_relationships_require_rationale: true
hard_guards_precede_candidate_ranking: true
cross_arena_truth_owners_remain_canonical: true
spatial_projection_is_explanatory_only: true
tensor_projection_is_advisory_only: true
learning_requires_verified_current_reproof: true
external_agents_receive_bounded_projections: true
human_or_community_authorization_is_preserved: true
source_spans_and_hashes_remain_patch_authority: true
planning_proposes: true
verification_proves: true
human_or_community_authority_decides: true
```

## Integration Across Aura Architecture

The Atlas is designed to integrate with every Aura surface:

- **Six-slot FST**: The slots select an Atlas query frame (DIR→neighborhood, ASP→lifecycle, CLASS→relation family, SUBJ→focal participant, VOICE→authority, STEM→action).
- **Capability Connectome**: Atlas adds under-wired capability detection, orphaned implementations, and prohibited capability combinations.
- **Emergent Evidence Spine**: The Spine grounds; the Atlas classifies.
- **Emergent Properties**: Becomes a higher-order Atlas discovery engine (role-labelled configurations, not just pairwise).
- **Planning Board**: Distinguishes exact vs proposed edges, missing prerequisites, prohibited actions.
- **Coding Waboose**: Provides complete causal paths, missing verifier/test roles, prohibited coupling patterns.
- **Council V3 / Architect / Surgeon**: Council receives Atlas deltas; Surgeon receives bounded repair surface with preservation relationships.
- **Agent Bridge**: External agents receive bounded Atlas projections (required, auxiliary, candidate, missing, prohibited relationships).
- **Observatory**: Primary explanation surface for the Atlas with drill-down to exact evidence.
- **Crucible**: Stores relationship motifs rather than simplistic blame labels.

## Testing

```bash
python -m py_compile aura_relationship_atlas.py tests/test_aura_relationship_atlas.py
python -m pytest tests/test_aura_relationship_atlas.py -v --tb=short -p no:xdist
```

The test suite covers 38 tests across: contract tests, exact wiring classification, overlap detection, all 7 prohibition patterns, auxiliary/adjacent detection, operational profiles, CLI commands, delta generation, schema round-trip, motif registry integrity, and boundary self-exclusion.

## Authority Boundary

The Relationship Atlas is a **relational type system, architectural diagnostic plane, and missing-configuration map**. It is not:

- a duplicate truth store;
- patch authority;
- execution authority;
- a second graph authority;
- a replacement for canonical owners.

Unknown, stale, ungrounded, malformed, expired, ambiguous, or unauthorized Atlas work fails closed.

## Suggested Capability Registration

```text
aura.relationship.atlas
aura.relationship.atlas.query
aura.relationship.atlas.motifs
aura.relationship.atlas.prohibitions
aura.relationship.atlas.spatial_projection
```

Connectome declarations remain advisory.
