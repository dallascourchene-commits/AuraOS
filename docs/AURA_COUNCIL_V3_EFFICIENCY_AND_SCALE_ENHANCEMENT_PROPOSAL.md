# Council V3 Efficiency, Scale, and Quality Enhancement Proposal

## Purpose

This proposal extends Selective Architect Council V3 without changing Aura's authority
model. Council remains planning-only: meaning and model judgment may guide retrieval and
critique, while exact repository evidence, capability leases, deterministic verifiers,
and human review remain authoritative.

The target outcome is not simply fewer calls. It is lower time and token cost per
verified result, higher defect discovery, predictable handling of larger operation
graphs, and evidence that makes those improvements auditable.

## Current V3 process and observed Phase 2 run

The implemented router in `aura_architect_council_v3.py` always selects `scope` and
`tests`, then conditionally selects `sequence`, `continuity`, `rollback`, and `cost` from
task count, dependency depth, large-task count, estimated turns, risk, and rollback
evidence. Candidate critics run serially, each receiving the candidate plan. Their scores
are averaged into the candidate score, blockers apply a fixed penalty, and the inherited
judge selects a plan.

The Aura Gate Phase 2 process used the following end-to-end sequence:

1. Intake and strategic framing from the Phase 2 brief.
2. Agent Bridge digest and topology health checks.
3. CODEMAP search, exact slices, connectome paths, capability resolution, and emergent
   ownership review.
4. Coding Arena localization, change graph, Act Capsules, GOAP ordering, and worker
   constraints.
5. Two architecture candidates: the canonical Gate authority envelope and a thin
   entrypoint guard.
6. Selective Council V3 lane routing and critic calls.
7. Premium judge selection, rejection/revision where required, and a selected plan.
8. Exact-file implementation through bounded tasks.
9. Focused tests, adversarial review, bounded repair, full regression, lint, CODEMAP,
   topology, and Waboose review.
10. GitHub PR creation and final CodeRabbit review as an external review boundary.

The instrumented Council run used 11 calls, an estimated 35,157 input tokens, and 1,852
output tokens. Selective routing saved an estimated 1,942 tokens (4.99%) against the
defined uniform six-lane counterfactual. The combined Bridge/Council scoped proxy reports
an estimated 56.66% reduction, but whole-session provider telemetry was unavailable. The
Bridge portion is a modeled chars/4 counterfactual and its first aggregate is a historical
planning snapshot, not billing data.

## Principal limitations

1. **Routing is threshold-based, not evidence-value-based.** A lane is selected because a
   structural threshold fires, not because its expected information gain exceeds cost.
2. **Critics repeat plan context.** Every selected lane receives most of the candidate,
   even when it needs only a dependency subgraph, test contract, or risk delta.
3. **Calls are serial.** Independent lanes and candidates do not exploit bounded parallel
   waves.
4. **Static scoring hides confidence.** Averages and a fixed blocker penalty do not
   distinguish corroborated blockers, uncertain criticism, missing evidence, or critic
   calibration.
5. **The Council plans but does not own an operation DAG.** Execution ordering is encoded
   inside candidate plans rather than represented by a scheduler-ready, checkpointed
   graph.
6. **No content-addressed critic cache exists.** Identical plan/lane/evidence inputs can be
   paid for again.
7. **Stopping is coarse.** There is no explicit early-consensus rule, marginal-value stop,
   or conflict-triggered escalation.
8. **Verification feedback is not a first-class lane.** Test and review findings can cause
   repairs, but the Council does not consume compact failure deltas through a formal
   replan protocol.
9. **Telemetry measures tokens, not quality-adjusted efficiency.** A cheaper plan can look
   better even if it creates more repair turns or misses defects.

## Proposed Council V3.1 architecture

### 1. Content-addressed Council Evidence Packet

Compile one immutable evidence packet before model calls:

```json
{
  "objective_digest": "...",
  "repository_digest": "...",
  "codemap_digest": "...",
  "plan_graph_digest": "...",
  "capability_graph_digest": "...",
  "candidate_digests": ["..."],
  "exact_evidence_refs": ["file:symbol:span:hash"],
  "risk_facts": [],
  "budget": {},
  "authority": {"planning_only": true, "production_mutation": false}
}
```

