# Aura GitHub Review Triad Policy V1

Status: **CANONICAL GOVERNANCE RULE — FAIL CLOSED**

## Invariant

Every GitHub change pushed to an AuraOS pull-request branch MUST receive a **clean exact-current-head outcome** from all three required reviewer classes before that change is eligible for merge, promotion, release, provider effect, public effect, or any equivalent production-admission claim:

1. **OpenAI Codex code review**
2. **CodeRabbit code review**
3. **Codacy static/code-quality review**

These three are cumulative. None substitutes for another. Sourcery, GitHub Actions, Aura-native review learning, security scanners, human review, and future reviewers are additive evidence only unless a later canonical policy explicitly promotes them into the required set.

A review merely occurring is not a pass. Unresolved exact-head Codex/CodeRabbit findings remain blocking.

## Push semantics

A raw `git push` happens before a pull-request reviewer can inspect the resulting remote commit. Therefore this policy does **not** claim that a review can precede the network push that creates the reviewable SHA.

Instead, the enforceable rule is:

> **Every push invalidates prior review admission and MUST trigger/reacquire Codex + CodeRabbit + Codacy clean evidence for the new exact head before the pushed change can become merge/promote/release admissible.**

`PushOccurred != ReviewAdmission`.

`NewHeadSHA => PriorHeadReviewAdmissionInvalid`.

`MergeOrPromotionAdmissible => CodexCleanExactHead AND CodeRabbitCleanExactHead AND CodacyPassedExactHead`.

## Trusted enforcement boundary

The canonical gate is `.github/workflows/aura-github-review-triad-gate.yml` backed by `scripts/aura_github_review_triad_gate.py`.

The **enforcement verifier MUST execute from the trusted default branch**, never from the pull request's own mutable copy. The PR SHA is evidence data; it is not allowed to supply the code that decides whether its own reviews are sufficient.

The enforcement workflow therefore uses default-branch-triggered events (`pull_request_target`, trusted provider comments/check completions/statuses), fetches the default-branch verifier, evaluates the target PR head, re-fetches the PR head after evidence collection, and explicitly publishes the `Aura GitHub Review Triad Gate` status onto that exact SHA.

The pull request that initially installs V1 is a **bootstrap HOLD**: until the verifier/workflow exist on the trusted default branch, that installing PR cannot self-certify an unbypassable review-triad admission. Its code may be reviewed/tested, but server-side enforcement becomes earned only after trusted installation plus branch-protection/ruleset configuration.

`UntrustedPRVerifier != AdmissionAuthority`.

`TrustedDefaultBranchVerifier + ExactPRHeadAsData => EligibleGateExecution`.

`InitialHead == FinalHead == RequestedHead` is required; a push during evidence collection fails closed.

## Exact-head evidence and provider identity

**Provider identity MUST NOT be inferred from mutable text.** A status context named `Codacy`, a check named `CodeRabbit`, a review body containing `@codex review`, or a copied bot login is not provider provenance.

V1 pins GitHub-owned provider identities:

- **Codex:** GitHub actor ID `199175422` with login `chatgpt-codex-connector[bot]`, or GitHub App slug `chatgpt-codex-connector`.
- **CodeRabbit:** GitHub actor ID `136622811` with login `coderabbitai[bot]`, or GitHub App slug `coderabbitai`.
- **Codacy:** GitHub App slug `codacy`. If an installed Codacy integration exposes a different GitHub-owned slug/identity, V1 remains HOLD until this canonical allowlist is deliberately updated from observed provider evidence.

The immutable actor ID + expected bot login pair is required for user/bot evidence; matching the login string alone is insufficient. Check-run evidence is attributed by GitHub App slug, never by check name.

Accepted completion semantics are provider-specific:

- **Codex:** a trusted exact-head APPROVED review/check, or a trusted Codex clean completion summary that explicitly binds the reviewed commit (for example its `Reviewed commit: <sha-prefix>` form plus a no-major-issues conclusion). Exact-head inline Codex findings block the Codex plane; merely mentioning the SHA, being queued, running, or unavailable never counts as completion.
- **CodeRabbit:** a trusted current-head successful status/check or approved completion, with no unresolved exact-head CodeRabbit finding. A draft/repository skip notice is not review completion. A historical skip does not poison future heads forever; a skip suppresses completion only when it is newer than or tied to the relevant CodeRabbit completion attempt.
- **Codacy:** a successful exact-head check from the pinned `codacy` GitHub App. Absence of Codacy is a failure, not a waiver.

