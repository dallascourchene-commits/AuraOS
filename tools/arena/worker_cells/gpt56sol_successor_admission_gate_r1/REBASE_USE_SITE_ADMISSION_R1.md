# Rebase Use-Site Admission Adapter R1.1

Keeper law:
`NextObjectiveSeed => ConveyorKeepPair AND ReceiptParentBindingsExact AND ImmediateTerminalReceiptsPresent AND CanonicalSuccessorParentAdmissionR2ReplayAtUse=FOREIGN_PARENT_PAIR_ACCEPTED AND ExactCanonicalPairRoot AND D0Authority`

Negative laws:
- `InjectedGateResult != SuccessorMintAuthority`.
- `PossessionOfAcceptedLookingResult != CanonicalGateReplay`.
- `ConveyorReceiptDigest != ImmediateTerminalReceiptRoot`.
- `ForeignAncestryPresent != ForeignImmediateParent`.

R1.1 closes the consequential-boundary seam in the earlier adapter. The historical R1 accepted an `admit_pair` callable from its caller and trusted the returned disposition, pair root, and authority ceiling. A caller could therefore supply a function that returned `FOREIGN_PARENT_PAIR_ACCEPTED`, a plausible 64-hex pair root, and `D0` without executing the authoritative R2 parent classifier.

The use-site API now accepts only `receipts`, `bindings`, and `ctx`. It imports and executes `admit_successor_pair()` from the canonical PR #851 R2 owner internally on the exact bound parent evidence. The resulting canonical pair root is then bound into the objective seed.

Current semantic Git blobs after R1.1:
- `rebase_use_site_admission.py`: `e07fdadebc765d83861d0f4530193af081d51037`
- `tests/test_rebase_use_site_admission.py`: `95e2636be31db2cb57be071bb12e22a5fb21f9a3`
- `campaign_rebase_use_site_admission.py`: `d8ebaa001479c99389ec03b32557785926329249`
- canonical R2 owner remains `successor_parent_admission_r2.py`: `77cfb3fb4c9bbd6876bb81227b8bef4303263c04`

Independent scope-faithful fresh-venv proof (separate from GitHub integration identity):
- 14 focused tests/environment x 3 = **42/42 PASS**;
- 100,000 randomized use-site decisions/environment = **300,000**, 0 false mints;
- HS1000 self-parent / foreign-ancestry attacks = **3,000**, 0 false mints;
- historical injected-ACCEPT seam reproduced **150,000** invalid objective mints across the same campaigns;
- Omega8: exactly 1/6,561 keeper;
- 13D: 243 context tails/environment, 0 repairs of a hard-invalid ancestry axis;
- stable campaign root `ca41d508f1997f7f4b68bccfe2af8885ce28bcb050b7cf1cbf8e98df0567b55b`;
- independent receipt root `adbbc698a16bc22c4c29d74111311f1ab537d1131f2edb250eb0dc3e32cdefad`.

Claim boundary: the independent venv model is scope-faithful falsification evidence, not fabricated byte-exact hosted CI proof. GitHub semantic identity is reported by the blobs above.

J59 / HyperScale: `HistoricalProof != CurrentProof`; `ArtifactSemanticProvenance != ExactCurrentProof`; replay the exact current owner contract at the consequential use-site and reopen only the minimum affected cone.

K27 remains deterministic locality only. Matching pair/locality coordinates never establish source truth, currentness, provider authentication, successor authority, native/private Transformer KV, or effect authority.

D0 only. No numbered successor is claimed here; no merge/deploy/effect/Gate10/OnePublisher authority.
