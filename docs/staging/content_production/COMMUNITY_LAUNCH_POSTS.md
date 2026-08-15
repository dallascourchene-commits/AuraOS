# Developer Community Launch Drafts — War Capsule 02 / Triad 2

**Coordinate:** `AD:DISTRIBUTION:MEDIA-MATERIALIZE:002`  
**State:** `DRAFT / NOT POSTED / HUMAN RELEASE GATE REQUIRED`

## Claim envelope used in every draft

The requested launch angle described “98% token cost reduction under 4GB RAM limits.” Current source-bound repository material does **not** support that sentence as written. These drafts preserve the actual evidence split:

- **Measured serialization result:** `286 B → 78 B`, or **72.73% fewer serialized bytes** in the bounded projection benchmark. This is not tokenizer-measured 94%+ compression.
- **Token/L0 reduction:** `≥94%` remains a **target / unverified source gap** in the current scorecard generation.
- **Operating-cost model:** a supplied local/edge model compares `$60–$180/month` with a `$4,900–$12,900/month` cloud-agent baseline, yielding approximately **98.60–98.78% lower modeled monthly OpEx** at paired endpoints. It is not an audited customer-savings benchmark and not token reduction.
- **Measured memory:** **116.71 MiB peak process RSS** in the bounded host benchmark. That is small relative to a **4 GiB device-class capacity**, but it is not a proof that every full deployment fits every 4 GB device, and it does not satisfy the separate `<95 MiB` target.
- **Bounded concurrency:** **25/25 exact-once DONE**, **0 duplicate fleet payloads** in the tested 25-slot daemon harness.
- **SQLite WAL:** **19,934.69 writes/s @ 5 workers**. Receipt throughput was not separately measured, so do not relabel this as receipts/s.
- **Security gate:** **0/868 attack transitions reached executable state** (`0.0000%` gate-layer ASR); not official end-to-end InjecAgent scoring.
- **Legacy τ-bench compatibility:** **42/42** bounded task-lane trials preserved exact oracle-action trajectories; not official τ-bench pass^k.

Repository source anchors for reviewers:

- `README.md`
- `docs/INDUSTRY_BENCHMARK_SCORECARD.md`
- `docs/MASTER_EXHAUSTIVE_BENCHMARK_SCORECARD.md`
- `docs/SECURITY_AND_ACCURACY_SCORECARD.md`
- `docs/staging/ready_review/PR_MANIFESTO_PRESS_RELEASE.md`

---

# Hacker News

## Title A

**Show HN: AuraOS – local-first agent coordination with 116 MiB process RSS and source-resolvable state**

## Title B

**Show HN: What if agent systems routed locally before paying for another model call?**

## Draft body

I’m building AuraOS, a local-first coordination substrate for AI/agent workloads.

The basic idea is simple: don’t send every routing, lookup, state, and retrieval decision to a large hosted model. Resolve deterministic structure locally, hydrate the smallest source-resolvable context needed for the objective, and escalate only the unresolved semantic work.

A few current repository measurements, with their boundaries:

- 1,366,040.46 deterministic FST iterations/s and 8,196,242.75 transitions/s in the routing microkernel;
- 19,934.69 SQLite WAL row writes/s at the best observed 5-worker run — not measured full receipts/s;
- 116.71 MiB peak process RSS in the bounded host benchmark;
- 25/25 exact-once bounded daemon tasks with 0 duplicate fleet payloads;
- 0/868 attack transitions reaching executable state in the current gate-layer security harness;
- 42/42 exact oracle-action trajectory preservation in the bounded legacy τ-bench compatibility sample;
- 72.73% fewer serialized bytes in one state-projection benchmark (`286 B → 78 B`).

There’s also an economic model comparing `$60–$180/month` local/edge operation with a `$4,900–$12,900/month` cloud-agent baseline, which works out to about **98.60–98.78% lower modeled monthly OpEx** at paired endpoints. That is a planning model, not audited savings, and it is **not** a claim of 98% token compression.

