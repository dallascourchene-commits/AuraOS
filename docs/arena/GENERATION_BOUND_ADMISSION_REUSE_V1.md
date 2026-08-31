# Generation-Bound Admission Reuse V1

Status: DRAFT / D0 / HS1 / NONPROMOTING

## Objective

Compile one cross-domain revalidation membrane from exactly two terminal-green other-Agent semantic parents so that a previously positive bounded admission can be reused only while its identity-bearing producer, subject, source, evidence, owner, and decision-context generations remain exact.

A positive historical admission is not a timeless lease.

## Exactly two earned foreign parents

### Parent A — PR #758 scheme-serializable hydration transaction

- semantic head: `8c30df774ad55507aa57bbfd49444991c1a2b379`
- semantic blob: `97211589682a7ed67c8c63530dac744b9c186e57`
- dedicated hosted run/job: `33436051562 / 99632632584` — SUCCESS
- reusable consequence: bounded hydration admission is lawful only inside one stable route/source/owner-epoch/retrieval-novelty transaction.

### Parent B — Q18 / PR #761 current-generation bounded C2 proposal

- semantic head: `aed81432db8b84d2f43b8a85d06d4b72e16f6a50`
- semantic blob: `4cee26edaf0759fc80d31889ab9e4e268f9a4fbe`
- dedicated hosted run/job: `33436580962 / 99634379758` — SUCCESS
- reusable consequence: current-generation identity must be revalidated before historical policy state can be reused; a green bounded proposal remains only proposal eligibility.

## True convergence

Commit `ea3a61a20b410fd02ed0520d0e4488fcd6987329` has exactly those semantic generations as parents, Q18 first and PR #758 second.

## Residual

`AdmissionValidAtProduce != AdmissionReusableAtUse`.

More exactly:

`HistoricalPositiveAdmission + CurrentUseRequest != LawfulReuseCandidateUntil ProducerGeneration + SubjectIdentity + SourceGeneration + EvidenceGeneration + OwnerContext + DecisionContext Commute`.

Any identity-bearing drift produces a typed HOLD and requires recomputation from the relevant owner. Exact agreement produces only `REUSE_CANDIDATE`.

## Material implementation

- `tools/aura_generation_bound_admission_reuse.py`
- `tests/test_aura_generation_bound_admission_reuse.py`
- `.github/workflows/aura-generation-bound-admission-reuse.yml`
- this provenance document

The membrane supports two admission families without converting their domain-specific semantics into one authority type:

- `HYDRATION_TRANSACTION`
- `GLM53_BOUNDED_C2_PROPOSAL`

The exact positive parent disposition is pinned independently for each family.

## Typed dispositions

- `REUSE_CANDIDATE`
- `HOLD_PARENT_GENERATION`
- `HOLD_ADMISSION_NOT_POSITIVE`
- `HOLD_CLAIM_CEILING`
- `HOLD_PRODUCER_GENERATION_CHANGED`
- `HOLD_SUBJECT_CHANGED`
- `HOLD_SOURCE_GENERATION_CHANGED`
- `HOLD_EVIDENCE_GENERATION_CHANGED`
- `HOLD_OWNER_CONTEXT_CHANGED`
- `HOLD_DECISION_CONTEXT_CHANGED`

HOLD receipts deliberately do not echo the historical subject/source/evidence/owner/decision keys as if they were current observations.

## Different-J finite proof

Two independently shaped classifiers must commute over:

`2 admission families × 2^6 current-use drift masks = 128 states`.

The six drift axes are producer generation, subject identity, source generation, evidence generation, owner context, and decision context. Focused adversarials separately attack stale parent heads, non-positive dispositions, authority-ceiling promotion, deterministic receipts, and stale-identity echoing.

HS1 is sufficient because this consequence surface is finite and exhaustible. Worker fanout would duplicate proof mass unless hosted execution exposes an unmodeled consequence-changing invalidator.

## External Different-J pressure

Current external work supports the boundary but grants no Aura authority:

