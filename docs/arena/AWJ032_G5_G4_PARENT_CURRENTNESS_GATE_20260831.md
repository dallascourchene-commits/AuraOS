# AWJ032 GLM53 G5 W3 — G4 parent-proof currentness gate

Status: D0 / HS1 / NONPROMOTING / STACKED ADDENDUM TO PR #766.

## Objective

Prevent G5 recompute-admission receipts from receiving terminal/current credit while they still bind the superseded G4 v1 proof generation.

Residual:

`HistoricalGreenGeneration + SemanticSubsetCompatibility != CurrentParentProof`.

## Exact parent/proof chronology

Historical G4 v1:
- semantic/proof head `68d76cb7d08366d085be13ad68871ab3c9cf00e1`;
- run/job `33436142388 / 99632931053`, SUCCESS;
- historical consequence included caller-constructible all-equal state as positive reuse.

Canonical G4 v2 repair:
- semantic repair `981971f5b34da2046f539ee92f3e272eccac8360`;
- exact proof head `025d619d24d95dd6acc29981b1bd61bce92e25a3`;
- dedicated `Aura GLM53 G4 Prefetch Plan Revalidation` run/job `33436948448 / 99635568410`, SUCCESS;
- 256-state proof: one `STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED`, 255 `HOLD_RECOMPUTE_G3`, zero reuse authorizations.

Current G5 owner at repair cut:
- PR #766 head `8b1f38a6c917a9e7f1af941273164ca0db69821b`;
- still embeds G4 v1 head/run/job as its `G4_PROOF_*` constants and as the positive receipt provenance.

## Important compatibility result

The G4 v2 repair preserves the changed-axis `HOLD_RECOMPUTE_G3` consequence used by G5. Therefore this addendum does not reject G5's 90-state recompute algebra.

It rejects only stale parent terminality/provenance.

`CurrentG4ChangedAxisHold == HistoricalG4ChangedAxisHold` may establish consequence compatibility.

It does not imply:

`HistoricalG4Proof == CurrentG4Proof`.

## Material guard

`audit_g5_g4_parent_currentness()` inspects the G4 proof coordinates carried by an existing G5 receipt without reissuing its admission consequence.

Typed states:
- `HOLD_STALE_G4_PARENT_PROOF` for the exact historical v1 green;
- `HOLD_UNKNOWN_G4_PARENT_PROOF` for an unrecognized proof generation;
- `CURRENT_G4_PROOF_COORDINATES_PRESENT` only when the exact v2 proof coordinates are carried.

Even the third state remains non-promoting here: this addendum does not authenticate G5's own semantic rebase or grant terminal credit. Canonical PR #766 must update its owned provenance contract and obtain its own exact hosted proof after that change.

## HyperDrive laws

`GreenProofOfSupersededParent != CurrentParentClosure`.

`CurrentParentSemanticRepair => DescendantProofBindingMustRecompute`.

`ReexecutingCurrentParentTestsInsideDescendant != ParentOwnerTerminalProof`.

`HistoricalProofRemainsHistory; ItDoesNotFollowSemanticHeadAutomatically`.

`ConsequenceSubsetCompatibility != ProofGenerationIdentity`.

`ProofCurrentnessFollowsSemanticGeneration`.

## HyperScale

HS1. The missing evidence is a single temporal/provenance edge, not more recompute-state fanout. G5 already exhausts its deterministic control lattice; the cheapest stronger evidence is exact current-parent proof binding.

`ExhaustedChildStateSpace + StaleParentProof => RebindParentProof, not MoreWorkers`.

## K27 / coordinate memory

Reuse the existing AWJ032 G4/G5 K27 coordinates. Add only the internal reopen edge:

`K27:AWJ032:G5:RECOMPUTE_PROGRESS_VERSION_ADMISSION -> W3:G4_PARENT_PROOF_CURRENTNESS_REQUIRED`.

K27 remains routing/reopen metadata only.

`K27Coordinate != ProofCurrentness != SemanticAuthority`.

`CoordinateMemory != MODEL_PREFIX_KV`.

## External Different-J pressure

- `Who Should Own the Expert Cache?` (arXiv:2608.12103) reports that under an equal-memory wall kernel LRU was near oracle-level while measured router lookahead translated poorly into realized prefetch benefit. This reinforces separating predictor evidence, cache ownership/policy generation, and physical runtime consequence.
- Current GLM-5.3 community measurements remain engine/cache/offload dependent and therefore cannot replace exact project proof generations.
- Direct task-specific Google-Scholar-native discovery remains `SCHOLAR_DIRECT_GAP`.

External evidence grants no Aura authority.

## Triadic Process

Thesis: G5's recompute algebra consumes G4's changed-axis HOLD.

Antithesis: the G4 generation G5 authenticates was semantically superseded even though the relevant HOLD subset survived.

Synthesis: preserve compatible algebra, but require descendant proof provenance to bind the current parent semantic/proof generation.

## Creation Process

Freeze G5 -> resolve current G4 owner -> compare semantic generations -> prove changed-axis subset continuity -> identify stale proof constants -> quarantine terminality only -> authenticate current G4 hosted proof -> preserve G5 algebra -> return repair to canonical G5 owner -> reprove G5 exact generation.

## Ω8

W0 exact G4 v1/v2 and G5 cut.
W1 parent semantic generation -> parent proof -> descendant provenance -> child proof.
W2 stale head/run/job, proof-only mirrors, reexecuted tests and K27 coordinates cannot substitute for current parent proof.
W3 stale-parent laundering contradiction.
W4 semantic compatibility, proof identity, currentness, admission algebra, runtime, I/O, routing and effect remain independent.
W5 G5 algebra × current G4 proof relation.
W6 duplicate/proof-only generations receive zero semantic mass.
W7 parent semantic repair invalidates descendant proof binding until recomputed.
W8 effects remain unearned.

## Claim ceiling

No G5 terminal credit, recompute execution, model/provider execution, retrieval/provider effect, transfer effect, physical I/O, source-currentness minting, semantic K27 authority, native/private transformer KV, G2/Gate-10, merge/deploy/spend or public/financial/human effect is granted.
