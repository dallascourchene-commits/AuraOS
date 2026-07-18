# Aura Gate — Sovereign Agent Governance Gateway

## Status and proof boundary

Aura Gate Phase 2 is a Forge-specific, private-deployment proof of Aura's governance
gateway. It wraps the retained Aura Forge evidence contract and worker lifecycle with
verified identity, content-addressed policy, expiring authority, purpose-limited egress,
protocol adapters, comparison controls, and append-only audit evidence.

It is more than an endpoint or rate-limit gateway because the authority it compiles is
bound to an exact purpose, actor, policy, Forge contract, repository state, files,
capabilities, destination, model route, data classes, retention class, verifier set,
budget, nonce, and expiry.

The implemented proof is deliberately narrow:

- Forge-specific rather than an arbitrary-domain policy engine;
- OIDC with one offline, pinned RS256 JWKS rather than SAML or SCIM;
- a private, single-node server and container profile rather than HA or Kubernetes;
- deterministic JSONL SIEM projection rather than a vendor-certified SIEM connector;
- human review at the terminal engineering boundary, with no release authority.

SAML/SCIM, HA/Kubernetes, arbitrary-domain policy, vendor-certified SIEM integrations,
and broader enterprise certification remain separate programs. This implementation does
not establish general production readiness.

## Authority flow

```text
OIDC bearer token at the private HTTP boundary
  → offline pinned-JWKS RS256 verification
  → pseudonymous VerifiedGateIdentity
  → exact objective/purpose digest + static Gate policy
  → Aura Forge prepare (no worker start)
  → frozen Forge contract ID + full contract digest
  → ArenaLease + GateAuthorityEnvelope
  → append PRE_ACTION audit evidence
  → durable lease issue
  → re-verify identity, policy, audit chain, lease, and expiry
  → Forge start_prepared(exact contract ID, exact contract digest)
  → purpose-limited egress capsule over exact canonical bytes
  → bounded worker turns and verifiers
  → READY_FOR_HUMAN_REVIEW
  → lease dissolution
  → separate human decision
```

The ordering is intentional. `prepare` freezes Forge evidence before Gate issues a
lease. `start` does not prepare again: it calls `AuraForgeRuntime.start_prepared(...)`
with both the retained contract ID and full digest. Forge then rechecks repository HEAD,
CODEMAP digest, allowed-file source hashes, and the retained contract before opening a
worker session. Gate records the relevant pre-action evidence before Forge actions,
egress releases, and lease lifecycle transitions.

Unknown, stale, malformed, expanded, expired, replayed, or unauthorized requests fail
closed. A valid Gate envelope authorizes only the bounded Forge workflow represented by
that envelope; it is not patch, release, policy-promotion, or production authority.

## Canonical owners

Aura Gate is an authority envelope around existing owners, not a replacement for them.

| Concern | Canonical owner | Boundary |
|---|---|---|
| Forge preparation and bounded worker lifecycle | `aura_forge.py` | Retains the frozen Arena Evidence Contract, staging, verification, and human-review stop |
| Gate policy, request, authority envelope, and lease lifecycle | `aura_gate.py` | Compiles and revalidates exact Forge-specific authority; durable SQLite stores operational lease state, not a second event truth |
| Identity verification | `aura_gate_oidc.py` | Offline single-issuer RS256 verification against an operator-pinned JWKS; no discovery or network key fetch |
| Purpose-limited egress | `aura_gate_egress.py` | Admits exact canonical JSON bytes and emits a content-addressed capsule; performs no provider call |
| Audit and SIEM projection | `aura_gate_audit.py` | Uses Aura's canonical append-only event/payload owners plus chained authority receipts |
| Shadow and paired-live evidence | `aura_gate_comparison.py` | Produces comparison evidence only; never promotes a route or mutates production |
| MCP/A2A translation | `aura_gate_adapters.py` | Strictly translates protocol messages into the Gate runtime; body-supplied identity has no authority |
| Private HTTP boundary | `aura_gate_server.py` | Authenticates before A2A dispatch, enforces bounded fixed routes, and emits safe error codes |
| Arena lease contract | `aura_liquid_planning_arena.py` | Remains the canonical Arena lease representation embedded in the Gate envelope |

