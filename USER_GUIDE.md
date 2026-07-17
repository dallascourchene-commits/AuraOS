# AuraOS User Guide

> Operator guide for the Arena-based AuraOS architecture

**Documentation audit:** through merged PR #133 and the canonical Human Agent, Observatory, and Crucible documentation sync.  
**CODEMAP rule:** regenerate with `python3 aura_codebase_navigator.py` after architecture or source changes; require non-zero indexes and `compiled_deep_topology`.

AuraOS is local-first. Many routing, grounding, topology, storage, verification, and governance functions run without a hosted model. External models are optional workers operating through controlled egress and Arena boundaries.

## 1. Recommended workflow

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

Do not begin by loading all of `aura_node.py`, opening all of `.aura/CODEMAP.json`, grepping blindly, treating visual topology as exact truth, or allowing an external worker to write production files directly.

## 2. Installation and validation

```bash
git clone https://github.com/dallascourchene-commits/AuraOS.git
cd AuraOS
python3 -m pip install -r requirements.txt
python3 aura_codebase_navigator.py
python3 -m aura_agent_arena_cli topology-health
python3 -m aura_agent_arena_cli stabilization-status
python3 -m aura_agent_arena_cli digest
```

Healthy navigation output has non-zero files, symbols, commands, topology nodes, and topology edges, with a topology source such as `compiled_deep_topology`.

Keep API keys, learner data, community-only language data, private memory, and raw prompts containing secrets outside the repository.

## 3. Interfaces

| Interface | Best use | Launch |
|---|---|---|
| Native Cockpit | Intent ingestion, grounding, capability paths, and handoff preparation | `python3 -m aura_native_cockpit_server` |
| Agent Arena CLI | Coding workflow, staging, verification, cost, and domain commands | `python3 -m aura_agent_arena_cli` |
| Coding Arena | Visual topology selection and capsule simulation | `python3 aura_coding_arena_server.py` |
| Human Agent Arena | Human/Aura/agent workflows, emergent evidence, hypotheses, and tools | `python3 aura_human_agent_arena_server.py --repo-root .` |
| Agent Arena MCP | MCP-compatible surface for external agents | `python3 -m aura_agent_arena_mcp` |
| Legacy REPL | Existing `!commands` and compatibility workflows | `python3 aura_node.py` |

## 4. Repository orientation

Read in this order:

1. `README.md`
2. `.aura/ARCHITECTURE.md`
3. `.aura/CODEMAP.md`
4. the relevant subsystem document under `docs/`
5. exact source slices returned by Aura tools

Query CODEMAP:

```bash
python3 aura_codebase_navigator.py --query "human agent emergent research"
```

Read an exact symbol slice:

```bash
python3 -m aura_agent_arena_cli read-slice \
  --file aura_emergent_refactor_workspace.py \
  --symbol EmergentRefactorWorkspace
```

Resolve existing capabilities before creating a new module:

```bash
python3 -m aura_agent_arena_cli resolve-capabilities \
  --objective "Extend the Human Agent emergent research workflow"
```

## 5. Human Agent lifecycle

The Human Agent Arena is phase-gated:

```text
FRAME → GROUND → PLAN → ACT → PROVE → DECIDE
```

A route may preview evidence before admission, but active workflow evidence is committed only after the guarded action succeeds. A denied operation must not mutate the workflow.

Exact local source spans, hashes, tests, verifier outputs, leases, and human approval are authoritative. Visual topology, VSA resonance, JSpace, ST3GG, summaries, and emergent hypotheses remain advisory.

## 6. Emergent Refactor Workspace

Merged PR #133 adds a local evidence workspace for Aura's stored emergent-property reports.

It can:

- import exact report objects while preserving source metadata;
- list stored runs and inspect findings;
- search findings by objective and status;
- store content-addressed research evidence;
- search bounded official arXiv and GitHub APIs;
- select finding IDs and research-evidence IDs;
- compile a reviewable refactor packet;
- register special executions in the normal Human Agent tool-run ledger;
- attach the packet to the guarded workflow only after admission.

### API endpoints

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

The committed seed run is under:

```text
Aura_Memory/emergent_results/seed_runs/2026-07-16/
```

`provenance.jsonl` records expected byte sizes and SHA-256 values. Verification fails when committed artifacts do not match. Stored files under the run and research directories are authoritative; secondary JSONL indexes are reconciled so interrupted writes can be recovered without duplicate records.

Research safeguards:

- network operations have bounded end-to-end deadlines;
- result and sidecar counts are bounded;
- PDF and README sidecars are explicitly untrusted text;
- rendered external links permit only HTTP and HTTPS;
- malformed identifiers return structured errors;
- missing requested evidence IDs fail closed;
- identical stable content receives stable content-addressed identity.

Research metadata does not automatically become patch evidence.

## 7. Observatory handoff

The Observatory explains how an intention was parsed, routed, localized, compressed, and bounded. It does not execute work or grant authority.

