from __future__ import annotations

import json
from pathlib import Path

import pytest

from aura_local_inference_gateway import (
    AuraLocalInferenceGateway,
    BackendAdapter,
    BUDGET_LEASE_SCHEMA,
    CapabilityAttestationV1,
    InferenceRequestV1,
    canonical_context_digest,
)


POLICY_REF = ".aura/model_policies/local_first.v1.json"
CAP_OWNER = "fixture://capability-owner/v1"
BUDGET_OWNER = "fixture://budget-owner/v1"


def _write_policy(root: Path, *, maximum_model_calls: int = 2) -> None:
    path = root / POLICY_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "AURA_MODEL_POLICY_V1",
                "component_id": "local_first.v1",
                "kind": "model_policy",
                "default": "local_model",
                "fallback": "local_model",
                "external_allowed": False,
                "maximum_model_calls": maximum_model_calls,
                "escalation_requires": [],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _context() -> dict[str, object]:
    payload: dict[str, object] = {"content": "bounded exact slice", "source_refs": ["SRC-1"]}
    return {"context_slice_digest": canonical_context_digest(payload), **payload}


def _request(context: dict[str, object]) -> InferenceRequestV1:
    return InferenceRequestV1(
        request_id="REQ-R2",
        objective_id="OBJ-R2",
        policy_ref=POLICY_REF,
        context_slice_digest=str(context["context_slice_digest"]),
        source_refs=("SRC-1",),
        currentness_refs=("CUR-1",),
        authority_refs=("AUTH-1",),
        privacy_refs=("PRIV-1",),
        reopen_refs=("REOPEN-1",),
    )


def _attest(adapter: BackendAdapter, policy):
    return CapabilityAttestationV1(
        owner_ref=CAP_OWNER,
        capability_ref=adapter.capability_ref,
        backend_id=adapter.backend_id,
        backend_class=adapter.backend_class,
        policy_blob_digest=policy.policy_blob_digest,
    )


def _gateway(root: Path, budget_owner):
    return AuraLocalInferenceGateway(
        root,
        capability_owner_ref=CAP_OWNER,
        capability_attestor=_attest,
        budget_owner_ref=BUDGET_OWNER,
        model_call_budget_owner=budget_owner,
    )


def _local(calls: list[dict[str, object]]) -> BackendAdapter:
    return BackendAdapter(
        backend_id="fake-local-v1",
        backend_class="local_model",
        callback=lambda payload: calls.append(dict(payload)) or {"output": "ok"},
        artifact_ref="fixture://local-v1",
        capability_ref="fixture-capability/local-v1",
    )


def _exact_lease(request, policy, *, reservation_id: str, status: str, count: int) -> dict[str, object]:
    return {
        "schema_version": BUDGET_LEASE_SCHEMA,
        "owner_ref": BUDGET_OWNER,
        "reservation_id": reservation_id,
        "request_id": request.request_id,
        "objective_id": request.objective_id,
        "policy_blob_digest": policy.policy_blob_digest,
        "model_call_count": count,
        "maximum_model_calls": policy.maximum_model_calls,
        "status": status,
    }


def test_exhausted_unknown_field_fails_exact_shape_before_effect(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    context = _context()
    calls: list[dict[str, object]] = []

    def budget_owner(request, policy, adapter):
        del adapter
        lease = _exact_lease(
            request,
            policy,
            reservation_id="owner-exhausted-2",
            status="EXHAUSTED",
            count=policy.maximum_model_calls,
        )
        lease["authority_override"] = True
        return lease

    result = _gateway(tmp_path, budget_owner).run(
        _request(context),
        context_compiler=lambda _: dict(context),
        local_backend=_local(calls),
    )

    assert result["ok"] is False
    assert result["receipt"]["blocked_reason"] == "model_call_budget_lease_mismatch"
    assert calls == []


@pytest.mark.parametrize("reservation_mode", ["missing", "blank"])
def test_exhausted_requires_nonempty_owner_reservation_identity(
    tmp_path: Path,
    reservation_mode: str,
) -> None:
    _write_policy(tmp_path)
    context = _context()
    calls: list[dict[str, object]] = []

    def budget_owner(request, policy, adapter):
        del adapter
        lease = _exact_lease(
            request,
            policy,
            reservation_id="owner-exhausted-2",
            status="EXHAUSTED",
            count=policy.maximum_model_calls,
        )
        if reservation_mode == "missing":
            lease.pop("reservation_id")
        else:
            lease["reservation_id"] = "   "
        return lease

    result = _gateway(tmp_path, budget_owner).run(
        _request(context),
        context_compiler=lambda _: dict(context),
        local_backend=_local(calls),
    )

    assert result["ok"] is False
    assert result["receipt"]["blocked_reason"] == "model_call_budget_lease_mismatch"
    assert result["receipt"]["budget_reservation_id"] is None
    assert calls == []


def test_valid_exact_exhausted_retains_owner_reservation_and_zero_backend_effect(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    context = _context()
    calls: list[dict[str, object]] = []

    def budget_owner(request, policy, adapter):
        del adapter
        return _exact_lease(
            request,
            policy,
            reservation_id="owner-exhausted-2",
            status="EXHAUSTED",
            count=policy.maximum_model_calls,
        )

    result = _gateway(tmp_path, budget_owner).run(
        _request(context),
        context_compiler=lambda _: dict(context),
        local_backend=_local(calls),
    )

    assert result["ok"] is False
    assert result["receipt"]["blocked_reason"] == "maximum_model_calls_exhausted"
    assert result["receipt"]["budget_reservation_id"] == "owner-exhausted-2"
    assert result["receipt"]["model_call_count"] == 2
    assert calls == []


def test_reserved_exact_shape_still_allows_one_candidate_effect(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    context = _context()
    calls: list[dict[str, object]] = []

    def budget_owner(request, policy, adapter):
        del adapter
        return _exact_lease(
            request,
            policy,
            reservation_id="owner-lease-1",
            status="RESERVED",
            count=1,
        )

    result = _gateway(tmp_path, budget_owner).run(
        _request(context),
        context_compiler=lambda _: dict(context),
        local_backend=_local(calls),
    )

    assert result["ok"] is True
    assert result["receipt"]["budget_reservation_id"] == "owner-lease-1"
    assert result["receipt"]["model_call_count"] == 1
    assert len(calls) == 1
