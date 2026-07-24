# Unified Memory and Continuity Verification

Run the focused contract tests inside AuraOS's repository environment:

```bash
python -m pip install -r requirements.txt
python -m pytest -q tests/test_aura_unified_memory_continuity.py
python aura_coding_waboose_cli.py run \
  --request .aura/waboose_requests/unified_memory_continuity.v1.json
```

The verification sequence must preserve these gates:

1. Decode or read the exact committed source and test tree.
2. Bind the repository head, working-tree digest, CODEMAP digest, source digest, and model profile identity.
3. Freeze P0 before any P1 observation is accepted.
4. Require an independent P1 observer, bind the receipt verifier to that observer, and reject self-observation or verifier spoofing.
5. Treat cross-model disagreement as additional verification depth, never voting authority.
6. Keep Continuity Sensitivity, Relationship Experience, and QDKT records proposal-only until typed current evidence, current reproof, canonical Relationship Experience, complete raw evidence, and required human or community disposition exist.
7. Run Coding Waboose against the exact current head after every repair.
8. Regenerate CODEMAP only after source and tests stabilize, commit the meaningful generated-map delta, and bind the final exact-head verification to that synchronized tree.
9. Do not commit, publish, promote, or merge from verification evidence alone.
10. Keep disposable logs outside tracked repository status, never weaken the Architecture Harness clean-tree check, and write Architecture Harness handoff/run outputs physically outside the repository before copying completed receipts into an ignored CI artifact directory.
11. During an exact-head verification pass, use the navigator's query mode against the committed CODEMAP; do not invoke map-generation mode and then treat the resulting dirty tree as verification evidence.
12. When a selected existing owner regression has a test-only import not declared by runtime requirements, add that dependency only to the verification environment; do not alter production dependencies or drop the regression to make the gate pass.
13. Run the full Ruff rule set on the integration module and focused tests, not only fatal syntax/import rules; unused imports, shadowed loop variables, stale annotations, and import ordering are review findings.
14. Prove nested P0/P1 mappings are recursively immutable and recompute the committed P0 digest before observation.
15. Reject canonical Act Capsule role, file, symbol, evidence, or tool expansion before model dispatch.
16. Reject duplicate evidence references and prove every required active evidence item survives model-packet compilation.
17. Require a complete canonical `ModelEndpointIdentity`; reject arbitrary mappings and forged profile identifiers.
18. Bind prompt/runtime identity into P0 and reject continuity receipts that substitute a different runtime digest.
19. Preserve the Crucible proposal, current reproof, human/community disposition, continuity receipt, and independent verifier through Relationship Experience and QDKT admission.
20. Reject non-string canonical JSON object keys before serialization so coercion cannot collapse distinct keys.

A focused failure blocks materialization. The failure must be diagnosed against the exact repository environment; the gate must not be weakened to make a local stub pass.
