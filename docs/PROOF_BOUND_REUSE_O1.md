# Proof-Bound Reuse & Reproof Closure V1 — O1

State: D0 NONPROMOTING / no effect authority / Gate10 false.

## Exact two fresh foreign rebase parents

1. `Arena_advance_report__HostedProofV2__2026-09-05.md` — Drive `10XRTWZEKU5ncZlrKwauamSqmX-kC6icx`. Consequence: durable local proof-evaluation reuse can reduce repeated evaluation work while preserving deterministic receipt roots, but reuse must expire/currentness-check correctly.
2. `ARENA_SUCCESSOR__Provider_Proof_Bridge__2026-09-05.md` — Drive `148NOTZjNfD8xVTQlCkd1QqsLVLzmfkGe`. Consequence: hosted proof is meaningful only when bound to exact current heads, workflow attempt/generation, required jobs/steps, and current observation cut.

These parents are consequence-distinct: one contributes durable calculation reuse; the other contributes exact provider/currentness proof identity.

## Objective

Compile those two laws into a proof-bound reuse controller where a cached proof can be reused only while source head, workflow generation, input root, dependency root, required-step root, binding generation, result digest, and receipt digest all remain exact. Dependency invalidation wakes only affected projects. Reproof closes stale state only through a fresh receipt for the currently expected identity.

## Falsifiers

- source-head change cannot reuse an old proof;
- workflow-generation change cannot reuse an old proof;
- input-root drift cannot reuse an old proof;
- dependency invalidation must wake exactly dependent projects;
- dependency rebinding removes old reverse edges and increments binding generation;
- old receipt cannot close a new binding generation;
- missing required step fails closed;
- receipt/result tampering fails closed;
- forged alternate-head identity cannot be admitted;
- no receipt may carry effect authority or Gate10.

## Local proof

- 19 focused tests x 3 fresh Python venvs = 57/57 PASS.
- 1,000-project benchmark: 20 affected by one dependency invalidation, 980 reused, 20 recomputed, 98% fewer proof evaluations, aggregate result root identical to full recomputation, zero stale reuse after head changes.
- Wall-time reduction across three fresh venvs: 95.67%–96.25% on the synthetic hash-heavy evaluation workload. This is an environment-sensitive local benchmark, not provider/model throughput.
- Omega-8 exhaustive: 6,561 states, 1 D0 nonpromoting admission, 6,560 HOLD, zero hard-invalid false admissions.
- 13D: 100,000 samples, zero routing/context repairs of hard-invalid consequence heads.
- HS1000: 1,000 deterministic adversarial cells across stale-head, workflow-drift, input-drift, dependency-drift, receipt-tamper, missing-step, and authority-escalation classes.

## Claim ceiling

This proves local/controller semantics and synthetic efficiency only. It does not prove physical GLM-5.3 speed, provider execution cost, production safety, merge/deploy authority, or Gate10.
