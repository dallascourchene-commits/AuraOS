# SPEC_REFUTATION_CACHE — Reusable Negative / Refutation Cache

**Work Order:** WO-STAGE-002  
**Worker:** W2 — `G_F` / Falsifier-First Engine  
**Status:** STAGED / NONCANONICAL / HUMAN-GATE-REQUIRED

## 1. Objective

The Negative Refutation Cache (NRC) reuses **definite negative evidence only**. It exists to terminate repeated containment attempts cheaply when the same necessary obligation is already known to be defeated in the same validity scope and generation.

It is not a positive-proof cache and must never turn absence of a known refutation into PASS.

## 2. Exact key

Canonical key schema:

```text
(
  necessary_obligation,
  defeat_condition,
  validity_domain,
  generation
)
```

Normalized field names:

```text
obligation_id
defeat_condition
validity_domain
generation
```

The four fields are jointly identifying. No field may be omitted from cache lookup.

## 3. Entry shape

```text
RefutationEntry {
    obligation_id: str
    defeat_condition: str
    validity_domain: str
    generation: str
    disposition: FAIL              # constant
    reason: str
    evidence_refs: [str]
    evidence_digest: str | null
    source_head: str | null
    created_at: timestamp | null
    expires_at: timestamp | null
}
```

Only `FAIL` may be stored.

The entry's evidence may be candidate-specific. If so, the `validity_domain` must include a stable candidate/model fingerprint so reuse cannot cross candidate boundaries.

## 4. Storage invariants

```text
INV-1: cache contains FAIL only.
INV-2: UNKNOWN is never inserted as FAIL.
INV-3: PASS is never represented in the negative cache.
INV-4: lookup requires exact generation equality.
INV-5: lookup requires exact validity-domain equality.
INV-6: stale/expired refutations do not fire.
INV-7: cache miss means "no reusable refutation found", not PASS.
INV-8: cache hit short-circuits the matching obligation before evaluator execution.
```

Expected lookup complexity for a hash-map implementation is `O(1)`.

## 5. Negative-space algebra

```text
UNKNOWN != FAIL
UNKNOWN != PASS
MISS != PASS
EXPIRED_FAIL != CURRENT_FAIL
FAIL@generation_A != FAIL@generation_B
```

A missing observation channel, unavailable source, or unresolvable generation returns UNKNOWN unless a distinct policy explicitly establishes a definite defeat from that absence.

## 6. Generation isolation

A refutation at `G0` cannot poison `G1`:

```text
cache[(O, D, V, G0)] = FAIL
lookup(O, D, V, G1)  => MISS
```

Generation wildcarding is prohibited in the core cache. If an invariant is genuinely generation-independent, the caller must bind that fact into a separately authorized invariant-generation namespace rather than bypass the generation field.

## 7. Validity-domain discipline

`validity_domain` names the complete reuse boundary.

Examples:

```text
D0::JOINT_MARGINAL_MUTANT::fixture-v1
model:sha256:<digest>::policy:v3
source-head:<sha>::membership-generation:M7
```

Unsafe examples:

```text
global
all-candidates
current
```

unless those labels are themselves canonical immutable identifiers with independently enforced semantics.

## 8. Invalidation

An entry is unusable when any required binding changes:

- generation advances;
- validity-domain fingerprint changes;
- source head changes when source-head-bound;
- policy revision invalidates the defeat definition;
- evidence expires;
- cryptographic digest or proof binding is no longer recognized;
- identity/membership generation changes where relevant.

Recommended APIs:

```python
lookup(obligation_id, defeat_condition, validity_domain, generation)
record(refutation)
discard(exact_key)
invalidate_generation(generation)
invalidate_domain(validity_domain)
clear()
```

Broad invalidation is preferable to unsafe reuse when the dependency graph is uncertain.

## 9. Generation Coherence Matrix

The cache and receipt combiner share one currentness rule: individually valid evidence cannot be composed across incompatible world generations.

### 9.1 Pairwise matrix

`P(g)` means PASS bound to generation `g`; `U` means UNKNOWN; `F` means FAIL.

| A | B | Combined disposition |
|---|---|---|
| `P(g1)` | `P(g1)` | PASS candidate |
| `P(g1)` | `P(g2)` where `g1 != g2` | FAIL — incoherent bundle |
| `P(g1)` | `P(?)` | UNKNOWN |
| `P(g1)` | `U` | UNKNOWN |
| `U` | `U` | UNKNOWN |
| any | `F` | FAIL immediately |

### 9.2 Timestamp relation

Generation identity and timestamp freshness are orthogonal:

```text
coherent_generation = every PASS receipt generation == required_generation
fresh_enough = every required timestamp falls within policy window
```

Known generation mismatch is a definite coherence FAIL. Missing/unverifiable timestamp evidence is UNKNOWN unless the policy makes missing freshness evidence itself a definite defeat.

## 10. Refutation reuse protocol

```text
1. Construct exact key from the obligation being attempted.
2. Query NRC.
3. If a current exact FAIL exists:
     return FAIL immediately; do not execute evaluator.
4. If miss/expired:
     evaluate obligation normally.
5. If evaluator returns definite reusable FAIL:
     bind evidence + exact scope + exact generation and record.
6. If evaluator returns UNKNOWN:
     do not cache as FAIL; continue searching for another decisive obligation.
7. If evaluator returns PASS:
     do not write to NRC.
```

## 11. Threat / mutation checklist

The cache must withstand:

- stale-generation reuse;
- candidate-domain collision;
- self-certified completeness masquerading as refutation;
- correlated recursive checker reuse;
- omission of one key component;
- digest collision assumptions outside the selected cryptographic primitive;
- replay under a different policy/root/generation;
- shared mutable cache contamination between isolated branches.

## 12. Claim ceiling

This staging specification defines semantics and a bounded reference data model. It does not establish distributed cache consistency, persistence durability, cryptographic security, production invalidation latency, or universal completeness.
