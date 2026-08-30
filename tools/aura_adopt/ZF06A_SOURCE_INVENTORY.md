# AURA-ADOPT-001 ZF-06A current-source inventory

Observation date: 2026-08-30. This file records discovery/currentness status and evidence-routing rules, not device performance claims.

## Historical labels

Repository code search on the current accessible/default index returned no executable mapping for the literal labels `D2RM`, `RO3DD`, `HyperDrive`, `K27`, or `Morton`. This means **NO_CURRENT_EXECUTABLE_MAPPING_FOUND** for those literal names in this inventory pass; it does not claim the ideas are absent from historical Drive research.

ZF-06 must not reconstruct an implementation from prose merely to manufacture a benchmark target. A historical label becomes assessable only when a current source ref and benchmark ref are supplied.

## Current reusable evidence seams

- **Objective-1 / PR #354 EntryRouteCompiler**: source/currentness-bound route decisions expose storage and compute constraints while keeping device truth upstream. It is a consumer of host evidence, not a low-storage benchmark.
- **ZF-02 HostSubstrateWitness/AdaptiveProvisioning lane**: designated source of Android host-fit evidence. Android retention claims in `LowStorageMechanismAssessmentV1` require a host-witness ref.
- **ZF-03 / PR #360 ArenaRecipeV1**: current executable recipe serialization/import/export/remix reference, but no measured retained-byte/browser-lifecycle comparison is currently bound here. It is therefore a future benchmark candidate, not a proven storage win.
- **ZF-00B / PR #355 AdoptionFrictionReceiptV1**: canonical measurement spine can carry downloaded/retained bytes and time, but does not itself prove that a particular math/storage mechanism caused the reduction.
- **PR #307 documented routing/hydration ablation**: contains bounded projection-equivalent/equal-cost-byte reductions, while its own claim boundary says those are not provider-token, latency, cost, or quality claims. Do not relabel those measurements as Android/browser storage performance without a matching payload/baseline responsibility and lifecycle benchmark.

## External research hydration — evidence only

The following papers/community reports inform falsifiers and benchmark fields. They are **not** local AuraOS benchmark evidence and cannot by themselves earn a device-level `RETAIN` disposition.

### Literature-reported KV-cache mechanisms

- **KIVI — arXiv:2402.02750**. Reports 2-bit asymmetric KV-cache quantization and demonstrates that context length/batch size make KV-cache memory and load behavior a material inference constraint. ZF-06 consequence: compare the same model/runtime/workload and capture KV-cache bytes plus latency/throughput consequences; paper results remain `LITERATURE_REPORTED` until reproduced on the target route.
- **KVQuant — arXiv:2401.18079**. Reports sub-4-bit KV-cache quantization with method-specific quality/performance results. ZF-06 consequence: memory reduction must bind a quality target and the runtime/kernel used; a byte ratio alone is insufficient.
- **KVTuner — arXiv:2502.04420**. Reports model/layer sensitivity and hardware-friendly mixed-precision KV-cache configurations. ZF-06 consequence: a single global bit-width label cannot stand in for quality evidence; bounded-loss claims need a predeclared accepted-quality threshold and model-bound evidence.
- **SnapKV — arXiv:2404.14469**, **CacheGen — arXiv:2310.07240**, and **H2O — arXiv:2306.14048** are additional eviction/compression/streaming references for later target-specific reproduction. Their reported gains remain literature evidence until exact runtime/workload/device reproduction exists.

Google-Scholar-targeted searches for the KIVI/KVTuner titles did not return a directly inspectable `scholar.google.com` record through the available search interface in this run; canonical arXiv/PMLR records were used instead. Do not fabricate Scholar-specific metadata.

### Community-reported mobile constraints

Recent Reddit/LocalLLM/LocalLLaMA/Android reports repeatedly identify memory bandwidth, OS memory headroom/reclaim, thermal throttling, GPU memory limits/driver behavior, KV-cache/activation overhead, first-run model download burden, and firmware/OS drift as practical mobile constraints. These reports are useful for selecting falsifiers but remain anecdotal `COMMUNITY_REPORTED` inputs, not benchmark proof.

ZF-06 consequence: target-device experiments should bind OS/firmware/runtime generation and re-open when those change; peak RAM alone is not enough. Measure at least retained/download bytes, peak working memory, KV-cache peak bytes when relevant, TTFT/prefill, decode cost, cache-load/recompute cost, and thermal/power proxy where observable.

## Coordinate-memory allocation for external research

Production semantic Coordinate Memory ownership remains unresolved in the current Arena schema. Therefore these allocations are **PENDING semantic bindings** with `semantic_owner_status=PENDING_EXTERNAL_OWNER` and `semantic_address_status=PENDING_EXTERNAL_OWNER`. The values below are only `PHYSICAL_CACHE_SHARD(K27)` hints, calculated by the checked rule `SHA-256(SID|domain) mod 3^27` and encoded as exactly 27 trits. They must never be promoted to semantic identity or authority.

| SID | Domain lens | Physical K27 hint | Evidence class | Affected cone |
|---|---|---|---|---|
| `arxiv:2402.02750` | `zf06-kv-cache` | `002012002021122021122101100` | LITERATURE_REPORTED | KV bytes, peak memory, TTFT/decode, quality |
| `arxiv:2401.18079` | `zf06-kv-cache` | `022210122122101011111211212` | LITERATURE_REPORTED | KV bytes, kernels, quality, long-context fit |
| `arxiv:2502.04420` | `zf06-kv-cache` | `112001100111202002121000012` | LITERATURE_REPORTED | layer/model sensitivity, mixed precision, quality threshold |
| `reddit:1r5fhpj` | `zf06-mobile-runtime` | `111010102020102000100112112` | COMMUNITY_REPORTED | bandwidth, thermal, GPU/NPU runtime |
| `reddit:1renuky` | `zf06-mobile-runtime` | `010101202021021022222021212` | COMMUNITY_REPORTED | model-fit preflight, KV/activation RAM overhead |
| `reddit:1ufw07o` | `zf06-mobile-runtime` | `122220100211201122001111101` | COMMUNITY_REPORTED | Android local model size/performance/download burden |
| `reddit:1ttyzpi` | `zf06-mobile-runtime` | `200010012121212102002010100` | COMMUNITY_REPORTED | RAM bandwidth, GPU cap/driver, OS/firmware drift |
| `reddit:1txpqru` | `zf06-kv-cache` | `102122202212210220200022222` | COMMUNITY_REPORTED | KV RAM/VRAM offload trade-off |

Each cell reopens only its affected metric cone when the paper/version, target runtime/model, OS/firmware, or device host witness changes. `K27 != semantic address`, `CACHE HIT != TRUTH`, and source/currentness remain identity-bearing.

## Assessment rule

A current mechanism is `READY_FOR_ASSESSMENT` only when both a source mapping and measurement source exist. Source without measurement is `EXECUTABLE_MAPPING_PRESENT_MEASUREMENT_MISSING`. Historical/prose-only names remain `NO_CURRENT_EXECUTABLE_MAPPING_FOUND`.

A comparable assessment must bind one `BenchmarkScenario` shared by candidate and baseline: workload ID, model, runtime, execution environment, prompt length, generated length, batch size, and configured context. The responsibility declares `required_metrics`; missing candidate or baseline values remain `UNKNOWN`, never zero. Literature/community evidence can shape the test plan but cannot substitute for target-route measurements.
