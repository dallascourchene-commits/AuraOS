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
)

POLICY_REF = ".aura/model_policies/local_first.v1.json"
BASELINE_PRIVACY = ("unrelated_sessions", "secrets", "hidden_reasoning")


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
        "privacy_exclusions": BASELINE_PRIVACY,
        "payload": {"included_classes": [], "slice": {"id": "bounded"}},
    }
    values.update(overrides)
    return CompiledContextV1(**values)


def _request(**overrides) -> InferenceRequestV1:
    values = {
        "request_id": "REVIEW-REGRESSION",
        "objective": "exercise the bounded gateway",
        "model_policy_ref": POLICY_REF,
        "required_privacy_exclusions": BASELINE_PRIVACY,
    }
    values.update(overrides)
    return InferenceRequestV1(**values)


def _gateway(tmp_path: Path, *, context=None, backends=None) -> LocalInferenceGateway:
    compiled = context or _context()
    if backends is None:
        backends = [
            DeterministicBackend(lambda _request, _context: "deterministic"),
            FakeLocalBackend(lambda _request, _context: "local"),
        ]
    return LocalInferenceGateway(
        policy_resolver=ModelPolicyResolver(tmp_path),
        context_compiler=lambda _request: compiled,
        backends=backends,
    )


def test_r21_external_allowed_policy_still_cannot_execute_external_backend(tmp_path: Path) -> None:
    _write_policy(tmp_path, external_allowed=True)
    external = ExternalBackendForTest()
    gateway = _gateway(
        tmp_path,
        backends=[
            DeterministicBackend(lambda _request, _context: None),
            FakeLocalBackend(lambda _request, _context: "local", available=False),
            external,
        ],
    )

    blocked = gateway.run(_request())
    assert blocked["status"] == "BLOCKED_NO_ELIGIBLE_BACKEND"
    assert external.call_count == 0

    delegated = gateway.run(_request(backend_hint="external_model"))
    assert delegated["status"] == "BLOCKED_EXTERNAL_DELEGATION_REQUIRED"
    assert external.call_count == 0


