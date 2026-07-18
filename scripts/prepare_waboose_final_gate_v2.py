from __future__ import annotations

from pathlib import Path


def replace_required(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"missing final-gate preparation target: {label}")
    return text.replace(old, new, 1)


def main() -> None:
    path = Path("scripts/run_waboose_learning_final_gate.sh")
    text = path.read_text(encoding="utf-8")
    text = replace_required(
        text,
        '''python scripts/apply_waboose_learning_followups.py
python scripts/apply_waboose_mcp_strict_booleans.py
''',
        '''python scripts/apply_waboose_learning_followups.py
python scripts/apply_waboose_semantic_detector_followups.py
python scripts/apply_waboose_mcp_strict_booleans.py
''',
        "semantic detector patch execution",
    )
    text = replace_required(
        text,
        '''  tests/test_aura_waboose_semantic_rules.py
  tests/test_aura_waboose_semantic_completeness.py
''',
        '''  tests/test_aura_waboose_semantic_rules.py
  tests/test_aura_waboose_semantic_rule_false_positives.py
  tests/test_aura_waboose_semantic_completeness.py
''',
        "false-positive test Ruff surface",
    )
    text = replace_required(
        text,
        '''  tests/test_aura_waboose_semantic_rules.py \\
  tests/test_aura_waboose_semantic_completeness.py \\
''',
        '''  tests/test_aura_waboose_semantic_rules.py \\
  tests/test_aura_waboose_semantic_rule_false_positives.py \\
  tests/test_aura_waboose_semantic_completeness.py \\
''',
        "false-positive pytest surface",
    )
    text = replace_required(
        text,
        '''rm -f scripts/apply_waboose_learning_followups.py
rm -f scripts/apply_waboose_mcp_strict_booleans.py
rm -f scripts/repair_waboose_learning_patch_markers.py
rm -f scripts/run_waboose_learning_final_gate.sh
rm -f .github/workflows/emergent-spine-waboose-learning-final-v3.yml
''',
        '''rm -f scripts/apply_waboose_learning_followups.py
rm -f scripts/apply_waboose_semantic_detector_followups.py
rm -f scripts/apply_waboose_mcp_strict_booleans.py
rm -f scripts/repair_waboose_learning_patch_markers.py
rm -f scripts/prepare_waboose_final_gate_v2.py
rm -f scripts/run_waboose_learning_final_gate.sh
rm -f .github/workflows/emergent-spine-waboose-learning-final.yml
rm -f .github/workflows/emergent-spine-waboose-learning-final-v3.yml
rm -f .github/workflows/emergent-spine-waboose-learning-final-v4.yml
''',
        "complete temporary cleanup",
    )
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
