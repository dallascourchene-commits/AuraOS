from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

from aura_local_inference_gateway import (
    BackendCapabilityV1,
    BackendResultV1,
    CompiledContextV1,
    DeterministicBackend,
    ExternalBackendForTest,
    FakeLocalBackend,
    InferenceRequestV1,
    LocalInferenceGateway,
    ModelPolicyResolver,
    request_from_route_capsule,
)

POLICY_REF = ".aura/model_policies/local_first.v1.json"
PRIVACY_EXCLUSIONS = ("unrelated_sessions", "secrets", "hidden_reasoning")


def _write_policy(tmp_path: Path, **overrides) -> str:
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
    target = tmp_path / POLICY_REF
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return hashlib.sha256(target.read_bytes()).hexdigest()


def _context(**overrides) -> CompiledContextV1:
    values = {
        "source_refs": ("source:alpha@1",),
        "currentness_refs": ("currentness:alpha@1",),
        "authority_refs": ("authority:read-only",),
        "privacy_refs": ("privacy:coding-localize",),
        "reopen_refs": ("reopen:source-move",),
        "privacy_exclusions": PRIVACY_EXCLUSIONS,
        "payload": {"slice": "bounded", "included_classes": []},
    }
    values.update(overrides)
    return CompiledContextV1(**values)


def _request(**overrides) -> InferenceRequestV1:
    values = {
        "request_id": "REQ-1",
        "objective": "answer from the bounded source slice",
        "model_policy_ref": POLICY_REF,
        "required_privacy_exclusions": PRIVACY_EXCLUSIONS,
    }
    values.update(overrides)
    return InferenceRequestV1(**values)


def _gateway(
    tmp_path: Path,
    *,
    deterministic_output: str | None = "deterministic",
    local_available: bool = True,
    context: CompiledContextV1 | None = None,
    extra_backends=(),
):
    deterministic = DeterministicBackend(lambda _request, _context: deterministic_output)
    local = FakeLocalBackend(lambda _request, _context: "local", available=local_available)
    compiled = context or _context()
    gateway = LocalInferenceGateway(
        policy_resolver=ModelPolicyResolver(tmp_path),
        context_compiler=lambda _request: compiled,
        backends=[deterministic, local, *extra_backends],
    )
    return gateway, deterministic, local, compiled


