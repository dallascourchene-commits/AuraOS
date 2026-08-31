# Aura GitHub Review Triad Policy V1

Status: **CANONICAL GOVERNANCE RULE — FAIL CLOSED**

## Invariant

Every GitHub change pushed to an AuraOS pull-request branch MUST receive a **clean exact-current-head outcome** from all three required reviewer classes before that head can be considered eligible for merge, promotion, release, provider effect, public effect, or equivalent admission:

1. **OpenAI Codex code review**
2. **CodeRabbit code review**
3. **Codacy static/code-quality review**

The three are cumulative. Sourcery, Aura review learning, GitHub Actions, security scanners, and human review are additive and do not substitute for any required plane.

`PushOccurred != ReviewAdmission`.

`NewHeadSHA => PriorHeadReviewAdmissionInvalid`.

`MergeOrPromotionAdmissible => CodexCleanExactHead AND CodeRabbitCleanExactHead AND CodacyPassedExactHead`.

`RepairPush => ReReviewAllRequiredPlanes`.

## Trusted enforcement boundary

The enforcement workflow is `.github/workflows/aura-github-review-triad-gate.yml`; the verifier is `scripts/aura_github_review_triad_gate.py`.

The admission verifier MUST execute from the trusted default branch, never from a pull request's mutable copy. The PR head is evidence data only. The verifier reads the requested PR head before collection, gathers all provider evidence with pagination, reads the PR head again, and fails closed unless both observations equal the requested SHA. The trusted workflow publishes the resulting `Aura GitHub Review Triad Gate` status directly to that PR SHA.

The pull request that installs V1 is a **bootstrap HOLD**. Its `.github/workflows/aura-github-review-triad-bootstrap-tests.yml` may compile and test the proposed verifier, but bootstrap testing is explicitly NONAUTHORITY and cannot certify its own admission.

`UntrustedPRVerifier != AdmissionAuthority`.

`InitialHead == FinalHead == RequestedHead`.

## Provider identity

Provider identity MUST NOT be inferred from mutable names or text. A check named `Codacy`, a status context named `CodeRabbit`, a review body saying `Codex review complete`, or a copied bot login does not establish provider provenance.

V1 accepts only GitHub-owned identities observed on AuraOS:

- **Codex:** user/bot identity `(actor_id=199175422, login=chatgpt-codex-connector[bot])`.
- **CodeRabbit:** user/bot identity `(actor_id=136622811, login=coderabbitai[bot])`.
- **Codacy:** GitHub App identity `(app_id=56611, slug=codacy-production)`.

No unobserved Codex or CodeRabbit GitHub App ID is guessed. If their evidence later arrives through an App rather than the pinned user/bot actor, the gate remains HOLD until the immutable App ID + slug pair is observed and deliberately added.

For GitHub App evidence, **both App ID and slug must match**. Matching the slug alone is insufficient. For bot/user evidence, **both actor ID and login must match**. Matching the login alone is insufficient.

`MutableProviderLabel != ProviderIdentity`.

`ProviderSlugAlone != ProviderIdentity`.

`ProviderActorLoginAlone != ProviderIdentity`.

## Clean outcome semantics

A reviewer merely running is not a pass.

- **Codex:** completion must bind the exact current head and report a clean outcome. An `@codex review` request is only a trigger. Queued/running/unavailable summaries do not count. Exact-head inline Codex findings are blockers.
- **CodeRabbit:** completion must come from the pinned actor and represent an actual completed review with no unresolved exact-head finding. A GitHub commit status whose state is `success` but whose provider-authored description says `Review skipped`, `manual review required`, queued, unavailable, or equivalent is **not completion**.
- **Codacy:** a successful completed exact-head check must come from App `(56611, codacy-production)`. The observed AuraOS check is `Codacy Static Code Analysis`; its mutable check name is not used as identity.

Historical CodeRabbit skip records do not poison future reviewed heads forever; only a skip/noncompletion at or after the relevant completion can suppress that completion.

`ProviderReviewOccurred != ProviderPassed`.

`SuccessState + ProviderDescriptionSaysSkipped != CleanCompletion`.

`UnresolvedExactHeadFinding => HOLD`.

## Review lifecycle

For every PR head:

1. Push/update the branch. The new SHA invalidates previous admission.
2. Request/trigger Codex review for that exact SHA.
3. Obtain an actual CodeRabbit review for that exact SHA; if automatic review is skipped, trigger manual review.
4. Codacy analyzes that exact SHA.
5. Evaluate provider findings. Repair any blocker; a repair creates a new SHA and restarts all three planes.
6. Trusted provider-completion/status/check events cause the default-branch gate to re-evaluate.
7. The gate paginates statuses, check runs, reviews, review comments, and issue comments; it revalidates the PR head after collection.
8. Only a clean three-plane exact-head conjunction may be called review-triad green.
9. A separate authority layer must still decide merge/promotion/release.

## Failure semantics

`ReviewerUnavailable != ReviewerPassed`.

Missing, stale, skipped, spoofed, rate-limited, unresolved, wrong-head, wrong-ID, or wrong-App evidence produces **HOLD / NONPROMOTING**. Another tool cannot substitute for the missing required reviewer.

A reviewer finding does not by itself authorize a repair. Repairs remain ordinary governed repository changes and require a fresh triad on the resulting SHA.

## Authority ceiling

The review triad proves only that the three required independent review planes reached clean outcomes under this bounded evidence policy on one exact current head. It does not prove semantic truth, producer identity beyond the pinned provider evidence, runtime behavior beyond executed tests, human/community consent, or mutation/execution/commit/merge/promotion/release/provider/public-effect authority.

`ThreeCleanReviews != MergeAuthority`.

`ThreeCleanReviews != SemanticCorrectness`.

`ReviewerAgreement != GroundTruth`.

## HyperDrive laws

- `Push != Review`.
- `ReviewOnOldHead != ReviewOnCurrentHead`.
- `Codex + CodeRabbit + Codacy` is a conjunction, not a vote.
- `ProviderReviewOccurred != ProviderPassed`.
- `ProviderAppId + ProviderSlug` is the App identity conjunction.
- `ProviderActorId + ProviderLogin` is the bot/user identity conjunction.
- `OneReviewerSuccess + AnotherReviewerMissing => HOLD`.
- `SuccessState + SkipDescription => HOLD`.
- `UnresolvedExactHeadFinding => HOLD`.
- `StaticAnalysis != IntentAwareReview`.
- `IntentAwareReview != StaticAnalysis`.
- `UntrustedPRVerifier != AdmissionAuthority`.
- `HeadChangedDuringEvidenceCollection => HOLD`.
- `RepairPush => ReReviewAllRequiredPlanes`.
- `ReviewTriadGreen != MergeAuthority`.

## Crystalline routing

The review triad is a governance/verification projection, not proof that all eight crystalline consequence planes are earned:

- W0: exact PR head + trusted verifier identity.
- W1: pinned clean Codex outcome.
- W2: pinned clean CodeRabbit outcome.
- W3: pinned successful Codacy App outcome.
- W4: stale/spoofed/skipped/noncompletion/unresolved/race challenge.
- W5: exact-head conjunction receipt/status.
- W6-W8: unearned by this policy alone.

## Operational note

GitHub repository rulesets/branch protection SHOULD make `Aura GitHub Review Triad Gate` a required protected-branch status. Until that server-side rule is verified, repository policy and exact-head receipts are canonical governance evidence but MUST NOT be described as an unbypassable GitHub merge rule.
