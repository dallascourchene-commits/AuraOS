# Safe Substrate Integration — P9

1. Identify the current owner, callers, stores, schemas, outputs, and authority boundary.
2. Snapshot only records the owner already produced.
3. Canonicalize and digest the snapshot without rerunning domain logic.
4. Map declared work one-to-one into proposal-only Planning Board actions.
5. Preserve order, dependencies, identifiers, evidence references, and source digests.
6. Require external authority; never infer it from scores, labels, recommendations, or generated plans.
7. Fail closed on unavailable, stale, reordered, duplicated, substituted, conflicting, or concurrently changed evidence.
8. Bind reports to the full board, mappings, and continuity evidence.
9. Add deterministic, adversarial, stress, and live-owner integration tests.
10. Record ownership disposition before any separate migration proposal.

A domain adapter may translate record shape, but not domain meaning or authority. Generated topology is navigation evidence, not ownership truth.

Validation requires the P9 verifier, Python 3.10/3.12 focused checks, full pytest-native, standalone legacy validators, inherited bounded workflows, and generated topology synchronization.