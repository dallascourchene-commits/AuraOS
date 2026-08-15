# W8 — provisional Batch-2 reproduction allocation

Work order: `WO-FLEET-PHASE3-DEPLOY-001`
Worker: W8
Target: `tailcallhq/rust-grpc#44` — Update all outdated dependencies
Upstream issue state at source check: OPEN
Allocation class: `PROVISIONAL_SOURCE_BOUND_FALLBACK_WEAK_FIT`

This mirrors the concurrent W8 receipt already emitted in Aura Drive. The receipt bound the target to repository `main` commit `e5faeec6e9d833ecf5d46da718d3d0b5e2b9e542`, recorded an offline dependency inventory, and stopped before networked Cargo mutation because the exact requested Batch-2 authority manifest remained unresolved.

No bounty claim, upstream comment, fork, branch, commit, patch, PR, wallet action, or payout is created here.

Required before further work:
1. materialize and verify `docs/staging/ready_review/LIVE_BOUNTY_TARGETS_BATCH2.md`;
2. confirm it assigns or permits this W8 target;
3. re-check issue currentness, competing claims/PRs, and acceptance contract;
4. reproduce against the bound upstream source in a network-capable full checkout.
