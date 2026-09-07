# O21 Frozen Proposals — before implementation

Objective: bind attenuated delegated authority to the exact installed runtime that will execute it.

P1 Cached-proof join: accept previously issued O18 + O20 receipts if both say PASS. Rejected: TOCTOU and cross-host transplant remain possible.
P2 At-use dual recomputation + cross-binding: recompute O18 delegation and O20 runtime attestation at use, then bind operation/source/release/host/measurement into one D0 permit. SELECTED.
P3 Fold host attestation fields into delegation hops. Rejected: collapses identity/currentness into authority and makes delegation tokens host-state truth.
P4 Host-first permit, delegation chain as audit metadata. Rejected: loses hop-by-hop attenuation as an admission condition.
P5 Central policy-server authorization. Rejected for D0: adds a new authority owner rather than composing existing proofs.

Selected discriminator:
ValidAttenuatedDelegation != CurrentInstalledRuntime != RuntimeBoundExecutionPermit.
Both parent proofs must be recomputed and cross-bound at use; neither may mint the other.
