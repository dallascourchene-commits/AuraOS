"""Validate the final Phase 5 record before clean map regeneration."""
from __future__ import annotations

import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
evidence = json.loads(
    (root / "docs/evidence/AURA_SCO_PHASE5_E9_E14_COMPLETION.json").read_text(
        encoding="utf-8"
    )
)
plan = (root / "docs/AURA_SCO_PHASE5_E9_E14_COMPLETION_PLAN.md").read_text(
    encoding="utf-8"
)
assert evidence["focused_tests_passed"] == 19
assert evidence["inherited_regressions_passed"] == 253
assert evidence["runtime_complete"] is True
assert evidence["unresolved"] == []
assert evidence["e14_release_status"] == "READY_FOR_PINNED_MERGE"
assert evidence["coderabbit"]["explicit_invocations"] == 1
assert evidence["coderabbit"]["invoke_again"] is False
assert "document_status: VERIFIED_PENDING_PINNED_MERGE" in plan
assert "CodeRabbit was invoked exactly once" in plan