```text
POST /api/showcase/observatory/handoff/human
POST /api/showcase/observatory/handoff/learning
```

The Human Agent handoff carries bounded observable facts such as objective, localized files and symbols, exact spans and hashes, focused tests, route decisions, compressed context, and selected topology identifiers.

The learning handoff is deliberately pre-experience:

```yaml
status: AWAITING_VERIFIED_EXPERIENCE
eligible_for_crucible: false
```

## 8. Crucible boundary

Crucible eligibility begins only after governed execution produces:

1. verifier evidence;
2. an `OutcomeVector`;
3. a complete sanitized `ArenaExperience V3`.

The Crucible separates TRAIN, VALIDATION, and SHADOW records. It may create only `CRYSTALLIZATION_PROPOSED` packets for verifier and human review.

The allowed learned surface is limited to:

```text
soft_weight_profile.empirical_uncertainty
```

The Crucible cannot alter hard guards, states, transitions, capabilities, risk classes, verifier requirements, source code, active grammar manifests, or consent rules. It cannot automatically commit, push, open a pull request, or merge.

## 9. Council–Surgeon workflow

Use Selective Council V3 for architecture, dependency, interface, invariant, sequence, rollback, and cross-domain decisions. Use the sliced Surgeon for bounded implementation and local repair.

```text
Council once → long execution graph
Surgeon → each bounded Act Capsule
local test failure → Surgeon local repair
interface/dependency/invariant failure → Council replan
```

Scope and tests are universal Council lanes. Other critic lanes are admitted only when plan structure and risk justify them.

## 10. Cost and benchmark interpretation

Keep evidence classes separate:

1. executable gate results;
2. deterministic comparative token proxies;
3. estimated structural projections;
4. discovery and capacity scans.

| Benchmark | Key result | Evidence class |
|---|---|---|
| Context localization | `131,655 → 14,431`; **89.04% lower** total proxy; quality `+0.0057` | Deterministic fixture |
| Selective Council V3 | `18 → 12` calls; `158,545 → 106,494`; **32.83% lower**, same accepted patch and quality | Controlled executable fixture |
| Executable patch | visible `3/3`, hidden `3/3`, regression `2/2`; observed `100.00`, benchmark `97.50` | Executable gate evidence |
| Real AuraOS refactor | `32/32`, `35/35`, `21/21`; observed `100.00`, benchmark `93.50` | Real branch gate evidence |
| State Ledger | `234` vs `6,140`; **96.19% less context**, preservation `1.0000`, drift `0.0000` | Synthetic continuity fixture |
| Emergent scan | `708` Python files, `10,815` nodes, `20,764` edges, `15` probes, `0` failures | Discovery evidence |
| Grounded projections | `7` probes, all `NEEDS_GROUNDING` | Projection only |
| Shared evidence | `2,004 → 938`; **53.1936% projected savings** | `ESTIMATED`, proposed PR #138 evidence |

Token proxies are comparative unless provider usage is explicitly recorded. Never present them as invoices.

## 11. Testing

Focused PR #133 tests:

```bash
python3 -m pytest -q \
  tests/test_aura_emergent_refactor_workspace.py \
  tests/test_aura_codemap_verify.py
```

Relevant broader tests should be added when changing the Human Agent server, research bridge, workflow admission, experience ledger, Observatory handoff, or Crucible.

After source or architecture changes:

```bash
python3 aura_codebase_navigator.py
```

Then verify that CODEMAP indexes and compiled topology remain healthy.

## 12. Troubleshooting

**The UI shows no research evidence after a server error**  
Inspect the API response. Successful evidence loading requires `ok: true`; non-network HTTP errors are surfaced through the UI error boundary.

**Research makes the interface feel blocked**  
Confirm the threaded server and bounded total research deadlines are active. Do not remove result and sidecar limits.

**A refactor packet is empty or partial**  
Verify every selected finding and research evidence ID exists. Missing selections must fail closed.

**A denied action changed workflow evidence**  
Treat this as a governance regression. Context must be built without mutation and committed only after guarded admission succeeds.

**CODEMAP reports zero metadata for a changed interface file**  
Regenerate CODEMAP from the current tree and verify the exact file entry.

## 13. Safety rules

- External workers are tools, not authorities.
- Semantic similarity and VSA are not patch authority.
- Observatory output is review evidence, not permission.
- Emergent findings are hypotheses until grounded and verified.
- Crucible proposals never self-promote.
- Unknown cost remains unknown.
- Consequential actions require explicit human or community authority.
- Restricted cultural and personal data must remain inside their consent and governance boundaries.

## 14. Documentation maintenance

Update `README.md`, `USER_GUIDE.md`, and `.aura/ARCHITECTURE.md` together when changing cross-cutting architecture. Regenerate `.aura/CODEMAP.json`, `.aura/CODEMAP.md`, and `topology_map.json` after source or architecture changes.

Historical documents remain useful as provenance, but current exact source, tests, schemas, and verifier evidence outrank old summaries.
