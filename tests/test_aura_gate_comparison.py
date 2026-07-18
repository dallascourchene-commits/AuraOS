from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from aura_gate_comparison import (
    DERIVED,
    HUMAN_REVIEW_ONLY,
    VERIFIER_BACKED,
    AuraGateComparisonRunner,
    GateArmLineage,
    GateComparisonArm,
    GateComparisonAuthorizationStore,
)
from aura_model_cognome_execution_auth import ExecutionAuthorization

BOUNDS = {
    "objective_digest": "objective-1",
    "repository_digest": "repo-1",
    "plan_phase_hash": "plan-1",
    "required_gates": ["canonical_arena_verifier", "hotswap_readiness"],
    "budgets": {"max_calls": 2, "max_output_tokens": 2400},
}


class ArmHarness:
    def __init__(
        self,
        arm_id: str,
        profile_id: str,
        *,
        lineage_prefix: str | None = None,
        bounds: dict[str, Any] | None = None,
        measured: dict[str, int | float] | None = None,
        estimated: dict[str, int | float] | None = None,
        verifier_id: str = "verifier-1",
    ) -> None:
        prefix = lineage_prefix or arm_id
        self.arm_id = arm_id
        self.profile_id = profile_id
        self.bounds = dict(bounds or BOUNDS)
        self.measured = dict(measured or {"cost_usd": 1.0, "quality": 1.0})
        self.estimated = dict(estimated or {"input_tokens": 100})
        self.verifier_id = verifier_id
        self.provider_calls = 0
        self.start_calls = 0
        self.prepare_calls = 0
        self.execute_calls = 0
        self.fail_execute = False
        self.result_ok = True
        self.verification_complete = True
        self.measurement_class = VERIFIER_BACKED
        self.reported_promotion = False
        self.reported_production_mutation = False
        self.arm = GateComparisonArm(
            arm_id=arm_id,
            profile_id=profile_id,
            lineage=GateArmLineage(
                runtime_id=f"{prefix}-runtime",
                bridge_id=f"{prefix}-bridge",
                controlled_session_namespace_id=f"{prefix}-sessions",
                staging_root_id=f"{prefix}-staging",
                output_root_id=f"{prefix}-output",
            ),
            prepare=self.prepare,
            execute=self.execute,
            provider_call_count=lambda: self.provider_calls,
            start_call_count=lambda: self.start_calls,
        )

    def prepare(self) -> dict[str, Any]:
        self.prepare_calls += 1
        return {"bounds": self.bounds, "estimated": self.estimated}

    def execute(self) -> dict[str, Any]:
        self.execute_calls += 1
        self.start_calls += 1
        self.provider_calls += 1
        if self.fail_execute:
            raise RuntimeError("provider detail must not escape")
        return {
            "ok": self.result_ok,
            "measurement_class": self.measurement_class,
            "verifier_id": self.verifier_id,
            "verification_complete": self.verification_complete,
            "measured": self.measured,
            "estimated": self.estimated,
            "promotion_performed": self.reported_promotion,
            "production_mutation": self.reported_production_mutation,
        }


def authorization(
    *,
    profiles: tuple[str, ...] = ("profile-a", "profile-b"),
    purpose: str = "purpose-1",
    graph: str = "graph-1",
    policies: tuple[str, ...] = ("DIRECT",),
    verifier: str = "verifier-1",
    max_calls: int = 2,
) -> ExecutionAuthorization:
    return ExecutionAuthorization.create(
        approved_by="human-reviewer",
        verifier_id=verifier,
        purpose_digest=purpose,
        capability_graph_digest=graph,
        allowed_policy_modes=policies,
        allowed_profile_ids=profiles,
        nonce=f"nonce-{purpose}-{graph}-{max_calls}",
        issued_at=100.0,
        expires_at=200.0,
        max_calls=max_calls,
    )


def runner(tmp_path: Path) -> AuraGateComparisonRunner:
    return AuraGateComparisonRunner(GateComparisonAuthorizationStore(tmp_path / "comparison.sqlite3"))


def run_paired(
    actual_runner: AuraGateComparisonRunner,
    left: ArmHarness,
    right: ArmHarness,
    auth: ExecutionAuthorization,
    **overrides: Any,
) -> dict[str, Any]:
    values = {
        "purpose_digest": "purpose-1",
        "graph_digest": "graph-1",
        "policy_mode": "DIRECT",
        "verifier_id": "verifier-1",
        "consumer_id": "gate-worker-1",
        "now": 150.0,
        "preference_metric": "cost_usd",
    }
    values.update(overrides)
    return actual_runner.run_paired(
        left.arm,
        right.arm,
        authorization=auth,
        **values,
    )


