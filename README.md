# AuraOS

AuraOS is a sovereign, local-first, Arena-based cognitive operating substrate. It compiles human intent into grounded, governed, temporary capability systems.

**AuraOS is not an LLM.** Hermes, Codex, OpenAI, Anthropic, Gemini, Fireworks-backed workers, and local models are optional workers inside Aura's governed environment. They are not Aura's architecture, memory, verifier, or authority.

Aura began as a locally controlled Anishinaabemowin tutor. That origin shaped the wider system: local control, data minimization, inspectable memory, provenance, purpose-limited egress, revocable capability leases, and governance above model convenience.

The longer pre-benchmark README is preserved at [`docs/README_PRE_ARCHITECT_BENCHMARK.md`](docs/README_PRE_ARCHITECT_BENCHMARK.md).

## Core workflow

```text
objective
  → structured intent packet
  → finite-state admission
  → capability discovery
  → exact files, symbols, spans, hashes, and tests
  → bounded Arena
  → temporary tools and optional external workers
  → staged change
  → tests and verifiers
  → human or community decision
  → governed evidence and lifecycle receipts
```

> **Meaning may guide retrieval. Only grounded evidence and authorized governance may grant authority.**

## Human Agent, Observatory, and Crucible

Aura separates understanding, execution, and learning.

| Surface | Role | Authority boundary |
|---|---|---|
| **Aura Observatory** | Explains how an intention was parsed, routed, localized, compressed, and bounded | Review-only; it does not stage, execute, mutate, or grant permission |
| **Human Agent Arena** | Runs `FRAME → GROUND → PLAN → ACT → PROVE → DECIDE` | Guarded WFST admission, leases, exact grounding, verifiers, and human approval remain authoritative |
| **Emergent Refactor Workspace** | Searches stored emergent findings, preserves provenance, gathers bounded research, and compiles reviewable packets | Findings and research are evidence inputs only; unresolved selections fail closed |
| **Learning Arena / Crucible** | Mines complete verified `ArenaExperience` records | TRAIN/VALIDATION/SHADOW separation and proposal-only crystallization; no automatic code, policy, commit, push, PR, or merge authority |

```text
ordinary intention
  → Observatory
  → bounded Human Agent task
  → governed execution
  → verifier evidence
  → OutcomeVector
  → ArenaExperience V3
  → Crucible
  → TRAIN / VALIDATION / SHADOW
  → CRYSTALLIZATION_PROPOSED
  → verifier and human review
```

## Emergent Refactor Workspace

Merged PR #133 adds the Human Agent emergent-research surface.

It provides:

- content-addressed run, finding, packet, and research-evidence storage;
- exact seed provenance verification using byte size and SHA-256;
- recovery from authoritative stored files when secondary JSONL indexes are incomplete;
- objective-aware finding search;
- bounded official arXiv and GitHub research;
- explicit treatment of PDF and README sidecars as untrusted text;
- total network deadlines so research cannot freeze the Arena;
- normalized Human Agent tool-run records;
- safe HTTP/HTTPS link rendering;
- fail-closed unresolved evidence handling;
- workflow mutation only after guarded admission succeeds.

Primary files:

- `aura_emergent_refactor_workspace.py`
- `aura_arena_research_bridge.py`
- `aura_human_agent_arena_server.py`
- `aura_human_agent_arena/emergent.js`
- `tests/test_aura_emergent_refactor_workspace.py`

Committed seed evidence is under `Aura_Memory/emergent_results/seed_runs/2026-07-16/`.

## Council–Surgeon engineering

Selective Council V3 handles architecture, dependencies, interfaces, invariants, sequence, and rollback. It calls only critic lanes justified by evidence. The sliced Surgeon performs exact-file implementation, focused verification, and bounded local repair.

Scope and tests are universal critic lanes. Sequence, continuity, rollback, and cost are admitted from plan structure and risk.

