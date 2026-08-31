# Aura K27 ASTGE recovery reconstitution

D0 / NONPROMOTING / HS1.

This crate inventories immutable-generation crash residue on top of PR471. It does not define or parse the storage ABI and it does not claim physical power-loss durability.

## Positive serving rule

A generation is serving **only** when PR471's existing `ImmutableMmapReader::open_current` accepts the exact `CURRENT -> manifest digest -> file length/digest -> generation binding` chain.

Everything else is recovery inventory:

- strict final `gen-<20 digits>` directories not selected by a valid CURRENT are orphans;
- `.gen-<20 digits>.tmp-*` directories are temp-generation residue;
- `.CURRENT.tmp-*` entries are temp-pointer residue;
- a missing CURRENT is HOLD;
- an invalid CURRENT is HOLD;
- corrupt bytes under the CURRENT target are HOLD;
- a newer complete orphan never overrides a valid older CURRENT;
- one or many complete generations without CURRENT are never auto-promoted.

## Why V1 does not choose the highest generation

A final directory proves that generation publication reached a namespace stage; it does not prove that the CURRENT commit point was durably selected. Selecting the largest generation number would turn crash residue into a new externally visible decision. V1 therefore refuses that inference.

## Laws

`CompleteLookingGeneration != CommittedCurrent`.

`HighestGeneration != RecoveryAuthority`.

`ValidCurrentChain => ServingCandidate`.

`MissingOrInvalidCurrent => HOLD`.

`CrashResidueInventory != CommitReplay`.

`HostedCrashStateFixture != PhysicalPowerLossDurability`.

`LogicalPublicationModelPass != CrossFilesystemDurabilityProof`.

## External pressure

Crash-consistency work such as B3/CrashMonkey and FlyTrap shows that small operation sequences around fsync/rename can expose serious recovery bugs, including broken rename atomicity. Snapshot/FAMS work separately illustrates that explicit failure-atomic persistence protocols are stronger than ordinary persistence calls. Practitioner discussions also reinforce that directory durability is a separate concern from writing file contents.

## Claim ceiling

No orphan promotion, rollback mutation, cleanup/deletion, physical crash durability, cross-filesystem equivalence, hostile-process-safe mmap, semantic source authority, merge/deploy/provider/public effect, or Gate-10 action.
