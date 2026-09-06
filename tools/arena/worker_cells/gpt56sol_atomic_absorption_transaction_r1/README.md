# Arena Atomic Absorption Transaction R1

D0-only worker cell for ManyResearchers/OnePublisher convergence.

Keeper law:

`Publish => ExactOwnerHeadCAS AND AtomicManifest AND NoConflictingPathWrites AND NoStagingDebris AND ConsequenceQuotientBeforeWrite AND AuthorityNonWidening`

Corollaries:
- stale proposal => REBASE_REQUIRED, zero writes;
- owner head moves after plan => commit false, zero writes;
- path conflict with different blob digest => CONFLICT_HOLD;
- exact consequence redelivery collapses before publication;
- staging/temp marker paths => DEBRIS_HOLD;
- D0 proposal asking effect authority => AUTHORITY_HOLD;
- identical path+blob writes may coalesce safely;
- publication receipt binds expected head, manifest root, and exact write set.

This is a deterministic publication planner/simulator. It does not merge PRs, deploy, grant effect authority, or replace GitHub/owner authorization.

Proof: three fresh stdlib-only venvs; 15 tests/environment = 45/45; 100,000 randomized transaction cases/environment = 300,000 total; HS1000 0 false commits; Omega8 exactly one keeper; 13D zero repairs. Stable campaign root `b845ddf3831b341d657234f3e1714de91007dc680c0e7448c71aa7371c634633`.
