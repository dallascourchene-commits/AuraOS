# WO-STAGE-003 — Fault Envelopes, Conservative Permission & Causal Recovery

**Worker:** W3 — `G_C` / Consequence & Governance lens  
**Status:** STAGING-ONLY / DESCRIPTIVE / NONCANONICAL / TEST_REQUIRED  
**Authority:** Safety/correctness evidence does not grant receiver-local materialization authority.

## 1. Compositional Fault-Envelope Closure (J116)

For local domains `i = 1..m`:

- membership domain: `M_i`
- current local admissible fault envelope: `F_i ⊆ 2^(M_i)`
- global membership: `M = union_i M_i`, using one canonical identity semantics across overlapping domains
- projection: `pi_i(F) = F ∩ M_i`

The conservative consistency join is:

```text
Join_i F_i = { F ⊆ M : for every i, pi_i(F) ∈ F_i }
```

This is the largest global fault envelope consistent with the local envelopes alone. It does **not** assume statistical, adversarial, provider, or control-domain independence.

Let `Gamma_t(F)` be the conjunction/set of current source-grounded cross-domain common-cause, control-domain, identity, topology, mutual-exclusion, or other admissibility constraints. Then:

```text
F_G,t = { F ∈ Join_i F_i : Gamma_t(F) }
```

### Conservative default

If `Gamma_t` is incomplete or unknown, omit unsupported narrowing and keep the larger join. Incomplete cross-domain knowledge may reduce liveness, but it must not be converted into optimistic safety by silently excluding possible faults.

### Empty model

```text
F_G,t = empty
```

does **not** certify safety. It means the source/model set is inconsistent or stale and must reopen.

## 2. Global Quorum Coverability

For each conflicting-decision quorum pair `Q1, Q2`:

```text
Safe iff there is no F ∈ F_G,t with (Q1 ∩ Q2) ⊆ F.
```

Equivalently:

```text
Unsafe(Q1,Q2) := SAT[ F ∈ F_G,t AND (Q1 ∩ Q2) ⊆ F ]
```

- `SAT` must materialize a concrete admissible global fault-set witness plus the source assumptions that make the quorum intersection faulty.
- `UNSAT` requires an independently checkable proof/certificate bound to the current model generation.
- `UNKNOWN` or uncheckable proof must remain `UNKNOWN/BLOCKED`.
- Hierarchical composition is lawful only when intermediate grouping preserves the same admissible global fault semantics. Grouping may alter cost, not meaning.

## 3. J116 Staged Primitive Pack

### `FAULT_ENVELOPE`

Required fields:

```json
{
  "primitive": "FAULT_ENVELOPE",
  "domain_id": "string",
  "membership_generation": "string",
  "model_generation": "string",
  "members": ["canonical member ids"],
  "admissibility": {},
  "source_refs": ["source refs"],
  "claim_ceiling": "string"
}
```

`admissibility` may represent extensional sets or a future source-grounded intensional form. It must not erase source/currentness bindings.

### `FAULT_COMPOSITION_JOIN`

Required fields:

```json
{
  "primitive": "FAULT_COMPOSITION_JOIN",
  "local_envelope_refs": ["FAULT_ENVELOPE refs"],
  "identity_map": {},
  "gamma_constraints": [{}],
  "model_generation": "string",
  "claim_ceiling": "string"
}
```

The `identity_map` prevents one physical/logical member from taking inconsistent states in overlapping domains. `gamma_constraints` may narrow only from current source-grounded cross-domain evidence.

### `QUORUM_COVERABILITY_RECEIPT`

Required fields:

```json
{
  "primitive": "QUORUM_COVERABILITY_RECEIPT",
  "model_generation": "string",
  "quorum_1": ["member ids"],
  "quorum_2": ["member ids"],
  "intersection": ["member ids"],
  "disposition": "SAT | UNSAT | UNKNOWN | BLOCKED",
  "witness_fault_set": ["optional SAT witness members"],
  "proof_ref": "optional independent UNSAT proof ref",
  "claim_ceiling": "string"
}
```

A separate checker must rebuild the composed constraints, validate current source bindings, and recompute/verify the coverability result without consuming the composer's safety conclusion.

## 4. Invalidation and Reverse Support

A change to local envelope `F_i` or any supporting `gamma` constraint reopens every global certificate whose proof support depends on that source. Localized recomputation is permitted only when explicit reverse support proves the affected connected component.

A CFEC certificate therefore carries at least:

```text
CFECCert = {
  local envelope refs + generations,
  canonical membership identity map,
  Gamma constraints + provenance,
  composition graph,
  quorum intersection,
  coverability query,
  SAT witness OR independently checkable UNSAT proof,
  reverse support,
  claim ceiling
}
```

## 5. Hard Conservative Envelope `H_t` vs. Heuristic/Empirical Estimator `S_t`

The permission boundary is typed:

```text
H_t = (U_t, L_t, A_t, G_t, F_t)
```

