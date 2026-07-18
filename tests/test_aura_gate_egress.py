from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import json
from typing import Any

import pytest

from aura_gate_egress import (
    GateEgressCapsule,
    GateEgressDenied,
    GateEgressGovernor,
    GateEgressGrant,
)

NOW = 1_800_000_000.0
PURPOSE = "sha256:37c9416cfc25f21474abfc1c9a0b02cd0c8006b866aa3c72e1ce70da59f91e02"


def _payload() -> dict[str, Any]:
    return {
        "message": "bounded answer",
        "metadata": {
            "confidence": 0.75,
            "citations": ["connectome:node-42"],
            "reviewed": True,
        },
    }


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _grant(**overrides: Any) -> GateEgressGrant:
    values: dict[str, Any] = {
        "authority_id": "gate-authority-1",
        "gate_run_id": "gate-run-1",
        "purpose_digest": PURPOSE,
        "expires_at": NOW + 300,
        "allowed_destinations": ("mcp://research-tool", "a2a://review-agent"),
        "allowed_providers": ("local", "approved-cloud"),
        "allowed_models": ("model-a", "model-b"),
        "allowed_data_classes": ("PUBLIC", "INTERNAL_DERIVED"),
        "allowed_top_level_fields": ("message", "metadata"),
        "allowed_retention_classes": ("EPHEMERAL", "AUDIT_30D"),
        "max_payload_bytes": 4096,
        "max_token_estimate": 1024,
    }
    values.update(overrides)
    return GateEgressGrant(**values)


def _compile(
    payload: dict[str, Any] | None = None,
    *,
    grant: GateEgressGrant | None = None,
    **overrides: Any,
):
    values: dict[str, Any] = {
        "purpose_digest": PURPOSE,
        "destination": "mcp://research-tool",
        "provider": "local",
        "model": "model-a",
        "data_classes": ("PUBLIC",),
        "retention_class": "EPHEMERAL",
        "now": NOW,
    }
    values.update(overrides)
    return GateEgressGovernor.compile(grant or _grant(), payload or _payload(), **values)


def test_compile_returns_exact_safe_payload_and_content_bound_capsule() -> None:
    payload = _payload()
    expected = _canonical(payload)

    result = _compile(payload)
    capsule = result.capsule

    assert result.canonical_payload == expected
    assert result.decoded_payload() == payload
    assert capsule.payload_digest == "sha256:" + hashlib.sha256(expected).hexdigest()
    assert capsule.payload_bytes == len(expected)
    assert capsule.token_estimate == (len(expected) + 3) // 4
    assert capsule.included_fields == ("message", "metadata")
    assert capsule.authority_id == "gate-authority-1"
    assert capsule.gate_run_id == "gate-run-1"
    assert capsule.purpose_digest == PURPOSE
    assert capsule.data_classes == ("PUBLIC",)
    assert capsule.source_mutation_performed is False
    assert capsule.production_promotion_authority is False
    assert capsule.vsa_patch_authority is False
    assert capsule.capsule_id.startswith("gate-egress-capsule:sha256:")


def test_compilation_does_not_mutate_or_retain_mutable_payload() -> None:
    payload = _payload()
    before = _canonical(payload)

    result = _compile(payload)
    payload["metadata"]["confidence"] = 0.0

    assert result.canonical_payload == before
    assert result.decoded_payload()["metadata"]["confidence"] == 0.75


def test_capsule_is_deterministic_for_same_exact_compilation() -> None:
    first = _compile(data_classes=("INTERNAL_DERIVED", "PUBLIC"))
    second = _compile(data_classes=("PUBLIC", "INTERNAL_DERIVED"))

    assert first.capsule.data_classes == ("INTERNAL_DERIVED", "PUBLIC")
    assert first.capsule.capsule_id == second.capsule.capsule_id
    assert first.capsule.to_dict() == second.capsule.to_dict()


def test_grant_and_capsule_are_frozen() -> None:
    grant = _grant()
    capsule = _compile(grant=grant).capsule

    with pytest.raises(FrozenInstanceError):
        grant.max_payload_bytes = 1  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        capsule.payload_digest = "sha256:tampered"  # type: ignore[misc]


def test_tampered_content_address_is_rejected() -> None:
    capsule = _compile().capsule
    values = capsule.identity_basis()
    values["payload_digest"] = "sha256:" + ("0" * 64)

    with pytest.raises(GateEgressDenied, match="invalid_capsule"):
        GateEgressCapsule(capsule_id=capsule.capsule_id, **values)


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"purpose_digest": "sha256:wrong"}, "invalid_purpose"),
        ({"destination": "mcp://unapproved"}, "unauthorized_destination"),
        ({"provider": "unapproved"}, "unauthorized_provider"),
        ({"model": "unapproved-model"}, "unauthorized_model"),
        ({"data_classes": ("SECRET",)}, "unauthorized_data_class"),
        ({"retention_class": "FOREVER"}, "unauthorized_retention_class"),
    ],
)
def test_authority_dimensions_fail_closed(overrides: dict[str, Any], code: str) -> None:
    with pytest.raises(GateEgressDenied, match=code):
        _compile(**overrides)


def test_authority_is_expired_at_the_exact_boundary() -> None:
    with pytest.raises(GateEgressDenied, match="expired_authority"):
        _compile(now=NOW + 300)


