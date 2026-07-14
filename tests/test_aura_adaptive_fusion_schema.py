from __future__ import annotations

import json

from aura_adaptive_fusion import AdaptiveFusionPanelExecutor


def test_fusion_telemetry_rejects_required_fields_with_invalid_types() -> None:
    invalid_judge = {
        "consensus": [],
        "contradictions": [],
        "coverage_gaps": [],
        "unique_insights": [],
        "blind_spots": [],
        "winning_approach": "bounded",
        "final_answer": "review",
        "confidence": "high",
        "should_escalate_to_human": False,
    }

    assert AdaptiveFusionPanelExecutor._schema_passed(
        "JUDGE", json.dumps(invalid_judge), None
    ) is False

def test_fusion_schema_rejects_additional_properties_and_nonfinite_numbers() -> None:
    import json

    extra = {
        "role": "THINKER", "answer": "x", "claims": [], "risks": [],
        "missing_info": [], "recommended_action": "review", "confidence": 0.5,
        "unexpected": True,
    }
    nonfinite = dict(extra)
    nonfinite.pop("unexpected")
    nonfinite["confidence"] = float("nan")
    assert AdaptiveFusionPanelExecutor._schema_passed("THINKER", json.dumps(extra), None) is False
    assert AdaptiveFusionPanelExecutor._schema_passed("THINKER", json.dumps(nonfinite), None) is False