The stable authority artifact is
[`schemas/aura_gate_authority_envelope.schema.json`](../schemas/aura_gate_authority_envelope.schema.json).
An operator policy example is
[`examples/aura_gate_policy.json`](../examples/aura_gate_policy.json). Policy IDs are
content-derived: changing any policy field without regenerating its ID is rejected.

## Identity and the Python trust boundary

`OIDCIdentityVerifier` accepts compact JWTs only when all configured checks pass. The
current verifier requires:

- exact issuer and an accepted audience;
- `azp` where OIDC multi-audience rules require it;
- valid `iat`, `exp`, optional `nbf`, configured clock skew, and maximum token age;
- an exact pinned `kid` from a local JWKS;
- RSA public signing material of at least 2048 bits and `RS256` only;
- configured role/group claim shapes and required entitlements;
- an exact nonce when the caller supplies one.

The verifier rejects `alg=none`, algorithm substitution, remote key URLs, embedded JWKs,
private JWK material, unsupported critical headers, duplicate key IDs, malformed JSON,
and invalid signature or time claims. It performs no OIDC discovery and no JWKS fetch.

The raw subject is transformed into a deployment-local pseudonym:

```text
actor_ref = HMAC-SHA256(actor_salt, canonical({issuer, subject}))
```

Neither the bearer token nor the raw subject/claims document belongs in audit, SIEM,
telemetry, or worker context. Safe authority metadata contains the pseudonymous
`actor_ref`, bounded issuer/audience/role/group values, validity times, key ID, and
digests of the token, claims, and pinned JWKS. The actor salt is a secret file and must
not be committed, logged, or copied into a policy.

`VerifiedGateIdentity` is a Python value object, not a self-authenticating credential.
Its constructor is public for deterministic integration and tests. Therefore:

- the HTTP boundary may create it only through `OIDCIdentityVerifier.verify(...)`;
- direct Python integrations must inject it only from that verifier or an equally
  trusted, separately reviewed identity boundary;
- never deserialize request JSON, MCP arguments, A2A message parts, or model output into
  `VerifiedGateIdentity`;
- never trust an `actor_ref`, role, group, token digest, or identity object supplied in a
  protocol body.

The private server rejects identity-shaped message fields and always supplies the
server-verified identity to the adapter after bearer verification.

The implementation follows the claim-validation semantics in
[OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html), while
intentionally using an offline, operator-pinned subset.

## Policy, authority, and lease lifecycle

`GatePolicyManifest` is immutable and deny-by-default. It binds:

- allowed purpose digests, capabilities, files, protocols, destinations, providers,
  models, data classes, egress fields, and retention classes;
- required verifiers, roles, and groups;
- lease, payload, token, context, output, turn, repair, and provider-call ceilings;
- `private_only=true`, `human_review_required=true`,
  `production_mutation=false`, and `automatic_promotion=false`.

`GateRunRequest` must match one exact policy and recompute to the declared purpose
digest. It cannot request a capability, file, destination, provider, model, protocol,
data/retention class, egress field, verifier budget, or TTL outside that policy.
The current `required_verifiers` values are exact Forge gates, not arbitrary command
selectors: `canonical_arena_verifier` and `hotswap_readiness`. Content-bearing turn fields
such as source/test slices, compressed context, failure packets, instructions, output
contracts, and Act Capsules require the canonical `BOUNDED_SOURCE_CONTEXT` data class.
Forge's context budget measures bounded context components; Gate's separate egress token
ceiling measures the whole serialized turn wrapper.
Its actor/policy/request-nonce tuple is one-use: Gate checks a digest-only durable nonce
index before Forge preparation and again transactionally when issuing the lease. A replay
therefore cannot prepare a second sequential Forge run or append a second issuance event.

On successful preparation, `GateAuthorityEnvelope` binds the verified identity basis,
policy and purpose digests, frozen Forge run/contract/repository identities, serialized
Arena lease, allowed scope, budgets, nonce, issue/expiry times, and immutable authority
flags. Its content-addressed ID and embedded digests are revalidated on every read.

The operational lifecycle is:

```text
ACTIVE → STARTING → STARTED → DISSOLVED
   └──────────────→ REVOKED
   └──────────────→ EXPIRED
```

SQLite provides transactional issue/transition/replay protection for local lease state.
The append-only audit/event chain remains the canonical history. Policy drift, actor or
entitlement drift, audit-chain failure, capability mismatch, invalid state, and expiry
block use before Forge is called. Reaching `READY_FOR_HUMAN_REVIEW` dissolves the lease;
it does not approve the patch.

