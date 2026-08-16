# WO-STAGE-003 — Tri-Generator Plurality Protocol

**Worker:** W3 — `G_C` / Consequence & Governance lens  
**Status:** STAGING-ONLY / NONCANONICAL / HUMAN-GATE-REQUIRED  
**Effect authority:** NONE. This specification chooses a question/disagreement to resolve; it does not authorize material effects, deployment, canonical promotion, or external API mutation.

## 1. Purpose

Aura retains three independently reproducible objective generators against the same achieved state `H_(r-1)`:

- `G_R` — **Residual-First**: select the smallest unresolved decision-changing residual after subtracting still-valid proof. Failure mode: can under-prioritize rare high-consequence surfaces when their residual is structurally large.
- `G_F` — **Falsifier-First**: select the earliest or strongest counterexample that could defeat the current synthesis. Failure mode: can over-focus on defeating a claim while under-building constructive closure.
- `G_C` — **Consequence-First**: select the unresolved uncertainty with the earliest/highest material consequence or obligation pressure. Failure mode: can under-investigate low-immediacy structural defects that later become systemic.

W3 uses `G_C` as its starting lens. That is a **lens choice, not a truth or authority grant**.

## 2. 18 Meta-Axes

The canonical 18-trit address uses one ternary digit per meta-axis. A digit selects which generator receives the *starting lens* on that axis; all three proposals remain present and testable.

| # | Axis | Subject |
|---|---|---|
| 01 | `GROUND` | canonical source grounding |
| 02 | `DUTY` | live obligation continuity |
| 03 | `AUTHORITY` | current rightful authority |
| 04 | `NEGATIVE_SPACE` | UNKNOWN / contradiction / inaccessibility |
| 05 | `EFFECT` | material-effect provenance and state |
| 06 | `REOPEN` | reproof / reopenability |
| 07 | `SURVIVOR` | irreducible survivor capability |
| 08 | `FAILURE_DOMAIN` | failure-domain separation |
| 09 | `RESERVE` | open-world heterogeneous reserve |
| 10 | `LINEAGE` | reserve-lineage diversity |
| 11 | `MODEL_PLURALITY` | independent failure-model plurality |
| 12 | `TEST_PLURALITY` | independent falsification/scenario generation |
| 13 | `GOVERNANCE` | human/community disposition |
| 14 | `SOVEREIGNTY` | privacy/owner/data-sovereignty boundaries |
| 15 | `TEMPORAL_DRIFT` | long-horizon topology and semantic drift |
| 16 | `ADVERSARIAL` | strategic/correlated attack surfaces |
| 17 | `CATASTROPHE` | assumption-light recovery under extreme loss |
| 18 | `SELF_MINIMALITY` | self-application and minimality |

Trit mapping:

```text
0 -> G_R / RESIDUAL-FIRST
1 -> G_F / FALSIFIER-FIRST
2 -> G_C / CONSEQUENCE-FIRST
```

For W3's default consequence-first orientation, the starting address is `222222222222222222`. This address does **not** erase or demote `G_R` or `G_F`.

## 3. Proposal Bundle

For round `r`:

```text
P_r = {
  G_R(H_(r-1)),
  G_F(H_(r-1)),
  G_C(H_(r-1))
}
```

Every proposal must carry at least:

```json
{
  "generator": "G_R | G_F | G_C",
  "objective": "string",
  "required_evidence": ["source-or-proof refs"],
  "consequence_surface": ["decision/effect surfaces"],
  "defeat_surface": ["falsifiers/counterexamples"],
  "expected_lifecycle_cost": "typed estimate or UNKNOWN",
  "unresolved_negative_space": ["UNKNOWN/contradiction/inaccessible items"],
  "proposed_disposition": "PASS | REOPEN | FENCE | BLOCK | UNKNOWN | ...",
  "decision_changing": true,
  "lawful": true,
  "falsifiers": ["explicit falsifier descriptions"],
  "provenance": {
    "engine_id": "model/provider identity",
    "source_generation": "current source generation",
    "grounded_state_ref": "state or evidence reference"
  }
}
```

The proposal journal is append-only at the application layer. Losing proposals, their falsifiers, and their engine/source provenance remain addressable after selection.

## 4. Disagreement Surface and Selection Rule

Define `D_r` as pairwise disagreement over:

1. required evidence,
2. consequence surface,
3. defeat surface,
4. expected lifecycle cost,
5. unresolved negative space,
6. executable disposition when it changes a lawful decision.

The dispatcher traverses the 18 axes in canonical order and selects:

```text
O_(r,1) = earliest lawful decision-changing disagreement under address A_r
```

### Mandatory selection invariants

