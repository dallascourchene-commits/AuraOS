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
4. Require an independent verifier for consequential receipts.
5. Treat cross-model disagreement as additional verification depth, never voting authority.
6. Keep Continuity Sensitivity, Relationship Experience, and QDKT records proposal-only until current reproof and required human or community disposition exist.
7. Run Coding Waboose against the exact current head after every repair.
8. Regenerate CODEMAP only after source and tests stabilize.
9. Do not commit, publish, promote, or merge from verification evidence alone.
10. Keep disposable logs, handoffs, and receipts outside tracked repository status, such as through a run-local `.git/info/exclude` entry; never weaken the Architecture Harness clean-tree check.

A focused failure blocks materialization. The failure must be diagnosed against the exact repository environment; the gate must not be weakened to make a local stub pass.