The memory result is similarly bounded: 116.71 MiB process RSS is small relative to a 4 GiB device-class budget, but I’m not claiming every complete deployment fits any arbitrary 4 GB machine.

The architecture combines guarded FST/WFST routing, SQLite WAL, recursive `3^n` Merkle aggregation, source-bound receipts, bounded worker execution, selective hydration, and explicit human disposition gates.

I’d especially value criticism on three questions:

1. What benchmark would you accept as a fair tokenizer-level test of the “smallest sufficient context” thesis?
2. What failure modes should be added before calling the 25-slot worker result meaningful for real local-agent workloads?
3. Where does local-first routing stop paying off once model/tool latency and cache effects are included?

The project is open source. I’d rather have the claims attacked than polished.

## HN posting note

Prefer Title A if the benchmark pages are easy to reach from the root README. Prefer Title B if the technical story is stronger than the numbers on launch day. Do not put “98% token reduction” in the HN title.

---

# Reddit — r/LocalLLaMA

## Title A

**Local-first agent orchestration: 116.71 MiB process RSS, 25-slot exact-once harness, and a modeled ~98.6–98.8% OpEx delta — looking for replication**

## Title B

**I’m testing an agent architecture where the expensive model call is the exception, not the router**

## Draft post

I’ve been building AuraOS around a slightly different local-agent assumption:

**the local machine should handle structure first; the model should get the smallest unresolved question.**

Instead of making every worker carry the whole repository/world, a worker gets a coordinate, a bounded objective, source-resolvable context, and a receipt. Deterministic routing/state/metadata work stays local whenever possible; model escalation happens when the substrate can’t resolve the semantic ambiguity.

Current bounded repository results:

- **116.71 MiB** peak process RSS in the host benchmark;
- **25/25** exact-once daemon tasks, **0 duplicate fleet payloads**;
- **19,934.69 SQLite WAL writes/s @ 5 workers** — row-write throughput, not receipts/s;
- **72.73% fewer serialized bytes** in one state-projection workload (`286 B → 78 B`);
- **0/868** gate-layer attack transitions reached executable state;
- **42/42** bounded legacy τ-bench trajectory-preservation trials.

Two numbers I want to be very explicit about because they’re easy to overstate:

- `≥94%` tokenizer/L0 reduction is still a **target**, not a verified tokenizer benchmark.
- The `~98.60–98.78%` figure is from a **supplied monthly OpEx model** (`$60–$180` local/edge vs `$4,900–$12,900` cloud-agent baseline). It is not “98% token reduction” and not audited production savings.

Likewise, 116.71 MiB process RSS is encouraging for a 4 GiB device class, but it’s not a universal guarantee that every model/tool stack fits inside 4 GB.

I’d love LocalLLaMA-style replication rather than applause. If you were benchmarking this fairly, what would you use for:

- identical task corpus across local-first vs model-first routing;
- token accounting including cache hits;
- local CPU/RAM/energy accounting;
- model/tool latency;
- quality equivalence / failure recovery;
- concurrency scaling at 3, 6, 9, 16, 25 workers?

The 3→6→9 motif in Aura is a conditional routing/rebase label, not a magic performance law. One staged router showed a 6:1 logical transition-count difference but only about 1.279× local wall-clock speedup, which is exactly why I’m trying to keep structure claims separate from performance claims.

If people here are interested, I can package the benchmark protocol so results from different local machines are comparable.

## r/LocalLLaMA posting note

Use Title A only when the benchmark source links are immediately available. If discussion gets pulled toward the 98% number, pin a comment clarifying that it is the **economic model**, not token compression.

---

# Reddit — r/Rust

## Important scope note

The current source material does **not** establish AuraOS as a Rust implementation or provide a Rust-specific benchmark. This draft is therefore framed as a **systems-design / implementation question for Rust developers**, not as a Rust project launch claim.

## Title A

