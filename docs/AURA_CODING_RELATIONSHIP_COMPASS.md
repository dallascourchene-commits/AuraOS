# Aura Coding Relationship Compass

> **Version:** `AURA_CODING_RELATIONSHIP_COMPASS_V1`
> **Owner:** `aura_coding_relationship_compass.py`
> **Authority:** read-only planning evidence; exact source spans and hashes remain patch authority.

## Purpose

The Coding Relationship Compass is the objective-scoped bridge between four existing Aura self-models:

| Plane | Question answered |
|---|---|
| Capability Connectome | Which reusable capabilities and implementations are relevant? |
| Emergent Evidence Spine | Which exact atomic functions, source hashes, dependencies, and tests ground the objective? |
| Relational Synthesis | Which temporary JIT configuration should be active for this one objective? |
| Relationship Atlas | What do the selected relationships mean, what must be preserved, what is missing, and what must not be wired? |

It does **not** merge these systems into a new truth store. Each source remains canonical. The Compass compiles a bounded packet for Architect, Surgeon, Coding Arena, and review surfaces.

## Why this layer exists

A broad prompt can mention architecture concepts without naming an exact file. Before this layer, Architect could fall back to filename-token matching and select a semantically adjacent but operationally incorrect module. A full global Atlas `STANDARD` scan is also unsuitable as a per-prompt operation: the July 20 full-repository harness contained 13,990 relational participants, which would imply about 97.8 million unordered participant-pair comparisons before filtering.

The Compass therefore uses this order:

```text
objective
  → canonical architecture component hints
  → Connectome capability path
  → exact Emergent Evidence Spine closure
  → six-slot intent packet
  → Relational Synthesis shadow capsule
  → validated current Relational Index (persisted, cached, or rebuilt)
  → deterministic bounded relational neighborhood
  → OBJECTIVE_STANDARD / OBJECTIVE_DEEP Atlas over that neighborhood
  → typed relationship compatibility hard guards
  → proposal-only Planning Board and Coding Breadboard receipt
  → bounded Emergent candidate discovery and verification
  → Change Graph, phase capsules, proposal-only Act Capsules, and Agent IR
  → Council V3 / Surgeon failure-class routing
  → governed bi-temporal experience projection template
  → Architect-compatible grounding packet and read-only bridge tools
```

The first compile is grounded against the current repository. In-process repeats are cached by repository root, repository head, atomic-inventory digest, and Connectome graph digest.

## Public API

```python
from aura_coding_relationship_compass import (
    compile_coding_relationship_compass,
    relationship_compass_grounding,
)

packet = compile_coding_relationship_compass(
    "combine Connectome, Relational Synthesis, and Atlas to code better",
    repo_root=".",
)

grounding = relationship_compass_grounding(packet)
```

The packet includes:

- exact recommended files, symbols, line ranges, and source hashes;
- required tests and bounded action-capsule hints;
- Connectome graph/path digests and execution classes;
- exact Emergent Evidence Spine packet and atomic inventory identity;
- a JIT Relational Synthesis capsule;
- a content-addressed relational neighborhood with inclusion reasons and truncation receipt;
- bounded objective-scoped Atlas assessments and projection;
- typed interface compatibility, exact hard-guard reasons, and required adapters;
- a proposal-only Planning Board plus human/machine Coding Breadboard receipt;
- bounded Emergent candidates with mechanism, benefit, risk, failure conditions, smallest experiment, and rejection/suppression receipts;
- a validated Change Graph, continuity-bound phase capsules, proposal-only Act Capsules, Agent IR, and Council/Surgeon routing;
- a governed relationship-experience projection template and explicit rollout receipt;
- relationships to preserve;
- required adapters, missing roles, and authority constraints;
- all active Atlas prohibitions;
- explicit non-authority flags.

## Architect integration

`ArchitectFusionCouncil.select_plan` invokes the Compass before legacy filename fallback for broad architecture/relationship objectives. When the Compass succeeds:

- the plan source is `deterministic_relationship_compass_plan`;
- legacy broad topology localization is not repeated;
- MUSIC-Mitosis fusion is skipped because bounded emergent and relational evidence is already included;
- the selected target remains proposal-only;
- downstream Builder/Surgeon work still requires exact patch generation, verification, and human review.

When the Compass cannot ground the objective, Architect fails closed to the existing Coding Arena grounding route and records the Compass error.

## Atlas improvements used by the Compass

The Compass first calls `extract_relational_neighborhood(...)` with explicit hop, node, edge, candidate-pair, byte, and elapsed-time budgets. It then calls `build_objective_relationship_atlas(...)` with `OBJECTIVE_STANDARD` or `OBJECTIVE_DEEP`. Global `STANDARD`/`DEEP` scans fail closed above the configured participant-pair limit. Objective snapshots are nonpersistent and cached only in a byte-bounded LRU whose removal does not change semantics.

Typed C5 preflight projects exact intent/evidence into two `RelationshipContract` records, checks direction, cardinality, lifecycle, actor, boundary, resource/data class, operation, policy, proof, prohibition, and budgets, then emits a proposal-only Planning Board and Coding Breadboard receipt.

## C6–C9 finalization

C6 runs only over the bounded C3 neighborhood and C5 compatibility result. It excludes exact, redundant, and prohibited pairs; preserves rejected and suppressed receipts; and never launches a generic repository scan. C7 converts accepted local evidence into a validated Change Graph, continuity checkpoints, proposal-only Act Capsules, SPEC-floor Agent IR, and explicit Council V3 versus Surgeon routing. C8 stores append-only, bi-temporal relationship experience derived from canonical receipts; decay changes advisory retrieval rank only and never canonical validity. C9 exposes six strict read-only/proposal-only bridge and MCP tools: `aura_compass_prepare`, `aura_compass_neighborhood`, `aura_compass_classify`, `aura_compass_breadboard`, `aura_compass_plan`, and `aura_compass_compile_capsules`.

Rollout defaults to `SHADOW`. `LIMITED` requires an explicit quality/verifier receipt. `PAIRED_LIVE` is rejected unless provider, bounded numeric budget, nonce, and verifier authorization are all supplied, and even an admitted paired-live receipt does not grant provider execution, patch, commit, PR, or merge authority.

## Safety and authority

```yaml
safe_to_patch: false
production_mutation: false
automatic_fix: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
human_review_required: true
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
```

Connectome recommendations, Atlas classifications, inferred motifs, and Relational Synthesis capsules are planning evidence. They cannot authorize source changes or promote candidate relationships to exact truth.

## Validation

```bash
python -m py_compile \
  aura_coding_relationship_compass.py \
  aura_relationship_atlas.py \
  aura_affordance_directory.py \
  aura_live_architect.py

python -m pytest -q \
  tests/test_aura_coding_relationship_compass.py \
  tests/test_aura_capability_connectome.py \
  tests/test_aura_capability_connectome_v2.py \
  tests/test_aura_relational_index.py \
  tests/test_aura_relational_synthesis.py \
  tests/test_aura_relationship_atlas.py \
  tests/test_aura_emergent_potential_repl.py \
  tests/test_aura_relationship_compass_finalization.py \
  test_aura_live_architect.py
```
