# AuraOS PR Kit / Investor Fact Sheet

**Document status:** Source-bound repository fact sheet  
**Work order:** `WO-DOCS-BENCHMARK-PR-SYNC-001`  
**Coordinate:** `AD:SYSTEM:DOCS-BENCHMARKS-PR-SYNC:001`

## Executive summary

AuraOS is a local-first deterministic coordination substrate built around guarded finite-state routing, SQLite WAL persistence, recursive `3^n` Merkle aggregation, source-bound receipts, bounded worker execution, and peer-to-peer transport surfaces.

The strongest current repository evidence is **engineering validation**, not third-party certification. This fact sheet therefore separates measured results from targets, cost-model assumptions, and staged architecture.

## Verified engineering snapshot

| Surface | Current result | Scope boundary |
| :--- | :--- | :--- |
| Six-slot FST deterministic routing | **1,366,040.46 iterations/s**; **8,196,242.75 transitions/s** | deterministic transition microkernel |
| `3^n` Merkle aggregation | **2,460.61 rollups/s**; **895,661.61 hashes/s** | depth 5, 243 leaves/rollup |
| SQLite WAL best observed | **19,934.69 writes/s @ 5 workers** | one-row transaction writes; not separately measured full-receipt throughput |
| Process peak RSS | **116.71 MiB** | host process high-water mark; separate `<95 MiB` target remains unmet/unverified for narrower core runtime |
| Serialized projection | **72.73% fewer bytes** (`286 B → 78 B`) | serialization bytes, not tokenizer-measured token compression |
| UDP localhost unicast | median **7.080 µs**, p95 **10.126 µs** | localhost synchronous RTT; not WAN/remote mesh |
| InjecAgent-derived hard gate | **0/868** attack transitions reached executable state | `0.0000%` gate-layer ASR; not official end-to-end InjecAgent score |
| Legacy τ-bench compatibility | **42/42 = 100.00%** exact oracle-action trajectory preservation | bounded 6-task sample × 7 deterministic lanes; not official pass^k |
| Bounded daemon fleet | **25/25 exact-once DONE**, **0 duplicate fleet payloads** | correctness validation, not fleet throughput |

## Operating-cost model

The work order supplies a comparison model of:

- **AuraOS local/edge operating-cost assumption:** `$60–$180/month`
- **Cloud-agent baseline assumption:** `$4,900–$12,900/month`

Using paired endpoints, the implied reduction is:

- `$60` versus `$4,900` → **98.78% lower modeled monthly OpEx**
- `$180` versus `$12,900` → **98.60% lower modeled monthly OpEx**

Accordingly, **“~98% OpEx reduction” is a conservative summary of the supplied paired-endpoint model**.

### Cost-model boundary

This is **not a measured billing benchmark in the current scorecards** and should not be represented as audited customer savings. The repository sources inspected for this synchronization do not independently establish the `$60–$180` or `$4,900–$12,900` inputs. Real deployment economics can vary with hardware amortization, inference/model fees, electricity, networking, storage, staffing, support, redundancy, and workload intensity.

## Edge deployment viability

AuraOS is intentionally local-first. Current executable evidence supports the following edge-oriented properties:

1. **Small process footprint relative to a 4 GiB device class.** The measured peak is **116.71 MiB**. That is compatible with a 4 GiB capacity envelope, while the stricter internal `<95 MiB` benchmark remains a separate unresolved target rather than being silently rewritten.
2. **Local durable state.** SQLite WAL validation reached **19,934.69 writes/s** at the best observed worker count, with row-count, WAL-mode, and integrity checks.
3. **Low local transport overhead.** UDP localhost p95 RTT measured **10.126 µs** in the industry scorecard. Remote/multi-node gossip remains a separate network benchmark.
4. **Bounded deterministic routing.** The six-slot FST/WFST transition kernel exceeded **8.19 million transitions/s** in its microbenchmark scope.
5. **Bounded exact-once coordination.** The 25-slot daemon fleet completed **25/25** tasks exactly once with no duplicate fleet payloads in the validation fixture.

## Cryptographic / Merkle provenance