- `When Stale Constraints Go Unchecked: Budgeted Verification Failures in Inherited Agent Memory` (arXiv:2608.25553) separates immutable historical provenance from which record is current and shows large stale-consistent failure when critical provenance is not rechecked.
- `STALE: Can LLM Agents Know When Their Memories Are No Longer Valid?` (arXiv:2605.06527) finds a gap between retrieving updated evidence and adapting downstream behavior.
- `Temporal Validity in Retrieval Memory` (arXiv:2606.26511) models explicit supersession rather than relying on similarity.
- Recent production-RAG practitioner reports describe source storage becoming fresh while indexes/caches remain mixed old/new and recommend source-version/reconciliation checks.
- Direct task-specific Google-Scholar-native discovery returned no stable stronger record in this pass: `SCHOLAR_DIRECT_GAP`.

## Persistent cognition / K27

External sources are stored as identity-bearing cognition records with source URI/title, retrieval time, content/version identity when available, evidence rank, and unresolved canonical K27 placement.

`K27Placement != SourceIdentity != SemanticTruth != Currentness != Authority`.

`CoordinateMemory != MODEL_PREFIX_KV`.

No native/private transformer KV cache is accessed or claimed. A provider-side persistent KV snapshot, if used by an external system, would itself require source/version/currentness revalidation before reuse.

## HyperDrive state road

`PARENT_A_EXACT_GREEN + PARENT_B_EXACT_GREEN`
`-> TRUE_TWO_PARENT_CONVERGENCE`
`-> GENERATION_BOUND_REVALIDATION`
`-> REUSE_CANDIDATE | TYPED_HOLD`
`-> HOSTED_EXACT_HEAD_PROOF`
`-> PERSIST_EARNED_LAWS`
`-> RECURSE_ONLY_FROM_TWO_FRESH_CONSEQUENCE_DISTINCT_FOREIGN_ARTIFACTS`.

## Triadic Process

Thesis: both parents can emit bounded positive admission states.

Counterplane: a historically lawful admission can become stale while its bytes and receipt digest remain unchanged.

Synthesis: preserve the receipt as provenance, but require an exact current-use generation vector before even candidate reuse.

Rebase: historical green is evidence of what was lawful then, never proof of what is lawful now.

## Creation Process

1. freeze two exact terminal-green foreign parents;
2. run collision quotient for an existing reuse-currentness owner;
3. form true Git convergence;
4. isolate the cross-domain residual;
5. factor minimum identity-bearing current-use axes;
6. implement independent classifiers;
7. attack substitutions and stale-identity echoes;
8. exhaust the finite lattice;
9. require exact hosted proof;
10. persist only earned laws and recurse from two new foreign artifacts.

## Eight crystalline lenses

- W0 Provenance: exact parent heads/blobs/runs/jobs.
- W1 Ordered flow: produce admission -> time/world changes -> observe current vector -> revalidate -> candidate/HOLD.
- W2 Substitution: producer/subject/source/evidence/owner/decision replacements.
- W3 Contradiction: identical receipt bytes with changed world state.
- W4 Factorization: provenance, currentness, truth, authorization, execution, effects remain independent leaves.
- W5 Synthesis: hydration admission × bounded C2 proposal yields a generic revalidation relation, not generic authority.
- W6 Quotient: duplicate historical receipts collapse by exact receipt identity while current-use observations remain generation-bound.
- W7 Temporal: every identity-bearing generation is a reopen invalidator.
- W8 Effect ceiling: execution/effect widening remains unearned.

## Laws

`AdmissionValidAtProduce != AdmissionReusableAtUse`.

`CurrentGenerationIdentityBeforeAdmissionReuse`.

`AnyIdentityBearingAdmissionAxisDrift => HOLD_RECOMPUTE`.

`HistoricalPositiveDisposition != TimelessLease`.

`ExactReuseCandidate != ExecutionAuthority`.

`RouteOrPolicyContextChangeRequiresRevalidation`.

`K27Placement != SemanticIdentity != Currentness != Authority`.

`CoordinateMemory != MODEL_PREFIX_KV`.

## Claim ceiling

No source currentness, semantic truth, evidence admission, persistence/materialization execution, model/provider/tool execution, routing/effect authority, semantic K27 authority, native/private transformer KV access, Gate-10, merge/deploy/spend, causal performance claim, or public/financial/human effect is granted.

Objective closure requires dedicated exact-head hosted SUCCESS.