The gate paginates review, comment, status, and check collections rather than silently ignoring later pages.

`MutableProviderLabel != ProviderIdentity`.

`ProviderReviewOccurred != ProviderPassed`.

`PinnedProviderIdentity + ExactHeadBinding + CleanOutcome => EligibleReviewEvidence`.

`UnresolvedExactHeadFinding => HOLD`.

Review evidence from an older SHA cannot be carried forward after `synchronize`/push.

## Review lifecycle

For every PR head:

1. Push or update the branch.
2. Codex review is requested/triggered for that exact head. Repository/workspace configuration SHOULD use Codex review-on-every-push where available; explicit `@codex review` is the fallback trigger.
3. CodeRabbit reviews the exact head. If automatic review is unavailable/skipped, manual `@coderabbitai review` is required.
4. Codacy analyzes the exact head and reports success.
5. Supplemental reviewers may run: Sourcery, Aura Review Learning, security/static-analysis workflows, and humans.
6. Findings are evaluated. A blocking finding MUST be repaired or explicitly dispositioned through the relevant governed review process. A repair push creates a new head and invalidates every prior-head triad admission.
7. Trusted provider completion events re-run the default-branch Review Triad Gate.
8. The gate revalidates that the PR head did not change while evidence was collected and publishes its status directly to the exact PR SHA.
9. Only after the triad status and all other required project-specific gates are green may a separate authority layer consider merge/promotion/release.

## Failure and unavailability

`ReviewerUnavailable != ReviewerPassed`.

If Codex, CodeRabbit, or Codacy is unavailable, disconnected, rate-limited, skipped, cannot prove its pinned GitHub identity, cannot bind evidence to the exact head, or reports unresolved findings, the change remains **HOLD / NONPROMOTING**. The correct response is to restore/re-run/configure/repair that reviewer plane, not to replace its evidence with another tool.

A reviewer finding does not authorize an automatic fix. Findings enter the normal repair/re-review loop. Any repair push creates a new head and therefore invalidates the previous triad admission.

## Authority ceiling

The Review Triad proves only that three independent review planes reached clean outcomes on the exact current head under the bounded provider-evidence rules above. It does not itself prove:

- semantic correctness or truth;
- producer identity beyond pinned GitHub provider evidence;
- runtime behavior beyond executed tests/checks;
- human/community consent;
- source mutation authority;
- execution, commit, merge, promotion, release, provider, or public-effect authority.

`ThreeCleanReviews != MergeAuthority`.

`ThreeCleanReviews != SemanticCorrectness`.

`ReviewerAgreement != GroundTruth`.

## HyperDrive laws

- `Push != Review`.
- `ReviewOnOldHead != ReviewOnCurrentHead`.
- `Codex + CodeRabbit + Codacy` is a conjunction, not a vote.
- `ProviderReviewOccurred != ProviderPassed`.
- `OneReviewerSuccess + AnotherReviewerMissing => HOLD`.
- `UnresolvedExactHeadFinding => HOLD`.
- `StaticAnalysis != IntentAwareReview`.
- `IntentAwareReview != StaticAnalysis`.
- `MutableProviderLabel != ProviderIdentity`.
- `ProviderStatusSuccess + NewerProviderSkip != ReviewCompletion`.
- `UntrustedPRVerifier != AdmissionAuthority`.
- `HeadChangedDuringEvidenceCollection => HOLD`.
- `CrossReviewerAgreement != SemanticTruth`.
- `RepairPush => ReReviewAllRequiredPlanes`.
- `ReviewTriadGreen != MergeAuthority`.

## Crystalline routing

The review triad is a governance/verification projection, not evidence that all eight crystalline consequence planes are earned. For this V1 policy:

- W0: exact head identity + trusted verifier identity.
- W1: pinned clean Codex outcome.
- W2: pinned clean CodeRabbit outcome.
- W3: pinned successful Codacy quality outcome.
- W4: disagreement/missing/stale/spoofed/skipped/blocking-review challenge.
- W5: exact-head conjunction receipt + status published to exact PR head.
- W6-W8: unearned by this policy alone.

## Operational note

GitHub repository rulesets/branch protection SHOULD make the `Aura GitHub Review Triad Gate` status a required check on protected merge targets. If repository-administration APIs are unavailable to an agent, the absence of that provider-side protection MUST be recorded explicitly; repository policy and the gate remain canonical, but cannot be represented as an unbypassable GitHub server rule until an administrator enables the required status context.
