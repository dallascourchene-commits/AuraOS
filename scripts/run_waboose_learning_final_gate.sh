#!/usr/bin/env bash
set -euo pipefail

python scripts/repair_waboose_learning_patch_markers.py
python scripts/apply_emergent_spine_agent_bridge.py
python scripts/apply_emergent_spine_agent_bridge_waboose_repairs.py
python scripts/apply_waboose_coderabbit_learning.py
python scripts/apply_waboose_learning_followups.py
python scripts/apply_waboose_mcp_strict_booleans.py

TOUCHED=(
  aura_emergent_evidence_spine.py
  aura_review_arena.py
  aura_coding_waboose.py
  aura_waboose_semantic_rules.py
  aura_waboose_learning.py
  aura_coderabbit_learning_cli.py
  aura_agent_arena_persistence_bridge.py
  aura_agent_arena_mcp.py
  aura_affordance_directory.py
  tests/test_aura_emergent_evidence_spine.py
  tests/test_aura_emergent_evidence_spine_coderabbit.py
  tests/test_aura_waboose_semantic_rules.py
  tests/test_aura_waboose_semantic_completeness.py
  tests/test_aura_waboose_learning.py
  tests/test_aura_coderabbit_learning_cli.py
  tests/test_aura_waboose_learning_mcp.py
  tests/test_aura_emergent_agent_bridge.py
  tests/test_aura_emergent_agent_bridge_mcp.py
)

ruff check --fix "${TOUCHED[@]}"

python -m py_compile \
  aura_emergent_evidence_spine.py \
  aura_review_arena.py \
  aura_coding_waboose.py \
  aura_waboose_semantic_rules.py \
  aura_waboose_learning.py \
  aura_coderabbit_learning_cli.py \
  aura_agent_arena_persistence_bridge.py \
  aura_agent_arena_mcp.py \
  aura_affordance_directory.py

python -m pytest -q \
  tests/test_aura_emergent_evidence_spine.py \
  tests/test_aura_emergent_evidence_spine_coderabbit.py \
  tests/test_aura_waboose_semantic_rules.py \
  tests/test_aura_waboose_semantic_completeness.py \
  tests/test_aura_waboose_learning.py \
  tests/test_aura_coderabbit_learning_cli.py \
  tests/test_aura_waboose_learning_mcp.py \
  tests/test_aura_emergent_agent_bridge.py \
  tests/test_aura_emergent_agent_bridge_mcp.py

python -m pytest -q tests/test_aura_review_arena.py
python -m pytest -q tests/test_aura_coding_waboose.py
python -m pytest -q tests/test_aura_coding_waboose_breadboard.py
python -m pytest -q tests/test_aura_waboose_callsite_resolution.py
python -m pytest -q tests/test_aura_review_arena_mcp.py
python -m pytest -q tests/test_aura_agent_arena_mcp.py
python -m pytest -q tests/test_aura_agent_arena_bridge.py
python -m pytest -q tests/test_aura_forge.py
python -m pytest -q tests/test_aura_external_llm_session.py
python -m pytest -q test_aura_dream_retrieval.py
python -m pytest -q tests/test_aura_qdkt_inventory.py

ruff check "${TOUCHED[@]}"
bandit -q -ll \
  aura_emergent_evidence_spine.py \
  aura_review_arena.py \
  aura_coding_waboose.py \
  aura_waboose_semantic_rules.py \
  aura_waboose_learning.py \
  aura_coderabbit_learning_cli.py \
  aura_agent_arena_persistence_bridge.py \
  aura_agent_arena_mcp.py

rm -f scripts/apply_emergent_spine_agent_bridge.py
rm -f scripts/apply_emergent_spine_agent_bridge_waboose_repairs.py
rm -f scripts/apply_waboose_coderabbit_learning.py
rm -f scripts/apply_waboose_learning_followups.py
rm -f scripts/apply_waboose_mcp_strict_booleans.py
rm -f scripts/repair_waboose_learning_patch_markers.py
rm -f scripts/run_waboose_learning_final_gate.sh
rm -f .github/workflows/emergent-spine-waboose-learning-final-v3.yml

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add -A
git commit -m "Teach Coding Waboose from grounded CodeRabbit reviews"