def test_shadow_is_prepare_only_derived_evidence_with_zero_live_calls(tmp_path: Path) -> None:
    left = ArmHarness("arm-a", "profile-a", estimated={"cost_usd": 0.4})
    right = ArmHarness("arm-b", "profile-b", estimated={"cost_usd": 0.3})

    result = runner(tmp_path).run_shadow(left.arm, right.arm)

    assert result["ok"] is True
    assert result["measurement_class"] == DERIVED
    assert left.prepare_calls == right.prepare_calls == 1
    assert left.execute_calls == right.execute_calls == 0
    assert left.provider_calls == right.provider_calls == 0
    assert left.start_calls == right.start_calls == 0
    assert all(arm["measured"] == {} for arm in result["arms"])
    assert result["human_review_evidence"] == {
        "preferred_arm_id": None,
        "reason": "shadow_evidence_is_derived_only",
        "authority": HUMAN_REVIEW_ONLY,
    }
    assert result["promotion_performed"] is False


def test_paired_live_isolated_measured_evidence_can_name_review_preference(tmp_path: Path) -> None:
    left = ArmHarness("arm-a", "profile-a", measured={"cost_usd": 2.0, "quality": 0.9})
    right = ArmHarness("arm-b", "profile-b", measured={"cost_usd": 1.0, "quality": 0.9})
    actual_runner = runner(tmp_path)
    auth = authorization()

    result = run_paired(actual_runner, left, right, auth)

    assert result["ok"] is True
    assert result["comparison_complete"] is True
    assert left.execute_calls == right.execute_calls == 1
    assert left.provider_calls == right.provider_calls == 1
    assert left.start_calls == right.start_calls == 1
    assert result["arms"][0]["measurement_class"] == VERIFIER_BACKED
    assert result["arms"][0]["measured"] == {"cost_usd": 2.0, "quality": 0.9}
    assert result["arms"][0]["estimated"] == {"input_tokens": 100}
    assert result["human_review_evidence"]["preferred_arm_id"] == "arm-b"
    assert result["human_review_evidence"]["authority"] == HUMAN_REVIEW_ONLY
    assert result["promotion_performed"] is False
    assert actual_runner.authorization_store.consumption(auth.authorization_id) is not None


def test_paired_rejects_any_shared_mutable_lineage_before_preparation(tmp_path: Path) -> None:
    left = ArmHarness("arm-a", "profile-a", lineage_prefix="shared")
    right = ArmHarness("arm-b", "profile-b", lineage_prefix="shared")
    actual_runner = runner(tmp_path)
    auth = authorization()

    result = run_paired(actual_runner, left, right, auth)

    assert result["error"] == "paired_isolation_invalid"
    assert left.prepare_calls == right.prepare_calls == 0
    assert left.execute_calls == right.execute_calls == 0
    assert actual_runner.authorization_store.consumption(auth.authorization_id) is None
    assert result["human_review_evidence"]["preferred_arm_id"] is None


def test_paired_rejects_deserialized_authorization_mapping(tmp_path: Path) -> None:
    left = ArmHarness("arm-a", "profile-a")
    right = ArmHarness("arm-b", "profile-b")
    auth = authorization()

    result = runner(tmp_path).run_paired(
        left.arm,
        right.arm,
        authorization=auth.to_dict(),  # type: ignore[arg-type]
        purpose_digest="purpose-1",
        graph_digest="graph-1",
        policy_mode="DIRECT",
        verifier_id="verifier-1",
        consumer_id="gate-worker-1",
        now=150.0,
    )

    assert result["error"] == "paired_authorization_invalid"
    assert left.prepare_calls == right.prepare_calls == 0


def test_authorization_consumption_survives_restart_and_blocks_new_claim(tmp_path: Path) -> None:
    database = tmp_path / "comparison.sqlite3"
    auth = authorization()
    first = GateComparisonAuthorizationStore(database)

    assert first.consume(auth, claim={"comparison": "one"}, consumer_id="worker-a", consumed_at=150.0)

    restarted = GateComparisonAuthorizationStore(database)
    assert not restarted.consume(
        auth,
        claim={"comparison": "different"},
        consumer_id="worker-b",
        consumed_at=151.0,
    )
    record = restarted.consumption(auth.authorization_id)
    assert record is not None
    assert record["consumer_id"] == "worker-a"
    assert "comparison" not in record
    assert len(record["authorization_digest"]) == 64
    assert len(record["claim_digest"]) == 64


def test_transactional_consumption_allows_only_one_competing_consumer(tmp_path: Path) -> None:
    database = tmp_path / "comparison.sqlite3"
    stores = [GateComparisonAuthorizationStore(database), GateComparisonAuthorizationStore(database)]
    auth = authorization()

    def consume(index: int) -> bool:
        return stores[index].consume(
            auth,
            claim={"comparison": "same"},
            consumer_id=f"worker-{index}",
            consumed_at=150.0 + index,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(consume, (0, 1)))

    assert sorted(outcomes) == [False, True]


