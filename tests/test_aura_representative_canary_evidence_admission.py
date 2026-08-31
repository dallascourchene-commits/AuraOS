from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "quantization" / "aura_representative_canary_evidence_admission.py"
spec = importlib.util.spec_from_file_location("aura_representative_canary_evidence_admission", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)

RegisteredCanaryScope = mod.RegisteredCanaryScope
CanaryObservation = mod.CanaryObservation
admit = mod.admit_representative_canary_evidence

H = "a" * 64
H2 = "b" * 64
H3 = "c" * 64
H4 = "d" * 64


def scope():
    return RegisteredCanaryScope(
        scope_id="glm53-l3-e0-representative-equal-rate-v1",
        source_set_digest=H,
        expected_tile_ids=("gate-0", "gate-128", "down-0", "down-128"),
        exact_bits_per_weight=1.25,
    )


def obs(tile_id: str, candidate: float, control: float):
    return CanaryObservation(
        tile_id=tile_id,
        source_set_digest=H,
        source_tile_sha256=H2,
        candidate_payload_sha256=H3,
        control_payload_sha256=H4,
        bits_per_weight=1.25,
        candidate_mse=candidate,
        control_mse=control,
        outcome=mod.classify_outcome(candidate, control),
    )


def test_partial_scope_returns_exact_missing_cone():
    receipt = admit(scope(), [obs("gate-0", 1.0, 2.0), obs("down-0", 3.0, 2.0)])
    assert receipt["disposition"] == "REPRESENTATIVE_VERIFICATION_INCOMPLETE"
    assert receipt["next_work_mode"] == "VERIFICATION"
    assert receipt["minimum_missing_evidence_cone"] == ["down-128", "gate-128"]
    assert receipt["semantic_sibling_credit"] is False


def test_complete_unanimous_e8_win_still_does_not_promote_geometry():
    rows = [obs(tile, 1.0, 2.0) for tile in scope().expected_tile_ids]
    receipt = admit(scope(), rows)
    assert receipt["registered_scope_complete"] is True
    assert receipt["outcome_counts"]["E8_WIN"] == 4
    assert receipt["next_work_mode"] == "STOP_OR_REGISTER_HIGHER_SCOPE"
    assert receipt["geometry_superiority_proven"] is False
    assert receipt["full_tensor_superiority_proven"] is False
    assert receipt["full_model_superiority_proven"] is False


def test_complete_control_win_and_tie_are_valid_evidence():
    rows = [
        obs("gate-0", 2.0, 1.0),
        obs("gate-128", 1.0, 1.0),
        obs("down-0", 3.0, 2.0),
        obs("down-128", 5.0, 5.0),
    ]
    receipt = admit(scope(), rows)
    assert receipt["registered_scope_complete"] is True
    assert receipt["outcome_counts"] == {"CONTROL_WIN": 2, "E8_WIN": 0, "TIE": 2}
    assert receipt["support_merge_eligible"] is True


def test_input_permutation_does_not_change_receipt():
    rows = [
        obs("gate-0", 1.0, 2.0),
        obs("gate-128", 2.0, 1.0),
        obs("down-0", 1.0, 1.0),
    ]
    a = admit(scope(), rows)
    b = admit(scope(), list(reversed(rows)))
    assert a == b


def test_duplicate_tile_rejected():
    row = obs("gate-0", 1.0, 2.0)
    with pytest.raises(ValueError, match="duplicate"):
        admit(scope(), [row, row])


def test_foreign_tile_rejected():
    with pytest.raises(ValueError, match="outside registered scope"):
        admit(scope(), [obs("foreign", 1.0, 2.0)])


def test_source_set_drift_rejected():
    row = obs("gate-0", 1.0, 2.0)
    drift = CanaryObservation(**{**row.__dict__, "source_set_digest": "e" * 64})
    with pytest.raises(ValueError, match="source set"):
        admit(scope(), [drift])


def test_rate_drift_rejected():
    row = obs("gate-0", 1.0, 2.0)
    drift = CanaryObservation(**{**row.__dict__, "bits_per_weight": 1.5})
    with pytest.raises(ValueError, match="rate drift"):
        admit(scope(), [drift])


def test_declared_outcome_must_match_mse_ordering():
    row = obs("gate-0", 1.0, 2.0)
    bad = CanaryObservation(**{**row.__dict__, "outcome": "CONTROL_WIN"})
    with pytest.raises(ValueError, match="disagrees"):
        admit(scope(), [bad])


def test_hash_domain_is_strict_lowercase_sha256():
    row = obs("gate-0", 1.0, 2.0)
    bad = CanaryObservation(**{**row.__dict__, "source_tile_sha256": "A" * 64})
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        admit(scope(), [bad])


def test_claim_ceiling_is_fail_closed():
    receipt = admit(scope(), [obs("gate-0", 1.0, 2.0)])
    for key in (
        "geometry_superiority_proven",
        "full_tensor_superiority_proven",
        "full_model_superiority_proven",
        "quality_superiority_proven",
        "runtime_superiority_proven",
        "effect_authority",
        "gate10_promoted",
        "native_private_kv_accessed",
        "semantic_k27_authority",
    ):
        assert receipt[key] is False


def test_scope_requires_unique_registered_tiles():
    bad = RegisteredCanaryScope(
        scope_id="x",
        source_set_digest=H,
        expected_tile_ids=("a", "a"),
        exact_bits_per_weight=1.25,
    )
    with pytest.raises(ValueError, match="unique"):
        admit(bad, [])
