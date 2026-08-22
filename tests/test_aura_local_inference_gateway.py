from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from aura_local_inference_gateway import (
    AuraLocalInferenceGateway,
    BackendAdapter,
    InferenceRequestV1,
    ModelPolicyResolver,
    PolicyResolutionError,
    canonical_context_digest,
)
from aura_route_capsule_registry import load_registry_component


POLICY_REF = ".aura/model_policies/local_first.v1.json"


def _write_policy(root: Path, **overrides) -> str:
    path = root / POLICY_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "AURA_MODEL_POLICY_V1",
        "component_id": "local_first.v1",
        "kind": "model_policy",
        "default": "no_model",
        "fallback": "local_model",
        "external_allowed": False,
        "maximum_model_calls": 2,
        "escalation_requires": [
            "local_attempt_failed",
            "budget_available",
            "expected_quality_gain",
        ],
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return POLICY_REF


def _context(content: str = "bounded exact slice", **extra):
    payload = {"content": content, "source_refs": ["SRC-1"], **extra}
    return {"context_slice_digest": canonical_context_digest(payload), **payload}


def _request(context=None, **overrides) -> InferenceRequestV1:
    context = context or _context()
    values = {
        "request_id": "REQ-1",
        "objective_id": "OBJ-1",
        "policy_ref": POLICY_REF,
        "context_slice_digest": context["context_slice_digest"],
        "source_refs": ("SRC-1",),
        "currentness_refs": ("CUR-1",),
        "authority_refs": ("AUTH-1",),
        "privacy_refs": ("PRIV-1",),
        "reopen_refs": ("REOPEN-1",),
    }
    values.update(overrides)
    return InferenceRequestV1(**values)


def _compile(context):
    return lambda _: dict(context)


def _trusted_fixture(adapter, policy):
    return (
        adapter.backend_class == "local_model"
        and adapter.backend_id.startswith("fake-local")
        and adapter.network_required is False
        and policy.external_allowed is False
    )


def test_policy_resolver_reuses_route_registry_digest(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    owner = load_registry_component(tmp_path, POLICY_REF, field_name="model_policy_ref")
    decision = ModelPolicyResolver(tmp_path).resolve(
        POLICY_REF,
        expected_blob_digest=owner.digest,
    )
    assert decision.policy_blob_digest == owner.digest
    assert decision.allowed_backend_classes == ("deterministic", "local_model")


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"default": []}, "policy_default_must_be_string"),
        ({"fallback": {}}, "policy_fallback_must_be_string"),
        ({"default": "mystery"}, "policy_default_unknown"),
        ({"schema_version": "UNKNOWN"}, "policy_schema_unknown"),
        ({"external_allowed": "false"}, "policy_external_allowed_must_be_bool"),
        ({"maximum_model_calls": -1}, "policy_maximum_model_calls_invalid"),
        ({"mystery_permission": True}, "policy_unknown_fields"),
    ],
)
def test_policy_resolver_fails_closed_on_malformed_policy(
    tmp_path: Path,
    overrides,
    code: str,
) -> None:
    _write_policy(tmp_path, **overrides)
    with pytest.raises(PolicyResolutionError) as exc:
        ModelPolicyResolver(tmp_path).resolve(POLICY_REF)
    assert exc.value.code == code