def test_runner_restart_replay_is_denied_before_any_second_live_call(tmp_path: Path) -> None:
    database = tmp_path / "comparison.sqlite3"
    auth = authorization()
    first_left = ArmHarness("arm-a", "profile-a")
    first_right = ArmHarness("arm-b", "profile-b")
    first = AuraGateComparisonRunner(GateComparisonAuthorizationStore(database))
    assert run_paired(first, first_left, first_right, auth)["comparison_complete"] is True

    replay_left = ArmHarness("arm-a", "profile-a")
    replay_right = ArmHarness("arm-b", "profile-b")
    restarted = AuraGateComparisonRunner(GateComparisonAuthorizationStore(database))
    replay = run_paired(restarted, replay_left, replay_right, auth)

    assert replay["error"] == "paired_authorization_already_consumed"
    assert replay_left.execute_calls == replay_right.execute_calls == 0
    assert replay_left.provider_calls == replay_right.provider_calls == 0
    assert replay["promotion_performed"] is False


def test_comparability_mismatch_blocks_consumption_and_live_execution(tmp_path: Path) -> None:
    left = ArmHarness("arm-a", "profile-a")
    different = {**BOUNDS, "plan_phase_hash": "different-plan"}
    right = ArmHarness("arm-b", "profile-b", bounds=different)
    actual_runner = runner(tmp_path)
    auth = authorization()

    result = run_paired(actual_runner, left, right, auth)

    assert result["error"] == "paired_comparability_mismatch"
    assert left.execute_calls == right.execute_calls == 0
    assert actual_runner.authorization_store.consumption(auth.authorization_id) is None
    assert result["human_review_evidence"]["preferred_arm_id"] is None


@pytest.mark.parametrize(
    ("auth_kwargs", "arm_profiles", "run_kwargs", "expected_fragment"),
    [
        ({}, ("profile-a", "profile-b"), {"purpose_digest": "wrong"}, "purpose digest"),
        ({}, ("profile-a", "profile-b"), {"graph_digest": "wrong"}, "graph digest"),
        ({}, ("profile-a", "profile-b"), {"policy_mode": "CASCADE"}, "policy mode"),
        ({}, ("profile-a", "profile-x"), {}, "outside the authorization"),
        ({"max_calls": 1}, ("profile-a", "profile-b"), {}, "call limit"),
        ({}, ("profile-a", "profile-b"), {"verifier_id": "wrong"}, "verifier"),
        ({}, ("profile-a", "profile-b"), {"now": 200.0}, "expired"),
    ],
)
def test_paired_validates_complete_execution_authorization_contract(
    tmp_path: Path,
    auth_kwargs: dict[str, Any],
    arm_profiles: tuple[str, str],
    run_kwargs: dict[str, Any],
    expected_fragment: str,
) -> None:
    left = ArmHarness("arm-a", arm_profiles[0])
    right = ArmHarness("arm-b", arm_profiles[1])
    actual_runner = runner(tmp_path)
    auth = authorization(**auth_kwargs)

    result = run_paired(actual_runner, left, right, auth, **run_kwargs)

    assert result["error"] == "paired_authorization_denied"
    assert any(expected_fragment in item for item in result["errors"])
    assert left.execute_calls == right.execute_calls == 0
    assert actual_runner.authorization_store.consumption(auth.authorization_id) is None


def test_partial_live_failure_still_attempts_exactly_two_arms_without_preference(tmp_path: Path) -> None:
    left = ArmHarness("arm-a", "profile-a")
    right = ArmHarness("arm-b", "profile-b")
    left.fail_execute = True

    result = run_paired(runner(tmp_path), left, right, authorization())

    assert result["ok"] is True
    assert result["comparison_complete"] is False
    assert left.execute_calls == right.execute_calls == 1
    assert any(item.startswith("execute_failed:arm-a") for item in result["errors"])
    assert result["human_review_evidence"]["preferred_arm_id"] is None
    assert result["human_review_evidence"]["reason"] == "comparison_or_verifier_evidence_incomplete"
    assert result["promotion_performed"] is False


def test_reported_production_mutation_invalidates_paired_evidence(tmp_path: Path) -> None:
    left = ArmHarness("arm-a", "profile-a")
    right = ArmHarness("arm-b", "profile-b")
    left.reported_production_mutation = True

    result = run_paired(runner(tmp_path), left, right, authorization())

    assert result["comparison_complete"] is False
    assert "arm_reported_production_mutation:arm-a" in result["errors"]
    assert result["production_mutation"] is False
    assert result["human_review_evidence"]["preferred_arm_id"] is None


def test_measured_and_estimated_overlap_invalidates_preference(tmp_path: Path) -> None:
    left = ArmHarness("arm-a", "profile-a", measured={"cost_usd": 1.0}, estimated={"cost_usd": 0.8})
    right = ArmHarness("arm-b", "profile-b", measured={"cost_usd": 2.0})

    result = run_paired(runner(tmp_path), left, right, authorization())

    assert result["comparison_complete"] is False
    assert "measurement_fields_invalid:arm-a" in result["errors"]
    assert result["arms"][0]["measured"] == {}
    assert result["arms"][0]["estimated"] == {}
    assert result["human_review_evidence"]["preferred_arm_id"] is None
    assert result["promotion_performed"] is False
