from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import subprocess
import time
from types import SimpleNamespace
from typing import Any

import pytest

import aura_unified_memory_continuity_learning as learning_runtime
from aura_agent_arena_bridge import AuraAgentArenaBridge
from aura_agent_arena_mcp import TOOL_DEFINITIONS, handle_request
from aura_architect_loop import ACT_CAPSULE_VERSION, ActCapsule
from aura_event_contracts import AuraEventEnvelope, ExactPayloadRef, stable_digest
from aura_model_cognome import ModelEndpointIdentity
from aura_qdkt_observations import GovernedRelationshipQDKTEventReceipt
from aura_unified_memory_continuity_learning import (
    CurrentReproofReceipt,
    HumanDispositionReceipt,
    bind_crucible_proposal,
    commit_bridge_prediction,
    compile_current_reproof,
    finalize_bridge_learning,
    observe_bridge_prediction,
)
from aura_unified_memory_continuity_toolchain import compile_bridge_execution_binding


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
    (root / ".aura" / "arena_routes").mkdir(parents=True)
    (root / "pkg").mkdir()
    (root / "tests").mkdir()
    (root / ".aura" / "CODEMAP.json").write_text('{"version": 1}', encoding="utf-8")
    (root / ".aura" / "arena_routes" / "test.json").write_text("{}", encoding="utf-8")
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
        self._session: dict[str, Any] = {
            "prepared": SimpleNamespace(plan=plan),
            "unified_execution_bindings": {},
            "unified_crucible_proposals": {},
            "unified_crucible_bindings": {},
            "unified_crucible_proposal_storage": {},
            "unified_prediction_packets": {},
            "unified_p1_observations": {},
            "unified_continuity_receipts": {},
            "unified_current_reproofs": {},
            "unified_human_dispositions": {},
            "unified_learning_decisions": {},
            "unified_relationship_experiences": {},
            "unified_qdkt_admissions": {},
            "unified_learning_results": {},
        }

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


def _binding_contract(head: str, observed: float) -> dict[str, Any]:
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
            "expires_at": observed + 300,
            "evidence_refs": ["test:model-profile"],
            "uncertainty": 0.1,
        },
        "provider_config_digest": stable_digest({"provider": "test-provider"}),
        "observed_at": observed,
    }


def _prepared(tmp_path: Path) -> tuple[_Bridge, float]:
    head = _repo(tmp_path)
    bridge = _Bridge(tmp_path)
    now = time.time()
    binding = compile_bridge_execution_binding(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        contract=_binding_contract(head, now),
    )
    bridge._session["unified_execution_bindings"]["A1"] = binding
    return bridge, now


def _prediction_contract(now: float, tmp_path: Path) -> dict[str, Any]:
    return {
        "current_state_digest": stable_digest({"state": "before"}),
        "prompt_runtime_digest": stable_digest({"prompt": "runtime"}),
        "proposed_transition": "retain verified failure evidence",
        "expected_state_delta": ["relationship evidence retained"],
        "expected_evidence": ["evidence:p1"],
        "expected_cost": {"tokens": 100, "seconds": 1.0},
        "expected_risk": ["stale source", "self verification"],
        "producer_id": "bounded-builder",
        "crucible_bound_at": now,
        "committed_at": now + 0.5,
        "crucible_proposal": _proposal(now),
        "storage": {"crucible_db_path": str(tmp_path / "crucible.db")},
    }


def _observation_contract(now: float, *, observer_id: str = "independent-verifier") -> dict[str, Any]:
    return {
        "observed_state_delta": ["relationship evidence retained"],
        "observed_evidence_refs": ["evidence:p1", "evidence:runtime"],
        "observed_cost": {"tokens": 90, "seconds": 0.8},
        "missing_measurements": [],
        "observer_id": observer_id,
        "observed_at": now + 1,
    }


