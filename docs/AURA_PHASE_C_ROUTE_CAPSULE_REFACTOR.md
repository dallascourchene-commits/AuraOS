# Aura Phase C — Polysynthetic Route Capsules and Crystallized Code

Status: `C1_FOUNDATIONS_DRAFT_REVIEW_REQUIRED`

Phase C reunifies architectural ideas that currently live in separate generations of
AuraOS:

```text
polysynthetic six-slot parsing
+ VSA bind / bundle / unbind
+ weighted finite-state routing
+ guarded evidence, lease, policy and verifier gates
+ capability binding
+ Crucible OutcomeVector evidence
+ Agent IR maturity floors
```

The target is not unconstrained self-programming. The target is a bounded compiler
that learns a repeatable procedure through isolated trials and produces reviewable,
use-case-specific deterministic code.

## Research basis

Primary adjacent results informing the refactor include:

- Allauzen and Mohri, **3-Way Composition of Weighted Finite-State Transducers**,
  arXiv:0802.1465 — supports composing separately testable routing machines rather
  than flattening morphology, lifecycle, capability and policy into one graph.
- Hannun et al., **Differentiable Weighted Finite-State Transducers**,
  arXiv:2010.01003 — supports explicit graph structure with learnable soft
  operations; Aura keeps learning offline and proposal-only.
- Mohri, Pereira and Riley, **Weighted Automata in Text and Speech Processing**,
  arXiv:cs/0503077 — establishes determinization, minimization and composition as
  practical foundations for weighted language machines.
- Kleyko et al., **A Survey on Hyperdimensional Computing aka Vector Symbolic
  Architectures, Part I**, arXiv:2111.06077 — supports explicit role/filler binding,
  bundling, permutation and distributed symbolic representation.
- Repoformer, arXiv:2403.10059 — shows that selective repository retrieval can avoid
  harmful context and materially improve inference efficiency.
- Adaptive-RAG, arXiv:2403.14403 — supports routing among no retrieval, bounded
  retrieval and iterative retrieval based on task complexity.
- LLMCompiler, arXiv:2312.04511 — supports compiling tool dependencies and parallel
  execution plans instead of repeatedly reasoning over an undifferentiated tool list.
- LILO, arXiv:2305.16291, and DSPy, arXiv:2310.03714 — provide adjacent precedent for
  compressing successful traces into reusable programs and compiling declarative LM
  pipelines against measurable outcomes.

These papers validate adjacent mechanisms. They do not prove Aura's full architecture
or establish the six-slot contract as a universal model of polysynthetic languages.
Aura's slots remain an engineering abstraction inspired by morphotactic ordering.

## Canonical execution model

```text
natural-language objective
  -> canonical six-slot intent packet
  -> LEXC / morphology validation
  -> hard evidence, policy, lifecycle and lease guards
  -> compile all grounded component references
  -> VSA resonance over already-admissible route capsules
  -> materialize bounded data, memory, tools, model, budget and verifier contract
  -> isolated execution and OutcomeVector capture
  -> Crucible train / validation / shadow comparison
  -> Agent IR procedure induction
  -> reviewable crystallized code package
```

Weights and VSA resonance never create admissibility. They can rank only the capsule
IDs returned by the guarded runtime after all hard checks pass.

## Core versus adjunct semantics

The canonical ordered core remains:

```text
DIR   lifecycle or routing direction
ASP   phase or temporal aspect
CLASS effect or artifact class
SUBJ  exact target
VOICE agency and authority mode
STEM  terminal operation
```

The following remain orthogonal adjuncts rather than being forced into the six slots:

```text
risk, grounding, tests, quality, cost, context class, model class,
resource budget, thermal class, jurisdiction
```

## Executable Route Capsule

A capsule contains repository-relative references only:

```json
{
  "schema_version": "AURA_EXECUTABLE_ROUTE_CAPSULE_V1",
  "capsule_id": "...",
  "capsule_version": "...",
  "transition_id": "...",
  "morphology_profile_ref": "...",
  "vsa_profile_ref": "...",
  "data_aperture_ref": "...",
  "memory_aperture_ref": "...",
  "tool_bundle_ref": "...",
  "model_policy_ref": "...",
  "execution_budget_ref": "...",
  "verifier_contract_ref": "...",
  "output_schema_ref": "...",
  "morphology_signature": {},
  "routing_adjuncts": {},
  "requested_capabilities": []
}
```

Capsule manifests cannot declare forbidden field names such as `python`, `code`,
`shell`, `command`, `prompt`, `secret`, `token`, or automatic promotion authority keys.
Reserved field name filtering prevents structural embedding but does not inspect field
values such as `metadata.description`. The compiler pins every component by canonical
digest and resolves every requested capability through Aura's existing capability-binding
registries.

## Phase sequence

### C1 — Foundations — this PR

- canonical BLAKE2-seeded complex phasor VSA profile;
- canonical polysynthetic intent packet;
- bound intent representation;
- strict repository-relative component registries;
- typed Executable Route Capsule contract;
- deterministic capsule compiler;
- advisory resonance ranking restricted to pre-admitted capsule IDs;
- one review-only repository-localization capsule fixture;
- removal of the merged temporary Phase B repair workflow.

C1 does **not** modify the live Arena WFST or activate any capsule.

### C2 — Live guarded capsule routing

- add capsule references to the guarded transition schema;
- compile intent packets after input normalization;
- run hard guards before capsule resonance;
- materialize data, memory, tools, model, budget and verifier apertures;
- record intent, profile, capsule and aperture digests in ArenaExperience;
- expose capsule decisions in Human and Coding Arena projections.

### C3 — Trial Crucible and procedure induction

- generate bounded capsule variants only across proposal-safe dimensions;
- execute variants in isolated worktrees or ephemeral sandboxes;
- measure OutcomeVector, token cost, latency, tool calls and reproducibility;
- preserve disjoint TRAIN, VALIDATION and SHADOW trials;
- induce typed procedures from repeated successful traces;
- advance procedures through Agent IR floors:
  `TEXT -> TYPED -> SPEC -> STUB -> SHIM -> PURE`.

### C4 — Hackathon crystallization package

The initial use case is repository localization and affected-test selection. The
Crucible compares an exploratory agent route, a WFST-selected capsule and a generated
deterministic procedure. It outputs a review package under
`Aura_Staging/crystallization/` but does not install or promote it automatically.

## Authority boundary

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
capsule_resonance_authority: advisory_after_hard_guards
automatic_capsule_activation: false
automatic_grammar_promotion: false
automatic_code_installation: false
automatic_commit: false
automatic_push: false
automatic_merge: false
```
