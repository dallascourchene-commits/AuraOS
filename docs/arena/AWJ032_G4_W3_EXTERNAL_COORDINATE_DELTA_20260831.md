# AWJ032 GLM-5.3 G4 W3 — External Coordinate Delta

Date: 2026-08-31  
Authority: retrieval / currentness / reopen metadata only.

The G4 owner already allocated deterministic `K27-B3MOD27-XYZ-v1` records for the original external sources used by this cone. This addendum reuses those coordinates and adds only consequence-relevant concurrency falsifiers; no coordinate mints semantic identity, currentness, authority or transformer KV state.

| External record | K27 XYZ | Use in W3 |
| --- | --- | --- |
| `arxiv:2607.24787` / SpecPrefetch | `(16,9,15)` | transfer prediction is optimization; native routing remains authoritative; cache/bandwidth context is runtime-sensitive |
| `reddit:1w0wgad` / GLM-5.3 runtime benchmark discussion | `(0,1,4)` | workload/runtime/cache/offload differences are community falsification pressure only |
| `github:tonyd2wild/GLM-5.3-DFlash2-DGX-Spark` | `(7,11,20)` | FP8-KV/MTP/DFlash2/KV-pool/host configuration sensitivity |
| `arxiv:2606.15376` / CoAgent | `(17,23,18)` | serializability/conflict repair is a runtime coordination property, not a caller-value property |
| `github:Amanieu/seqlock` | `(10,1,19)` | before/after equality is meaningful only because the sequence token tracks writes; opaque-label equality alone is insufficient |
| `arxiv:2607.10487` / commit-time authorization | `(5,3,9)` | freshness/authority must still be rebound at durability/effect time |
| `scholar:direct-gap:2026-08-31` | `(12,12,16)` | explicit unresolved Scholar-native task-specific discovery gap |

Source-hash bindings added in this cut:
- CoAgent URL SHA-256 `ce17cfc8ca2a7aca0ddd6bfc84bf38475f0784f0d67ec3784af06902db285242`;
- seqlock URL SHA-256 `c7a313d0f77c005fe9eadcccd89d7b3382ec82d7adca3365dea49f4d88543e94`;
- commit-time authorization URL SHA-256 `f854fc3d76bbbf8df9bd250207cd8243eabc0cf55edaed5f3d1b3313ab1f7de7`.

New internal reopen relation:

`K27:AWJ032:G4:PREFETCH_PLAN_REVALIDATION -> W3:OWNER_CURRENTNESS_REQUIRED`

This relation does not mint a new semantic coordinate, evidence rank, currentness witness, resolver authentication, epoch-serializability proof, owner identity, runtime truth, execution authority, or transformer KV state.

`K27Coordinate != OwnerCurrentness != ResolverAuthentication != EpochSerializability != RuntimeTruth != Authority`.

`CoordinateMemory != MODEL_PREFIX_KV`.
