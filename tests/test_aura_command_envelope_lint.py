import json

from tools.aura_command_envelope_lint import extract_drive_ids, lint_text, validate_d0_envelope


AUTHORITY_ID = "1SnLzRLRDGib2DltXNDKBkgfgI3PWayj6O6b5I8AkyP8"
WORK_ORDER_ID = "1PkEPzyF0_25yGA776_TIcHAWv9ho_N4mkqJ2WfM5mP4"


def _good_envelope():
    return {
        "schema": "AuraCommandEnvelopeV1-candidate",
        "command_id": "AWJ032-GLM53-06-TEST",
        "idempotency_key": "AWJ032-GLM53-06-TEST-R1",
        "authority_ref": f"OWNER-DIRECT + Drive {AUTHORITY_ID}",
        "execution_authorized": True,
        "currentness": {
            "resolve_awj001_current_at_admission": True,
            "stale_behavior": "REBASE_RECOMPILE_REISSUE",
        },
        "effect_ceiling": "D0",
        "work_order_ref": f"Drive {WORK_ORDER_ID}",
        "objective": {"requested_effect": "D0", "task": "validate source-bound D0 work"},
        "negative_intent": ["NO_PROVIDER_SPEND", "NO_MAIN_MERGE"],
    }


def test_valid_json_first_d0_envelope_passes():
    receipt = validate_d0_envelope(_good_envelope())
    assert receipt["valid"] is True
    assert receipt["errors"] == []
    assert receipt["authority_resolution"] == "UNVERIFIED"
    assert receipt["drive_ids"] == [AUTHORITY_ID]


def test_google_docs_bom_is_tolerated():
    text = "\ufeff" + json.dumps(_good_envelope())
    assert lint_text(text)["valid"] is True


def test_trailing_prose_after_json_fails_parse():
    receipt = lint_text(json.dumps(_good_envelope()) + "\nNOT PART OF JSON")
    assert receipt["valid"] is False
    assert receipt["errors"][0].startswith("JSON_PARSE_ERROR:")


def test_effect_ceiling_is_byte_exact_d0():
    env = _good_envelope()
    env["effect_ceiling"] = "D0 MODEL_OUTPUT_ONLY"
    assert "EFFECT_CEILING_NOT_EXACT_D0" in validate_d0_envelope(env)["errors"]


def test_requested_effect_is_byte_exact_d0():
    env = _good_envelope()
    env["objective"]["requested_effect"] = " d0 "
    assert "REQUESTED_EFFECT_NOT_EXACT_D0" in validate_d0_envelope(env)["errors"]


def test_constraints_fail_closed_unless_exact_d0_string():
    env = _good_envelope()
    env["constraints"] = {"D0": "yes"}
    assert "CONSTRAINTS_NOT_EXACT_D0" in validate_d0_envelope(env)["errors"]

    env["constraints"] = "D0"
    assert "CONSTRAINTS_NOT_EXACT_D0" not in validate_d0_envelope(env)["errors"]


def test_authority_requires_real_drive_id_candidate():
    env = _good_envelope()
    env["authority_ref"] = "OWNER-DIRECT-CURRENT-TURN"
    assert "AUTHORITY_REF_NO_DRIVE_ID" in validate_d0_envelope(env)["errors"]


def test_drive_id_extraction_does_not_consume_work_order_prefix():
    real_id = "1COzOmPmKje6LhEgmzaBpFlQqfeJPgFAwG1PVLEV3yKk"
    text = f"WORK-ORDER-DRIVE-{real_id}"
    assert extract_drive_ids(text) == [real_id]


def test_known_raw_executor_key_is_blocked_at_any_depth():
    env = _good_envelope()
    env["objective"]["nested"] = {"executor_command": "echo unsafe"}
    errors = validate_d0_envelope(env)["errors"]
    assert any(error.startswith("FORBIDDEN_KEY:") for error in errors)


def test_missing_currentness_is_warning_not_fabricated_failure():
    env = _good_envelope()
    del env["currentness"]
    receipt = validate_d0_envelope(env)
    assert receipt["valid"] is True
    assert "CURRENTNESS_BLOCK_MISSING" in receipt["warnings"]


def test_objective_must_be_structured_for_current_d0_profile():
    env = _good_envelope()
    env["objective"] = "D0 prose objective"
    assert "OBJECTIVE_NOT_OBJECT" in validate_d0_envelope(env)["errors"]