def test_r22_policy_symlink_is_rejected_even_when_target_stays_in_repo(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    original = tmp_path / POLICY_REF
    elsewhere = tmp_path / "alternate-policy.json"
    elsewhere.write_bytes(original.read_bytes())
    original.unlink()
    original.symlink_to(elsewhere)

    receipt = _gateway(tmp_path).run(_request())
    assert receipt["status"] == "BLOCKED_POLICY_INVALID"
    assert "policy_symlink_forbidden" in receipt["details"]["error"]


def test_r23_unsupported_or_nonfinite_context_identity_fails_closed(tmp_path: Path) -> None:
    _write_policy(tmp_path)

    unsupported = _context(payload={"included_classes": [], "bad": {"not", "json"}})
    unsupported_receipt = _gateway(tmp_path, context=unsupported).run(_request())
    assert unsupported_receipt["status"] == "BLOCKED_CONTEXT_UNAVAILABLE"

    nonfinite = _context(payload={"included_classes": [], "score": float("nan")})
    nonfinite_receipt = _gateway(tmp_path, context=nonfinite).run(_request())
    assert nonfinite_receipt["status"] == "BLOCKED_CONTEXT_UNAVAILABLE"


def test_r24_context_is_deep_frozen_before_backend_invocation(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    mutable_payload = {"included_classes": [], "nested": {"value": 1}}
    compiled = _context(payload=mutable_payload)

    class MutatingNoModel:
        counts_as_model_call = False

        def __init__(self) -> None:
            self.capability = BackendCapabilityV1("mutator", "no_model", True)

        def invoke(self, _request, context):
            context.payload["nested"]["value"] = 2
            return BackendResultV1(satisfied=True, output="mutated")

    receipt = _gateway(
        tmp_path,
        context=compiled,
        backends=[MutatingNoModel(), FakeLocalBackend(lambda _r, _c: "x", available=False)],
    ).run(_request())

    assert receipt["status"] == "BLOCKED_NO_ELIGIBLE_BACKEND"
    assert receipt["details"]["attempts"][0]["status"] == "FAILED_TYPED"
    assert mutable_payload["nested"]["value"] == 1


def test_r25_malformed_backend_result_is_typed_instead_of_raising(tmp_path: Path) -> None:
    _write_policy(tmp_path)

    class MalformedLocal:
        counts_as_model_call = True

        def __init__(self) -> None:
            self.calls = 0
            self.capability = BackendCapabilityV1("malformed", "local_model", True)

        def invoke(self, _request, _context):
            self.calls += 1
            return None

    malformed = MalformedLocal()
    receipt = _gateway(
        tmp_path,
        backends=[DeterministicBackend(lambda _r, _c: None), malformed],
    ).run(_request())

    assert receipt["status"] == "BLOCKED_NO_ELIGIBLE_BACKEND"
    assert receipt["details"]["attempts"][-1]["status"] == "FAILED_TYPED"
    assert receipt["model_calls"] == 1
    assert malformed.calls == 1


def test_r26_no_model_network_requirement_is_blocked_before_invoke(tmp_path: Path) -> None:
    _write_policy(tmp_path)

    class NetworkNoModel:
        counts_as_model_call = False

        def __init__(self) -> None:
            self.calls = 0
            self.capability = BackendCapabilityV1(
                "network-no-model",
                "no_model",
                True,
                network_required=True,
            )

        def invoke(self, _request, _context):
            self.calls += 1
            return BackendResultV1(satisfied=True, output="network")

    network = NetworkNoModel()
    receipt = _gateway(
        tmp_path,
        backends=[network, FakeLocalBackend(lambda _r, _c: "x", available=False)],
    ).run(_request())

    assert receipt["details"]["attempts"][0]["status"] == "BLOCKED_P0_BACKEND_REQUIRES_NETWORK"
    assert network.calls == 0


def test_r27_model_call_budget_is_derived_from_backend_class_not_adapter_flag(tmp_path: Path) -> None:
    _write_policy(tmp_path, maximum_model_calls=0)

    class MisdeclaredLocal:
        counts_as_model_call = False

        def __init__(self) -> None:
            self.calls = 0
            self.capability = BackendCapabilityV1("misdeclared-local", "local_model", True)

        def invoke(self, _request, _context):
            self.calls += 1
            return BackendResultV1(satisfied=True, output="should-not-run")

    local = MisdeclaredLocal()
    receipt = _gateway(
        tmp_path,
        backends=[DeterministicBackend(lambda _r, _c: None), local],
    ).run(_request())

    assert receipt["details"]["attempts"][-1]["status"] == "BLOCKED_MODEL_CALL_BUDGET"
    assert receipt["model_calls"] == 0
    assert local.calls == 0


def test_r28_malformed_request_sequence_still_returns_blocked_receipt(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    malformed = replace(_request(), required_evidence=None)

    receipt = _gateway(tmp_path).run(malformed)

    assert receipt["status"] == "BLOCKED_POLICY_INVALID"
    assert receipt["request_digest"]
    assert receipt["production_mutation"] is False


def test_r29_baseline_privacy_exclusions_are_mandatory_with_request_defaults(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    context = _context(privacy_exclusions=())
    request = InferenceRequestV1(
        request_id="DEFAULT-PRIVACY",
        objective="default privacy request",
        model_policy_ref=POLICY_REF,
    )

    receipt = _gateway(tmp_path, context=context).run(request)

    assert receipt["status"] == "BLOCKED_PRIVACY_EXCLUSIONS_INCOMPLETE"


def test_r30_blocked_receipt_preserves_model_calls_uncertainty_and_counterevidence(tmp_path: Path) -> None:
    _write_policy(tmp_path)

    class InsufficientLocal:
        counts_as_model_call = True

        def __init__(self) -> None:
            self.capability = BackendCapabilityV1("insufficient-local", "local_model", True)

        def invoke(self, _request, _context):
            return BackendResultV1(
                satisfied=False,
                uncertainty=("local-uncertain",),
                counterevidence=("local-counterevidence",),
                measurements={"model_calls": 1},
                measurement_class="MEASURED_FAKE",
            )

    receipt = _gateway(
        tmp_path,
        backends=[DeterministicBackend(lambda _r, _c: None), InsufficientLocal()],
    ).run(_request())

    assert receipt["status"] == "BLOCKED_NO_ELIGIBLE_BACKEND"
    assert receipt["model_calls"] == 1
    assert "deterministic_path_insufficient" in receipt["uncertainty"]
    assert "local-uncertain" in receipt["uncertainty"]
    assert receipt["counterevidence"] == ["local-counterevidence"]


def test_r31_nonfinite_capability_identity_is_blocked_before_invoke(tmp_path: Path) -> None:
    _write_policy(tmp_path)

    class BadCapability:
        counts_as_model_call = False

        def __init__(self) -> None:
            self.calls = 0
            self.capability = BackendCapabilityV1(
                "bad-capability",
                "no_model",
                True,
                resource_state={"load": float("inf")},
            )

        def invoke(self, _request, _context):
            self.calls += 1
            return BackendResultV1(satisfied=True, output="should-not-run")

    bad = BadCapability()
    receipt = _gateway(
        tmp_path,
        backends=[bad, FakeLocalBackend(lambda _r, _c: "x", available=False)],
    ).run(_request())

    assert receipt["details"]["attempts"][0]["status"] == "BLOCKED_CAPABILITY_INVALID"
    assert bad.calls == 0
