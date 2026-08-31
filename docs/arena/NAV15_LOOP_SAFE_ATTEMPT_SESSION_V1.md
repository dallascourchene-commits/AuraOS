# NAV-15 Loop-Safe Attempt Session V1

Status: DRAFT / D0 / HS1 / NONPROMOTING

## Objective

Bind one exact NAV-14 progress-bound handoff candidate to one presented attempt-history/session identity and one universal loop-guard state before a currentness/tool owner may consider an operational attempt.

The positive disposition is only `ATTEMPT_SESSION_CANDIDATE`.

This contract does not execute a tool, authenticate an attempt-ledger producer, prove the ledger is durably persisted, resolve currentness, admit evidence, persist content, or grant effects.

## Exactly two terminal-green foreign parents

### Parent A — NAV-14 / PR #768

- exact head: `6cdd1be40428250bffba20e924f664c7be585469`
- semantic blob: `b1bdfb4c65281c314e658a6fb6fc8727a4b54245`
- hosted run/job: `33437542974 / 99637538062` — SUCCESS
- earned consequence: an exact hydrated-version handoff may become only `PROGRESS_BOUND_HANDOFF_CANDIDATE` when material, semantic purpose, and independently visible retrieval progress commute; no-progress and axis-only activity cannot mint a consequence.

### Parent B — Universal Execution Loop Guard / PR #770

- exact head: `6406e2f302335f940a7e780d818966a539c88845`
- semantic blob: `ba5800c20b09fd736054ef69615fd2e8f872b664`
- hosted run/job: `33437846633 / 99638534069` — SUCCESS
- earned consequence: repeated unchanged reads/polls, wrong mutation primitives/targets/fields, no-op history drift, and unintended semantic mutations fail closed at the process-control layer.

## True convergence

`5e986b2a40f6575ca7c42a8b8a93c89c8ca13872`

Parents:
1. NAV-14 exact-green generation `6cdd1be40428250bffba20e924f664c7be585469`
2. Universal loop-guard exact-green generation `6406e2f302335f940a7e780d818966a539c88845`

The convergence tree intentionally starts from NAV-14 and consumes the loop-guard parent through an exact typed projection rather than silently importing unrelated branch state.

## Collision quotient

Repository search found no owner for the exact relation:

`ProgressBoundHandoffCandidate × AttemptHistoryProjection × LoopGuardState × OperationIntent`.

PR #758 owns loop-safe hydration transaction admission. PR #769 owns historical admission reuse revalidation. PR #770 owns objective-global process control. NAV-15 owns only the missing candidate-bound attempt-session relation.

## Residual

`ProgressBoundHandoffCandidate + UniversalLoopGuard != LawfulAttemptSessionUntil CandidateIdentity + SessionIdentity + PresentedAttemptHistory + GuardHealth + OperationIntent Commute`.

A new in-memory wrapper cannot itself pay prior terminal/no-progress debt. However, this contract also cannot prove that the presented attempt-history projection is authentic or durably stored.

Therefore:

`AttemptHistoryProjectionRequiredBeforeSessionCandidate`.

`AttemptHistoryProjection != LedgerProducerAuthentication != PersistenceProof`.

## Material implementation

- `tools/aura_nav14_loop_safe_attempt_session.py`
- `tests/test_aura_nav14_loop_safe_attempt_session.py`
- `.github/workflows/aura-nav15-loop-safe-attempt-session.yml`
- this document

## Typed dispositions

- `ATTEMPT_SESSION_CANDIDATE`
- `HOLD_PARENT_GENERATION`
- `HOLD_HANDOFF_NOT_READY`
- `HOLD_CLAIM_CEILING`
- `HOLD_CANDIDATE_BINDING_MISMATCH`
- `HOLD_SESSION_BINDING_MISMATCH`
- `HOLD_ATTEMPT_LEDGER_REOPEN_REQUIRED`
- `HOLD_LOOP_GUARD_TAINTED`

Positive state requires:

1. exact NAV-14 and universal-loop parent generations;
2. NAV-14 positive candidate disposition;
3. exact candidate digest across handoff, attempt-history projection, and operation intent;
4. exact session identity across attempt-history projection, loop-guard objective identity, and operation intent;
5. presented attempt-history has no prior terminalization/no-progress debt and carries a durable-identity-bound assertion;
6. loop guard carries zero incidents, no mutation stop, no frozen primitive, and no blocked no-op write key;
7. all authority/currentness/effect ceilings remain false.

A positive receipt still records `ledger_producer_authenticated=false` and `ledger_persistence_proven=false`.

## Different-J / HyperScale

Two independently shaped classifiers must commute over:

`2 candidate-ready × 2 candidate-binding × 2 session-binding × 2 attempt-history-open × 2 guard-clean × 2 claim-ceiling = 64 states`.

Focused adversarials separately attack parent generation, candidate/session substitutions, terminal/no-progress history, mutation-stop/frozen/no-op debt, self-minted ledger authentication, boolean/type substitution, stale identity echoing, and deterministic receipt generation.

HS1 is sufficient because the bounded structural state surface is exhaustible. Broader worker fanout would duplicate consequence mass unless hosted proof exposes an unmodeled invalidator.

## External Different-J pressure

External work is falsification/methodology pressure only and grants no Aura authority.

