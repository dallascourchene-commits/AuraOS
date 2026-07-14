# Aura Model Cognome Adaptive Router

## Status

Aura's public router now exposes three compatibility modes:

```text
LEGACY       existing calibration-ledger router; default and rollback path
SHADOW       plan and record a governed route; never call a provider
PAIRED_LIVE  execute one explicitly authorized comparison route
```

The environment variable `AURA_ADAPTIVE_ROUTER_MODE` may select a mode, but its default is `LEGACY`. A caller may also pass `routing_mode` directly or use the CLI `--routing-mode` option.

## Context routing

`aura_ai_router.query_router()` now resolves an arbitrary objective through:

```text
current objective and explicit targets
→ Capability Resolver V2
→ Capability Connectome path packet
→ Topological Context Anchor
→ exact source spans and hashes
→ callers, callees, tests, dependencies
→ bounded worker context
```

The generated Markdown task table is consulted only when current exact topology cannot identify a target. Its output is marked advisory and cannot authorize a patch.

## Model planning

`AdaptiveModelRouter` constructs a graph-bound `TaskContext`, queries the Model Cognome, and delegates hard admission plus policy evaluation to `aura_shadow_model_router`.

Admission remains fail-closed for:

- endpoint lifecycle status and drift;
- privacy and egress policy;
- required capabilities and current graph digest;
- evidence split and minimum evidence;
- context, cost, latency, tool, and consequential-risk limits.

A forced model is a human override request, not an admission bypass. It must already be admitted, and it cannot replace a required high-risk panel.

## Live authorization

PAIRED_LIVE requires a content-addressed `ExecutionAuthorization` bound to:

- named human approver;
- verifier identity;
- Purpose digest;
- current Capability Connectome graph digest;
- allowed route modes and endpoint profiles;
- nonce, issue time, expiry, and maximum calls;
- explicit permission for a forced-model override when applicable.

The authorization is consumed once per router instance. Before execution—and before every fallback call—the router revalidates the capability path and endpoint ACTIVE status.

## Execution semantics

```text
ZERO_MODEL  injected deterministic executor only
DIRECT      one admitted model, followed by the named verifier
CASCADE     next model only after call failure or verifier rejection
PANEL       at least two panel profiles and one judge profile through AuraFusion
```

Every DIRECT, CASCADE, panel, and judge call receives stable task, route, profile, call, cost-run, comparison, and observation identities. Calls use the canonical egress boundaries and preserve unknown usage or cost as unknown.

## Authority boundary

```yaml
legacy_default: true
shadow_provider_calls: false
paired_live_requires_authorization: true
high_risk_requires_explicit_verifier: true
automatic_policy_activation: false
automatic_policy_promotion: false
automatic_source_mutation: false
automatic_commit: false
automatic_push: false
automatic_merge: false
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
```

## CLI examples

Legacy behavior is unchanged:

```powershell
python aura_router.py route --task mesh_offload --mock
python aura_router.py fusion --task "Analyze this architecture" --mock
```

Shadow planning requires a Purpose digest but makes no provider calls:

```powershell
python aura_router.py route `
  --task mesh_offload `
  --routing-mode shadow `
  --purpose-digest PURPOSE_DIGEST
```

An authorized live comparison additionally requires approved data egress and a reviewed authorization JSON file:

```powershell
python aura_router.py route `
  --task mesh_offload `
  --routing-mode paired_live `
  --purpose-digest PURPOSE_DIGEST `
  --authorization-file .\approved-experiment.json `
  --allow-data-egress
```

No command in this interface promotes the resulting policy. Promotion remains a separate REPLAY/SHADOW evidence proposal requiring verifier and human review.
