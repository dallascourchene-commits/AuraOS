# AuraOS Cost-First Cognitive Allocation SOP

Status: staged / nonpromoting / owner-directed operational policy.

## Purpose

Aura should minimize *incremental* cognitive cost while preserving correctness, currentness, authority, source fidelity and reopenability. Cheap work is not merely a model-selection problem: the cheapest lawful computation is often reuse or deterministic AuraOS execution rather than another inference call.

## Standing execution ladder

1. **Reuse current coordinated cognition first.** Reopen current Coordinate Memory, WorkCapsules, receipts, source-bound summaries, code, tests, equations, proofs and prior model outputs before asking any model to reconstruct them.
2. **AuraOS/no-model next.** Use scripts, deterministic routing, FSTs, indexes, currentness checks, affected-cone recompute, CODEMAP, tests, Arena state and receipt logic before inference.
3. **ChatGPT interactive control plane when available.** For top-level planning, synthesis, review and decisions in an active ChatGPT session, use the existing interactive reasoning surface before creating a separate paid API call. AuraOS must not assume a ChatGPT subscription is programmatically callable as an API.
4. **Local model when it is sufficient and lawful.** A resident/local model can beat paid API cost for bounded work, subject to host resource policy.
5. **DeepSeek is the default paid remote swarm provider.** Ordinary paid A+/B-/C0 lanes use the current Aura-owned DeepSeek route when authorized and cost-bounded.
6. **Expensive frontier models are exceptions.** Kimi/Fireworks/OpenRouter or another higher-cost frontier route requires an earned reasoning need, a named provider/model, explicit owner spend authorization, a finite cost ceiling where rates are available, and an amortization plan.

## Bootstrap/control-plane rule

OpenCode or the model powering an interactive terminal is **bootstrap/control-plane only by default**. It may inspect host state, recover the resident, compile/rebase WorkCapsules, initiate/check/stop the DeepSeek swarm, and verify receipts. It should not silently perform the entire substantive work order when DeepSeek workers can do it.

If DeepSeek is unavailable, Aura returns a typed blocker. It does **not** silently fall back to Kimi, Fireworks, OpenRouter or another paid provider.

## Cost admission

Before a paid provider call, the current owner should compare the available lawful routes:

`reuse -> AuraOS/no-model -> interactive ChatGPT (when available) -> local model -> DeepSeek -> requested expensive frontier`.

Selection rule:

> Choose the lowest incremental lawful cost that can satisfy the bounded consequence.

Unknown monetary cost is `UNKNOWN`, never zero/free. Retries, duplicate dispatch and provider fallback remain visible cost.

## Cognitive amortization contract

Every paid inference must leave reusable coordinated cognition so future work does not pay to reconstruct the same state. At minimum preserve:

- source/currentness-bound result receipt;
- WorkCapsule/result digest;
- Coordinate Memory placement or exact reopen pointer;
- compact L0 successor summary;
- reusable code/test/equation/proof artifact where produced;
- counterevidence, invalidators and residuals;
- provider/model/attempt/cost evidence class;
- rebase triggers.

The intended loop is:

`paid inference -> verified material delta -> coordinate/place -> collapse -> exact reopen -> reuse before re-inference`.

## Swarm rule

DeepSeek workers receive role-specific current WorkCapsules and surgical hydration. Worker count increases only when unresolved independent frontier earns it. Three role labels from one provider call are not three independent workers.

## Governance boundary

Cost optimization never widens authority. D1+ remains separately authorized. Autonomous background execution stops at Gate 10 / ready-for-owner-promotion. No provider's model confidence is evidence of correctness, authority or promotion readiness.
