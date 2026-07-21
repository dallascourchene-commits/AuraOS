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
  → current in-memory Relational Index
  → MINIMAL Atlas exact/prohibition plane
  → objective-bounded participant and assessment projection
  → Architect-compatible grounding packet
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
- bounded Atlas assessments and projection;
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

`build_relationship_atlas` now supports:

```python
snapshot = build_relationship_atlas(
    repo_root=Path("."),
    relational_index_data=current_index,
    profile="MINIMAL",
    persist=False,
)
```

This compiles a current Atlas in memory without writing generated artifacts. The canonical persisted build remains the default. `load_relationship_atlas` provides a public validated loader for stored snapshots.

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
  test_aura_live_architect.py
```