def _proposal(now: float) -> dict[str, Any]:
    return {
        "proposal_id": "CPROP-u7-test",
        "run_id": "CRUN-u7-test",
        "candidate_id": "candidate-u7-test",
        "arena_id": "coding",
        "grammar_version": "test-v1",
        "manifest_path": ".aura/arena_routes/test.json",
        "manifest_digest": stable_digest({"manifest": "test"}),
        "state_before": "PENDING",
        "transition_id": "learn-from-verified-experience",
        "change_path": "soft_weight_profile.empirical_uncertainty",
        "current_value": 0.5,
        "proposed_value": 0.4,
        "validation": {
            "passed": True,
            "proposal_recommendation": "PROPOSE",
            "all_proposal_thresholds_met": True,
        },
        "proposal_thresholds": {"minimum": 1},
        "threshold_assessment": {"all_proposal_thresholds_met": True},
        "train_experience_ids": ["train-1"],
        "validation_experience_ids": ["validation-1"],
        "shadow_experience_ids": ["shadow-1"],
        "source_experience_digest": stable_digest({"experience": "u7"}),
        "created_at": now - 1,
    }


def _final_contract(tmp_path: Path, now: float, *, disposition: str = "APPROVED") -> dict[str, Any]:
    return {
        "human_disposition_requirement_ref": "disposition:required:u7",
        "error_class": "NONE",
        "prediction_error": [],
        "consequence_dimensions": ["correctness", "continuity"],
        "protected_pathways": ["exact source evidence", "human authority"],
        "mutation_budget": ["no automatic mutation"],
        "replay_burden": ["re-run focused verifier"],
        "raw_evidence_refs": ["evidence:p1", "evidence:runtime", "evidence:reproof"],
        "replacement_candidate_refs": [],
        "uncertainty": 0.1,
        "receipt_producer_id": "continuity-receipt-producer",
        "verifier_evidence_refs": ["evidence:p1"],
        "reproof_verifier_id": "independent-verifier",
        "reproof_evidence_refs": ["evidence:reproof"],
        "reproof_verified_at": now + 3,
        "disposition_actor_id": "community-review-board",
        "disposition_actor_type": "COMMUNITY",
        "human_disposition": disposition,
        "disposition_reason_ref": "decision:minutes:1",
        "disposition_created_at": now + 4,
        "relationship_recorded_at": now + 4.5,
        "relationship_id": "relationship:router-failure-retention",
        "relationship_digest": stable_digest({"relationship": "router-failure-retention"}),
        "outcome": "FAILURE",
        "source_refs": ["pkg/router.py", "tests/test_router.py"],
        "privacy_class": "PROJECT",
        "reason": "Verified failure evidence remains useful and bounded.",
        "purpose_compatible": True,
        "privacy_compatible": True,
        "consent_compatible": True,
        "sovereignty_compatible": True,
        "trace_id": "trace-u7",
        "qdkt_actor_id": "aura-governed-qdkt-adapter",
        "arena_id": "coding",
        "qdkt_created_at": now + 5,
        "storage": {
            "crucible_db_path": str(tmp_path / "crucible.db"),
            "experience_db_path": str(tmp_path / "experience.db"),
            "qdkt_event_root": str(tmp_path / "qdkt-events"),
            "attempt_archive_db_path": str(tmp_path / "attempts.db"),
        },
    }


def test_three_stage_lifecycle_reaches_governed_qdkt_without_crystallization(tmp_path: Path) -> None:
    bridge, now = _prepared(tmp_path)
    prediction = commit_bridge_prediction(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        contract=_prediction_contract(now, tmp_path),
    )
    observation = observe_bridge_prediction(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        observation=_observation_contract(now),
    )
    result = finalize_bridge_learning(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        contract=_final_contract(tmp_path, now),
    )
    assert prediction.committed_at < observation.observed_at
    assert result["learning_decision"]["eligible_for_relationship_experience"] is True
    assert result["relationship_storage"]["ok"] is True
    assert result["qdkt_admission"]["admitted"] is True
    assert result["qdkt_event_receipt"]["appended"] is True
    assert result["qdkt_event_receipt"]["automatic_crystallization"] is False
    assert result["attempt_archive"]["ok"] is True
    assert result["automatic_promotion"] is False


