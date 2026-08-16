# SPEC_FALSIFIER_ROUTING — Falsifier-First Containment Routing

**Work Order:** WO-STAGE-002  
**Worker:** W2 — `G_F` / Falsifier-First Engine  
**Status:** STAGED / NONCANONICAL / HUMAN-GATE-REQUIRED  
**Execution mode:** Fail-Closed / Negative-Space Isolation

## 1. Purpose

Containment is a conjunction of necessary obligations. A candidate closure is embeddable only when every required obligation is positively established for the same admissible world generation.

Let `O = {o_1, ..., o_n}` be the necessary obligations for candidate closure `W` under policy `P`:

```text
Embed(W, P) => AND_{o in O} Pass(o)

exists o in O : Fail(o)  =>  NOT Embed(W, P)
```

The engine is **falsifier-first**: it searches for cheap, decisive defeats before spending work on expensive semantic or cryptographic proof checks.

## 2. Three-valued decision algebra

The only dispositions are:

```text
PASS     obligation established for the exact stated scope
FAIL     a definite defeat condition is established
UNKNOWN  available evidence is insufficient to establish PASS or FAIL
```

Hard invariants:

```text
UNKNOWN != FAIL
UNKNOWN != PASS
FAIL dominates a conjunction immediately.
UNKNOWN does not dominate a later definite FAIL.
PASS is returned only when every required obligation is PASS.
```

Conjunction reduction:

| Seen FAIL? | Seen UNKNOWN? | End disposition |
|---|---:|---|
| yes | any | FAIL immediately |
| no | yes | UNKNOWN |
| no | no | PASS |

## 3. `evaluate_containment_fast`

Reference semantics:

```python
def evaluate_containment_fast(candidate_closure, required_obligations):
    first_unknown = None

    for obligation in order_for_falsification(required_obligations):
        cached = negative_cache.lookup(obligation.exact_refutation_key)
        if cached is not None:
            return FAIL(cached)  # no evaluator call

        result = obligation.evaluate(candidate_closure)

        if result is FAIL:
            if result.reusable_for_exact_scope:
                negative_cache.record(result.refutation)
            return FAIL(result)  # do not evaluate any remaining obligation

        if result is UNKNOWN and first_unknown is None:
            first_unknown = result

    return UNKNOWN(first_unknown) if first_unknown else PASS
```

### Complexity claim ceiling

- Exact negative-cache lookup is expected `O(1)` for a hash-map implementation.
- An indexed generation/hash/fact check can be `O(1)`.
- **Once a definite FAIL is obtained, termination is immediate and remaining obligations are not evaluated.**
- Finding an arbitrary first failure among previously unevaluated black-box checks is `O(k)` where `k` is the position of the first discovered failure (`O(n)` worst case). No stronger claim is made.

This distinction prevents the invalid claim that arbitrary failure discovery itself is `O(1)`.

## 4. Falsifier ordering heuristic

Ordering is deterministic and evidence-aware. It has two levels.

### 4.1 Hard tiers

Evaluate lower tiers first:

1. **T0 — exact cached refutation**
   - exact `(obligation, defeat, domain, generation)` cache hit
2. **T1 — cheap currentness/integrity defeats**
   - generation mismatch
   - authoritative world-head mismatch
   - digest/hash mismatch
   - malformed/missing required receipt fields
   - expired validity window
3. **T2 — structural/local obligations**
   - membership/identity consistency
   - dependency presence
   - local admission constraints
   - path/root binding
4. **T3 — semantic/compositional obligations**
   - common-mode reasoning
   - cross-domain composition
   - semantic equivalence
5. **T4 — expensive proof verification**
   - ZK proof verifier
   - independent UNSAT/proof certificate verification
   - other high-cost external verifiers

A known T1 defeat must prevent T3/T4 work.

### 4.2 Within-tier priority

When trusted estimates exist, sort descending by:

```text
priority(o) = p_fail(o) / max(cost(o), epsilon)
```

Tie-break deterministically by `obligation_id`.

If cost/failure estimates are absent, stale, self-certified, or untrusted, ignore them and retain stable declared order. Optimization metadata may change order; it may not change semantics.

## 5. Generation coherence gate

No set of individually valid PASS receipts may compose into a PASS unless they are coherent in world generation.

Each receipt used in a conjunction carries:

```text
receipt_id
obligation_id
disposition
world_generation
world_timestamp
validity_domain
source_head / commitment_root when applicable
```

Default coherence rule:

```text
all PASS receipts MUST share the required world_generation.
```

Timestamp freshness is a separate gate:

```text
abs(receipt.world_timestamp - reference_world_timestamp) <= allowed_skew
```

when a policy defines `allowed_skew`. A timestamp match never substitutes for generation equality.

### Generation coherence truth table

| Inputs | Generation relation | Result |
|---|---|---|
| PASS + PASS | same required generation, fresh | PASS candidate |
| PASS + PASS | known different generations | FAIL |
| PASS + PASS | generation missing/unresolvable | UNKNOWN |
| PASS + UNKNOWN | any non-failing relation | UNKNOWN |
| UNKNOWN + UNKNOWN | any non-failing relation | UNKNOWN |
| any + FAIL | any | FAIL immediately |

A stale, incompatible, or cross-generation PASS bundle must not be relabeled PASS.

## 6. Negative-space containment law

A closure may be rejected because of a positive refutation, but absence of a refutation is not positive proof:

```text
cache miss != PASS
no known defeat != PASS
unobservable defeat path != PASS
```

This is the operational boundary required by the D0 falsification lineage: unobservable or inadequately grounded consequence-changing novelty remains `UNKNOWN` rather than silently closing.

## 7. D0 canonical adversarial lanes

The stage harness must include all five named mutants:

```text
JOINT_MARGINAL_MUTANT
OMISSION_MUTANT
RECURSIVE_SAME_BLINDSPOT
SELF_CERTIFIED_KNOWN_ONLY
STALE_GENERATION_MUTANT
```

Acceptance criterion:

```text
unsafe_passes == 0
all canonical intentionally flawed lanes are rejected
```

`UNKNOWN` controls remain first-class and must not be coerced to FAIL solely to improve the mutant rejection score.

## 8. Halting / `STOP_SCALING`

Synthetic recurrence stops when additional symbolic scale cannot reveal a new decision-changing distinction, stronger falsifier/certificate, composition behavior, complexity result, or source-grounded objective.

For the D0 lineage, the canonical halting condition is:

```text
STOP_SCALING = True
reason = "synthetic evidence exhausted; remaining residual requires production/source instrumentation"
```

`STOP_SCALING` freezes recurrence expansion. It does not promote the synthetic harness to production validation.

## 9. Security and authority boundary

- Staged code/specification is noncanonical until Human Gate approval.
- Cache entries have no authority beyond their exact validity domain and generation.
- A verifier does not create authority; it checks a statement under an already-authorized policy/root/generation.
- Cryptographic interfaces must fail closed on unsupported algorithms, unknown verifier keys, malformed proofs, root mismatch, generation mismatch, or missing trusted inputs.
- No deployment, runtime wiring, or effect authorization is implied by this staging artifact.
