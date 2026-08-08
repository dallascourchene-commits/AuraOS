from copy import deepcopy

import pytest

from scripts.aura_arch_v2_3_capsule_validator import validate_arch_v2_3_capsule_semantics


def _digest(char: str) -> str:
    return "sha256:" + char * 64


def _capsule() -> dict:
    head = "a" * 40
    gates = {
        "identity_binding": "PASSED",
        "witness_fresh_and_unrevoked": "PASSED",
        "lease_current_and_eligible": "PASSED",
        "causal_prior": "PASSED",
        "effect_binding_current": "PASSED",
        "dependency_and_threat_model_current": "PASSED",
        "proof_freshness": "PASSED",
        "verifier_independence": "PASSED",
        "governance_disposition": "PASSED",
    }
    return {
        "schema_version": "AURA_PR_CONTINUITY_CAPSULE_V2_3",
        "harness_version": "AURA_ARCH_V2_3",
        "head_sha": head,
        "jspace_projection": {
            "status": "ENABLED",
            "head_sha": head,
            "freshness": "CURRENT",
            "source_refs": ["src:1"],
            "origin_refs": ["origin:1"],
        },
        "commit_authorization": {
            "status": "VALIDATED",
            "validated_head_sha": head,
            "authorized_effect_digest": _digest("1"),
            "planned_effect_digest": _digest("1"),
            "candidate_effect_digest": _digest("1"),
            "gate_outcomes": gates,
        },
        "verification_independence": {
            "status": "INDEPENDENT",
            "verifier_refs": ["verifier:1"],
            "model_provider_refs": ["provider:1"],
            "input_origin_refs": ["input:1"],
            "sybil_resistance_evidence": ["receipt:sybil"],
            "disposition": "accepted",
            "receipt_ref": "receipt:independence",
        },
    }


def test_valid_semantics_pass() -> None:
    validate_arch_v2_3_capsule_semantics(_capsule())


@pytest.mark.parametrize("path", ["jspace_projection", "commit_authorization"])
def test_cross_head_is_rejected(path: str) -> None:
    value = _capsule()
    key = "head_sha" if path == "jspace_projection" else "validated_head_sha"
    value[path][key] = "b" * 40
    with pytest.raises(ValueError, match="head"):
        validate_arch_v2_3_capsule_semantics(value)


def test_stale_enabled_jspace_is_rejected() -> None:
    value = _capsule()
    value["jspace_projection"]["freshness"] = "STALE"
    with pytest.raises(ValueError, match="CURRENT"):
        validate_arch_v2_3_capsule_semantics(value)


def test_effect_digest_mismatch_is_rejected() -> None:
    value = _capsule()
    value["commit_authorization"]["candidate_effect_digest"] = _digest("2")
    with pytest.raises(ValueError, match="effect digests"):
        validate_arch_v2_3_capsule_semantics(value)


def test_independence_without_evidence_is_rejected() -> None:
    value = _capsule()
    value["verification_independence"]["sybil_resistance_evidence"] = []
    with pytest.raises(ValueError, match="lacks evidence"):
        validate_arch_v2_3_capsule_semantics(value)
