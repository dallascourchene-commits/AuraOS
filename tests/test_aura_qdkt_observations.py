from __future__ import annotations

from dataclasses import replace

import pytest

from aura_qdkt_observations import QDKTObservation, QDKTTruthClass

LEGACY_RESULT = {"root": "A1B2C3D4E5F60718", "belief": 6900}
SOURCE_SNAPSHOT = (
    {"path": "alpha.py", "digest": "a" * 64},
    {"path": "beta.py", "digest": "b" * 64},
)


def observation(**kwargs) -> QDKTObservation:
    return QDKTObservation.from_legacy_result(
        LEGACY_RESULT,
        source_snapshot=SOURCE_SNAPSHOT,
        **kwargs,
    )


def test_exact_legacy_result_is_nondeterministic_advisory() -> None:
    value = observation(
        planning_board_ref="board-ref",
        planning_history_ref="history-ref",
        continuity_ref="continuity-ref",
    )
    assert value.legacy_result == LEGACY_RESULT
    assert value.truth_class is QDKTTruthClass.LEGACY_NONDETERMINISTIC_ADVISORY
    assert value.source_count == 2
    assert value.proposal_only is True
    assert value.reproducible is False
    assert value.qdkt_patch_authority is False


def test_same_snapshot_has_same_identity_and_digest() -> None:
    left = observation()
    right = observation()
    assert left == right
    assert left.observation_id == right.observation_id
    assert left.digest == right.digest


def test_boolean_and_negative_beliefs_are_rejected() -> None:
    for invalid in (True, -1):
        with pytest.raises(ValueError, match="non-negative integer"):
            QDKTObservation.from_legacy_result(
                {"root": LEGACY_RESULT["root"], "belief": invalid},
                source_snapshot=SOURCE_SNAPSHOT,
            )


def test_malformed_or_extra_legacy_fields_are_rejected() -> None:
    with pytest.raises(ValueError, match="root is malformed"):
        QDKTObservation.from_legacy_result(
            {"root": "abcdef", "belief": 1},
            source_snapshot=SOURCE_SNAPSHOT,
        )
    with pytest.raises(ValueError, match="exactly root and belief"):
        QDKTObservation.from_legacy_result(
            {"root": LEGACY_RESULT["root"], "belief": 1, "extra": 2},
            source_snapshot=SOURCE_SNAPSHOT,
        )


def test_prohibited_observation_field_is_rejected() -> None:
    field_name = "scratch" + "Pad"
    with pytest.raises(ValueError):
        QDKTObservation.from_legacy_result(
            LEGACY_RESULT,
            source_snapshot={field_name: "hidden"},
        )


def test_lossy_or_sensitive_provenance_is_rejected() -> None:
    field_name = "api" + "_key"
    with pytest.raises(ValueError, match="sensitive or lossy"):
        QDKTObservation.from_legacy_result(
            LEGACY_RESULT,
            source_snapshot={field_name: "placeholder-value"},
        )


def test_from_dict_requires_canonical_input_array() -> None:
    payload = observation().to_dict()
    payload["nondeterministic_inputs"] = "thermal_reading"
    with pytest.raises(ValueError, match="JSON array"):
        QDKTObservation.from_dict(payload)


def test_identity_and_authority_forgery_is_rejected() -> None:
    value = observation()
    with pytest.raises(ValueError, match="observation_id"):
        replace(value, observation_id="qdkt-observation_forged")
    with pytest.raises(ValueError, match="authority boundary"):
        replace(value, qdkt_patch_authority=True)
    with pytest.raises(ValueError, match="non-reproducible"):
        replace(value, reproducible=True)


def test_incomplete_nondeterminism_declaration_is_rejected() -> None:
    value = observation()
    with pytest.raises(ValueError, match="complete legacy set"):
        replace(value, nondeterministic_inputs=("filesystem_snapshot",))