Critics receive a shared packet reference plus the minimum lane-specific projection.
Cache keys become `hash(council_version, model_profile, lane, candidate_digest,
evidence_projection_digest, prompt_schema_version)`. Any repository, policy, prompt
schema, or model-profile drift invalidates the cache.

### 2. Operation DAG as the primary plan artifact

Replace a flat `act_tasks` list as the internal execution representation with a validated
operation DAG. Each node declares inputs, outputs, exact scope, capabilities, authority,
tests, rollback, cost bounds, concurrency group, checkpoint, and evidence digest. Edges
declare data, authority, or ordering dependencies.

This allows Council to handle more operations safely:

- ready nodes can execute in parallel waves;
- shared dependencies are grounded once;
- fan-out/fan-in is explicit;
- concurrency and provider limits are enforceable;
- backpressure pauses new work when repair or evidence queues grow;
- checkpoints make bounded replay possible without replanning completed nodes;
- cancellation can dissolve only the affected branch when dependencies permit.

### 3. Risk- and uncertainty-aware lane router

Keep deterministic universal safety rules, but score optional lanes using expected value:

```text
lane_value = defect_probability
             × consequence_weight
             × expected_detection_gain
             × critic_calibration
             - normalized_token_cost
             - normalized_latency_cost
```

Inputs should include changed trust boundaries, authority transitions, external protocols,
data classes, persistence, concurrency, deployment surface, graph centrality, test gaps,
novelty, prior failure history, and disagreement between deterministic analyzers. Security,
protocol, data-governance, and concurrency lanes should be available in addition to the
current six lanes. Scope/tests remain mandatory unless exact deterministic proof makes a
model call unnecessary.

### 4. Parallel critic waves with bounded fan-out

Run independent critic lanes concurrently per candidate, subject to one Council budget
broker. Use waves rather than unrestricted fan-out:

1. deterministic preflight and cheap universal lanes;
2. optional high-value lanes in parallel;
3. conflict-resolution lanes only when reports disagree;
4. one synthesis/judge call after compact aggregation.

The broker reserves call, input, output, latency, and cost budgets transactionally before
launch. A cancellation token stops remaining calls when a blocker is decisive or the
candidate is dominated.

### 5. Delta prompts and structured critic contracts

Critics should receive only:

- the lane rubric;
- candidate summary and changed fields;
- relevant operation-DAG nodes/edges;
- exact evidence references or compact slices;
- unresolved findings from earlier waves.

Require a versioned response schema containing finding IDs, severity, confidence,
evidence refs, affected nodes, proposed invariant, blocker status, and uncertainty. This
eliminates free-form rationale duplication and enables semantic merging.

### 6. Incremental synthesis and conflict handling

Use deterministic aggregation before the judge:

- merge duplicate findings by evidence and invariant;
- distinguish independent corroboration from repeated wording;
- reject blockers without an exact evidence reference or explicit missing-evidence reason;
- identify contradictions and route only those to a conflict resolver;
- send the judge a compact decision table, not all raw prompts and reports.

The judge should choose among `APPROVE`, `REVISE_LOCAL`, `REPLAN_SUBGRAPH`,
`ESCALATE_EVIDENCE`, and `REJECT`, with exact affected operation nodes.

### 7. Verification-to-Council repair loop

When implementation verification fails, produce a compact failure packet containing the
failed gate, exact command, bounded stderr digest/slice, changed-node IDs, source hashes,
and prior repair count. Route it deterministically:

- local, known failure and unchanged architecture: Surgeon repair only;
- interface/dependency/security invariant invalidated: replan affected DAG subgraph;
- new authority owner, public API, dependency, or deployment claim: full Council
  escalation;
- repeated same failure beyond the configured limit: stop for human review.

This prevents full-plan replay for a local defect and prevents local repair from hiding an
architectural invalidation.

### 8. Quality-adjusted stopping rules

