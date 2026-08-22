from __future__ import annotations

import json
from pathlib import Path

import pytest

from aura_local_inference_gateway import (
    AuraLocalInferenceGateway,
    BackendAdapter,
    InferenceRequestV1,
    ModelPolicyResolver,
    PolicyResolutionError,
)


POLICY_REF = ".aura/model_policies/local_first.v1.json"


def _write_policy(root: Path, **overrides) -> str:
    policy_dir = root / ".aura" / "model_policies"
    policy_dir.mkdir(parents=True, exist_ok=True)
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
    path = root / POLICY_REF
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return POLICY_REF


def _request(**overrides) -> InferenceRequestV1:
    values = {
        "request_id": "REQ-1",
        "objective_id": "OBJ-1",
        "policy_ref": POLICY_REF,
        "context_slice_digest": "CTX-1",
        "source_refs": ("SRC-1",),
        "currentness_refs": ("CUR-1",),
        "authority_refs": ("AUTH-1",),
        "privacy_refs": ("PRIV-1",),
        "reopen_refs": ("REOPEN-1",),
    }
    values.update(overrides)
    return InferenceRequestV1(**values)


def _context(request: InferenceRequestV1):
    return {
        "context_slice_digest": request.context_slice_digest,
        "content": "bounded exact slice",
        "source_refs": list(request.source_refs),
    }


