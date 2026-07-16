# P9 Release Checks

The release gate requires deterministic manifest regeneration, exact pinned-file identities, module-scope symbols, literal version constants, ordered phase dependencies, and unchanged ownership and authority boundaries.

The public index must contain only normalized allowlisted source and documentation files. Every listed file is bound to its exact repository bytes by a Git blob SHA-1, while the index itself is bound by SHA-256. Multipart manifest parts remain bound by SHA-256 values and byte lengths. Tests, workflows, caches, stores, logs, databases, environment files, runtime directories, CODEMAP, and topology are excluded.

Validation requires Python 3.10 and 3.12 focused checks, full pytest-native, every standalone legacy validator, inherited bounded workflows, direct regressions for manual-review findings, and generated-only final topology synchronization.

P9 stops at a verified index. Package publication, deployment activation, deprecation, caller migration, and store transfer require separate review.
