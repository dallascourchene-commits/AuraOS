# ThinkPad Resident MoE Autonomy — AWJ-017 staged reference

Status: **STAGED / NONPROMOTING / host-benchmark-required**.

## Host envelope

Source-bound inventory: Intel Core i5-1335U, 15.68 GiB RAM, Intel Iris Xe (~2 GiB reported adapter RAM), WSL `/dev/dxg`. No local model/runtime was observed in the bounded Aug. 21 inventory.

## Decision

Aura itself remains the always-on deterministic/event-driven resident. **The model is not the resident.** Models are demand-loaded execution resources behind the Expert Fabric.

Primary local background model: `LiquidAI/LFM2.5-8B-A1B-GGUF:Q4_K_M` (5.16 GB GGUF; 8.3B total / ~1.5B active; 32 experts / 4 routed per token). It is the first model allowed to be installed and benchmarked after host preflight.

Cold near-fit reasoner: `openai/gpt-oss-20b`. Its llama.cpp reference working set is ~14.9 GB at 8K context, so on a 15.68 GB Windows+WSL machine it is **not** an always-on model. It may run only after the warm model is unloaded and an exact memory preflight proves enough free memory.

AirLLM: experimental cold tier only. Start with a tiny fixture and I/O/security/runtime tests; do not auto-download a giant model. `Qwen/Qwen3-30B-A3B` is the initial architecture candidate because current AirLLM v3.x advertises Qwen3 MoE support, but it is not admitted until the host benchmark closes compatibility, disk and latency obligations.

## 27-trit / MoE composition

The current checked K27 key is **27 trits**, not 27 binary bits.

```text
Sub-Arena / current source generation
→ DomainLens + Temporal NOW
→ minimum WorkCapsule
→ K27 physical/cache prefix
→ ExpertBundle backend selection
→ chosen model
→ model-internal MoE gate chooses its own experts
```

`K27 != model expert ID`. Do not pin one of 27 Aura shards to one neural expert. Aura scopes the cognition; the model's native router selects its own experts.

## 24/7 background ladder

T0, no model: currentness scan, ArtifactBirth/L0 allocation, manifests/digests, CODEMAP/source anchors, duplicate-ID scars, stale affected cones, receipt integrity, queue/restart reconciliation.

T1, warm LFM2.5: classify deltas, propose relations/placement, compress verified deltas, regression triage, bounded patch proposals. Run only when power/thermal/foreground/memory gates admit it.

T2, deep local: cross-document reconciliation, difficult falsification, hard reasoning/synthesis. Prefer gpt-oss-20b only if exact host preflight earns the near-fit slot; otherwise stay on LFM2.5 or defer.

T3, AirLLM cold experimental: very slow private overnight jobs after separate adapter/I/O benchmark. Never the control plane.

T4, remote/swarm: only for independent challenge or residuals that truly require it. Prefer 0/1/3/9 workers; 27 real calls only for preregistered or independently justified frontiers.

## Gate 10 law

Background autonomy may advance D0 work through source/currentness binding, deterministic checks, Construct, Challenge, Verify, reproduction and independent review **up to Gate 10**. It may not auto-promote a model proposal merely because a model is confident. D1+ effects and owner/publication/authority changes remain gated.

## Idle behavior

- Battery: deterministic T0 by default.
- User active: T0 plus short T1 only if it does not interfere.
- Idle >=5 min + AC + >=7 GiB available RAM + >=12 GiB free disk: T1 may load.
- Idle >=30 min + AC: T2 may be considered only after warm unload and exact working-set preflight.
- Idle >=60 min + AC + >=80 GiB free disk: AirLLM experiment may be considered only if separately admitted.
- Heavy foreground load or thermal warning: defer model work immediately.

These thresholds are staged safety defaults, not measured performance claims; the owner-host benchmark must tune them.

## Morning successor

Every maintenance epoch collapses to one compact `MORNING_SUCCESSOR_FRAME`: what changed; tests and failures; accepted Gate-10-ready proposals; blocked work; falsifiers; exact model/backend usage; RAM/disk/time/energy proxy; remote calls/cost; source/currentness reopen routes; and ordered unresolved residuals.

No transcript or private chain-of-thought is stored as durable cognition. Durable learning is source-bound structured rationale/procedure/failure evidence only.
