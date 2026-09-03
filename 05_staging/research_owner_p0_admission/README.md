# Research Lead -> Owner-Authorized P0 Admission

This D0 staging candidate composes two post-O5 foreign semantic terminals:

1. World-L0 -> Research Discovery Admission Conformance (Drive `1MTca63-9SES3r6dJxS2AvrxGfxtNr0s_PqSlSOFpI3E`), which proves research retrieval/source access/currentness/K27 cannot authorize a proof target.
2. Research-to-Owner Evidence Pipeline O1-O5 (Drive `14Cw0oA7ac-vM-DxMMp1ju0Ull62ItDKp8ka8bL2im_M`), which ends in an exact owner experiment packet and strict P0 -> P1 -> P2 evidence ladder.

The membrane compiles only a bounded P0 command when both source-side research evidence and target-side owner authorization/currentness are independently valid. It preserves:

- source identity/currentness/evidence lease independent from proof-target identity/currentness/authorization;
- K27 as navigation only, never authorization;
- exact repository-qualified owner reference + exact target head;
- transfer basis + falsifier;
- D0/P0-only negative intent;
- `MATERIALIZED != ACKED != RESULT`;
- command-bound result lease + semantic root before P0 result admission.

The live AWJ032 command `AWJ032-GLM53-RESEARCH-TO-PHYSICAL-BENCHMARK-P0-20260902-R1` is currently a materialized command envelope with no command-bound ACK/RESULT observed in the bounded Drive search. This candidate therefore models that state as `MATERIALIZED_WAIT_ACK`, not execution.

Run:

```bash
cd 05_staging/research_owner_p0_admission
python -m unittest -v test_research_owner_p0.py
```

Local evidence: 20/20 tests pass in each of three fresh stdlib-only Python venvs. The test suite includes 1,000 randomized authority-laundering attempts.

Authority ceiling: D0 draft only. No owner-host execution, model generation, P1/P2 profiling, workflow rerun, merge/deploy, public effect, Gate10, or native transformer KV access is authorized or claimed.