def test_p0_and_p1_are_first_write_only(tmp_path: Path) -> None:
    bridge, now = _prepared(tmp_path)
    prediction = commit_bridge_prediction(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        contract=_prediction_contract(now, tmp_path),
    )
    retained_prediction = bridge._session["unified_prediction_packets"]["A1"]
    with pytest.raises(ValueError, match="immutable P0 is already retained"):
        commit_bridge_prediction(
            bridge,
            plan_phase_hash="phase-1",
            task_id="A1",
            contract=_prediction_contract(now, tmp_path),
        )
    assert bridge._session["unified_prediction_packets"]["A1"] is retained_prediction
    assert retained_prediction == prediction

    observation = observe_bridge_prediction(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        observation=_observation_contract(now),
    )
    retained_observation = bridge._session["unified_p1_observations"]["A1"]
    with pytest.raises(ValueError, match="independent P1 observation is already retained"):
        observe_bridge_prediction(
            bridge,
            plan_phase_hash="phase-1",
            task_id="A1",
            observation=_observation_contract(now),
        )
    assert bridge._session["unified_p1_observations"]["A1"] is retained_observation
    assert retained_observation == observation


def test_finalize_is_first_write_only(tmp_path: Path) -> None:
    bridge, now = _prepared(tmp_path)
    commit_bridge_prediction(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        contract=_prediction_contract(now, tmp_path),
    )
    observe_bridge_prediction(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        observation=_observation_contract(now),
    )
    result = finalize_bridge_learning(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        contract=_final_contract(tmp_path, now),
    )
    retained_result = bridge._session["unified_learning_results"]["A1"]
    with pytest.raises(ValueError, match="governed learning result is already retained"):
        finalize_bridge_learning(
            bridge,
            plan_phase_hash="phase-1",
            task_id="A1",
            contract=_final_contract(tmp_path, now),
        )
    assert retained_result is result
    assert bridge._session["unified_learning_results"]["A1"] is retained_result


@pytest.mark.parametrize("missing_field", ["human_disposition", "disposition_actor_type"])
def test_mandatory_disposition_fields_fail_closed(tmp_path: Path, missing_field: str) -> None:
    bridge, now = _prepared(tmp_path)
    commit_bridge_prediction(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        contract=_prediction_contract(now, tmp_path),
    )
    observe_bridge_prediction(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        observation=_observation_contract(now),
    )
    contract = _final_contract(tmp_path, now)
    contract.pop(missing_field)
    with pytest.raises(ValueError, match=missing_field):
        finalize_bridge_learning(
            bridge,
            plan_phase_hash="phase-1",
            task_id="A1",
            contract=contract,
        )


def test_missing_crucible_storage_fails_with_governed_error(tmp_path: Path) -> None:
    bridge, now = _prepared(tmp_path)
    commit_bridge_prediction(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        contract=_prediction_contract(now, tmp_path),
    )
    observe_bridge_prediction(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        observation=_observation_contract(now),
    )
    bridge._session["unified_crucible_proposal_storage"].pop("A1")
    with pytest.raises(ValueError, match="lacks successful canonical storage"):
        finalize_bridge_learning(
            bridge,
            plan_phase_hash="phase-1",
            task_id="A1",
            contract=_final_contract(tmp_path, now),
        )


