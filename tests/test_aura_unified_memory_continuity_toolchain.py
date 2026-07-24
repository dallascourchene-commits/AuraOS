from __future__ import annotations

import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
import time
from typing import Any

import pytest

from aura_agent_arena_mcp import TOOL_DEFINITIONS, handle_request
from aura_architect_council_v2 import profile_refactor_length
from aura_architect_council_v3 import _selection_reasons, select_critic_lanes
from aura_architect_loop import ACT_CAPSULE_VERSION, ActCapsule
from aura_event_contracts import stable_digest
from aura_model_cognome import ModelEndpointIdentity
from aura_unified_memory_continuity_toolchain import (
    PATCH_AUTHORITY,
    UnifiedExecutionBinding,
    _authority,
    _semantics,
    compile_bridge_execution_binding,
)


def _run(root: Path, *args: str) -> str:
    result = subprocess.run(
        [*args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return result.stdout.strip()


def _repo(root: Path) -> str:
    (root / ".aura").mkdir(parents=True)
    (root / "pkg").mkdir()
    (root / "tests").mkdir()
    (root / ".aura" / "CODEMAP.json").write_text('{"version": 1}', encoding="utf-8")
    (root / "pkg" / "router.py").write_text(
        "def route_failure():\n    return 'retained'\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_router.py").write_text(
        "def test_route_failure():\n    assert True\n",
        encoding="utf-8",
    )
    _run(root, "git", "init")
    _run(root, "git", "config", "user.email", "tests@example.com")
    _run(root, "git", "config", "user.name", "AuraOS Tests")
    _run(root, "git", "add", ".")
    _run(root, "git", "commit", "-m", "fixture")
    return _run(root, "git", "rev-parse", "HEAD")


class _Bridge:
    def __init__(self, root: Path) -> None:
        self.repo_root = root
        capsule = ActCapsule(
            capsule_version=ACT_CAPSULE_VERSION,
            task_id="A1",
            role="bounded_builder",
            objective="Preserve exact unified continuity evidence",
            target_file="pkg/router.py",
            target_symbol="route_failure",
            related_files=[],
            acceptance="Focused tests pass.",
            escalate_if=["scope expands"],
            constraints=["preserve canonical owners"],
        )
        plan = SimpleNamespace(act_capsules=[capsule])
        self._session = {"prepared": SimpleNamespace(plan=plan)}

    def _require_session(self, _phase_hash: str) -> dict[str, Any]:
        return self._session

    def aura_get_micro_context(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "target_file": "pkg/router.py",
            "target_symbol": "route_failure",
            "line_ranges": [
                {
                    "file": "pkg/router.py",
                    "symbol": "route_failure",
                    "line_range": [1, 2],
                }
            ],
            "tests": ["tests/test_router.py"],
            "route_decision": {"route": "BUILDER_PATCH"},
        }


def _contract(head: str, *, now: float | None = None) -> dict[str, Any]:
    observed = time.time() if now is None else now
    endpoint = ModelEndpointIdentity.create(
        provider="test-provider",
        requested_model="test-model",
        returned_model="test-model",
        base_url_digest=stable_digest({"base_url": "local"}),
        access_class="BLACK_BOX",
        endpoint_fingerprint=stable_digest({"endpoint": "local-test"}),
        fingerprint_version="identity-v1",
        provider_revision="r1",
        tokenizer_family="test",
        price_snapshot_digest=stable_digest({"price": 0}),
        first_seen_at=observed - 120,
        last_seen_at=observed - 60,
        status="ACTIVE",
    )
    return {
        "expected_repository_head": head,
        "purpose": "Bind exact model-relative execution to prepared evidence",
        "user_meaning": "Do not create a second memory or authority plane",
        "authority": {"inspect": True, "edit": True, "test": True},
        "semantic_definitions": [
            {
                "term": term,
                "means": [f"governed {term}"],
                "does_not_mean": [f"automatic {term} authority"],
                "source_refs": [f"test:{term}"],
            }
            for term in ("memory", "continuity", "verified", "authority")
        ],
        "model_profile": {
            "endpoint_identity": endpoint.to_dict(),
            "calibrated_at": observed - 60,
            "expires_at": observed + 60,
            "evidence_refs": ["test:model-profile"],
            "uncertainty": 0.1,
        },
        "provider_config_digest": stable_digest({"provider": "test-provider"}),
        "observed_at": observed,
    }


def _compile(tmp_path: Path, contract: dict[str, Any]) -> UnifiedExecutionBinding:
    return compile_bridge_execution_binding(
        _Bridge(tmp_path),
        plan_phase_hash="phase-1",
        task_id="A1",
        contract=contract,
    )


def test_authority_omission_fails_closed() -> None:
    assert _authority(None).to_dict() == {
        "inspect": False,
        "edit": False,
        "test": False,
        "commit": False,
        "publish_pr": False,
        "merge": False,
        "production_mutation": False,
    }


def test_successful_binding_uses_exact_head_and_canonical_owners(tmp_path: Path) -> None:
    head = _repo(tmp_path)
    binding = _compile(tmp_path, _contract(head))
    assert binding.task_id == "A1"
    assert binding.records["model_execution_packet"]["repository_head"] == head
    assert binding.authority["patch_authority"] == PATCH_AUTHORITY
    assert binding.authority["automatic_merge"] is False


def test_missing_expected_head_rejected_before_capsule_lookup(tmp_path: Path) -> None:
    head = _repo(tmp_path)
    contract = _contract(head)
    contract.pop("expected_repository_head")
    with pytest.raises(ValueError, match="expected_repository_head must not be empty"):
        _compile(tmp_path, contract)


def test_head_mismatch_rejected(tmp_path: Path) -> None:
    head = _repo(tmp_path)
    contract = _contract(head)
    contract["expected_repository_head"] = "0" * 40
    with pytest.raises(ValueError, match="differs from exact current head"):
        _compile(tmp_path, contract)


def test_expired_model_profile_rejected(tmp_path: Path) -> None:
    head = _repo(tmp_path)
    observed = time.time()
    contract = _contract(head, now=observed)
    contract["model_profile"]["expires_at"] = observed - 1
    with pytest.raises(ValueError, match="Model Cognome profile is not current"):
        _compile(tmp_path, contract)


def test_malformed_semantic_definitions_rejected() -> None:
    with pytest.raises(ValueError, match="means must not be empty"):
        _semantics(
            [
                {
                    "term": "memory",
                    "means": [],
                    "source_refs": ["test:memory"],
                }
            ]
        )


def test_binding_digest_cannot_replay_across_tasks() -> None:
    authority = {
        "patch_authority": PATCH_AUTHORITY,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "automatic_promotion": False,
        "production_mutation": False,
        "model_vote_authority": False,
    }
    records = {"intent_packet": {"intent_digest": "intent"}}
    owners = {"bridge": "aura_agent_arena_bridge.AuraAgentArenaBridge"}
    first_identity = {
        "plan_phase_hash": "phase",
        "task_id": "A1",
        "records": records,
        "owner_refs": owners,
        "authority": authority,
    }
    first_digest = stable_digest(first_identity)
    first = UnifiedExecutionBinding(
        "phase",
        "A1",
        records,
        owners,
        authority,
        first_digest,
        f"umcbind_{first_digest}",
    )
    with pytest.raises(ValueError, match="identity mismatch"):
        UnifiedExecutionBinding(
            "phase",
            "A2",
            records,
            owners,
            authority,
            first.binding_digest,
            first.binding_id,
        )


def test_council_depth_is_bounded_for_malformed_input() -> None:
    candidate = {
        "candidate_id": "candidate-1",
        "plan": {"tasks": []},
        "unified_memory_continuity": {"required_verification_depth": "high"},
    }
    assert select_critic_lanes(candidate) == ["scope", "tests"]
    reasons = _selection_reasons(profile_refactor_length(candidate["plan"]), candidate)
    assert "cross_model_disagreement_requires_deeper_verification" not in reasons


def test_council_routes_continuity_and_rollback_from_valid_binding() -> None:
    candidate = {
        "candidate_id": "candidate-2",
        "plan": {"tasks": []},
        "unified_memory_continuity": {
            "required_verification_depth": 2,
            "disagreement_refs": ["model:a-vs-b"],
            "p0_required": True,
        },
    }
    lanes = select_critic_lanes(candidate)
    assert "continuity" in lanes
    assert "rollback" in lanes


class _ProjectionBridge:
    def aura_unified_continuity_projection(self, **kwargs: Any) -> dict[str, Any]:
        return {"ok": True, **kwargs, "production_mutation": False}


def test_projection_is_exposed_through_mcp() -> None:
    names = {item["name"] for item in TOOL_DEFINITIONS}
    assert "aura_unified_continuity_projection" in names
    response = handle_request(
        _ProjectionBridge(),
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "aura_unified_continuity_projection",
                "arguments": {"plan_phase_hash": "phase-1", "task_id": "A1"},
            },
        },
    )
    assert response is not None
    result = json.loads(response["result"]["content"][0]["text"])
    assert result == {
        "ok": True,
        "plan_phase_hash": "phase-1",
        "task_id": "A1",
        "production_mutation": False,
    }
