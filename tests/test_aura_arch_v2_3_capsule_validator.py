import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

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
        "dependency_and_threat_model_freshness": "PASSED",
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


_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "architecture_harness"
    / "ARCH_V2_3"
    / "aura_pr_continuity_capsule.v2_3.schema.json"
)
_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "architecture_harness"
    / "ARCH_V2_3"
    / "AURA_PR_CONTINUITY_CAPSULE_TEMPLATE_V2_3.md"
)


def _subvalidator(name: str) -> Draft202012Validator:
    root = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    subschema = dict(root["properties"][name])
    subschema["$defs"] = root["$defs"]
    Draft202012Validator.check_schema(subschema)
    return Draft202012Validator(subschema)


def _valid_commit_authorization() -> dict:
    gates = _capsule()["commit_authorization"]["gate_outcomes"]
    digest = _digest("1")
    return {
        "status": "VALIDATED",
        "workspace_id": "workspace:1",
        "authorized_effect_digest": digest,
        "planned_effect_digest": digest,
        "candidate_effect_digest": digest,
        "witness_digest": _digest("2"),
        "capability_lease_digest": _digest("3"),
        "dependency_digest": _digest("4"),
        "validated_head_sha": "a" * 40,
        "gate_outcomes": gates,
        "validated_at": "2026-08-08T00:00:00Z",
        "expires_at": "2026-08-08T01:00:00Z",
        "receipt_ref": "receipt:commit-auth",
        "freshness_revalidation_required": True,
    }


def test_schema_rejects_validated_authorization_with_failed_gate() -> None:
    value = _valid_commit_authorization()
    value["gate_outcomes"]["identity_binding"] = "FAILED"
    with pytest.raises(ValidationError):
        _subvalidator("commit_authorization").validate(value)


def _valid_jspace_projection() -> dict:
    return {
        "status": "ENABLED",
        "projection_id": "projection:1",
        "codec_version": "AURA_JSPACE_CODEC_V0",
        "workspace_id": "workspace:1",
        "head_sha": "a" * 40,
        "active_limit": 25,
        "packet_digest": _digest("5"),
        "phase_hash": "phase:1",
        "source_refs": ["src:1"],
        "origin_refs": ["origin:1"],
        "freshness": "CURRENT",
        "authority_class": "ADVISORY_NONE",
        "authoritative": False,
        "patch_authority": False,
        "persistent_truth": False,
        "reconstructable": True,
        "expires_at": "2026-08-08T01:00:00Z",
    }


def test_schema_rejects_enabled_jspace_without_required_binding() -> None:
    value = _valid_jspace_projection()
    value["workspace_id"] = None
    with pytest.raises(ValidationError):
        _subvalidator("jspace_projection").validate(value)


def test_schema_rejects_stale_enabled_jspace() -> None:
    value = _valid_jspace_projection()
    value["freshness"] = "STALE"
    with pytest.raises(ValidationError):
        _subvalidator("jspace_projection").validate(value)


def test_template_exposes_verification_independence_contract_fields() -> None:
    text = _TEMPLATE_PATH.read_text(encoding="utf-8")
    for label in (
        "Model-provider refs:",
        "Input-origin refs:",
        "Shared-tool refs:",
        "Shared-session refs:",
        "Sybil-resistance evidence:",
        "Independence receipt:",
    ):
        assert label in text