def test_governed_qdkt_receipt_rejects_sidecar_coherence_forgery(tmp_path: Path) -> None:
    bridge, now = _prepared(tmp_path)
    commit_bridge_prediction(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        contract=_prediction_contract(now, tmp_path),
    )
    observe_bridge_prediction(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        observation=_observation_contract(now),
    )
    result = finalize_bridge_learning(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        contract=_final_contract(tmp_path, now),
    )
    raw = result["qdkt_event_receipt"]
    payload_ref = ExactPayloadRef(**raw["payload_ref"])
    event_raw = dict(raw["event"])
    event_raw["parent_event_ids"] = tuple(event_raw["parent_event_ids"])
    event_raw["evidence_refs"] = tuple(event_raw["evidence_refs"])
    event = AuraEventEnvelope(**event_raw)
    receipt = GovernedRelationshipQDKTEventReceipt(
        projection=raw["projection"],
        payload_ref=payload_ref,
        event=event,
        appended=raw["appended"],
    )
    with pytest.raises(ValueError, match="byte count"):
        replace(receipt, payload_ref=replace(payload_ref, byte_count=payload_ref.byte_count + 1))
    with pytest.raises(ValueError, match="timestamps disagree"):
        replace(receipt, payload_ref=replace(payload_ref, created_at=payload_ref.created_at + 1))


def test_finalize_rejects_unappended_qdkt_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bridge, now = _prepared(tmp_path)
    commit_bridge_prediction(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        contract=_prediction_contract(now, tmp_path),
    )
    observe_bridge_prediction(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        observation=_observation_contract(now),
    )
    record_advisory = learning_runtime.record_relationship_experience_advisory

    def _report_unappended(*args: Any, **kwargs: Any) -> GovernedRelationshipQDKTEventReceipt:
        return replace(record_advisory(*args, **kwargs), appended=False)

    monkeypatch.setattr(
        learning_runtime,
        "record_relationship_experience_advisory",
        _report_unappended,
    )
    with pytest.raises(ValueError, match="governed QDKT event was not appended"):
        finalize_bridge_learning(
            bridge,
            plan_phase_hash="phase-1",
            task_id="A1",
            contract=_final_contract(tmp_path, now),
        )
    assert "A1" not in bridge._session["unified_learning_results"]


def test_denial_is_archived_without_relationship_or_qdkt_admission(tmp_path: Path) -> None:
    bridge, now = _prepared(tmp_path)
    commit_bridge_prediction(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        contract=_prediction_contract(now, tmp_path),
    )
    observe_bridge_prediction(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        observation=_observation_contract(now),
    )
    result = finalize_bridge_learning(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        contract=_final_contract(tmp_path, now, disposition="DENIED"),
    )
    assert result["learning_decision"]["eligible_for_relationship_experience"] is False
    assert result["relationship_experience"] is None
    assert result["qdkt_admission"]["admitted"] is False
    assert result["qdkt_event_receipt"] is None
    assert result["attempt_archive"]["ok"] is True
    assert result["attempt_archive"]["status"] == "FAILURE"


def test_p1_self_observation_fails_closed(tmp_path: Path) -> None:
    bridge, now = _prepared(tmp_path)
    commit_bridge_prediction(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        contract=_prediction_contract(now, tmp_path),
    )
    with pytest.raises(ValueError, match="cannot independently observe"):
        observe_bridge_prediction(
            bridge,
            plan_phase_hash="phase-1",
            task_id="A1",
            observation=_observation_contract(now, observer_id="bounded-builder"),
        )