python - <<'PY'
import json
request = {
    "objective": "Verify CodeRabbit parity and Connectome DREAM-lite QDKT learning without authority escalation.",
    "mode": "range",
    "base_ref": "origin/main",
    "head_ref": "HEAD",
    "profile": "precision",
    "graph_depth": 2,
    "graph_node_budget": 240,
    "run_tests": True,
    "run_optional_tools": True,
    "focus_directives": [
        {
            "name": "strict_boolean_options",
            "question": "Are boolean options parsed with strict types rather than truthiness?",
            "risk": "correctness",
            "target_patterns": ["boolean option", "strict type"],
            "required_evidence": ["semantic_rule", "regression_test"],
        },
        {
            "name": "qualified_symbol_identity",
            "question": "Are qualified symbols and same-named methods kept distinct at every target binding boundary?",
            "risk": "dependency_impact",
            "target_patterns": ["qualified symbol", "symbol identity"],
            "required_evidence": ["semantic_rule", "regression_test"],
        },
        {
            "name": "source_inventory_integrity",
            "question": "Does source inventory fail closed on unreadable files and decoding errors?",
            "risk": "correctness",
            "target_patterns": ["source inventory", "decoding", "unreadable file"],
            "required_evidence": ["semantic_rule", "regression_test"],
        },
        {
            "name": "bounded_closure_integrity",
            "question": "Are closure edge endpoints always inside the bounded closure node set?",
            "risk": "dependency_impact",
            "target_patterns": ["bounded closure", "edge endpoint"],
            "required_evidence": ["semantic_rule", "regression_test"],
        },
        {
            "name": "test_evidence_preservation",
            "question": "Are test callable nodes and test edges preserved in bounded audit evidence?",
            "risk": "test_gap",
            "target_patterns": ["test callable", "test edge"],
            "required_evidence": ["semantic_rule", "regression_test"],
        },
    ],
    "invariants": [
        "Unsupported agent focus directives block deterministic-only completion.",
        "CodeRabbit lessons require exact reviewed-head and source-span grounding.",
        "Connectome paths, DREAM-lite ranking, QDKT memory, and causal crystals remain advisory.",
        "Learned similarity findings never become repair authority without current corroboration.",
        "Production mutation and automatic merge remain false.",
    ],
    "risk_map": [
        "semantic_completeness",
        "teacher_authority",
        "source_integrity",
        "symbol_identity",
        "bounded_graph_integrity",
        "test_evidence",
    ],
}
with open("/tmp/waboose-learning-request.json", "w", encoding="utf-8") as handle:
    json.dump(request, handle)
PY

python aura_coding_waboose_cli.py \
  --repo-root . \
  --state-file /tmp/waboose-learning-state.json \
  run --request /tmp/waboose-learning-request.json \
  | tee /tmp/waboose-learning-result.json

python - <<'PY'
import json
with open("/tmp/waboose-learning-result.json", encoding="utf-8") as handle:
    packet = json.load(handle)
assert packet.get("ok") is True, packet
assert packet.get("semantic_review_complete") is True, packet
assert not packet.get("unverified_focus_directives"), packet
assert not packet.get("forge_repair_requests"), packet
assert set(packet.get("semantic_rule_packs_executed") or []) == {
    "strict_input_types",
    "symbol_identity",
    "source_integrity",
    "bounded_graph_integrity",
    "test_evidence_preservation",
}
assert packet.get("production_mutation") is False
assert packet.get("automatic_merge") is False
PY

git push origin HEAD:"${HEAD_REF:-feature/aura-emergent-evidence-spine}"
