from __future__ import annotations

import json
from pathlib import Path

from aura_local_inference_gateway import (
    AuraLocalInferenceGateway,
    BackendAdapter,
    InferenceRequestV1,
)


POLICY_REF = ".aura/model_policies/local_first.v1.json"


def _write_policy(root: Path, *, maximum_model_calls: int = 2) -> None:
    path = root / POLICY_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "AURA_MODEL_POLICY_V1",
                "component_id": "local_first.v1",
                "kind": "model_policy",
                "default": "no_model",
                "fallback": "local_model",
                "external_allowed": False,
                "maximum_model_calls": maximum_model_calls,
                "escalation_requires": [
                    "local_attempt_failed",
                    "budget_available",
                    "expected_quality_gain",
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _request() -> InferenceRequestV1:
    return InferenceRequestV1(
        request_id="REQ-HARDEN",
        objective_id="OBJ-HARDEN",
        policy_ref=POLICY_REF,
        context_slice_digest="CTX-HARDEN",
        source_refs=("SRC-1",),
        currentness_refs=("CUR-1",),
        authority_refs=("AUTH-1",),
        privacy_refs=("PRIV-1",),
        reopen_refs=("REOPEN-1",),
    )


def test_policy_movement_during_context_compilation_blocks_before_backend_effect(
    tmp_path: Path,
) -> None:
    _write_policy(tmp_path)
    backend_calls = []

    def moving_context(request: InferenceRequestV1):
        _write_policy(tmp_path, maximum_model_calls=1)
        return {
            "context_slice_digest": request.context_slice_digest,
            "content": "bounded exact slice",
        }

    result = AuraLocalInferenceGateway(tmp_path).run(
        _request(),
        context_compiler=moving_context,
        deterministic_backend=BackendAdapter(
            "det-v1",
            "deterministic",
            lambda payload: backend_calls.append(payload) or {"output": "must not run"},
        ),
    )

    assert result["ok"] is False
    assert result["receipt"]["blocked_reason"] == "policy_digest_mismatch"
    assert result["receipt"]["model_call_count"] == 0
    assert backend_calls == []


def test_noncanonical_backend_output_fails_closed_without_string_coercion(
    tmp_path: Path,
) -> None:
    _write_policy(tmp_path)

    result = AuraLocalInferenceGateway(tmp_path).run(
        _request(),
        context_compiler=lambda request: {
            "context_slice_digest": request.context_slice_digest,
            "content": "bounded exact slice",
        },
        deterministic_backend=BackendAdapter(
            "det-v1",
            "deterministic",
            lambda _: {"output": {"not-json": {object()}}},
        ),
    )

    assert result["ok"] is False
    assert result["receipt"]["blocked_reason"] == "backend_output_not_canonicalizable"
    assert result["receipt"]["output_digest"] is None
    assert result["output"] is None
