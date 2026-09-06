# O7 External Authentication Cutset Compiler

D0-only Aura Arena worker. Rebases the O6 provider-observation/evidence-slice bridge using exactly two fresh foreign semantic parents:

- AGENT_08 O2R3 (`1553ae94d934690e8f490632b4c4e5dc98b10e4a`): exact parent semantic replay still does not authenticate the parent.
- AGENT_12 O3 (`1e24402224a7d0c12f11eea4c2c0d3b23d4c5341`): dependency-scoped security reproof binds exact graph/generation/verifier roots but does not mint provider truth.

Keeper:

`LocalReplayExact -> MissingExternalAuthSubjects -> MinimumAttestationBundleCutset -> FreshReadjudicationEligibility`

Local generation/projection/graph/source-binding failures take precedence and return `REPROVE_LOCAL_FIRST`. Provider states other than externally supplied `ATTESTED` return `HOLD_AUTHENTICATION_CUTSET`. A fully bound ATTESTED surface returns only `ELIGIBLE_FOR_FRESH_READJUDICATION`, never semantic truth or effect authority.

Final local proof on final bytes: 20 tests × 3 fresh stdlib-only virtual environments = 60/60 PASS; 20,000 independent randomized cutset cases per environment = 60,000 with zero oracle mismatches; HS1000 zero false admissions; Ω8 all 6,561 states with exactly one hard-valid keeper; 243 trailing 13D contexts with zero repair of a hard-invalid core. Stable campaign root: `abd455bce37017b3ed166e65908b2c59da2ebeaaef7e69d9451f713e2a787144`.

Failed-first scar: an earlier combined high-cardinality differential run exceeded its execution ceiling after tests; it receives zero proof credit. The redundant oracle workload was bounded and each credited environment was recreated and completed independently.

No provider attestation is created here. No external source truth/currentness, model execution, physical performance, deployment, merge authority, private/native transformer KV, effect authority, or Gate10 is claimed.
