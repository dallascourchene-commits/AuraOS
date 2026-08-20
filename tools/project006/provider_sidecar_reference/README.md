# Project006 Provider Dispatcher Sidecar Reference

Status: **AUTHOR REPAIR STAGING / NOT DEPLOYED / FRESH INDEPENDENT REVIEW REQUIRED**

Parent work order: `PROJECT006-RESIDENT-DEEPSEEK-WORKERCRYSTAL-BB-POC-001`

Source floor at branch creation: `50ef5c3970cd0ebaa408b49335b5c7d01dba6c30`

This directory stages a bounded Lane-B reference. It does not claim live
Project006 integration, provider connectivity, credential availability, systemd
deployment, benchmark success, test-pass status, or production readiness.

## Security boundary

The Resident remains network-incapable. The reference accepts only a logical
`route_ref` (`primary`, `premium`, `reasoner`, `coding`, `cheap_builder`,
`shadow`, or `summarizer`). Provider, model, and HTTPS endpoint are resolved
inside the provider-facing process from Aura's canonical `ProviderRegistry`.
The Resident/WorkCapsule cannot supply a URL, host, IP address, or credential.

Credentials are consumed only by the provider-facing transport. Health and
dispatch receipts expose only `configured` and `key_count`; they contain no
credential prefix, suffix, fingerprint, identifier, or value.

## First independent HOLD

Drive review `1kakoSXR5EYFMfMOdiNOzQfxkD7OQ-bwu7jAZSO7xHRQ` identified four
blockers in the canonical source floor:

1. `aura_api_rotator._post_json` retries TLS certificate failures with
   `CERT_NONE` and hostname checking disabled.
2. `ProviderRegistry.get_redacted_health_report()` exposes API-key substrings.
3. Existing key rotation is not provider/account concurrency control.
4. Resident-supplied arbitrary provider endpoints would widen authority.

This reference takes the reviewer's permitted isolation route rather than
claiming the unsafe legacy transport is repaired globally.

## PR #291 independent-review repair generation

The first PR review generation was reviewed independently by Sourcery and
Greptile. Their returned findings are repair inputs, not author self-review.
The current author generation addresses those reported issues by staging:

- strict default-verified HTTPS with no `CERT_NONE` or hostname-disabled retry;
- redirects disabled at the opener, with 3xx mapped to typed `REDIRECT_BLOCKED`;
- a bounded provider response size with `Content-Length` precheck and bounded
  body read;
- JSON content-type enforcement before parsing;
- zero-secret health/dispatch receipts;
- explicit bounded in-flight and queue limits;
- HTTP 429 as `RETRYABLE_PROVIDER_PRESSURE`, without treating API-key count as
  multiplied provider/account capacity;
- half-open 429 handling that releases the probe and reopens the circuit rather
  than wedging recovery;
- side-effect-free circuit introspection separated from mutating probe admission;
- dispatch attempt identity bound to capsule ID, lease generation, fencing
  token, currentness reference, logical route, and a deterministic digest of
  messages/max_tokens/temperature;
- explicit route-marker tests in addition to logical-role allowlisting.

The canonical `aura_api_rotator.py` fail-open path and the legacy registry
health-report key-substring behavior remain unchanged on this branch. Other
callers of those legacy functions remain outside this candidate's claim ceiling.
Independent review must decide whether this isolated bypass is sufficient for
Project006 or whether a separate global repair is required before reuse.

## Candidate adversarial tests

`test_provider_sidecar.py` supplies author-created tests for independent
execution/review covering:

- logical-route allowlisting and network-destination marker rejection;
- registry-owned DeepSeek routing;
- one-shot fail-closed TLS behavior;
- redirect blocking;
- response byte ceilings and JSON content type;
- zero credential material on serialized status surfaces;
- lease/fence/currentness/execution-bound attempt identity;
- 429 pressure without key-count capacity multiplication;
- half-open 429 recovery state;
- side-effect-free circuit introspection;
- bounded queue admission;
- circuit opening/blocking.

Their presence is not a claim that they pass. The Lane-B author will consume
only external CI/reviewer results as validation evidence.

## Integration seam

Expected flow:

`Resident AF_UNIX request -> logical route_ref + WorkCapsule lease/fence/currentness -> ProviderSidecarReference -> ProviderRegistry -> strict bounded HTTPS transport -> typed/redacted receipt -> Lane C scheduler`

Lane B must not absorb Lane A AF_UNIX protocol ownership or Lane C scheduling
state. Lane C should consume only typed pressure/result receipts and must never
receive credentials.

## Rollback

The candidate is isolated on branch `p0plus/project006-provider-sidecar-reference`
and PR #291. Before any later deployment, rollback is abandonment/closure of
that branch/PR. No runtime service, provider credential, main branch, live
Resident, bounty target, or deployment is changed merely by this staging branch.

## Claim ceiling

Established only by source materialization and external repository receipts:

- a reversible Lane-B review candidate exists;
- the candidate encodes the intended logical-route, strict/bounded transport,
  bounded pressure/circuit, execution-bound attempt identity, and zero-secret
  receipt contract;
- independent review findings were converted into a new author repair generation.

Not established until new independent evidence exists:

- candidate tests pass;
- correctness/security of the repaired candidate;
- all reviewer findings are actually resolved;
- safe integration with the running Project006 Resident;
- canonical egress global repair;
- live DeepSeek/provider behavior;
- measured concurrency/cost/rotation performance;
- systemd deployment, reboot persistence, rollback execution, merge, or production use.

Next boundary: **fresh independent review of the repaired exact head**. The
Lane-B author must not approve, resolve-as-correct, or certify its own repair.
