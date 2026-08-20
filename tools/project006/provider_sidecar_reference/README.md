# Project006 Provider Dispatcher Sidecar Reference

Status: **AUTHOR STAGING / NOT DEPLOYED / INDEPENDENT REVIEW REQUIRED**

Parent work order: `PROJECT006-RESIDENT-DEEPSEEK-WORKERCRYSTAL-BB-POC-001`

Source floor at branch creation: `50ef5c3970cd0ebaa408b49335b5c7d01dba6c30`

This directory stages a bounded reference for Lane B. It does not claim live
Project006 integration, provider connectivity, credential availability, systemd
deployment, benchmark success, or production readiness.

## Security boundary

The Resident remains network-incapable. The reference accepts only a logical
`route_ref` (`primary`, `premium`, `reasoner`, `coding`, `cheap_builder`,
`shadow`, or `summarizer`). Provider, model, and HTTPS endpoint are resolved
inside the provider-facing process from Aura's canonical `ProviderRegistry`.
The Resident/WorkCapsule cannot supply a URL, host, IP address, or credential.

Credentials are consumed only by the provider-facing transport. Health and
dispatch receipts expose only `configured` and `key_count`; they contain no
credential prefix, suffix, fingerprint, identifier, or value.

## Independent HOLD addressed by this candidate

The independent Lane-B source review identified four blockers:

1. `aura_api_rotator._post_json` retries TLS certificate failures with
   `CERT_NONE` and hostname checking disabled.
2. `ProviderRegistry.get_redacted_health_report()` exposes API-key substrings.
3. Existing key rotation is not provider/account concurrency control.
4. Resident-supplied arbitrary provider endpoints would widen authority.

This reference takes the reviewer's permitted isolation route rather than
claiming the unsafe transport is repaired globally:

- `StrictJsonTransport` uses Python's default verified HTTPS context and has no
  insecure TLS retry path.
- TLS verification failure becomes typed `TLS_FAILURE` state.
- health/pressure receipts never use `ProviderRegistry.get_redacted_health_report()`
  and contain no key material.
- admission is bounded by explicit in-flight and queue limits.
- 429 is returned as `RETRYABLE_PROVIDER_PRESSURE`; multiple API keys are not
  interpreted as multiplied provider/account concurrency.
- circuit state is explicit and scheduler-visible.
- dispatch attempt identity binds capsule ID, lease generation, fencing token,
  currentness reference, and route reference.
- endpoints are registry-owned and selected from logical roles only.

The canonical `aura_api_rotator.py` fail-open path and the legacy registry
health-report key-substring behavior remain unchanged on this branch. Therefore
other callers of those legacy functions remain outside this candidate's claim
ceiling. Independent review must decide whether isolated bypass is sufficient
for Project006 or whether a separate global repair is required before reuse.

## Candidate tests

`test_provider_sidecar.py` stages adversarial tests for:

- rejection of URLs/hosts/arbitrary provider names as route references;
- registry-owned DeepSeek routing for the logical premium route;
- one-shot fail-closed TLS behavior with no custom insecure context;
- zero credential material on serialized health/receipt surfaces;
- attempt identity changes across lease/fence/currentness generations;
- 429 pressure without API-key concurrency multiplication;
- bounded admission/queue fail-closed behavior;
- circuit opening and subsequent blocking.

These tests are supplied as author artifacts for independent execution and
review. Their presence is not a self-certification that they pass.

## Integration seam

Expected flow:

`Resident AF_UNIX request -> logical route_ref + WorkCapsule lease/fence/currentness -> ProviderSidecarReference -> ProviderRegistry -> strict HTTPS transport -> typed/redacted receipt -> Lane C scheduler`

Lane B must not absorb Lane A AF_UNIX protocol ownership or Lane C scheduling
state. Lane C should consume only typed pressure/result receipts and must never
receive credentials.

## Rollback

The candidate is isolated on branch `p0plus/project006-provider-sidecar-reference`.
Rollback before any later deployment is deletion/abandonment of that branch or
PR. No runtime service, credentials, provider calls, main-branch merge, or live
Project006 process is changed by this staged reference.

## Claim ceiling

Demonstrated by source materialization only:

- a bounded review candidate exists on a reversible branch;
- the candidate encodes strict TLS, logical registry routing, bounded admission,
  circuit/pressure state, lease/fence/currentness-bound attempt identity, and
  zero-secret receipt structure.

Not demonstrated until independent evidence exists:

- candidate test pass status;
- correctness/security of the candidate;
- safe integration with the running Project006 Resident;
- canonical egress global repair;
- live DeepSeek/provider behavior;
- measured concurrency/cost/rotation performance;
- systemd deployment, reboot persistence, rollback execution, or production use.

Next boundary: independent review/adversarial execution. The Lane-B author must
not approve or certify this candidate.
