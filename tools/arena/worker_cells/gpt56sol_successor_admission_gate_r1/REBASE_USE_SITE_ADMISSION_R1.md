# Rebase Use-Site Admission Adapter R1

Keeper law:
`NextObjectiveSeed => ConveyorKeepPair AND ReceiptParentBindingsExact AND ImmediateTerminalReceiptsPresent AND SuccessorParentAdmissionR2=FOREIGN_PARENT_PAIR_ACCEPTED AND D0Authority`

This is a non-owning adapter. It preserves the conveyor's distinct-lineage/distinct-consequence prefilter but that predicate alone can never mint a next objective. Each conveyor semantic receipt is explicitly bound to a separate source-bound immediate-terminal receipt, and PR #851 R2 remains the authoritative succession-admission classifier.

`ConveyorReceiptDigest != ImmediateTerminalReceiptRoot`; the adapter binds them rather than conflating them.

D0 only. No merge/deploy/effect/Gate10 authority.