where `H_t` is the hard conservative activation envelope used for **permission**. `S_t` is the empirical/statistical estimator used for optimization and prioritization. `C_t` is an optional current certificate with validity domain `Gamma_C`.

They are typed views in one source-rooted projection; they do not create separate truth, scheduler, authority, or persistence planes.

### Permission law

```text
LEARN FOR SPEED; PROVE FOR PERMISSION.
SUCCESS MAY SHRINK EXPECTATION; ONLY A CERTIFICATE MAY SHRINK THE HARD SAFETY ENVELOPE.
```

`S_(t+1) = Learn(S_t, receipt_t)` may update means, quantiles, frequencies, regressors, or other declared estimates. Under sample-only success:

```text
H_(t+1) = H_t
```

by default. Sample success may trigger a search for a certificate; it does not mint one.

A hard tightening is lawful only when a current certificate proves the proposed extremal exclusion over its full validity domain, or when an explicitly authorized probabilistic risk contract changes the obligation class. A statistical policy must never be silently relabeled as a deterministic hard bound.

### Counterexample law

If a receipt realizes recovery later than `U_t`, or a divergent consequence earlier than `L_t`, within the claimed validity domain, the receipt defeats the hard certificate/scope. Widen or revoke the affected permission before renewed consequence and stale dependent parent certificates.

## 6. Causal Recovery Invariant

For an omitted/cold distinction `d`:

- `delta_d` — invalidating change event
- `R_d` — completion of detection + wake + source resolution + reproof + reconstitution
- `C_d` — earliest admissible material consequence whose lawful disposition can differ because of `d`

Lawful causal precedence requires:

```text
R_d < C_d
```

in the enforced causal partial order, **or** a non-bypassable fence `F_d` must be established before `C_d` and released only after `R_d` closes.

Operationally:

```text
RECOVER BEFORE CONSEQUENCE, OR FENCE CONSEQUENCE UNTIL RECOVERY.
```

A useful numeric specialization is:

```text
L_max(d) = T_detect + T_wake + T_source + T_reproof + T_reconstitute
D_min(d) = minimum time to first divergent consequence
sigma(d) = D_min(d) - L_max(d)
```

- `sigma > 0`: timing-based coldness may be lawful, subject to current source/authority/concurrency guards.
- `sigma <= 0` or unknown: prewarm, retain, fence, or block.

Recoverable is not the same as timely-recoverable.

## 7. Invalidation Wake Cone

For a delta `delta` and material consequence targets `C_o`:

```text
W(delta) = ForwardReachable(delta) ∩ BackwardReachable(C_o)
```

The active cone should retain mandatory counterevidence, authority, repair, and source roots needed to reprove or revoke permission. Unknown mapping fails closed for material consequences.

The runtime bridge must:

1. observe a local file/state delta,
2. compute a delta hash,
3. resolve the changed path/state into dependency nodes,
4. compute `W(delta)`,
5. register a blocking recovery ticket **before** downstream callbacks/effects,
6. permit the material consequence only after recovery is explicitly `VERIFIED`,
7. keep `PENDING` and `FAILED` tickets blocking.

## 8. Observation-Channel Currentness

Live Drive instrumentation established an important runtime refinement: freshness is **observation-channel/cursor-relative**, while independence is **failure-domain-relative**. Eventual convergence is not equivalent to deadline-safe wake, and multiple correlated views of the same provider do not create independent defeat paths.

Therefore the local watcher may certify only its local observation channel/cursor. It must not infer provider-wide freshness from its own scan or count multiple correlated Google/Drive views as independent wake coverage.

## 9. Human Gate

The fault/consequence layer can return evidence dispositions such as `PASS`, `SAT`, `UNSAT`, `REOPEN`, `FENCE`, `UNKNOWN`, or `BLOCKED`, but it does not authorize:

- canonical/symbolic promotion,
- external API mutation,
- protected-branch merge,
- deployment/publication,
- irreversible receiver-local effect.

Those require a separate current human approval receipt covering the requested action/scope/source generation.

## 10. Claim Ceiling

The J116/CFEC primitives are staged `TEST_REQUIRED` proof projections. They do not establish that Aura's actual replica/control-domain graph is complete, that all cross-domain causes are known, or that a production solver exists. The local watcher bridge is a fail-closed implementation specimen over a mounted/synced filesystem channel; it is not a provider-neutral latency theorem or Google Drive push-notification service.

## 11. Source Lineage

Normalized from:

- `J116_V01_SEED_RECURSIVE_MASTER.txt` — Compositional Fault-Envelope Closure.
- `aura_fault_envelope_primitives_v0_1.schema.json` — staged primitive schema.
- `AURA__AGENT-JOURNAL__J56-V18__...LAWFUL-CONSEQUENCE-BOUNDED-RECONSTITUTION...` — `R_d < C_d` and wake-cone timing law.
- `AURA__AGENT-JOURNAL__J56-V20__...LAWFUL-CONSERVATIVE-LEARNING...` — `H_t`, `S_t`, certificate/risk separation.
- J124/V01 EDOC live instrumentation — channel/cursor freshness and failure-domain independence refinement.