def test_policy_resolver_reads_exact_local_first_policy(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    decision = ModelPolicyResolver(tmp_path).resolve(POLICY_REF)

    assert decision.default == "no_model"
    assert decision.fallback == "local_model"
    assert decision.external_allowed is False
    assert decision.maximum_model_calls == 2
    assert decision.allowed_backend_classes == ("deterministic", "local_model")
    assert decision.policy_blob_digest
    assert decision.currentness == "CURRENT_AT_RESOLUTION"


@pytest.mark.parametrize(
    ("mutator", "code"),
    [
        (lambda p: p.pop("default"), "policy_missing_required_fields"),
        (lambda p: p.__setitem__("schema_version", "UNKNOWN"), "policy_schema_unknown"),
        (lambda p: p.__setitem__("external_allowed", "false"), "policy_external_allowed_must_be_bool"),
        (lambda p: p.__setitem__("maximum_model_calls", -1), "policy_maximum_model_calls_invalid"),
        (lambda p: p.__setitem__("mystery_permission", True), "policy_unknown_fields"),
    ],
)
def test_policy_resolver_fails_closed_on_malformed_or_unknown_policy(
    tmp_path: Path,
    mutator,
    code: str,
) -> None:
    _write_policy(tmp_path)
    path = tmp_path / POLICY_REF
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutator(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PolicyResolutionError) as exc:
        ModelPolicyResolver(tmp_path).resolve(POLICY_REF)
    assert exc.value.code == code


def test_policy_resolver_rejects_traversal_and_digest_movement(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    resolver = ModelPolicyResolver(tmp_path)
    decision = resolver.resolve(POLICY_REF)

    with pytest.raises(PolicyResolutionError) as traversal:
        resolver.resolve("../secret.json")
    assert traversal.value.code == "policy_ref_outside_model_policy_root"

    path = tmp_path / POLICY_REF
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["maximum_model_calls"] = 1
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PolicyResolutionError) as moved:
        resolver.resolve(POLICY_REF, expected_blob_digest=decision.policy_blob_digest)
    assert moved.value.code == "policy_digest_mismatch"


def test_deterministic_default_satisfies_without_model_call(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    calls = []
    gateway = AuraLocalInferenceGateway(tmp_path)
    result = gateway.run(
        _request(),
        context_compiler=_context,
        deterministic_backend=BackendAdapter(
            "det-v1",
            "deterministic",
            lambda payload: calls.append(payload) or {"satisfied": True, "output": "exact"},
        ),
    )

    assert result["ok"] is True
    assert result["output"] == "exact"
    assert result["receipt"]["selected_backend_class"] == "deterministic"
    assert result["receipt"]["model_call_count"] == 0
    assert result["receipt"]["effect_state"] == "CANDIDATE_ONLY"
    assert len(calls) == 1


def test_local_fallback_requires_escalation_and_capability(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    gateway = AuraLocalInferenceGateway(tmp_path)
    deterministic = BackendAdapter(
        "det-v1",
        "deterministic",
        lambda _: {"satisfied": False, "reason": "local_attempt_failed"},
    )
    local_calls = []
    local = BackendAdapter(
        "fake-local",
        "local_model",
        lambda payload: local_calls.append(payload) or {"output": "local answer"},
        artifact_ref="fake://local-v1",
    )

    blocked = gateway.run(
        _request(),
        context_compiler=_context,
        deterministic_backend=deterministic,
        local_backend=local,
    )
    assert blocked["ok"] is False
    assert blocked["receipt"]["blocked_reason"] == "fallback_escalation_requirements_unsatisfied"
    assert local_calls == []

    allowed = gateway.run(
        _request(
            escalation_evidence=(
                "local_attempt_failed",
                "budget_available",
                "expected_quality_gain",
            )
        ),
        context_compiler=_context,
        deterministic_backend=deterministic,
        local_backend=local,
    )
    assert allowed["ok"] is True
    assert allowed["receipt"]["selected_backend_class"] == "local_model"
    assert allowed["receipt"]["model_call_count"] == 1
    assert allowed["receipt"]["backend_artifact_ref"] == "fake://local-v1"


def test_missing_local_capability_is_blocked_unknown(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    gateway = AuraLocalInferenceGateway(tmp_path)
    result = gateway.run(
        _request(
            escalation_evidence=(
                "local_attempt_failed",
                "budget_available",
                "expected_quality_gain",
            )
        ),
        context_compiler=_context,
        deterministic_backend=BackendAdapter(
            "det-v1",
            "deterministic",
            lambda _: {"satisfied": False},
        ),
    )

    assert result["ok"] is False
    assert result["status"] == "BLOCKED_UNKNOWN"
    assert result["receipt"]["blocked_reason"] == "backend_capability_missing"


def test_external_label_cannot_bypass_policy(tmp_path: Path) -> None:
    _write_policy(tmp_path, default="external_model", fallback="external_model")
    external_calls = []
    gateway = AuraLocalInferenceGateway(tmp_path)
    result = gateway.run(
        _request(requested_backend_label="deepseek"),
        context_compiler=_context,
        external_backend=BackendAdapter(
            "deepseek",
            "external",
            lambda payload: external_calls.append(payload) or {"output": "should not run"},
            network_required=True,
        ),
    )

    assert result["ok"] is False
    assert result["receipt"]["blocked_reason"] == "external_backend_forbidden_by_policy"
    assert external_calls == []


def test_materialization_or_provider_label_is_not_authority(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    (tmp_path / ".aura" / "PROVIDER_ROUTING_MATERIALIZE_REQUEST").write_text(
        "provider=deepseek",
        encoding="utf-8",
    )
    external_calls = []
    gateway = AuraLocalInferenceGateway(tmp_path)
    result = gateway.run(
        _request(requested_backend_label="deepseek"),
        context_compiler=_context,
        deterministic_backend=BackendAdapter(
            "det-v1",
            "deterministic",
            lambda _: {"output": "no model"},
        ),
        external_backend=BackendAdapter(
            "deepseek",
            "external",
            lambda payload: external_calls.append(payload) or {"output": "external"},
            network_required=True,
        ),
    )

    assert result["ok"] is True
    assert result["receipt"]["selected_backend_class"] == "deterministic"
    assert external_calls == []


def test_context_compiler_is_required_and_exact_digest_bound(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    gateway = AuraLocalInferenceGateway(tmp_path)
    backend = BackendAdapter("det-v1", "deterministic", lambda _: {"output": "ok"})

    missing = gateway.run(
        _request(),
        context_compiler=None,
        deterministic_backend=backend,
    )
    assert missing["receipt"]["blocked_reason"] == "context_compiler_required"

    mismatch = gateway.run(
        _request(),
        context_compiler=lambda _: {"context_slice_digest": "OTHER", "content": "x"},
        deterministic_backend=backend,
    )
    assert mismatch["receipt"]["blocked_reason"] == "context_slice_digest_mismatch"


def test_policy_digest_movement_between_selection_and_use_blocks(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    resolver = ModelPolicyResolver(tmp_path)
    digest = resolver.resolve(POLICY_REF).policy_blob_digest

    path = tmp_path / POLICY_REF
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["maximum_model_calls"] = 1
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = AuraLocalInferenceGateway(tmp_path).run(
        _request(expected_policy_digest=digest),
        context_compiler=_context,
        deterministic_backend=BackendAdapter(
            "det-v1",
            "deterministic",
            lambda _: {"output": "must not run"},
        ),
    )
    assert result["ok"] is False
    assert result["receipt"]["blocked_reason"] == "policy_digest_mismatch"


def test_backend_switch_preserves_request_and_context_identity(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    gateway = AuraLocalInferenceGateway(tmp_path)
    request = _request(
        escalation_evidence=(
            "local_attempt_failed",
            "budget_available",
            "expected_quality_gain",
        )
    )

    deterministic = gateway.run(
        request,
        context_compiler=_context,
        deterministic_backend=BackendAdapter(
            "det-v1",
            "deterministic",
            lambda _: {"output": "A"},
        ),
    )
    local = gateway.run(
        request,
        context_compiler=_context,
        deterministic_backend=BackendAdapter(
            "det-v1",
            "deterministic",
            lambda _: {"satisfied": False},
        ),
        local_backend=BackendAdapter(
            "fake-local",
            "local_model",
            lambda _: {"output": "B"},
        ),
    )

    assert deterministic["receipt"]["request_digest"] == local["receipt"]["request_digest"]
    assert deterministic["receipt"]["context_slice_digest"] == local["receipt"]["context_slice_digest"]
    assert deterministic["receipt"]["selected_backend_id"] != local["receipt"]["selected_backend_id"]
    assert deterministic["receipt"]["output_digest"] != local["receipt"]["output_digest"]


def test_backend_failure_never_falls_through_to_forbidden_external(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    external_calls = []
    result = AuraLocalInferenceGateway(tmp_path).run(
        _request(
            requested_backend_label="external",
            escalation_evidence=(
                "local_attempt_failed",
                "budget_available",
                "expected_quality_gain",
            ),
        ),
        context_compiler=_context,
        deterministic_backend=BackendAdapter(
            "det-v1",
            "deterministic",
            lambda _: {"satisfied": False},
        ),
        local_backend=BackendAdapter(
            "fake-local",
            "local_model",
            lambda _: (_ for _ in ()).throw(RuntimeError("boom")),
        ),
        external_backend=BackendAdapter(
            "external",
            "external",
            lambda payload: external_calls.append(payload) or {"output": "bad fallback"},
            network_required=True,
        ),
    )

    assert result["ok"] is False
    assert result["receipt"]["blocked_reason"] == "backend_call_failed"
    assert result["receipt"]["model_call_count"] == 1
    assert external_calls == []


def test_model_call_budget_zero_blocks_local_fallback(tmp_path: Path) -> None:
    _write_policy(tmp_path, maximum_model_calls=0)
    local_calls = []
    result = AuraLocalInferenceGateway(tmp_path).run(
        _request(
            escalation_evidence=(
                "local_attempt_failed",
                "budget_available",
                "expected_quality_gain",
            )
        ),
        context_compiler=_context,
        deterministic_backend=BackendAdapter(
            "det-v1",
            "deterministic",
            lambda _: {"satisfied": False},
        ),
        local_backend=BackendAdapter(
            "fake-local",
            "local_model",
            lambda payload: local_calls.append(payload) or {"output": "should not run"},
        ),
    )

    assert result["ok"] is False
    assert result["receipt"]["blocked_reason"] == "maximum_model_calls_exhausted"
    assert local_calls == []


def test_receipt_digests_change_with_protected_consequence_fields(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    gateway = AuraLocalInferenceGateway(tmp_path)
    backend = BackendAdapter("det-v1", "deterministic", lambda _: {"output": "same"})

    one = gateway.run(_request(request_id="R1"), context_compiler=_context, deterministic_backend=backend)
    two = gateway.run(_request(request_id="R2"), context_compiler=_context, deterministic_backend=backend)

    assert one["receipt"]["request_digest"] != two["receipt"]["request_digest"]
    assert one["receipt"]["output_digest"] == two["receipt"]["output_digest"]


def test_p0_uses_injected_callbacks_only_no_model_or_network_install(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    observed = {}

    def deterministic(payload):
        observed.update(payload)
        return {"output": "bounded"}

    result = AuraLocalInferenceGateway(tmp_path).run(
        _request(),
        context_compiler=_context,
        deterministic_backend=BackendAdapter("det-v1", "deterministic", deterministic),
    )

    assert result["ok"] is True
    assert observed["effect_state"] == "CANDIDATE_ONLY"
    assert observed["policy"]["external_allowed"] is False
    assert observed["context"]["content"] == "bounded exact slice"
