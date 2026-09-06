# Frontier-27 R11.5 owner-authoritative mutation epoch donor

D0 non-owner donor. This cell composes the PR862 R11.4 ABA mutation-epoch falsifier with the repaired PR865 lifecycle-epoch routing oracle and the J231 at-use captured-source rule.

## Objective

Move lifecycle-currentness fencing from a caller-owned wrapper to an owner process that exclusively holds the mutable `FrontierOffload` object. Parent callers receive only immutable snapshots and receipts. Every admitted persistent mutation crosses the owner process command boundary and advances a monotone `mutation_epoch`, including writes that restore byte-identical state.

The transaction sequence is:

`captured verified owner bytes -> owner-process snapshot(generation, epoch, full-state) -> pinned transition over captured bytes -> owner-process CAS(generation, epoch, full-state) -> atomic post-state commit`

The raw Frontier owner is not returned to the parent. A parent-side retained object therefore cannot perform the R11.4 raw `S0 -> S1 -> S0` bypass against owner memory. This is a runtime-boundary donor, not canonical AGENT_01 adoption.

## Keeper laws

- `ByteStateEqualAfterABA != SameLifecycleState`.
- `MutationEpochAuthorityMustOwnMutationSurface`.
- `CallerOwnedEpochWrapper != OwnerAuthoritativeEpoch`.
- `CapturedVerifiedSource != MutablePathReopen`.
- `GenerationCAS + MutationEpochCAS + FullStateCAS > GenerationCAS + FullStateCAS` for ABA currentness.
- `OwnerProcessIsolation != PR858 ContainmentProof`.
- `PersistentMutationEpoch != ExternalEffectTransaction`.
- `K27Coordinate != Truth != Currentness != Authority`.

## Proof boundary

Local source-equivalent fixture proof is separate from hosted exact-PR825 proof. The hosted test pins `tools/arena/frontier27_runtime.py` to SHA-256 `d255abf8b6b59fd6fc86944a715b77104c334ce5112b1c52c6f0c3783607d5ee`, the current AGENT_01/PR825 source root identified by the R11.3/R11.4 donor chain.

No merge/deploy, provider/model execution, physical-performance claim, Gate10, external effect authority, native/private Transformer KV access, or canonical owner adoption is claimed.
