"""Validate final Phase 4 evidence before the self-cleaning topology commit."""
from __future__ import annotations

import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
evidence_path = root / "docs/evidence/AURA_SCO_PHASE4_E9_E12_TEMPORAL_PERSISTENCE.json"
plan_path = root / "docs/AURA_SCO_PHASE4_E9_E12_TEMPORAL_PERSISTENCE_PLAN.md"
evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
plan = plan_path.read_text(encoding="utf-8")
assert evidence["coderabbit"]["explicit_invocations"] == 1
assert evidence["coderabbit"]["invoke_again"] is False
assert evidence["tests"]["focused_passed"] == 25
assert evidence["tests"]["canonical_owner_regressions_passed"] == 95
assert evidence["claim_boundaries"]["human_review_required"] is True
assert "document_status: VERIFIED_PENDING_PINNED_MERGE" in plan
assert "CodeRabbit was invoked exactly once" in plan
