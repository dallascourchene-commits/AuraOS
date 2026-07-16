# AuraOS User Guide

> **Operator guide for the current Arena-based AuraOS architecture**

**Documentation audit:** July 16, 2026, through merged PR #133 and the governed-learning documentation sync.  
**Previous full operator reference:** [`f38fca0/USER_GUIDE.md`](https://github.com/dallascourchene-commits/AuraOS/blob/f38fca03304b37b51738db99b3076490a880c31f/USER_GUIDE.md).  
**CODEMAP rule:** regenerate from the current tree with `python aura_codebase_navigator.py`; require non-zero indexes and `compiled_deep_topology`.

AuraOS is local-first. Many deterministic functions run without a hosted model. External models are optional workers operating through controlled egress and Arena boundaries.

## Contents

1. [Operating Principles](#1-operating-principles)
2. [Installation and Validation](#2-installation-and-validation)
3. [Choose an Interface](#3-choose-an-interface)
4. [Repository Orientation](#4-repository-orientation)
5. [Coding Workbench and Coding Arena](#5-coding-workbench-and-coding-arena)
6. [Human Agent Arena](#6-human-agent-arena)
7. [Emergent Refactor Workspace](#7-emergent-refactor-workspace)
8. [Observatory and Crucible](#8-observatory-and-crucible)
9. [External Workers and Ephemeral Organs](#9-external-workers-and-ephemeral-organs)
10. [Benchmarks and Cost Evidence](#10-benchmarks-and-cost-evidence)
11. [Safety and Governance](#11-safety-and-governance)
12. [Testing and Documentation Maintenance](#12-testing-and-documentation-maintenance)

## 1. Operating Principles

For new code work, use:

```text
topology health
→ repository digest
→ capability resolution
→ CODEMAP search
→ exact source slices
→ prepared Arena task
→ optional external worker
→ staged patch
→ tests and verifiers
→ human review
```

Do not begin by loading all of `aura_node.py`, opening all of `.aura/CODEMAP.json`, asking a model to grep blindly, treating a visual graph as exact truth, allowing an external worker to write production files directly, or creating a module before checking existing capabilities.

The Human Agent workflow is phase-gated:

```text
FRAME → GROUND → PLAN → ACT → PROVE → DECIDE
```

A route may preview evidence before admission, but workflow evidence is committed only after a guarded action succeeds. A denied operation must not mutate the active workflow.

## 2. Installation and Validation

### Requirements

- Python 3
- Git
- Linux, Windows, macOS, or Android/Termux
- optional Rust and Wasmtime/WASI for native or restricted ephemeral components
- optional Docker for containerized demonstrations
- optional provider keys for external workers

```bash
git clone https://github.com/dallascourchene-commits/AuraOS.git
cd AuraOS
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Build and validate the architecture map:

```bash
python aura_codebase_navigator.py
python -m aura_agent_arena_cli topology-health
python -m aura_agent_arena_cli stabilization-status
```

Expected CODEMAP properties include non-zero file, symbol, command, topology-node, and topology-edge counts, with a topology source such as `compiled_deep_topology`.

Never commit API keys, learner data, community-only language data, private memory, raw provider prompts containing secrets, or databases containing personal information.

## 3. Choose an Interface

| Surface | Best use | Mutation boundary |
|---|---|---|
| Native Cockpit | Local capability discovery and compact orchestration | Governed actions only |
| Agent Arena CLI / MCP | Machine-agent preparation, staging, verification, and repair | No direct production write |
| Coding Workbench | Checkpointed software-engineering workflow | Staged patches and gates |
| Coding Arena | Visual topology selection and route simulation | Advisory topology; no patch authority |
| Human Agent Arena | Human/Aura/agent command centre | Guarded WFST lifecycle |
| Aura Observatory | Explain parsing, routing, localization, and bounds | Review-only |
| Learning Arena / Crucible | Mine complete verified experiences and propose learning | Proposal-only |
| Civic Commons | Governed community coordination and decision support | Human/community authority |
| Legacy REPL | Compatibility and specialist commands | Follow current authority contracts |

## 4. Repository Orientation

Read in this order:

1. `.aura/ARCHITECTURE.md`
2. `.aura/CODEMAP.md`
3. targeted `.aura/CODEMAP.json` records
4. exact source files and tests
5. focused domain documentation

Do not treat semantic similarity, screenshots, summaries, VSA resonance, JSpace, ST3GG, DREAM, QDKT, MUSIC, MITOSIS, inferred edges, or ghost edges as patch authority.

## 5. Coding Workbench and Coding Arena

The Coding Workbench follows:

```text
OPEN_WORKSPACE
→ SCOPE_TASK
→ FILTER_CONTEXT
→ LOCALIZE_CODE
→ RANK_CODE_REGIONS
→ SLICE_CONTEXT
→ BUILD_CHANGE_GRAPH
→ DETECT_REFACTOR_CANDIDATES
→ SPLIT_WORK
→ CREATE_ACT_CAPSULES
→ PREPARE_AGENT_HANDOFF
→ STAGE_PATCH
→ RUN_TESTS
→ VERIFY_PATCH
→ HUMAN_REVIEW
→ PR_READY
```

Representative commands:

```bash
python -m aura_agent_arena_cli topology-health
python -m aura_agent_arena_cli open-workspace --objective "Refactor a bounded capability"
python -m aura_agent_arena_cli localize-code --objective "Refactor a bounded capability"
python -m aura_agent_arena_cli rank-code-regions --objective "Refactor a bounded capability" --max-lines 400
python -m aura_agent_arena_cli change-graph --objective "Refactor a bounded capability"
python -m aura_agent_arena_cli verify --scope declared
```

Launch the Coding Arena:

```bash
python aura_coding_arena_server.py --host 127.0.0.1 --port 8080
```

The Coding Arena may select nodes, isolate a micro-arena, show dependencies, compile advisory Action Capsules, identify missing routes, and compare raw versus compact context. It does not grant patch authority.

## 6. Human Agent Arena

Launch:

```bash
python aura_human_agent_arena_server.py --repo-root .
# Open http://127.0.0.1:8090
```

Demo mode:

```bash
python aura_human_agent_arena_server.py --demo
```

Useful commands include:

| Command | Result |
|---|---|
| `show Coding Arena` | Build a grounded concept workspace |
| `show everything connected to <concept>` | Expand files, symbols, docs, tests, and neighbors |
| `isolate selected` | Build a depth-bounded micro-arena |
| `inspect selected` | Produce a NodeIntelligencePacket |
| `show exact source for selected` | Return file, symbol, lines, digest, and read-slice command |
| `show callers` / `show callees` | Show incoming or outgoing relationships |
| `show tests for selected` | Show related tests |
| `show risks` | Show grounding, test, hub, and fan-in/out risks |
| `show unwired connections here` | Run a scoped report-only emergent audit |
| `hypothesize connection` | Add a session-local ghost edge |
| `prepare agent task` | Prepare a governed Agent Arena handoff |
| `export handoff packet` | Export the current workspace and prepared tasks |

Core API:

```text
GET  /api/human-agent/state
GET  /api/human-agent/events?since=N
GET  /api/human-agent/topology
GET  /api/human-agent/workflow
GET  /api/human-agent/routes
POST /api/human-agent/command
POST /api/human-agent/workflow/action
POST /api/human-agent/workflow/command
GET  /api/human-agent/tools
POST /api/human-agent/tools/run
```

Every command separates advisory `visual_update` from authoritative `truth_packet` evidence.

## 7. Emergent Refactor Workspace

The Human Agent Arena includes a local evidence workspace for studying Aura's stored emergent-property reports.

It can:

- import exact report objects and preserve source metadata;
- list stored runs and inspect findings;
- search findings by objective and status;
- store content-addressed research evidence;
- search bounded official arXiv and GitHub APIs for missing evidence;
- attach selected finding IDs and research-evidence IDs to a refactor packet;
- register special executions in the normal Human Agent tool-run ledger; and
- expose compiled evidence to the workflow only after guarded admission.

Endpoints:

```text
GET  /api/human-agent/emergent/runs
GET  /api/human-agent/emergent/runs/{run_id}
GET  /api/human-agent/emergent/search?q=...
GET  /api/human-agent/emergent/findings/{finding_id}
POST /api/human-agent/emergent/import
POST /api/human-agent/emergent/refactor-packet

POST /api/human-agent/research/search
GET  /api/human-agent/research/evidence
GET  /api/human-agent/research/evidence/{evidence_id}
```

The committed seed run under `Aura_Memory/emergent_results/seed_runs/2026-07-16/` is checked against `provenance.jsonl`; byte-size or SHA-256 mismatches fail verification. Files under the run and research stores are authoritative over recoverable JSONL indexes.

Missing requested finding or evidence IDs fail closed. Optional PDF/README sidecars are explicitly untrusted text. Network work has bounded deadlines. Rendered links permit only HTTP/HTTPS schemes.

## 8. Observatory and Crucible

The Observatory is an explanation and review surface. Its Human Agent handoff clears stale showcase evidence and carries only bounded facts such as the objective, exact localized files and symbols, source spans and hashes, focused tests, route decisions, compressed context, and selected topology identifiers.

```text
POST /api/showcase/observatory/handoff/human
POST /api/showcase/observatory/handoff/learning
```

The learning handoff is deliberately pre-experience:

```yaml
status: AWAITING_VERIFIED_EXPERIENCE
eligible_for_crucible: false
```

Crucible eligibility begins only after governed execution produces verifier evidence, an `OutcomeVector`, and a complete sanitized `ArenaExperience V3`.

```text
GET  /api/showcase/learning/status
POST /api/showcase/learning/run
POST /api/showcase/learning/pause
POST /api/showcase/learning/resume
```

The Crucible separates TRAIN, VALIDATION, and SHADOW records and may produce only `CRYSTALLIZATION_PROPOSED` packets for verifier and human review. The allowed learned surface is limited to:

```text
soft_weight_profile.empirical_uncertainty
```

It cannot alter hard guards, states, transitions, capabilities, risk classes, verifier requirements, source code, or active grammar manifests. It cannot automatically commit, push, open a pull request, or merge.

## 9. External Workers and Ephemeral Organs

External workers receive bounded context, an Act Capsule, allowed files, do-not-touch files, output contracts, token budgets, and compact State Ledger facts. They do not receive repository authority.

An ephemeral organ is a temporary, capability-bounded application with validation, lease, run, status, and dissolution stages.

```bash
python -m aura_agent_arena_cli ephemeral-plan --objective "Investigate a bounded capability" --ttl 300
python -m aura_agent_arena_cli ephemeral-validate --organ-id <id> --human-approval
python -m aura_agent_arena_cli ephemeral-run --organ-id <id>
python -m aura_agent_arena_cli ephemeral-status --organ-id <id>
python -m aura_agent_arena_cli ephemeral-dissolve --organ-id <id>
```

## 10. Benchmarks and Cost Evidence

Do not combine unlike evidence into one headline score. Use this hierarchy:

1. executable gate results;
2. deterministic comparative token proxies;
3. estimated structural projections; and
4. discovery and capacity-projection scans.

| Benchmark | Key result | Evidence class |
|---|---|---|
| Context localization | `131,655 → 14,431` total proxy; **89.04% lower**; quality `+0.0057` | Deterministic comparative fixture |
| Selective Council V3 | `18 → 12` calls; `158,545 → 106,494` total proxy; **32.83% lower**, same accepted patch and quality | Controlled executable fixture |
| Executable cross-module patch | visible `3/3`, hidden `3/3`, regression `2/2`; observed `100.00`, benchmark `97.50` | Executable gate evidence |
| Real AuraOS refactor at `52c9423` | `32/32`, `35/35`, `24/24`; observed `100.00`, benchmark `93.50`; scope and all required gates passed | Exact-head branch gate evidence |
| State Ledger | step 7 `234` vs `6,140`; **96.19% less context**, preservation `1.0000`, drift `0.0000` | Synthetic continuity fixture |
| Emergent capacity scan | `708` Python files, `10,815` nodes, `20,764` edges, 15 probes, 0 failures | Discovery evidence |
| Grounded capacity projections | 7 probes, 0 failures; all candidates still `NEEDS_GROUNDING` | Projection, not implementation proof |
| Shared grounding evidence, PR #138 | `2,004 → 938`; **53.1936% projected savings** | `ESTIMATED`; proposed branch, not provider billing |

The shared-evidence projection compares serialized phase-capsule output against a counterfactual that repeats the same grounding evidence in all nine capsules. It does not measure provider prompts, inference latency, or invoices. Keep it provisional until governed executions supply comparable quality and usage records.

## 11. Safety and Governance

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
visual_topology_patch_authority: false
research_metadata_patch_authority: false
learned_weight_patch_authority: false
crystallization_patch_authority: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
```

Unknown, ungrounded, expired, ambiguous, or unauthorized actions fail closed. Community, language, learner, private, and ceremonial data remain subject to consent and applicable governance rather than software convenience.

## 12. Testing and Documentation Maintenance

Run focused tests first, then declared-scope tests, then wider regression suites when justified. Preserve exact test IDs, outputs, failures, errors, digests, and unmeasured categories.

After architecture or documentation changes:

```bash
python aura_codebase_navigator.py
```

Verify:

- non-zero indexes;
- `compiled_deep_topology`;
- current file cards and line counts;
- valid Markdown links and anchors;
- no stale benchmark heads or unsupported claims;
- clear separation of measured, estimated, projected, and provider-reported evidence.