AuraOS uses recursive aggregation and source-bound evidence so higher-order state can remain compact without treating compact pointers as truth or authority.

Current measured Merkle surface:

- `3^n` rollups: **2,460.61 rollups/s**
- hashing: **895,661.61 hashes/s**
- benchmark depth: `n=5`
- leaves per rollup: `243`

Receipts and benchmark artifacts may be hashed and/or signed for integrity. An artifact signature proves consistency with the declared signing material; it does **not**, by itself, prove human identity, repository ownership, or promotion authority.

## Six-slot guarded runtime

The Human Agent / guarded WFST projection uses:

```text
DIR → ASP → CLASS → SUBJ → VOICE → STEM
```

with the governing order:

```text
hard guards
→ admitted state-local transitions
→ exact WFST ranking
→ six-slot packet
→ deterministic/model-assisted explanation
→ human choice
```

This creates a clear separation between **routing/addressability** and **truth/authority**. External content, vector similarity, compact state, or a model suggestion cannot independently mint an executable capability.

## 3→6→9 Harmonic architecture

The current Aura Drive provenance generation defines `3 → 6 → 9/1′` as a **conditional diagonal-rebase shortcut** across independently verified/current boundaries. It is a staged routing/discovery contract, not universal arithmetic law and not an authority mechanism.

Current GitHub `main` does not expose a source-bound executable service under the literal name `3-6-9 Harmonic Daemon`. For investor/press accuracy, treat the Harmonic Daemon as a **staged daemonization target** of the conditional diagonal-rebase theorem until its runtime source and benchmark receipt are committed.

## Defense-in-depth / engineering defensibility

AuraOS's defensibility is architectural rather than dependent on a single model:

- **Provenance before authority:** external tool/content data is data, not permission.
- **Fail-closed action grammar:** malformed tool/action names are rejected by the guarded FST surface.
- **Source-defeasible state:** compact summaries and inherited priors can be defeated by exact source/currentness evidence.
- **Merkle/receipt lineage:** recursive state can retain inspectable cryptographic ancestry instead of relying on opaque conversational memory.
- **Local-first persistence:** SQLite WAL and deterministic worker leases reduce dependence on a remote orchestration control plane.
- **Human promotion boundary:** proposal/routing layers cannot silently promote themselves into commit, push, merge, or sovereign disposition.
- **Measured attack-surface gate:** 0/868 executed gate trials reached an executable attack state in the current InjecAgent-derived harness scope.

These are technical defense surfaces, not a legal claim of exclusivity, patent validity, or an uncrossable competitive moat.

## What not to claim yet

Do **not** represent the following as verified current benchmark facts:

- `94% token compression (~48 tokens/step)` — the current master exhaustive scorecard marks the ≥94% L0 compression claim **UNVERIFIED_SOURCE_GAP**; the current measured projection is **72.73% fewer serialized bytes**.
- `<95 MB RSS` — current measured process/controller peaks are about **116.71–117.348 MiB**; the internal `<95 MiB` gate is not currently satisfied for those measured processes.
- `>5,250 receipts/sec` — current repository evidence measures **SQLite WAL writes/s**, not full source-bound receipt issuance throughput.
- `<500 µs remote mesh gossip` — current measurements are localhost UDP RTT proxies only.
- `0% official InjecAgent exploit rate` — current result is **0% gate-layer ASR** over 868 trials, not official end-to-end episode ASR.
- `100% official τ-bench score` — current result is **100% bounded legacy trajectory preservation**, not official pass^k.

## Source documents

- `docs/INDUSTRY_BENCHMARK_SCORECARD.md`
- `docs/MASTER_EXHAUSTIVE_BENCHMARK_SCORECARD.md`
- `docs/SECURITY_AND_ACCURACY_SCORECARD.md`
- `docs/AURA_HUMAN_AGENT_SIX_SLOT_GUIDE.md`
- `docs/AURA_ST3GG_CANONICAL_CONTRACTS.md`

For public communication, **source boundary wins over headline compression**: a narrower accurate claim is preferable to a broader unsupported one.