Stop critic expansion when all are true:

- mandatory lanes approve;
- no unresolved high-severity finding exists;
- confidence exceeds a calibrated threshold;
- the next lane's expected information gain is below its budget cost;
- deterministic coverage and evidence completeness thresholds pass.

Escalate instead of stopping when critic disagreement, missing evidence, novel authority,
or high-consequence uncertainty exceeds thresholds. Early stop must be recorded with the
lanes skipped and the exact rule used.

## Token, speed, and quality metrics

Measure each Council run with provider-reported usage where available and label every
fallback estimate. Required metrics:

| Dimension | Metric |
|---|---|
| Token efficiency | input/output tokens per candidate, lane, accepted operation node, and verified result |
| Context reuse | shared packet tokens, delta tokens, cache-hit tokens avoided |
| Speed | wall time, critical-path time, queue time, parallelism factor, cancellation savings |
| Quality | pre-implementation blockers found, post-implementation defects, escaped defects, repair turns |
| Calibration | confidence versus validated finding rate by lane/model/profile |
| Stability | replan count, repeated-failure rate, cache invalidation rate |
| Authority | unauthorized scope attempts, missing evidence refs, verifier/audit failures |

The primary optimization target should be:

```text
quality_adjusted_cost = total_tokens + latency_weight × critical_path_ms
                        + repair_weight × repair_tokens
                        + escape_weight × escaped_defect_severity
```

Do not report tokens saved without the counterfactual definition, artifact digests,
per-call telemetry class, and quality result. Whole-session totals remain unavailable
unless the provider or host exposes them.

## Recommended implementation sequence

### Priority 0 — truthful telemetry and schemas

- Add versioned `CouncilEvidencePacket`, `CriticRequest`, `CriticFinding`, and
  `CouncilRunMetrics` schemas.
- Record per-call input/output, latency, provider/model profile, cache status, prompt and
  evidence digests, selected/skipped lanes, and stop reason.
- Add deterministic arithmetic/reproducibility tests.

### Priority 1 — shared evidence and delta prompts

- Compile the content-addressed evidence packet once through Agent Bridge/CODEMAP.
- Add lane-specific projections and content-addressed caching.
- Replace full candidate repetition in `_critic_prompt` with compact request packets.

### Priority 2 — bounded parallel waves

- Add a Council budget broker with transactional reservations and concurrency caps.
- Execute independent lanes concurrently; retain deterministic output ordering.
- Add cancellation, timeout, partial-failure, and replay tests.

### Priority 3 — operation DAG and scheduler handoff

- Normalize selected plans into validated DAG nodes/edges.
- Add ready-wave calculation, checkpoint receipts, backpressure, subgraph cancellation,
  and dependency-aware repair.
- Keep execution authority in Arena/Forge; Council emits proposal artifacts only.

### Priority 4 — calibrated routing and stopping

- Collect validation outcomes by lane and model profile.
- Introduce expected-value lane selection, early consensus, and conflict escalation behind
  a shadow flag.
- Compare V3 and V3.1 on the same repository/objective corpus before promotion.

## Acceptance targets for a V3.1 shadow trial

- At least 25% lower median critic input tokens than current V3 on program-size plans.
- At least 20% lower median critical-path latency with bounded parallel waves.
- No reduction in validated high-severity finding recall.
- No increase in post-implementation repair turns or escaped verifier failures.
- 100% of blockers carry exact evidence references or a bounded missing-evidence reason.
- 100% of cache hits match all evidence/prompt/model/version digests.
- 100% of runs record selected/skipped lanes, stop reason, telemetry class, and authority
  boundary.
- Any failure of authority, evidence integrity, budget reservation, or result schema fails
  closed and reaches human review.

## Bottom line

Council V3 already removes unnecessary uniform critic calls. The largest next gains will
come from avoiding repeated candidate context, parallelizing independent evidence review,
representing the plan as an operation DAG, and optimizing for verified quality rather
than token count alone. These changes can increase capacity and speed without granting
models more authority: Council proposes, deterministic evidence and verifiers prove, and
humans authorize.