Lease and audit state survive process restart, but all Forge run/session state is
process-local, including an `ACTIVE` prepared run. This proof does not claim session
resumption or HA failover: after restart, status inspection revokes a nonterminal lease
when its Forge state is unavailable. Drain, revoke, or expire every nonterminal run before
a planned restart, then prepare again with a new nonce.

The Gate runtime currently exposes five lifecycle operations:

| Operation | Required leased capability | Effect |
|---|---|---|
| `prepare` | policy admission precedes lease creation | Prepares Forge and issues exact Gate authority |
| `start` | `FORGE_START` | Starts only the retained Forge contract and governs the first egress capsule |
| `submit` | `FORGE_SUBMIT` | Submits one bounded response and governs any next-turn egress |
| `status` | `FORGE_STATUS` | Reads bounded Gate/Forge status after full reauthorization |
| `revoke` | `FORGE_REVOKE` | Records and applies an explicit terminal revocation |

Protocol adapters can expose only these Gate operations. They do not expose Forge's
internal runtime as a bypass.

## Purpose-limited egress

`GateEgressGovernor` compiles an exact JSON object without performing an external call.
Before release it verifies the envelope expiry and exact purpose, destination, provider,
model, data class, retention class, top-level field allowlist, payload-byte ceiling, and
token estimate. Nested content has structural and sensitive-key bounds.

The result contains:

- exact canonical payload bytes;
- a payload digest and byte/token estimates;
- destination/model/data/retention identity;
- the exact included top-level fields;
- a content-addressed `GateEgressCapsule`;
- explicit `source_mutation_performed=false` and
  `production_promotion_authority=false`.

Gate first consumes the durable egress-release allowance, then records a pre-action
`EGRESS_RELEASE` event containing evidence references to the capsule and payload digest,
and only then returns the admitted bytes. If audit persistence fails after allowance
reservation, the allowance remains conservatively consumed. The capsule proves which bytes were admitted; it does not
prove that a provider received them or that its response is correct.
Each distinct egress-capsule operation consumes one durable, idempotent Gate
egress-release allowance used as a provider-call budget proxy. This is not provider
billing telemetry and not a network-level limit on retries made after bytes leave Gate.
When provider usage is supplied, Gate rejects and revokes on input/output budget overrun
or inconsistent totals; absent usage remains unavailable rather than being treated as
enforced telemetry.

## MCP and A2A surfaces

The adapter adds an Aura authority envelope around existing protocol shapes. It does not
claim to replace either standard.

The MCP adapter targets MCP 2025-06-18 at the strict JSON-RPC message layer.
Only `aura_gate_prepare`, `aura_gate_start`, `aura_gate_submit`, `aura_gate_status`, and
`aura_gate_revoke` are advertised and dispatched. The adapter supplies the already-
verified identity out of band; identity in tool arguments is removed as untrusted input.
There are no comparison, SIEM export, raw Forge, staging, verification, or filesystem
tools. Unknown methods, tools, versions, fields, oversized values, and malformed
envelopes fail closed.

This MCP component is a strict message-level projection, not a complete network
transport. It validates `initialize`, `notifications/initialized`, `tools/list`, and
`tools/call`, but it does not retain per-connection initialization state or implement MCP
the [MCP HTTP authorization profile](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization),
OAuth/protected-resource discovery, TLS, Origin checks, or transport session management. A production
MCP host must supply and test those lifecycle and authorization controls before injecting
a verified identity.

