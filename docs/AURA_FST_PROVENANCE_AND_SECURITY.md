# Aura FST Provenance and Security

## Three Distinct Routing Layers

Aura's routing architecture draws from three distinct cultural and computational sources. They must not be conflated.

## 1. Anishinaabemowin-Derived Semantic/Governance Layer

**Source inspiration:** Anishinaabemowin (Ojibwe) language and Anishinaabe governance principles.

**What it provides:** Semantic organization concepts and governance alignments used in Aura's design philosophy.

**Specific concepts:**
- **GIZAAGI'IN** — mutual benefit. Applied as: every Aura operation should benefit both the human and the system. Enforced through boundary contracts and human approval gates.
- **GIDINAWENDIMIN** — relational/swarm responsibility. Applied as: multi-agent coordination through Mesh/Swarm plans where agents share responsibility.
- **GWAYAKWAADIZIWIN** — integrity. Applied as: exact source spans, hashes, and verifier gates must be preserved. No advisory layer may become patch authority.
- **MIIGWECH** — extension-based storage. Applied as: QDKT knowledge transfer and memory extension patterns.

**Engineering consequence:** These concepts appear in module headers (`PWFST_ALIGNMENT` field) and influence policy decisions, but they are **not formal software behavior by themselves**. They are design constraints whose value is demonstrated through tests and measurements.

**Linguistic validation status:** These are project-creator identifications of conceptual alignment. They have not received formal linguistic/community validation as software architecture patterns.

## 2. Dene/Navajo/Athabaskan-Inspired Six-Slot Morphotactic Constraint

**Source inspiration:** Athabaskan language family morphotactic structure, as identified by the project creator.

**What it provides:** A canonical ordering constraint for routing frames.

**Canonical execution contract:**
```
DIR → ASP → CLASS → SUBJ → VOICE → STEM
```

**Canonical names and aliases:**
| Canonical | Aliases | Meaning |
|-----------|---------|---------|
| DIR | SPATIAL, DIRECTION | Lifecycle/routing direction |
| ASP | ASPECT | Duration/execution aspect |
| CLASS | CLASSIFIER | Effect class |
| SUBJ | SUBJECT | Target resource |
| VOICE | — | Authority/execution context |
| STEM | — | Terminal operation |

**Code implementation:**
- `aura_lexc.SlotName` — enum with canonical names
- `aura_lexc.SLOT_ORDER` — tuple of SlotName in canonical order
- `aura_lexc.CANONICAL_SLOT_ORDER` — string tuple of canonical names
- `aura_lexc.SLOT_ALIASES` — mapping from aliases to canonical names
- `aura_lexc.canonicalize_slot_name()` — resolve aliases to canonical
- `aura_lexc.AuraLexc.complete_routes()` — enumerate valid six-slot routes
- `aura_lexc.AuraLexc.validate_symbols()` — validate a symbol sequence
- `aura_fst_routing.SlotType` — enum mapping slots to indices
- `aura_fst_routing.FSTLexiconRoutingCore.slot_order` — FST core slot ordering

**USER_GUIDE reconciliation:** The USER_GUIDE previously used `SPATIAL` in one description while code uses `DIR`. This has been reconciled — `DIR` is the canonical execution name; `SPATIAL` is documented as an alias.

**Linguistic validation status:** The six-slot morphotactic ordering is identified by the project creator as inspired by Athabaskan language structure. It has not received formal linguistic validation. It is a software design constraint, not a claim about linguistic accuracy.

## 3. Machine-Oriented FST Routing Language

**Source:** Aura's own computational routing DSL, implemented in `aura_fst_routing.py`.

**What it provides:** Deterministic structural routing with hard gates, weighted alternatives, and grounding/test/risk blockers.

**Components:**
- Intent symbols (code_refactor, localize, verify, repair, etc.)
- Artifact symbols (python_module, test_file, codemap, etc.)
- Action symbols (inspect, create, modify, rank, verify, etc.)
- Scope symbols (symbol, file, capsule, subsystem, repo)
- Risk symbols (low, medium, high, live)
- Grounding symbols (full, file_exists, symbol_exists, etc.)
- Test symbols (none, existing, generated, required)
- Quality symbols (fast, balanced, accuracy_first, verifier_required)
- Cost symbols (no_model, local_first, cloud)
- Route symbols (BUILDER_PATCH, LOCALIZE_FIRST, PLAN_ONLY, etc.)
- Deterministic hard routing gates (priority-ordered rules)

**Security role:** The FST is an **admission grammar** — it determines whether an action is structurally expressible and policy-valid. It is **not** a security sandbox. A route may deny authority. A route may never create authority that was not explicitly granted.

## Attribution Requirement

Do not flatten distinct Indigenous languages into one generic "Indigenous grammar." The three layers above have distinct sources, distinct roles, and distinct validation statuses.

## Security Composition

An operation may run only when ALL of the following are true:

```
intent_route.complete
AND machine_route.accepted
AND lifecycle.transition_allowed
AND requested_capabilities ⊆ granted_lease
AND component_digests_verified
AND policy_checks_pass
AND sandbox_available
AND verifier_gate_passes
AND required_human_approval_present
```

Unknown, missing, ungrounded, expired, or ambiguous authority must fail closed.

VSA, DREAM, JSpace, ST3GG, summaries, generated interfaces, and semantic similarity never grant capabilities.