- arXiv `2607.01641`, *When Agents Do Not Stop: Uncovering Infinite Agentic Loops in LLM Agents*: feedback paths without effective bounds create recurrent nontermination failure modes.
- arXiv `2606.04990`, *From Agent Traces to Trust: Evidence Tracing and Execution Provenance in LLM Agents*: process-level execution provenance is a separate trust surface from output content.
- arXiv `2608.23623`, *When May an Agent Stop? Evidence-Carrying Termination for Tool-Using LLMs*: termination support can be carried as typed process evidence without proving external-world truth.
- Current practitioner reports on production agents independently stress durable retry/idempotency state and explicit loop-stop conditions because process-local retry state can disappear and repeated non-idempotent attempts can duplicate effects.
- `SCHOLAR_DIRECT_GAP:NAV15:loop-safe-attempt-session`: direct task-specific Google-Scholar-native discovery returned no stable stronger record in this pass.

## External coordinate / persistent cognition record

Stable external coordinate identity is represented as:

`SourceCoordinate := SourceURI-or-arXivID + source/version identity when available + retrieval epoch + evidence rank + provenance digest`.

Canonical K27 placement remains an owner function; this objective does not invent a semantic K27 address.

`K27Placement != SourceIdentity != SemanticTruth != Currentness != Authority`.

`CoordinateMemory != MODEL_PREFIX_KV`.

No native/private transformer KV cache was accessed. If provider/model cache state is ever surfaced, it remains a separate generation/currentness input and cannot substitute for the attempt-history projection.

## HyperDrive road

`NAV14_EXACT_GREEN + LOOP_GUARD_EXACT_GREEN`
`-> TRUE_TWO_PARENT_CONVERGENCE`
`-> CANDIDATE_SESSION_BINDING`
`-> PRESENTED_ATTEMPT_HISTORY_CHECK`
`-> LOOP_GUARD_HEALTH_CHECK`
`-> ATTEMPT_SESSION_CANDIDATE | TYPED_HOLD`
`-> EXACT_HOSTED_PROOF`
`-> PERSIST_EARNED_LAWS`
`-> RECURSE_ONLY_FROM_TWO_NEW_CONSEQUENCE_DISTINCT_FOREIGN_TERMINAL_ARTIFACTS`.

## Triadic Process

Thesis: NAV-14 can prove a progress-bearing candidate relation.

Counterplane: candidate readiness does not bound the execution loop, preserve retry history, or prevent no-op/mutation-loop failure.

Synthesis: require candidate identity, presented attempt-history/session identity, operation intent, and universal loop-guard health to commute before producing only an attempt-session candidate.

Rebase: process-control readiness is still downstream from ledger producer authentication/currentness owner/tool authorization.

## Creation Process

1. freeze exact terminal-green NAV-14 and loop-guard parents;
2. collision-scan candidate-session ownership;
3. form true Git convergence;
4. isolate candidate/session/retry-history residual;
5. type candidate, attempt history, guard snapshot, and operation intent independently;
6. implement independent classifiers;
7. attack identity/type/terminal/no-progress/mutation debt substitutions;
8. exhaust the 64-state lattice;
9. require exact hosted proof and preserve trust ceilings;
10. persist only earned laws and recurse only from two new foreign terminal artifacts.

## Eight crystalline lenses

- W0 Provenance: exact parent heads/blobs/runs/jobs and convergence.
- W1 Ordered flow: candidate -> attempt-history/session bind -> guard health -> attempt-session candidate/HOLD.
- W2 Substitution: candidate/session/parent/type/intent/guard-state swaps.
- W3 Contradiction: fresh wrapper vs carried terminal/no-progress history; clean candidate vs tainted process loop.
- W4 Factorization: candidate readiness, ledger projection, producer authentication, persistence, currentness, execution, authority, and effects remain independent leaves.
- W5 Synthesis: NAV-14 × universal loop safety yields a candidate-bound process membrane, not an executor.
- W6 Quotient: repeated/no-op process state cannot become evidence merely through new history or wrapper identity.
- W7 Temporal: terminal/no-progress/guard debt reopens or blocks the attempt session.
- W8 Effect ceiling: tool/provider/model execution remains unearned.

## Laws

`ProgressBoundHandoffCandidate != ToolExecutionAuthority`.

`CandidateIdentityMustBindAttemptSession`.

`AttemptHistoryProjectionRequiredBeforeSessionCandidate`.

`AttemptHistoryProjection != LedgerProducerAuthentication != PersistenceProof`.

`LoopGuardIncidentDebtInvalidatesAttemptSession`.

`NoOpHistoryDrift != ProofProgress`.

`AttemptSessionCandidate != CurrentnessResolved`.

`K27Placement != SemanticIdentity != Currentness != Authority`.

`CoordinateMemory != MODEL_PREFIX_KV`.

## Claim ceiling

No attempt-ledger producer authentication, durable-storage proof, source/read currentness, semantic truth, evidence admission, retrieval/materialization execution, persistent-store mutation, tool/provider/model execution, write/effect authority, semantic K27 authority, native/private transformer KV access, Gate-10, merge/deploy/spend, causal performance claim, or public/financial/human effect is granted.

NAV-15 closes only after its dedicated exact-head hosted workflow succeeds.
