# Aura Tensor Evidence Engine — Arena Integration

## Summary

A shared, local-first Tensor Evidence and Belief Propagation Engine that converts bounded Aura graphs into small tensor factors, evidence messages, and deterministic belief propagation. Integrated into three Arena surfaces: Coding Arena, Human Agent Arena, and Civic Commons Arena.

## Architecture

```
Aura Tensor Evidence Engine (aura_tensor_evidence.py)
        │
        ├── Coding Arena (aura_coding_tensor_adapter.py)
        │     code impact
        │     confinement
        │     boundary risk
        │
        ├── Human Agent Arena (CLI commands + API + visual panel)
        │     visual beliefs
        │     contradictions
        │     influence boundaries
        │
        └── Civic Commons Arena (aura_civic_tensor_adapter.py)
              evidence support
              scenario conflicts
              dissent
              consent gaps
```

## Core Engine

**File:** `aura_tensor_evidence.py`

### Variable States
- `SUPPORTED`
- `CONTRADICTED`
- `UNRESOLVED`

### Belief Propagation
- Damped, log-space, deterministic
- Defaults: damping=0.5, max_iterations=20, residual_tolerance=1e-4
- NaN/Inf rejection, maximum iteration cutoff, non-convergence fallback
- Statuses: CONVERGED, NOT_CONVERGED, CONTRADICTORY_HARD_FACTORS, INVALID_GRAPH
- Non-converged results remain visible and are not presented as resolved conclusions

### Tensor Compression
- NumPy SVD-based low-rank compression
- Reports original shape, compressed rank, element counts, reconstruction error
- Refuses compression when error exceeds threshold or no benefit

### Confinement Analysis
- Measures: internal edges, boundary edges, external effects, test closure, influence radius
- Levels: HIGH_CONFINEMENT, MODERATE_CONFINEMENT, LOW_CONFINEMENT, UNKNOWN
- Local recomputation allowed only when: region grounded, boundary influence below threshold, no unresolved high-risk external effects, evidence present, BP converged

### Authority Boundaries
```
patch_authority: exact_source_spans_and_hashes_only
tensor_patch_authority: false
belief_propagation_patch_authority: false
civic_decision_authority: false
```

The engine is **advisory only**. It never becomes patch authority, test authority, or Civic decision authority.

## Coding Arena Integration

**File:** `aura_coding_tensor_adapter.py`

### Variables
- TARGET_GROUNDED
- TEST_COVERAGE_PRESENT
- DEPENDENCY_IMPACT_BOUNDED
- PUBLIC_API_RISK
- EXTERNAL_EFFECT_RISK
- CHANGE_REGION_CONFINED
- READY_FOR_AGENT_HANDOFF

### Output
- Belief summary, supporting evidence, contradictions, unresolved variables
- Confinement score, boundary edges, influence radius
- Local recomputation recommendation
- Human-review recommendation
- Attached to Action Capsule as `tensor_evidence` (advisory field)

## Human Agent Arena Integration

### CLI Commands
```
python -m aura_agent_arena_cli tensor-analyze-coding --grounded --tests --deps 2
python -m aura_agent_arena_cli tensor-analyze-civic --session-id CIVIC-xxx
python -m aura_agent_arena_cli tensor-compress
python -m aura_agent_arena_cli tensor-contradictions --session-id CIVIC-xxx
python -m aura_agent_arena_cli tensor-confinement --session-id CIVIC-xxx
```

### API Endpoint
```
POST /api/civic/sessions/{id}/tensor-analyze
```

### Visual Panel
The Civic workspace includes a "Tensor Evidence Analysis" panel showing:
- Convergence status, iterations, max residual
- Supported, contradicted, and unresolved variables
- Confinement level and influence radius
- Evidence references

### Handoff Packet
When preparing agent tasks, the handoff includes:
- `tensor_evidence_summary`
- `tensor_graph_hash`
- `convergence_status`
- `confinement_score`
- `unresolved_variables`

## Civic Commons Arena Integration

**File:** `aura_civic_tensor_adapter.py`

### Variables
- NEED_SUPPORTED, OFFER_AVAILABLE, MATCH_FEASIBLE
- EVIDENCE_SUFFICIENT, SCENARIO_VIABLE
- BUDGET_INFORMATION_COMPLETE, LEGAL_INFORMATION_CURRENT
- REPRESENTATION_SUFFICIENT, CONSENT_UNRESOLVED
- DISSENT_PRESENT, PILOT_READY_FOR_DELIBERATION

### Civic Rules
- Preserves dissent
- Preserves representation gaps
- Shows unresolved evidence
- Shows conflicting contributions
- Shows missing consent
- Remains non-binding
- Never declares community consensus
- Never infers cultural profile
- Never overrides human/community decision

### Integration Point
Analysis runs after resource matching, MITOSIS, and MUSIC, and before final Civic export.
Result attached to session and decision packet as `tensor_evidence_analysis`.

## JSpace Integration
Only compact references are serialized:
- `tensor_graph_ref`, `tensor_graph_hash`, `tensor_domain`
- `convergence_status`, `maximum_residual`, `confinement_score`
- `supported_count`, `contradicted_count`, `unresolved_count`

Full graphs remain in the Arena session or local sidecar.

## Emergent-Capability Integration
Emergent candidates can become weak advisory factors only when they include evidence references.
Marked: `factor_origin: emergent_candidate`, `authority: advisory`.
They may influence ranking slightly but cannot create topology edges, alter code, or authorize decisions.

## Performance Measurement
Reports: graph variables, graph factors, tensor elements before/after compression, compression ratio, reconstruction error, BP iterations, maximum residual, convergence, execution time, peak memory estimate, nodes locally recomputed, total available nodes.

## Demo Commands

### Demo 1 — Coding Arena
```python
from aura_coding_tensor_adapter import analyze_coding_region
r = analyze_coding_region(source_grounded=True, tests_present=True, dependency_depth=2, node_ids=["node1"])
print(r["tensor_evidence"]["confinement"]["confinement_level"])
```

### Demo 2 — Human Agent Arena
```bash
python -m aura_agent_arena_cli tensor-analyze-coding --grounded --tests
python -m aura_agent_arena_cli tensor-compress
```

### Demo 3 — Civic Arena
```bash
python -m aura_agent_arena_cli civic-demo --story youth_centre
# Then analyze:
python -m aura_agent_arena_cli tensor-analyze-civic --session-id CIVIC-xxx
```

## Current Limitations
- CPU + NumPy only (no GPU acceleration)
- Loopy graphs may not converge within default iterations
- Compression is SVD-based for 2D+ tensors only
- Influence radius is estimated, not exact
- No quantum-grade performance claims
- No infinite scalability claims
