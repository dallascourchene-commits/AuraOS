# Project006 O15 HyperDrive Projection

State: D0 NONPROMOTING / local exact-byte proof complete / hosted exact-head proof pending.

Transition: semantic WORK and host-private execution proof are now exercised through a durable effect transaction fault harness rather than only through static authorization models.

Keepers:
- WORK != ProviderPermit.
- ProviderAttemptDurable != ProviderAccepted.
- ProviderAccepted != ResultObserved != ReturnWritten.
- AmbiguousCompletion => ReconcileBeforeReplay.
- ProviderAcceptedSameGovernedOperation => ConsumeOrReconcileWithoutProviderReplay.
- ResultObserved => ReturnWriterOnly despite later pre-effect/workcell drift.

Proof: 3 fresh venvs; 60/60 focused executions; 90,000 decision-oracle cases; 180 stateful fault-matrix executions; duplicate provider effects 0; accepted effects left unresolved 0; Omega8 one keeper; exact factored 13D 1,594,323 states with 0 hard-invalid contextual repairs; HS1000 1,000 cells -> 60 consequence groups, cardinality novelty credit 0.

Receipt root: `19d21e3622a8ebac84f8c7faa2d00c0032de2825717e9d3aa4dd4198de4541b6`.

Reopen on: real provider/sink fault trace; parent execution-basis semantic movement; evidence that sink acceptance is not operation-bound; evidence of duplicate externalized effect under concurrent recovery; terminal-return equivocation; or production owner/key semantics becoming available.
