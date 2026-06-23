from aura_phase_capsule import (
    PHASE_LOCK_POWER,
    capture_phase_capsule,
    detect_incomplete_json,
    resume_instruction,
    verify_capsule_prefix,
)


def test_detect_incomplete_json_boundary():
    incomplete, state = detect_incomplete_json('{"answer": "partial"')
    assert incomplete is True
    assert state.startswith("JSON_INCOMPLETE")

    complete, state = detect_incomplete_json('{"answer": "done"}')
    assert complete is False
    assert state == "JSON_COMPLETE"


def test_phase_capsule_records_offsets_crc_and_resume_marker():
    prefix = '{"answer": "partial"'
    capsule = capture_phase_capsule(
        prefix,
        run_id="run-1",
        previous_agent="worker",
        next_role="VERIFIER",
        target_file="aura_fusion.py",
        target_symbol="AuraFusionCoordinator",
    )

    assert capsule.byte_offset == len(prefix.encode("utf-8"))
    assert capsule.char_offset == len(prefix)
    assert capsule.permutation_power == PHASE_LOCK_POWER
    assert verify_capsule_prefix(capsule, prefix)

    resume = resume_instruction(capsule)
    assert "PI^4097" in resume
    assert "AuraFusionCoordinator" in resume
