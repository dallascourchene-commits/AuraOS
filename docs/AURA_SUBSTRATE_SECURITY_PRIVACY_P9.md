# Substrate Security and Privacy — P9

## Boundaries

- Exact source spans and hashes remain patch authority.
- Manifest, index, topology, planning, continuity, compression, and compatibility records grant no execution or governance authority.
- Tool schemas and live provider behavior are unchanged.
- Event contracts reject private-reasoning fields and redact credential-shaped material before hashing or persistence.
- Release files exclude mutable stores, event logs, databases, caches, secrets, environment files, generated user records, and runtime directories.
- Cultural, civic, legal, financial, medical, and community authority cannot be inferred by an adapter.

## Integrity

The P9 verifier checks normalized paths, exact Git blob identities where pinned, AST symbols, literal version constants, phase ordering, dependencies, ownership dispositions, authority flags, manifest bytes, and release-index file hashes.

## Fail-closed behavior

Missing files or symbols, stale digests, conflicting phase records, untracked release files, unsafe paths, duplicated entries, authority expansion, false migration claims, or forbidden bundle content produce blocking findings.

## Publication boundary

P9 produces a deterministic index only. It does not upload a package, publish a release, alter a deployment, redirect a caller, transfer a store, enforce deprecation, or delete a legacy surface.