def test_policy_registry_blocks_traversal_and_symlink_escape(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    resolver = ModelPolicyResolver(tmp_path)

    with pytest.raises(PolicyResolutionError) as traversal:
        resolver.resolve("../secret.json")
    assert traversal.value.code == "policy_ref_unsafe"

    outside = tmp_path.parent / f"{tmp_path.name}-outside-policy"
    outside.mkdir(exist_ok=True)
    (outside / "local_first.v1.json").write_text(
        (tmp_path / POLICY_REF).read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    policy_root = tmp_path / ".aura" / "model_policies"
    for child in list(policy_root.iterdir()):
        child.unlink()
    policy_root.rmdir()
    try:
        os.symlink(outside, policy_root, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink unavailable on this platform")

    with pytest.raises(PolicyResolutionError) as linked:
        resolver.resolve(POLICY_REF)
    assert linked.value.code == "policy_ref_unsafe"


def test_deterministic_default_satisfies_without_model_call(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    context = _context()
    calls = []
    result = AuraLocalInferenceGateway(tmp_path).run(
        _request(context),
        context_compiler=_compile(context),
        deterministic_backend=BackendAdapter(
            "det-v1",
            "deterministic",
            lambda payload: calls.append(payload) or {"output": "exact"},
        ),
    )
    assert result["ok"] is True
    assert result["receipt"]["selected_backend_class"] == "deterministic"
    assert result["receipt"]["model_call_count"] == 0
    assert result["receipt"]["effect_state"] == "CANDIDATE_ONLY"
    assert len(calls) == 1


def test_context_content_is_rehashed_not_label_trusted(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    context = _context("first")
    forged = dict(context)
    forged["content"] = "second"
    calls = []

    result = AuraLocalInferenceGateway(tmp_path).run(
        _request(context),
        context_compiler=_compile(forged),
        deterministic_backend=BackendAdapter(
            "det-v1",
            "deterministic",
            lambda payload: calls.append(payload) or {"output": "bad"},
        ),
    )
    assert result["ok"] is False
    assert result["receipt"]["blocked_reason"] == "context_claimed_digest_mismatch"
    assert calls == []


def test_context_request_digest_mismatch_blocks(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    one = _context("one")
    two = _context("two")
    result = AuraLocalInferenceGateway(tmp_path).run(
        _request(one),
        context_compiler=_compile(two),
        deterministic_backend=BackendAdapter(
            "det-v1", "deterministic", lambda _: {"output": "bad"}
        ),
    )
    assert result["ok"] is False
    assert result["receipt"]["blocked_reason"] == "context_slice_digest_mismatch"


def test_policy_movement_inside_context_compilation_blocks_before_effect(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    context = _context()
    calls = []

    def moving_context(_):
        _write_policy(tmp_path, maximum_model_calls=1)
        return dict(context)

    result = AuraLocalInferenceGateway(tmp_path).run(
        _request(context),
        context_compiler=moving_context,
        deterministic_backend=BackendAdapter(
            "det-v1",
            "deterministic",
            lambda payload: calls.append(payload) or {"output": "must not run"},
        ),
    )
    assert result["ok"] is False
    assert result["receipt"]["blocked_reason"] == "policy_digest_mismatch"
    assert calls == []


def test_existing_policy_pin_detects_movement_before_run(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    owner = load_registry_component(tmp_path, POLICY_REF, field_name="model_policy_ref")
    _write_policy(tmp_path, maximum_model_calls=1)
    context = _context()

    result = AuraLocalInferenceGateway(tmp_path).run(
        _request(context, expected_policy_digest=owner.digest),
        context_compiler=_compile(context),
        deterministic_backend=BackendAdapter(
            "det-v1", "deterministic", lambda _: {"output": "bad"}
        ),
    )
    assert result["ok"] is False
    assert result["receipt"]["blocked_reason"] == "policy_digest_mismatch"


def test_local_fallback_requires_escalation_and_trusted_capability(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    context = _context()
    gateway = AuraLocalInferenceGateway(tmp_path)
    deterministic = BackendAdapter(
        "det-v1",
        "deterministic",
        lambda _: {"satisfied": False, "reason": "local_attempt_failed"},
    )
    local_calls = []
    local = BackendAdapter(
        "fake-local-v1",
        "local_model",
        lambda payload: local_calls.append(payload) or {"output": "local answer"},
        artifact_ref="fixture://local-v1",
        capability_ref="fixture-capability/local-v1",
    )

    no_escalation = gateway.run(
        _request(context),
        context_compiler=_compile(context),
        deterministic_backend=deterministic,
        local_backend=local,
        capability_validator=_trusted_fixture,
    )
    assert no_escalation["receipt"]["blocked_reason"] == "fallback_escalation_requirements_unsatisfied"

    evidence = (
        "local_attempt_failed",
        "budget_available",
        "expected_quality_gain",
    )
    unverified = gateway.run(
        _request(context, request_id="REQ-2", escalation_evidence=evidence),
        context_compiler=_compile(context),
        deterministic_backend=deterministic,
        local_backend=local,
    )
    assert unverified["receipt"]["blocked_reason"] == "backend_capability_unverified"
    assert local_calls == []

    allowed = gateway.run(
        _request(context, request_id="REQ-3", escalation_evidence=evidence),
        context_compiler=_compile(context),
        deterministic_backend=deterministic,
        local_backend=local,
        capability_validator=_trusted_fixture,
    )
    assert allowed["ok"] is True
    assert allowed["receipt"]["selected_backend_class"] == "local_model"
    assert allowed["receipt"]["model_call_count"] == 1
    assert len(local_calls) == 1


def test_provider_backed_callback_mislabeled_local_is_not_authorized_by_metadata(tmp_path: Path) -> None:
    _write_policy(tmp_path, default="local_model", fallback="local_model")
    context = _context()
    calls = []
    result = AuraLocalInferenceGateway(tmp_path).run(
        _request(context),
        context_compiler=_compile(context),
        local_backend=BackendAdapter(
            "deepseek-disguised",
            "local_model",
            lambda payload: calls.append(payload) or {"output": "external leak"},
            network_required=False,
        ),
    )
    assert result["ok"] is False
    assert result["receipt"]["blocked_reason"] == "backend_capability_unverified"
    assert calls == []


def test_external_label_cannot_bypass_policy(tmp_path: Path) -> None:
    _write_policy(tmp_path, default="external_model", fallback="external_model")
    context = _context()
    calls = []
    result = AuraLocalInferenceGateway(tmp_path).run(
        _request(context, requested_backend_label="deepseek"),
        context_compiler=_compile(context),
        external_backend=BackendAdapter(
            "deepseek",
            "external",
            lambda payload: calls.append(payload) or {"output": "bad"},
            network_required=True,
        ),
        capability_validator=lambda *_: True,
    )
    assert result["ok"] is False
    assert result["receipt"]["blocked_reason"] == "external_backend_forbidden_by_policy"
    assert calls == []


def test_model_call_budget_carries_across_retries_on_gateway_instance(tmp_path: Path) -> None:
    _write_policy(
        tmp_path,
        default="local_model",
        fallback="local_model",
        maximum_model_calls=1,
        escalation_requires=[],
    )
    context = _context()
    gateway = AuraLocalInferenceGateway(tmp_path)
    calls = []
    local = BackendAdapter(
        "fake-local-v1",
        "local_model",
        lambda payload: calls.append(payload) or {"satisfied": False, "reason": "nope"},
    )
    request = _request(context)

    first = gateway.run(
        request,
        context_compiler=_compile(context),
        local_backend=local,
        capability_validator=_trusted_fixture,
    )
    assert first["receipt"]["model_call_count"] == 1
    assert first["receipt"]["selected_backend_id"] == "fake-local-v1"

    second = gateway.run(
        request,
        context_compiler=_compile(context),
        local_backend=local,
        capability_validator=_trusted_fixture,
    )
    assert second["receipt"]["blocked_reason"] == "maximum_model_calls_exhausted"
    assert second["receipt"]["model_call_count"] == 1
    assert len(calls) == 1


def test_failed_model_call_receipt_attributes_backend(tmp_path: Path) -> None:
    _write_policy(
        tmp_path,
        default="local_model",
        fallback="local_model",
        escalation_requires=[],
    )
    context = _context()
    result = AuraLocalInferenceGateway(tmp_path).run(
        _request(context),
        context_compiler=_compile(context),
        local_backend=BackendAdapter(
            "fake-local-v1",
            "local_model",
            lambda _: (_ for _ in ()).throw(RuntimeError("boom")),
            artifact_ref="fixture://local-v1",
        ),
        capability_validator=_trusted_fixture,
    )
    assert result["ok"] is False
    assert result["receipt"]["blocked_reason"] == "backend_call_failed"
    assert result["receipt"]["selected_backend_id"] == "fake-local-v1"
    assert result["receipt"]["selected_backend_class"] == "local_model"
    assert result["receipt"]["backend_artifact_ref"] == "fixture://local-v1"
    assert result["receipt"]["model_call_count"] == 1


@pytest.mark.parametrize(
    "output",
    [
        {"not-json": {object()}},
        {1: "a", "2": "b"},
        float("nan"),
    ],
)
def test_noncanonical_backend_output_fails_closed(tmp_path: Path, output) -> None:
    _write_policy(tmp_path)
    context = _context()
    result = AuraLocalInferenceGateway(tmp_path).run(
        _request(context),
        context_compiler=_compile(context),
        deterministic_backend=BackendAdapter(
            "det-v1",
            "deterministic",
            lambda _: {"output": output},
        ),
    )
    assert result["ok"] is False
    assert result["receipt"]["blocked_reason"] == "backend_output_not_canonicalizable"
    assert result["receipt"]["output_digest"] is None


def test_receipt_digests_change_with_protected_request_but_not_same_output(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    context = _context()
    gateway = AuraLocalInferenceGateway(tmp_path)
    backend = BackendAdapter("det-v1", "deterministic", lambda _: {"output": "same"})

    one = gateway.run(
        _request(context, request_id="R1"),
        context_compiler=_compile(context),
        deterministic_backend=backend,
    )
    two = gateway.run(
        _request(context, request_id="R2"),
        context_compiler=_compile(context),
        deterministic_backend=backend,
    )
    assert one["receipt"]["request_digest"] != two["receipt"]["request_digest"]
    assert one["receipt"]["output_digest"] == two["receipt"]["output_digest"]


def test_p0_uses_injected_callbacks_and_candidate_only_effect(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    context = _context()
    observed = {}

    result = AuraLocalInferenceGateway(tmp_path).run(
        _request(context),
        context_compiler=_compile(context),
        deterministic_backend=BackendAdapter(
            "det-v1",
            "deterministic",
            lambda payload: observed.update(payload) or {"output": "bounded"},
        ),
    )
    assert result["ok"] is True
    assert observed["effect_state"] == "CANDIDATE_ONLY"
    assert observed["policy"]["external_allowed"] is False
    assert observed["context"]["content"] == "bounded exact slice"