@pytest.mark.parametrize("invalid_time", [True, "false", float("nan"), float("inf"), -1])
def test_evaluation_time_is_strict(invalid_time: Any) -> None:
    with pytest.raises(GateEgressDenied, match="invalid_time"):
        _compile(now=invalid_time)


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"purpose_digest": True}, "invalid_purpose"),
        ({"destination": False}, "invalid_destination"),
        ({"provider": True}, "invalid_provider"),
        ({"model": False}, "invalid_model"),
        ({"data_classes": "PUBLIC"}, "invalid_data_classes"),
        ({"data_classes": ["PUBLIC"]}, "invalid_data_classes"),
        ({"retention_class": True}, "invalid_retention_class"),
    ],
)
def test_string_boolean_and_container_coercions_are_rejected(
    overrides: dict[str, Any],
    code: str,
) -> None:
    with pytest.raises(GateEgressDenied, match=code):
        _compile(**overrides)


@pytest.mark.parametrize(
    "grant_override",
    [
        {"max_payload_bytes": True},
        {"max_token_estimate": "1024"},
        {"expires_at": False},
        {"allowed_destinations": ["mcp://research-tool"]},
        {"allowed_models": "model-a"},
    ],
)
def test_grant_types_are_not_coerced(grant_override: dict[str, Any]) -> None:
    with pytest.raises(GateEgressDenied):
        _grant(**grant_override)


def test_payload_field_allowlist_is_exact() -> None:
    payload = _payload()
    payload["extra"] = "not in the grant"

    with pytest.raises(GateEgressDenied, match="unauthorized_payload_field"):
        _compile(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"message": {"access_token": "sensitive"}},
        {"message": {"nested": {"apiKey": "sensitive"}}},
        {"message": {"modelChainOfThought": "sensitive"}},
        {"message": {"source-diff": "sensitive"}},
        {"message": {"credential": "sensitive"}},
        {"message": {"result_auth_token": "sensitive"}},
    ],
)
def test_sensitive_nested_keys_are_denied(payload: dict[str, Any]) -> None:
    with pytest.raises(GateEgressDenied, match="forbidden_payload_key"):
        _compile(payload)


@pytest.mark.parametrize(
    "material",
    [
        "Bearer very-secret-bearer-token-value",
        "Basic dXNlcjpwYXNzd29yZA==",
        "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJwcml2YXRlIn0.signature-value",
        "private reasoning: never export this scratchpad",
        "diff --git a/aura.py b/aura.py\n@@ -1,1 +1,1 @@\n-old\n+new",
        "-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----",
        "sk-abcdefghijklmnopqrstuvwxyz123456",
        "AKIAABCDEFGHIJKLMNOP",
    ],
)
def test_secret_private_reasoning_and_source_diff_material_is_denied(material: str) -> None:
    with pytest.raises(GateEgressDenied, match="forbidden_material"):
        _compile({"message": material})


@pytest.mark.parametrize(
    "payload",
    [
        {"message": float("nan")},
        {"message": float("inf")},
        {"message": b"bytes"},
        {"message": ("tuple",)},
        {"message": {1, 2}},
        {"message": {1: "non-string-key"}},
        {1: "non-string-top-level-key"},
    ],
)
def test_non_json_and_non_finite_payloads_are_denied(payload: Any) -> None:
    with pytest.raises(GateEgressDenied, match="invalid_json_payload"):
        _compile(payload)


def test_empty_payload_is_denied() -> None:
    with pytest.raises(GateEgressDenied, match="invalid_json_payload"):
        GateEgressGovernor.compile(
            _grant(),
            {},
            purpose_digest=PURPOSE,
            destination="mcp://research-tool",
            provider="local",
            model="model-a",
            data_classes=("PUBLIC",),
            retention_class="EPHEMERAL",
            now=NOW,
        )


def test_exact_byte_budget_boundary() -> None:
    payload = _payload()
    exact_bytes = len(_canonical(payload))

    result = _compile(payload, grant=_grant(max_payload_bytes=exact_bytes))
    assert result.capsule.payload_bytes == exact_bytes

    with pytest.raises(GateEgressDenied, match="payload_byte_budget_exceeded"):
        _compile(payload, grant=_grant(max_payload_bytes=exact_bytes - 1))


def test_exact_token_estimate_budget_boundary_uses_canonical_bytes() -> None:
    payload = _payload()
    expected = (len(_canonical(payload)) + 3) // 4

    result = _compile(payload, grant=_grant(max_token_estimate=expected))
    assert result.capsule.token_estimate == expected

    with pytest.raises(GateEgressDenied, match="payload_token_budget_exceeded"):
        _compile(payload, grant=_grant(max_token_estimate=expected - 1))


def test_utf8_byte_budget_uses_exact_serialized_bytes() -> None:
    payload = {"message": "anishinaabemowin: aaniin ᐊᓂᔑᓈᐯ"}
    exact = _canonical(payload)

    result = _compile(payload, grant=_grant(max_payload_bytes=len(exact)))

    assert result.canonical_payload == exact
    assert result.capsule.payload_bytes == len(exact)
    assert result.capsule.payload_bytes > len(exact.decode("utf-8"))


def test_denial_does_not_leak_payload_or_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "Bearer one-very-private-token-that-must-not-leak"

    with pytest.raises(GateEgressDenied) as captured:
        _compile({"message": secret})

    assert secret not in str(captured.value)
    assert "one-very-private-token" not in str(captured.value)
    assert not caplog.records


def test_allowlist_cannot_authorize_a_forbidden_field() -> None:
    with pytest.raises(GateEgressDenied, match="forbidden_payload_key"):
        _grant(allowed_top_level_fields=("message", "chainOfThought"))