Executable work can emit `AURA_REFACTOR_OUTPUT_RECORD_V1`, preserving estimated and provider-reported usage separately, exact gate evidence, failed gates, working status, disposition, and claim boundaries.

## Benchmark evidence

Evidence classes must not be collapsed into one score. Executable gates outrank deterministic token proxies; deterministic proxies outrank estimated structural projections; discovery scans identify candidates but do not prove implementation quality.

### Tier 1 — Executable gate evidence

| Benchmark | Result | Boundary |
|---|---|---|
| Executable fixture | visible `3/3`, hidden `3/3`, regression `2/2`; `WORKING`, `ACCEPTED`; observed `100.00`, benchmark `97.50` | Required API, scope, security, compilation, and static-analysis gates passed |
| Real AuraOS refactor | visible/property `32/32`, review-derived adversarial `35/35`, focused regression `24/24`; `WORKING`, `ACCEPTED`; observed `100.00`, benchmark `93.50` | Exact-head branch evidence; planning arms were frozen assisted artifacts rather than blinded independent-provider generations |

### Tier 2 — Deterministic comparative proxies

| Benchmark | Result | Boundary |
|---|---|---|
| Context localization | `131,655 → 14,431` total-token proxy; **89.04% lower**; quality `+0.0057` | Deterministic fixture proxy, not provider billing |
| Selective Council V3 | `18 → 12` calls and `158,545 → 106,494` total proxy; **32.83% lower** with the same accepted plan, patch, and quality | Controlled executable fixture |
| State Ledger | step 7: `234` vs `6,140` proxy tokens; **96.19% less context**, preservation `1.0000`, drift `0.0000` | Synthetic continuity test |

### Tier 3 — Estimated structural projection

| Benchmark | Result | Boundary |
|---|---|---|
| Shared grounding evidence | `2,004 → 938` proxy; `1,066` avoided; **53.1936% projected savings** | `ESTIMATED` / `PROJECTED_STRUCTURAL_TOKEN_PROXY`; proposed PR #138 evidence, not provider billing or merged-main proof |

### Tier 4 — Discovery and capacity projections

| Benchmark | Result | Boundary |
|---|---|---|
| Emergent scan | `708` Python files, `10,815` nodes, `20,764` edges, `15` probes, `0` failures | Discovery evidence only |
| Grounded projections | `7` probes, `0` failures; all remained `NEEDS_GROUNDING` | Projection, not implementation proof |

## SCO Construction advisory runtime

PR #148 adds the bounded Phase 3 E7–E11 Construction Arena vertical slice:

```text
ConstructionProjectState
  → exact evidence readiness
  → hard blockers before ranking
  → advisory probabilistic signal
  → cheapest / fastest / recommended / safest options
  → ActionCapsule + BoundaryContract + ArenaLease
  → verifier-backed proposal
  → human review
  → ArenaExperience V3
  → proposal-only Crucible
```

Verified on source head `15b3c26a3228a95174a845c75a178cf772cf5e81`:

- exact Python 3.11 compile, fatal Ruff selection, and diff checks passed;
- `81/81` focused Phase 3 tests passed in `22.45s`;
- focused adapter/fixture/benchmark coverage was `88%`, with learning coverage at `82%`;
- `241/241` Construction and canonical-owner regressions passed in `10.53s`;
- the zero-model benchmark completed `250` candidate-order permutations;
- native Selective Council V3 selected the bounded Surgeon plan at score `0.99`;
- Architect verification recorded `16` checks, `0` failures, four exact-file leases, and Judge `promote_hotswap`;
- the Experience Ledger stored `15` unique seeded episodes from one fictional scenario and one objective;
- Crucible produced one `CRYSTALLIZATION_PROPOSED` candidate and did not mutate active grammar.

