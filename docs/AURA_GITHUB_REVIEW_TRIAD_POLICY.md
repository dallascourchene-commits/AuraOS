# Aura GitHub Review Triad Policy V1

Status: **CANONICAL GOVERNANCE RULE — FAIL CLOSED**

## Invariant

Every GitHub change pushed to an AuraOS pull-request branch MUST be reviewed on the **exact current head SHA** by all three required reviewer classes before that change is eligible for merge, promotion, release, provider effect, public effect, or any other production-admission claim:

1. **OpenAI Codex code review**
2. **CodeRabbit code review**
3. **Codacy static/code-quality review**

These three are cumulative. None substitutes for another. Sourcery, GitHub Actions, Aura-native review learning, security scanners, human review, and future reviewers are additive evidence only unless a later canonical policy explicitly promotes them into the required set.

## Push semantics

A raw `git push` happens before a pull-request reviewer can inspect the resulting remote commit. Therefore this policy does **not** claim that a review can precede the network push that creates the reviewable SHA.

Instead, the enforceable rule is:

> **Every push invalidates prior review admission and MUST trigger/reacquire Codex + CodeRabbit + Codacy evidence for the new exact head before the pushed change can become merge/promote/release admissible.**

`PushOccurred != ReviewAdmission`.

`NewHeadSHA => PriorHeadReviewAdmissionInvalid`.

`MergeOrPromotionAdmissible => CodexReviewedExactHead AND CodeRabbitReviewedExactHead AND CodacyPassedExactHead`.

## Exact-head evidence

The canonical gate is `.github/workflows/aura-github-review-triad-gate.yml` backed by `scripts/aura_github_review_triad_gate.py`.

The gate fails closed unless the pull request still points at the requested head SHA and the exact head carries all required evidence.

Accepted evidence classes are intentionally provider-specific:

- **Codex:** a current-head PR review/check/status authored by or named for an identifiable Codex/OpenAI-Codex reviewer. A user-authored `@codex review` request is a trigger only and is never counted as review completion.
- **CodeRabbit:** a successful current-head CodeRabbit status/check or a current-head review from `coderabbitai[bot]`. A draft-skip notice is not review completion.
- **Codacy:** a successful current-head Codacy status/check. Absence of Codacy is a failure, not a waiver.

Review evidence from an older SHA cannot be carried forward after `synchronize`/push.

## Review lifecycle

For every PR head:

1. Push or update the branch.
2. Codex review is requested/triggered for that exact head. Repository/workspace configuration SHOULD use Codex review-on-every-push where available; explicit `@codex review` is the fallback trigger.
3. CodeRabbit reviews the exact head. Draft PRs are enabled for automatic CodeRabbit review by repository configuration.
4. Codacy analyzes the exact head and reports success.
5. Supplemental reviewers may run: Sourcery, Aura Review Learning, security/static-analysis workflows, and humans.
6. The Review Triad Gate verifies exact-head evidence.
7. Only after the triad gate and all other required project-specific gates are green may a separate authority layer consider merge/promotion/release.

## Failure and unavailability

`ReviewerUnavailable != ReviewerPassed`.

If Codex, CodeRabbit, or Codacy is unavailable, disconnected, rate-limited, skipped, or cannot bind evidence to the exact head, the change remains **HOLD / NONPROMOTING**. The correct response is to restore/re-run that reviewer, not to replace its evidence with another tool.

A reviewer finding does not authorize an automatic fix. Findings enter the normal repair/re-review loop. Any repair push creates a new head and therefore invalidates the previous triad admission.

## Authority ceiling

The Review Triad proves only that three independent review planes examined the exact current head and that Codacy's required quality check succeeded. It does not itself prove:

- semantic correctness or truth;
- producer identity beyond provider evidence exposed by GitHub;
- runtime behavior beyond executed tests/checks;
- human/community consent;
- source mutation authority;
- execution, commit, merge, promotion, release, provider, or public-effect authority.

`ThreeReviews != MergeAuthority`.

`ThreeReviews != SemanticCorrectness`.

`ReviewerAgreement != GroundTruth`.

## HyperDrive laws

- `Push != Review`.
- `ReviewOnOldHead != ReviewOnCurrentHead`.
- `Codex + CodeRabbit + Codacy` is a conjunction, not a vote.
- `OneReviewerSuccess + AnotherReviewerMissing => HOLD`.
- `StaticAnalysis != IntentAwareReview`.
- `IntentAwareReview != StaticAnalysis`.
- `CrossReviewerAgreement != SemanticTruth`.
- `RepairPush => ReReviewAllRequiredPlanes`.
- `ReviewTriadGreen != MergeAuthority`.

## Crystalline routing

The review triad is a governance/verification projection, not evidence that all eight crystalline consequence planes are earned. For this V1 policy:

- W0: exact head identity.
- W1: Codex review evidence.
- W2: CodeRabbit review evidence.
- W3: Codacy quality evidence.
- W4: disagreement/missing/stale reviewer challenge.
- W5: exact-head conjunction receipt.
- W6-W8: unearned by this policy alone.

## Operational note

GitHub repository rulesets/branch protection SHOULD make the Review Triad Gate a required check on protected merge targets. If repository-administration APIs are unavailable to an agent, the absence of that provider-side protection MUST be recorded explicitly; repository policy and the gate remain canonical, but cannot be represented as an unbypassable GitHub server rule until an administrator enables the required check.
