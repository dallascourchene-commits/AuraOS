# Successor Parent Admission R2 — Immediate Terminal Identity

Additive D0 layer in the existing Successor Admission Gate worker cell.

Keeper law:

`QualifiedSuccessorParents => ExactlyTwoImmediatePostCutSemanticTerminals AND ImmediateIdentityReceiptBound AND BothImmediateActorsForeignToCurrentActor AND DistinctImmediateActors AND DistinctImmediateLineages AND DistinctConsequences AND DistinctReceipts AND DistinctDerivations`

Critical non-substitution law:

`ForeignAncestorPresent != ForeignImmediateParent`

Ancestry actor IDs are provenance-only fields inside `ImmediateTerminalReceipt`; they cannot satisfy the foreign-actor gate. The receipt binds artifact ID, immediate actor, immediate lineage, creation time, terminal/projection class, consequence root, derivation root, source owner/revision, ancestry list, and D0 authority into one deterministic root. The parent artifact's `receipt_root` must equal that exact root.

Explicit dispositions include `FOREIGN_PARENT_PAIR_ACCEPTED`, `SAME_LINEAGE_PAIR_HOLD`, `FOREIGN_ANCESTRY_ONLY_HOLD`, `CONSEQUENCE_DUPLICATE_HOLD`, `PARENT_IDENTITY_UNRESOLVED_HOLD`, and `TERMINAL_RECEIPT_INTEGRITY_HOLD`.

D0 only. A self-consistent receipt does not authenticate a real-world actor by itself; the source-owner/revision binding is an admission obligation, and provider/source authentication remains external to this local deterministic gate.