**Systems design question: how would you map a guarded FST + SQLite WAL + proof-carrying worker runtime into Rust?**

## Title B

**Would Rust be a good fit for a local-first agent substrate with bounded workers and source-resolvable state?**

## Draft post

I’m working on an open-source local-first coordination substrate called AuraOS. The current implementation/evidence is not a Rust benchmark, so I’m posting here for architectural critique rather than pretending it is.

The runtime model has a few pieces that look like they could benefit from Rust’s type system and explicit effect boundaries:

- guarded finite-state routing before expensive model calls;
- a six-slot runtime grammar (`DIR → ASP → CLASS → SUBJ → VOICE → STEM`);
- SQLite WAL for local durable state;
- bounded worker execution with exact-once completion receipts;
- recursive `3^n` Merkle aggregation;
- source/currentness/verification/authority kept as separate state rather than one “trusted” bool;
- fail-closed behavior when the source or promotion authority is unresolved.

The current host-side measurements include **116.71 MiB peak process RSS**, **25/25 exact-once** bounded daemon tasks with **0 duplicate fleet payloads**, and **19,934.69 SQLite WAL row writes/s @ 5 workers**. Those are not Rust results and I would not expect a Rust port to reproduce them automatically.

There is also a local/edge economic model that comes out roughly **98.60–98.78% lower monthly OpEx** than a supplied cloud-agent baseline. Again: that is a model, not 98% token compression and not an audited savings claim. The measured state projection is **72.73% fewer serialized bytes**; tokenizer-level `≥94%` remains unverified.

If you were designing the Rust boundary, what would you make impossible at the type level?

For example:

```text
RouteResolved != SourceVerified != Current != Authorized
```

I’m interested in whether these should be distinct newtypes/state-machine phases so that a routed object literally cannot call promotion/deployment effects until the correct authority token exists.

I’m also curious about the best approach for:

- typestate vs enums for the six-slot/FST transition surface;
- `sqlx` / `rusqlite` WAL patterns under bounded worker concurrency;
- Merkle receipt batching without a second persistence plane;
- deterministic replay and receipt hashing;
- keeping an LLM/tool adapter outside the trusted routing/authority core.

If anyone has examples of Rust systems that do this kind of capability/effect separation cleanly, I’d appreciate pointers and criticism.

## r/Rust posting note

Do not use a title implying a Rust port exists until one exists. The strongest reason to post here is to seek implementation critique around typestate, authority/effect separation, concurrency, SQLite, and deterministic receipts.

---

# Optional pinned clarification for any platform

> **Benchmark clarification:** the ~98.6–98.8% number discussed here is a modeled monthly OpEx delta from supplied local/edge vs cloud-agent cost ranges. It is not measured token compression. Current measured projection evidence is 72.73% fewer serialized bytes; tokenizer-level ≥94% remains a target. Peak process RSS was 116.71 MiB in the bounded host run; “4 GB” refers to a device-class capacity comparison, not a universal deployment ceiling.

# Release checklist

Before a human posts any of these drafts:

1. Confirm the root README and benchmark scorecards still contain the same current measurements.
2. Replace stale metrics rather than leaving historical numbers in the launch copy.
3. Keep `modeled`, `bounded`, `gate-layer`, `legacy compatibility`, and `row writes/s` qualifiers adjacent to the applicable claims.
4. Do not turn the 4 GiB capacity comparison into a universal hardware guarantee.
5. Do not call the OpEx model “token reduction.”
6. Do not call the bounded 42/42 result official τ-bench pass^k.
7. Do not call 0/868 gate transitions official end-to-end InjecAgent ASR.
8. For r/Rust, confirm the post still clearly says there is no Rust-specific implementation/benchmark being claimed.
9. Publish only under explicit human disposition; this artifact itself performs no external posting.

**FINAL STATE:** `HN DRAFT + r/LocalLLaMA DRAFT + r/Rust DRAFT PACKAGED / CLAIMS SOURCE-BOUNDED / NOT POSTED`
