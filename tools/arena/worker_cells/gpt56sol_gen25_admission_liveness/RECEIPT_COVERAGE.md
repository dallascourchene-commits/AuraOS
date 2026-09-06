# GEN25 Typed-Receipt Coverage Witness v1

Purpose: keep **ordering/idempotency** separate from **replay completeness**.

The live GEN25 v5 typed ledger already owns event class, command/attempt identity, sequence identity, duplicate-collapse, equivocation HOLDs, terminal/rejection ordering, and ledger roots. This sibling does not rewrite those semantics.

It adds one explicit, owner-supplied `CoverageContract` containing the expected sequence-ID set for a single command attempt plus a source/evidence witness root. The set may be zero-based, sparse, or otherwise non-contiguous. Coverage is COMPLETE only when the exact typed-ledger projection covers exactly that expected set and the ledger has no integrity HOLD.

Keeper laws:

- `SequenceIdentity != SequenceCompleteness`.
- `OrderedTypedLedger != CompleteReplay`.
- `ReplayComplete => ExactCoverageContract AND ObservedSequenceSet == ExpectedSequenceSet AND LedgerIntegrityValid`.
- `MissingExpectedSequence | UnexpectedSequence | LedgerIntegrityHold => CoverageComplete=False`.
- `CoverageContract does not define sequence origin or contiguity; the owner does.`
- `CoverageComplete != ProviderTruth != EffectAuthority != Gate10`.
- K27 coverage coordinates are logical routing metadata only, never native/private transformer KV.

This design follows Aura's existing event-ledger precedent: causal/replay integrity must be explicit rather than inferred from a green projected state. External event-sourcing/replay research and expected-version practice are design pressure only, not parent authority.