This is synthetic/shadow software evidence, not a real-project or production-readiness claim. Provider tokens, provider cost, and real-project savings remain `NOT_MEASURED`. The runtime cannot authorize physical work, release payment, control access, certify safety or engineering, mutate authoritative records, or automatically promote grammar. See [`docs/evidence/AURA_SCO_PHASE3_E7_E11_VERIFICATION.json`](docs/evidence/AURA_SCO_PHASE3_E7_E11_VERIFICATION.json).

## Temporal persistence across arenas

Aura now separates three continuity layers:

```text
intra-session State Ledger V3
  → content-addressed TemporalCheckpoint
  → append-only parent/fork registry
  → restore assessment against current HEAD and invariants
  → DIRECT_RESUME_REVIEW_REQUIRED
     | MITOSIS_REQUIRED
     | RESTORATION_COUNCIL_REQUIRED
  → existing Arena guards, verifiers, and human review
```

The engine is shared by the Coding Workbench, Human Agent Arena, Agent Bridge Arena, and Construction Arena. Construction is the first domain profile, not a second persistence store.

Primary files:

- `aura_temporal_persistence.py`
- `aura_wfst_temporal_adapter.py`
- `aura_arena_persistence_adapters.py`
- `aura_agent_arena_persistence_bridge.py`
- `aura_persistence_cli.py`

Checkpoints live under `Aura_Memory/checkpoints/` and are excluded from production authority. A checkpoint can be inspected, forked, handed to another Arena as a payload-free digital baton, or assessed for restoration. Restore assessment never applies state automatically. Repository-head or invariant drift routes to the Restoration Council; large remaining context routes to MITOSIS.

Temporal labels such as `TEMP:CURRENT`, `TEMP:STALE`, and `TEMP:BRANCH_OFFSET` are guard evidence only. They do not mutate active grammar. The engine does not claim legal immutability, court admissibility, production readiness, automatic physical action, automatic hotswap, or automatic merge.

## Truth and authority

Source-of-truth order:

1. exact source, schemas, and current repository state;
2. tests and verifier artifacts;
3. healthy current CODEMAP and compiled topology;
4. exact snapshots, sidecars, and ledgers;
5. manifests, leases, consent, and boundary contracts;
6. current subsystem documentation;
7. summaries and historical reports.

VSA/HDC resonance, semantic similarity, DREAM, JSpace, ST3GG, visual topology, summaries, emergent hypotheses, and research sidecars are advisory.

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
```

Unknown, ungrounded, expired, ambiguous, or unauthorized actions fail closed.

## Quick start

```bash
git clone https://github.com/dallascourchene-commits/AuraOS.git
cd AuraOS
python3 -m pip install -r requirements.txt
python3 aura_codebase_navigator.py
python3 -m aura_agent_arena_cli topology-health
python3 -m aura_agent_arena_cli digest
```

Launch the Human Agent Arena:

```bash
python3 aura_human_agent_arena_server.py --repo-root .
```

Focused PR #133 validation:

```bash
python3 -m pytest -q tests/test_aura_emergent_refactor_workspace.py tests/test_aura_codemap_verify.py
```

## Documentation

- [`USER_GUIDE.md`](USER_GUIDE.md) — operator workflows and endpoints
- [`.aura/ARCHITECTURE.md`](.aura/ARCHITECTURE.md) — canonical architecture and authority model
- [`.aura/CODEMAP.md`](.aura/CODEMAP.md) — compact repository navigation
- [`docs/AURA_HUMAN_AGENT_ARENA.md`](docs/AURA_HUMAN_AGENT_ARENA.md)
- [`docs/AURA_OBSERVATORY_CRUCIBLE_HANDOFF.md`](docs/AURA_OBSERVATORY_CRUCIBLE_HANDOFF.md)
- [`docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md`](docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md)
- [`docs/AURA_REFACTOR_CODE_QUALITY_STANDARD.md`](docs/AURA_REFACTOR_CODE_QUALITY_STANDARD.md)

AuraOS is an active research and engineering system. Recorded evidence does not establish consciousness, unrestricted autonomy, certification, universal model superiority, or production readiness beyond the exact measured gates.