def test_t01_no_model_default_uses_no_model_and_zero_model_calls(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    gateway, _, local, _ = _gateway(tmp_path)
    receipt = gateway.run(_request())
    assert receipt["status"] == "SATISFIED"
    assert receipt["backend"]["backend_class"] == "no_model"
    assert receipt["model_calls"] == 0
    assert local.call_count == 0


def test_t02_local_fallback_requires_available_bound_capability(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    gateway, _, local, _ = _gateway(tmp_path, deterministic_output=None)
    receipt = gateway.run(_request())
    assert receipt["status"] == "SATISFIED"
    assert receipt["backend"]["backend_class"] == "local_model"
    assert receipt["model_calls"] == 1
    assert local.call_count == 1

    blocked_gateway, _, blocked_local, _ = _gateway(
        tmp_path,
        deterministic_output=None,
        local_available=False,
    )
    blocked = blocked_gateway.run(_request(request_id="REQ-2"))
    assert blocked["status"] == "BLOCKED_NO_ELIGIBLE_BACKEND"
    assert blocked_local.call_count == 0


def test_t03_external_label_cannot_override_external_false(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    external = ExternalBackendForTest()
    gateway, _, _, _ = _gateway(tmp_path, extra_backends=(external,))
    receipt = gateway.run(_request(backend_hint="external_model"))
    assert receipt["status"] == "BLOCKED_POLICY_EXTERNAL_FORBIDDEN"
    assert external.call_count == 0


def test_t04_provider_materialize_request_does_not_grant_authority(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    materialize = tmp_path / ".aura/PROVIDER_ROUTING_MATERIALIZE_REQUEST"
    materialize.parent.mkdir(parents=True, exist_ok=True)
    materialize.write_text("provider=deepseek\n", encoding="utf-8")
    external = ExternalBackendForTest()
    gateway, _, _, _ = _gateway(tmp_path, extra_backends=(external,))
    receipt = gateway.run(_request(backend_hint="external_model"))
    assert receipt["status"] == "BLOCKED_POLICY_EXTERNAL_FORBIDDEN"
    assert receipt["provider_authority"] is False
    assert external.call_count == 0


def test_t05_malformed_or_unknown_policy_fails_closed(tmp_path: Path) -> None:
    _write_policy(tmp_path, unexpected=True)
    gateway, _, _, _ = _gateway(tmp_path)
    receipt = gateway.run(_request())
    assert receipt["status"] == "BLOCKED_POLICY_INVALID"
    assert "policy_unknown_fields" in receipt["details"]["error"]


def test_t06_policy_digest_move_blocks_stale_decision(tmp_path: Path) -> None:
    original_digest = _write_policy(tmp_path)
    _write_policy(tmp_path, maximum_model_calls=1)
    gateway, _, _, _ = _gateway(tmp_path)
    receipt = gateway.run(_request(expected_policy_sha256=original_digest))
    assert receipt["status"] == "BLOCKED_STALE_POLICY"
    assert receipt["production_mutation"] is False


def test_t07_backend_switch_preserves_context_identity(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    context = _context()
    deterministic_gateway, _, _, _ = _gateway(tmp_path, context=context)
    local_gateway, _, _, _ = _gateway(tmp_path, deterministic_output=None, context=context)
    deterministic = deterministic_gateway.run(_request(request_id="REQ-D"))
    local = local_gateway.run(_request(request_id="REQ-L"))
    assert deterministic["context_digest"] == local["context_digest"] == context.digest
    assert deterministic["backend"]["backend_class"] == "no_model"
    assert local["backend"]["backend_class"] == "local_model"
    assert deterministic["backend_capability_digest"] != local["backend_capability_digest"]


def test_t08_backend_switch_never_mutates_source_or_authority_context(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    context = _context()
    before = context.protected_dict()
    gateway, _, _, _ = _gateway(tmp_path, deterministic_output=None, context=context)
    receipt = gateway.run(_request())
    assert receipt["status"] == "SATISFIED"
    assert context.protected_dict() == before
    assert context.source_refs == ("source:alpha@1",)
    assert context.authority_refs == ("authority:read-only",)


def test_t09_coordinate_proximity_never_substitutes_for_source_identity(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    context = _context(source_refs=())
    gateway, _, _, _ = _gateway(tmp_path, context=context)
    receipt = gateway.run(_request(coordinate_hint="0/1/2/nearby"))
    assert receipt["status"] == "BLOCKED_REQUIRED_EVIDENCE_UNRESOLVED"
    assert receipt["backend"] is None


def test_t10_privacy_exclusions_are_required_before_backend_use(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    context = _context(privacy_exclusions=("unrelated_sessions",))
    gateway, _, local, _ = _gateway(tmp_path, deterministic_output=None, context=context)
    receipt = gateway.run(_request())
    assert receipt["status"] == "BLOCKED_PRIVACY_EXCLUSIONS_INCOMPLETE"
    assert local.call_count == 0


def test_t10b_forbidden_context_class_blocks_even_if_exclusion_label_is_present(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    context = _context(payload={"included_classes": ["hidden_reasoning"]})
    gateway, _, _, _ = _gateway(tmp_path, context=context)
    receipt = gateway.run(_request())
    assert receipt["status"] == "BLOCKED_FORBIDDEN_CONTEXT_CLASS"


def test_t11_unknown_consequence_evidence_blocks_instead_of_prompt_drop(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    context = _context(currentness_refs=())
    gateway, _, local, _ = _gateway(tmp_path, deterministic_output=None, context=context)
    receipt = gateway.run(_request())
    assert receipt["status"] == "BLOCKED_REQUIRED_EVIDENCE_UNRESOLVED"
    assert local.call_count == 0


def test_t12_receipt_never_grants_patch_runtime_provider_or_human_authority(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    gateway, _, _, _ = _gateway(tmp_path)
    receipt = gateway.run(_request())
    assert receipt["production_mutation"] is False
    assert receipt["runtime_authority"] is False
    assert receipt["provider_authority"] is False
    assert receipt["human_gate"] is False
    assert receipt["effect_state"] == "NO_PRODUCTION_MUTATION"


def test_t13_usage_measurement_class_is_not_silently_upgraded(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    gateway, _, _, _ = _gateway(tmp_path, deterministic_output=None)
    receipt = gateway.run(_request())
    assert receipt["measurement_class"] == "MEASURED_FAKE"
    assert receipt["measurements"] == {"model_calls": 1}


def test_t14_protected_request_context_backend_and_output_digests_move_exactly(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    request = _request()
    changed_request = replace(request, objective="different objective")
    assert request.digest != changed_request.digest

    context = _context()
    changed_context = replace(context, source_refs=("source:beta@1",))
    assert context.digest != changed_context.digest

    gateway, _, _, _ = _gateway(tmp_path, context=context)
    receipt = gateway.run(request)
    changed_gateway, _, _, _ = _gateway(tmp_path, deterministic_output="different", context=context)
    changed_receipt = changed_gateway.run(request)
    assert receipt["context_digest"] == changed_receipt["context_digest"]
    assert receipt["output_digest"] != changed_receipt["output_digest"]
    assert receipt["receipt_digest"] != changed_receipt["receipt_digest"]


class _FailingLocalBackend:
    counts_as_model_call = True

    def __init__(self) -> None:
        self.call_count = 0
        self.capability = BackendCapabilityV1(
            backend_id="failing-local",
            backend_class="local_model",
            available=True,
            artifact_ref="fake://failure",
        )

    def invoke(self, _request, _context) -> BackendResultV1:
        self.call_count += 1
        raise RuntimeError("backend failed")


def test_t15_backend_failure_is_typed_and_never_falls_through_to_external(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    failing = _FailingLocalBackend()
    external = ExternalBackendForTest()
    gateway = LocalInferenceGateway(
        policy_resolver=ModelPolicyResolver(tmp_path),
        context_compiler=lambda _request: _context(),
        backends=[DeterministicBackend(lambda _request, _context: None), failing, external],
    )
    receipt = gateway.run(_request())
    assert receipt["status"] == "BLOCKED_NO_ELIGIBLE_BACKEND"
    assert receipt["details"]["attempts"][-1]["status"] == "FAILED_TYPED"
    assert failing.call_count == 1
    assert external.call_count == 0


def test_t16_bound_model_call_budget_is_enforced_before_local_call(tmp_path: Path) -> None:
    _write_policy(tmp_path, maximum_model_calls=0)
    gateway, _, local, _ = _gateway(tmp_path, deterministic_output=None)
    receipt = gateway.run(_request())
    assert receipt["status"] == "BLOCKED_NO_ELIGIBLE_BACKEND"
    assert receipt["details"]["attempts"][-1]["status"] == "BLOCKED_MODEL_CALL_BUDGET"
    assert local.call_count == 0


def test_t17_no_sufficient_backend_returns_explicit_blocked_unknown(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    gateway = LocalInferenceGateway(
        policy_resolver=ModelPolicyResolver(tmp_path),
        context_compiler=lambda _request: _context(),
        backends=[DeterministicBackend(lambda _request, _context: None)],
    )
    receipt = gateway.run(_request())
    assert receipt["status"] == "BLOCKED_NO_ELIGIBLE_BACKEND"
    assert receipt["output_digest"] is None


def test_t18_new_gateway_keeps_external_session_boundary_additive(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    import aura_external_llm_session as external_session

    assert external_session.VSA_PATCH_AUTHORITY is False
    assert external_session.PATCH_AUTHORITY == "exact_source_spans_and_hashes_only"
    gateway, _, _, _ = _gateway(tmp_path)
    receipt = gateway.run(_request())
    assert receipt["production_mutation"] is False


def test_t19_route_capsule_explicit_model_policy_ref_is_honored(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    route_capsule = {
        "capsule_id": "CODING.LOCALIZE.V1",
        "model_policy_ref": POLICY_REF,
    }
    request = request_from_route_capsule(
        route_capsule,
        request_id="REQ-CAPSULE",
        objective="localize bounded source",
        required_privacy_exclusions=PRIVACY_EXCLUSIONS,
    )
    assert request.model_policy_ref == POLICY_REF
    gateway, _, _, _ = _gateway(tmp_path)
    receipt = gateway.run(request)
    assert receipt["policy_ref"] == POLICY_REF
    assert receipt["status"] == "SATISFIED"


def test_t20_p0_path_performs_no_install_network_or_external_call(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    external = ExternalBackendForTest()
    gateway, _, local, _ = _gateway(tmp_path, extra_backends=(external,))
    receipt = gateway.run(_request())
    assert receipt["status"] == "SATISFIED"
    assert receipt["backend"]["backend_class"] == "no_model"
    assert receipt["backend"]["network_required"] is False
    assert local.call_count == 0
    assert external.call_count == 0
