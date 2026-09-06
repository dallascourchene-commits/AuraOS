# K27 Memory City runtime binding (Lane 2 addendum)

This package is the executable store/locality layer beneath PR #859's declaration-only Spatial seam.

- The 1,115-row `research_registry.sqlite` is **not vendored**. It is mounted from `AURA_K27_MEMORY_REGISTRY_PATH` and must match SHA-256 `246dbded0a33eaede035b829bfcae9f8ee50d769f5c28f1a955a16073131d86f` and semantic root `7e0095415ffb6450aeb39f1faba782f27a1fb628e481fe7d1975aa5a649cf1c1`.
- `K27Path` is locality only. `FrameAddress` carries object identity. `MemoryStore.publish` requires exact expected revision and lifecycle epoch.
- The PR #859 `SPATIAL.GROUND.COMPILE_SCENE` seam remains projection/review-only. This addendum validates its schema and authority ceiling; it does not replace the seam owner.
- External source currentness is not minted by local registry consistency.
- This package has no Gate 10, truth, execution, effect, renderer, merge, or canonical-promotion authority.