1. **Preserve all three proposals.** Selection does not delete a proposal.
2. **Preserve falsifiers.** A losing objective remains falsifiable/reopenable.
3. **Choose a disagreement, not a winner.** The selected output is the narrowest executable objective needed to discriminate the earliest decision-changing disagreement.
4. **Fail closed when discrimination is not earned.** If no lawful decision-changing disagreement is established, return `UNKNOWN/ACQUIRE_EVIDENCE`; do not fabricate consensus.
5. **Lens is non-authoritative.** The trit-selected starting generator controls examination order only.
6. **Evidence, not model identity, decides.** Agreement by multiple LLMs is not itself proof, authority, or currentness.

## 5. Non-Authoritative Rebase Grammar

After each achieved local objective:

```text
1. STOP at the achieved result.
2. Synthesize generator-specific attribution:
   - unique decision-changing discovery,
   - missed surface,
   - false positive / unsupported assumption,
   - lifecycle cost,
   - surviving falsifier / negative space.
3. Recompute P_(r+1) from the achieved state.
4. Recompute D_(r+1).
5. Select the next earliest lawful decision-changing disagreement.
```

No rebase may promote a generator, adjudicator, model, or summary into a second truth/authority plane.

## 6. Local 27-Stage Grammar

The source plurality protocol uses the following local grammar:

1. `BRIDGE / TRI-GENERATOR FORM` — run all three generators; preserve all candidate objectives.
2. `SEED / DISAGREEMENT SEED` — map pairwise disagreement; form the narrowest lawful discriminator.
3. `GROUND` — canonical source grounding.
4. `CURRENT` — currentness and semantic generation.
5. `DUTY` — live obligations and deadlines.
6. `AUTHORITY` — rightful authority and access.
7. `EFFECT` — effect admission and post-effect duty.
8. `NEGSPACE` — UNKNOWN, contradictions, unmodeled residual.
9. `INVALIDATE` — earliest decision-changing invalidators.
10. `REOPEN` — shortest lawful reopen path.
11. `SURVIVOR` — irreducible survivor-capability loss.
12. `DOMAIN` — correlated failure-domain collapse.
13. `RESERVE` — open-world reserve depletion.
14. `LINEAGE` — reserve-lineage convergence/obsolescence.
15. `PLURAL` — failure-model monoculture.
16. `TEST` — independent scenario-generator cross-falsification.
17. `DRIFT` — temporal/topology/semantic drift.
18. `SURPRISE` — unmodeled failure residual.
19. `CONTAIN` — consequence containment with least unsupported assumption.
20. `EVIDENCE` — first divergence and observation/explanation separation.
21. `LEARN` — failure-class admission without hindsight laundering.
22. `SOVEREIGN` — owner/privacy/jurisdiction constraints.
23. `ADVERSARY` — shared blind spots, reward hacking, proposal manipulation.
24. `EXTERNAL` — independent evaluator reproduction from frozen evidence.
25. `ATTRIBUTION` — unique discoveries, missed surfaces, false positives, lifecycle cost by lineage.
26. `MINIMALITY` — remove generator machinery whose absence changes no decision-changing residual.
27. `SYNTHESIS` — synthesize generator-specific value and rebase without erasing losers.

## 7. Multi-LLM Interpretation

The model router may use Ollama/Qwen, DeepSeek, ChatGPT, or another engine to produce generator proposals. Engine identity and generator identity remain separate dimensions.

A model response is only an **advisory proposal object**. It cannot directly:

- write project truth,
- mutate external APIs,
- grant authority,
- deploy,
- merge,
- perform canonical/symbolic promotion,
- bypass the local consequence/fault-envelope kernel,
- bypass Human Gate receipts.

The local dispatcher validates schema, source generation, 18-axis coverage, falsifiers, and human-gate state before any downstream effect admission.

## 8. Human-Gated Corrigibility

The following actions are hard-gated:

- symbolic hierarchy promotion,
- canonical promotion,
- external API mutation,
- repository merge to protected branches,
- deployment/publication,
- irreversible material effect.

A gate can open only with a current local human approval receipt whose scope digest covers the requested action and source generation. Missing, stale, mismatched, or exhausted receipts result in `BLOCK/UNKNOWN`, never implicit approval.

## 9. Claim Ceiling

This staging spec operationalizes the previously derived objective-generator plurality grammar. It does **not** prove that any generator is globally best, that three models are independent, that LLM agreement is truth, or that the dispatcher can authorize effects. The intended fixed point is domain-local, evidence-attributed generator plurality: preserve competing ways to choose the next question and let current evidence determine which disagreement matters.

## 10. Source Lineage

Normalized from the staged Aura artifacts:

- `AURA__J100__3POW18-OBJECTIVE-GENERATOR-PLURALITY__OGPCFP__SPEC.txt`
- `AURA__J100__3POW18__OGPCFP__MANIFEST.json`
- W3 Human Gate 1 plurality implementation (`aura_plurality_dispatcher.py`) as an implementation specimen, not canonical source.