The A2A surface follows the
[A2A v1.0 specification](https://a2a-protocol.org/v1.0.0/specification/) for preconfigured,
authenticated Agent Card discovery and the HTTP+JSON `message/send`, task-get, and
task-cancel mappings. Cancellation maps
to a bounded Gate revocation. Gate accepts one `ROLE_USER` message with one v1 `DataPart`
carrying `application/json` Gate operation data. Send requests must explicitly set
`configuration.returnImmediately=true`, accept only `application/json`, and request no
history; HTTP success uses the A2A `{"task": ...}` response wrapper. Errors use the
JSON representation of `google.rpc.Status` with bounded `ErrorInfo`. It
rejects text parts and the legacy `kind` shape, and does not accept body identity as
authority.

Protocol input is limited to 256 KiB and output to 512 KiB. Individual strings are
limited to 128 KiB; containers to 256 items; JSON trees to 4,096 nodes and depth 10.

The private HTTP boundary exposes only:

```text
GET  /health                    anonymous liveness, no repository detail
GET  /.well-known/agent-card.json
POST /message:send
GET  /tasks/{id}?historyLength=0
POST /tasks/{id}:cancel
```

Agent-card and message routes require one `Authorization: Bearer ...` header plus exact
`A2A-Version: 1.0`. `POST /message:send` additionally requires
`Content-Type: application/a2a+json`. Chunked/compressed bodies, duplicate security
headers, unsupported methods/routes, oversized bodies/headers, and identity spoof fields
are rejected. Access logging is disabled at this boundary so bearer tokens and request
targets do not enter the canonical audit trail.

## Shadow and paired-live comparisons

`AuraGateComparisonRunner` preserves the distinction between derived planning and live
evidence:

- `SHADOW` prepares two isolated arms and rejects evidence when injected provider/start
  counters change;
  its measurements are `DERIVED`, incomplete, and cannot select or promote a route.
- `PAIRED_LIVE` requires distinct declared arm lineage IDs, identical objective/repo/
  plan/gate/budget bounds, a one-use `ExecutionAuthorization`, invokes each adapter once,
  and requires reported one-call deltas plus verifier-backed measured results.

Authorization consumption is durable and transactional. Stored comparison consumption
evidence contains digests, not the raw claim. A preferred arm, when a named metric supports
one, is human-review evidence only. Both modes report
`promotion_performed=false`, `production_mutation=false`, and
`human_review_required=true`.

The paired runner authorizes the attempt and verifies observable provider/start counter
deltas after each injected arm returns. It cannot prevent an opaque executor from making
extra internal calls before returning; a mismatch invalidates the comparison evidence but
is not a network sandbox. Production integrations therefore need an independently
enforced provider quota or broker around each arm. Comparison is currently a trusted
in-process proof: it is not exposed through Gate's MCP/A2A/server surface, is not bound to
OIDC policy/audit, and must not accept caller-deserialized authorization as human proof.

## Audit, receipts, and SIEM export

`GateAuditLedger` writes through Aura's canonical append-only event/payload store and adds
a chained authority receipt. The operation ID is the idempotency key: identical retries
return the retained IDs, while reuse with different content fails closed. Parent-event,
event/sidecar, payload, operation, and receipt-chain integrity are rechecked before an
authorized Gate action.

The audit API intentionally accepts no free-form payload or metadata field. Records are
limited to bounded authority facts such as actor pseudonym, purpose/policy/lease IDs,
protocol, destination, decision, verifier/cost classes, revocation/dissolution reasons,
and content-addressed evidence references. Raw bearer tokens, raw OIDC claims, raw worker
prompts/responses, credentials, and provider secrets must never be written.

`AuraGateRuntime.export_siem(...)` requires the verified role `aura-gate-auditor`. It
first verifies the complete event/receipt chain and writes a deterministic JSONL
projection inside the configured, non-overlapping SIEM export root. Export uses exclusive
creation (an identical retry is idempotent; different existing content is never
overwritten). The export is a read-only integration artifact, not a vendor certification
and not a second event owner. The shipped server exposes no SIEM route or scheduler;
deployment code must call this auditor-authorized Python API or provide a separately
reviewed offline operator job.

## Private deployment

The standalone server loads only explicit local files and performs no identity discovery
or remote key fetch. All required paths must already exist; state and audit roots must be
separate. The cleartext single-node server accepts numeric loopback addresses only; the
container profile intentionally fixes the bind to `127.0.0.1`.

| Configuration | Required value |
|---|---|
| `AURA_GATE_REPO_ROOT` | AuraOS Git worktree root whose HEAD/CODEMAP/allowed-file digests are bound per run; the source bind itself may be a dirty mutable worktree |
| `AURA_GATE_POLICY_FILE` | One policy JSON object, or `{"policies": [...]}` plus an exact `AURA_GATE_POLICY_ID` selector |
| `AURA_GATE_OIDC_FILE` | Local OIDC verifier configuration (`issuer`, `audiences`, and optional bounded claim/time settings) |
| `AURA_GATE_JWKS_FILE` | Local pinned public JWKS JSON; no private keys |
| `AURA_GATE_ACTOR_SALT_FILE` | Secret file containing at least 32 nontrivial bytes |
| `AURA_GATE_STATE_ROOT` | Writable directory for operational SQLite state |
| `AURA_GATE_AUDIT_ROOT` | Separate writable directory for canonical audit evidence |
| `AURA_GATE_SIEM_ROOT` | Third, non-overlapping writable directory confining SIEM exports |
| `AURA_GATE_HOST` | Numeric loopback bind address only |
| `AURA_GATE_PORT` | Integer TCP port from 1 through 65535 |

The unprefixed deployment concepts `POLICY_FILE`, `OIDC_FILE`, `JWKS_FILE`,
`ACTOR_SALT_FILE`, `STATE_ROOT`, `AUDIT_ROOT`, `HOST`, and `PORT` map to the
`AURA_GATE_*` process variables above. The optional `AURA_GATE_POLICY_ID` is required
when a policy file contains more than one manifest. The hardened Compose profile requires
an exact `AURA_GATE_POLICY_ID` even for a single-policy file.

Local launch:

```bash
python -m aura_gate_server
```

`Dockerfile.aura-gate` and `docker-compose.aura-gate.yml` define the container proof.
Keep policy/OIDC/JWKS inputs read-only, mount the actor salt through the explicit read-only
bind at `/run/aura-gate/actor-salt`, keep state/audit/SIEM on distinct writable volumes,
mount the exact worktree's pre-created `Aura_Staging` directory as the only writable
repository subtree, use a read-only root filesystem, drop Linux
capabilities, set resource ceilings, and expose the service only on a numeric loopback
interface. Never use a mutable `latest` base image or place literal credentials in the
compose file.

The Dockerfile has no fallback base. `AURA_GATE_BASE_IMAGE` must be a purpose-built,
immutable Aura runtime reference
of the form `<image>@sha256:<64-lowercase-hex>`; its build-time guard rejects a tag-only,
missing, or malformed reference. The runtime uses numeric user/group `65532:65532` and
starts only `python -B -m aura_gate_server`. The base must already contain Git, pytest,
and the complete Aura `pyproject` runtime/test dependency closure; the Dockerfile performs
import/toolchain preflights and resolves no mutable packages. Application source is not
embedded in the image: Compose mounts the repository, policy, OIDC config, and JWKS
read-only, uses an explicit actor-salt bind, and gives only staging plus separate
state/audit/SIEM volumes write access. The host salt and staging paths must be readable or
writable, respectively, by UID/GID `65532:65532`; Compose does not change their host ACLs.
`Aura_Staging` contains prompts, responses, and candidate patches, so retention and cleanup
are operator responsibilities.

Container execution deliberately uses `network_mode: host`, fixes
`AURA_GATE_HOST=127.0.0.1`, and publishes no `ports:` mapping. This is required to keep the
cleartext bearer boundary on the host loopback interface: under an isolated bridge,
container loopback would not be host loopback. Host networking is supported on Docker
Engine for Linux. Docker Desktop requires version 4.34 or later and the explicit
**Enable host networking** opt-in before this profile can run.

Host networking removes the container's network-namespace isolation. The Gate process can
share the host network stack, so host firewall policy, operating-system controls, provider
allowlists, DNS controls, and enterprise egress enforcement remain required. Do not treat
`cap_drop`, a read-only root, or the Gate egress capsule as a network firewall. Do not add
a public bind, `ports:` publication, or unreviewed reverse proxy to this cleartext proof.
Remote/TLS termination and multi-node deployment require a separate threat model and
implementation.

The A2A v1.0 production transport requirement is HTTPS. This deliberately cleartext HTTP
profile is a loopback-only local proof, not an A2A production deployment. Do not make it
remotely reachable by changing the bind or adding an unreviewed proxy.

Compose also requires exact policy ID, port, CPU/memory limits, and distinct durable
volume names. Validate interpolation before launch; missing values fail immediately:

```text
AURA_GATE_BASE_IMAGE
AURA_GATE_REPO_ROOT
AURA_GATE_POLICY_FILE
AURA_GATE_OIDC_FILE
AURA_GATE_JWKS_FILE
AURA_GATE_ACTOR_SALT_FILE
AURA_GATE_POLICY_ID
AURA_GATE_PORT
AURA_GATE_MEMORY_LIMIT
AURA_GATE_CPU_LIMIT
AURA_GATE_STATE_VOLUME
AURA_GATE_AUDIT_VOLUME
AURA_GATE_SIEM_VOLUME
AURA_GATE_STAGING_ROOT
```

```bash
docker compose -f docker-compose.aura-gate.yml config
docker compose -f docker-compose.aura-gate.yml up --build
```

OIDC key rotation is explicit: drain, revoke, or expire all nonterminal leases, replace the
pinned public JWKS under operator control, restart the process, and retain the resulting
JWKS digest boundary. Changing the actor
salt changes pseudonymous actor references and therefore requires a deliberate identity/
audit migration decision.

## Operations and verification

Before serving Gate:

1. verify the repository HEAD and regenerate/verify CODEMAP when source or architecture
   changed;
2. generate a policy through `GatePolicyManifest.create(...)` and inspect every allowlist,
   budget, verifier, and immutable authority flag;
3. provide one exact OIDC issuer/audience configuration, a pinned public JWKS, and an
   independent local actor salt secret;
4. create separate state/audit/SIEM directories and the worktree's writable
   `Aura_Staging` directory with least-privilege filesystem access;
5. bind the current cleartext proof only to `127.0.0.1` and verify host-network support;
6. verify the focused implementation before admitting a real token or provider route.

Focused verification:

```bash
python -m pytest -q \
  tests/test_aura_forge.py \
  tests/test_aura_gate.py \
  tests/test_aura_gate_oidc.py \
  tests/test_aura_gate_egress.py \
  tests/test_aura_gate_audit.py \
  tests/test_aura_gate_comparison.py \
  tests/test_aura_gate_adapters.py \
  tests/test_aura_gate_server.py \
  tests/test_aura_gate_deployment.py \
  tests/test_aura_gate_contract_artifacts.py
```

Also run the repository's applicable static checks, schema validation, CODEMAP
regeneration/verification, and final diff review. Tests prove only the exact evaluated
tree and fixtures. They do not certify an external identity provider, provider network,
container platform, SIEM product, or production environment. The deployment tests are
static artifact-contract tests; when Docker is available, build/launch and real
prepare/start smoke tests remain required.

## Benchmark record

Phase 2 planning used Aura's Agent Bridge for bounded repository grounding and Selective
Council V3 for architecture deliberation. The auditable benchmark record is
[`docs/evidence/AURA_GATE_PHASE2_AGENT_BRIDGE_COUNCIL_V3_BENCHMARK_2026-07-18.json`](evidence/AURA_GATE_PHASE2_AGENT_BRIDGE_COUNCIL_V3_BENCHMARK_2026-07-18.json).

Full Codex-session provider input/output totals were not available and remain
`NOT_AVAILABLE`; unknown usage is not converted to zero. For the non-overlapping,
instrumented Bridge and Council scopes, the record reports:

| Field | Scoped token proxy |
|---|---:|
| Recorded input | 37,907 |
| Recorded output | 1,852 |
| Recorded total | 39,759 |
| Estimated counterfactual total | 91,746 |
| Estimated saved | 51,987 (56.66%) |

The original Bridge aggregate was captured during planning without per-file hashes and is
therefore explicitly marked as a historical snapshot that cannot be reproduced from the
larger final tree. A separate current-tree reference records per-file sizes and digests.
The Council arithmetic and instrumented artifact digest remain reproducible. This is
`DERIVED_COUNTERFACTUAL_WITH_CHAR4_TOKEN_PROXY` engineering evidence, not provider
billing and not a whole-session total. The Agent Bridge estimate compares bounded
digest/search/slice/micro context with a chars/4 full-file counterfactual. The Council V3
estimate compares selected critic lanes with a uniform six-lane counterfactual and
conservatively excludes a larger downstream judge prompt.

## Non-negotiable authority boundary

```yaml
planning_proposes: true
governance_authorizes: true
verification_proves: true
patch_authority: exact_source_spans_and_hashes_only
verified_identity_from_protocol_body: false
raw_tokens_or_claim_documents_in_evidence: false
production_mutation: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
automatic_promotion: false
human_review_required: true
```

Aura Gate can deny, constrain, record, revoke, expire, and dissolve Forge authority. It
cannot turn a model response, protocol message, comparison preference, SIEM export,
verifier score, or review-ready packet into a commit, push, pull request, merge, release,
policy activation, or production promotion.