def test_current_reproof_rejects_source_drift(tmp_path: Path) -> None:
    bridge, now = _prepared(tmp_path)
    commit_bridge_prediction(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        contract=_prediction_contract(now, tmp_path),
    )
    observe_bridge_prediction(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        observation=_observation_contract(now),
    )
    contract = _final_contract(tmp_path, now)
    (tmp_path / "pkg" / "router.py").write_text(
        "def route_failure():\n    return 'changed'\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="source digest"):
        finalize_bridge_learning(
            bridge,
            plan_phase_hash="phase-1",
            task_id="A1",
            contract=contract,
        )


def test_p0_must_follow_crucible_binding(tmp_path: Path) -> None:
    bridge, now = _prepared(tmp_path)
    contract = _prediction_contract(now, tmp_path)
    contract["committed_at"] = now
    with pytest.raises(ValueError, match="strictly after Crucible proposal binding"):
        commit_bridge_prediction(
            bridge,
            plan_phase_hash="phase-1",
            task_id="A1",
            contract=contract,
        )


def test_existing_canonical_crucible_proposal_is_reused_without_mutation(
    tmp_path: Path,
) -> None:
    from aura_crucible_store import CrucibleStore

    bridge, now = _prepared(tmp_path)
    proposal = _proposal(now)
    with CrucibleStore(tmp_path, db_path=tmp_path / "crucible.db") as store:
        stored = store.record_proposal(proposal)
        assert stored["ok"] is True
        before = store.get_proposal(proposal["proposal_id"])
    prediction = commit_bridge_prediction(
        bridge,
        plan_phase_hash="phase-1",
        task_id="A1",
        contract=_prediction_contract(now, tmp_path),
    )
    with CrucibleStore(tmp_path, db_path=tmp_path / "crucible.db") as store:
        after = store.get_proposal(proposal["proposal_id"])
    assert before == after
    binding = bridge._session["unified_crucible_bindings"]["A1"]
    assert binding.proposal_id == proposal["proposal_id"]
    assert binding.execution_binding_id == bridge._session["unified_execution_bindings"]["A1"].binding_id
    assert binding.bound_at < prediction.committed_at


def test_extended_outcomes_are_supported_by_relationship_owner(tmp_path: Path) -> None:
    from aura_relationship_experience import RelationshipExperienceObservation

    for outcome in ("SUPERSEDED", "EXPIRED", "CONTRADICTED"):
        item = RelationshipExperienceObservation.create(
            relationship_id=f"relationship:{outcome}",
            relationship_digest=stable_digest({"relationship": outcome}),
            repository_head="a" * 40,
            working_tree_digest=stable_digest({"tree": outcome}),
            valid_from_head="a" * 40,
            outcome=outcome,
            verifier_evidence_refs=["verifier:evidence"],
            receipt_refs=["receipt:evidence"],
            source_refs=["source:evidence"],
            current_source_digest=stable_digest({"source": outcome}),
            human_disposition="APPROVED",
            privacy_class="PROJECT",
            objective_digest=stable_digest({"objective": outcome}),
        )
        assert item.outcome.value == outcome


def test_bridge_and_mcp_expose_all_three_lifecycle_stages() -> None:
    names = {item["name"] for item in TOOL_DEFINITIONS}
    assert {
        "aura_commit_unified_prediction",
        "aura_observe_unified_prediction",
        "aura_finalize_unified_learning",
    }.issubset(names)

    class Stub:
        def aura_commit_unified_prediction(self, **kwargs: Any) -> dict[str, Any]:
            return {"ok": True, "stage": "P0", **kwargs}

    response = handle_request(
        Stub(),
        {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "aura_commit_unified_prediction",
                "arguments": {
                    "plan_phase_hash": "phase-1",
                    "task_id": "A1",
                    "contract": {"producer_id": "builder"},
                },
            },
        },
    )
    assert response is not None
    assert response["result"]["isError"] is False


def test_receipt_contracts_are_proposal_only() -> None:
    now = time.time()
    reproof_identity = {
        "continuity_receipt_ref": "continuity:1",
        "repository_head": "a" * 40,
        "source_digest": "source:1",
        "verifier_id": "verifier:1",
        "verifier_evidence_refs": ["evidence:1"],
        "verified_at": now,
    }
    reproof_digest = stable_digest(reproof_identity)
    reproof = CurrentReproofReceipt(
        reproof_id=f"reproof_current_{reproof_digest}",
        reproof_digest=reproof_digest,
        **reproof_identity,
    )
    disposition_identity = {
        "continuity_receipt_ref": "continuity:1",
        "current_reproof_ref": reproof.reproof_id,
        "actor_id": "community:1",
        "actor_type": "COMMUNITY",
        "disposition": "APPROVED",
        "reason_ref": "minutes:1",
        "created_at": now + 1,
    }
    disposition_digest = stable_digest(disposition_identity)
    disposition = HumanDispositionReceipt(
        disposition_id=f"disposition_{disposition_digest}",
        disposition_digest=disposition_digest,
        **disposition_identity,
    )
    assert reproof.promotion_authority is False
    assert disposition.promotion_authority is False
