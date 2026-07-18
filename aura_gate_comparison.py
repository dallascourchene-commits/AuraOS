"""Governed SHADOW and PAIRED_LIVE comparison boundary for Aura Gate.

The runner deliberately has no promotion callable.  SHADOW prepares evidence
without live execution.  PAIRED_LIVE consumes one content-bound authorization
before exactly two isolated arms may execute, and all preference output remains
human-review evidence only.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time
from typing import Any

from aura_model_cognome_execution_auth import PAIRED_LIVE, ExecutionAuthorization

GATE_COMPARISON_VERSION = "AURA_GATE_COMPARISON_V1"
SHADOW = "SHADOW"
DERIVED = "DERIVED"
VERIFIER_BACKED = "VERIFIER_BACKED"
HUMAN_REVIEW_ONLY = "HUMAN_REVIEW_ONLY"


def _digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=32).hexdigest()


def _clean_id(value: Any, *, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} must not be empty")
    return text


def _counter_value(reader: Callable[[], int], *, name: str) -> int:
    value = reader()
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must return a non-negative integer")
    return value


def _numeric_fields(value: Any, *, name: str) -> dict[str, int | float]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    result: dict[str, int | float] = {}
    for raw_key, raw_value in value.items():
        key = _clean_id(raw_key, name=f"{name} metric")
        try:
            finite = type(raw_value) in {int, float} and math.isfinite(float(raw_value))
        except (OverflowError, ValueError):
            finite = False
        if not finite:
            raise ValueError(f"{name}.{key} must be a finite number")
        result[key] = raw_value
    return result


@dataclass(frozen=True)
class GateArmLineage:
    """Mutable execution owners that must never be shared by paired arms."""

    runtime_id: str
    bridge_id: str
    controlled_session_namespace_id: str
    staging_root_id: str
    output_root_id: str

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            _clean_id(value, name=name)

    def ids(self) -> frozenset[str]:
        return frozenset(str(value) for value in asdict(self).values())

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class GateComparisonArm:
    """One bounded comparison executor with observable live-call counters."""

    arm_id: str
    profile_id: str
    lineage: GateArmLineage
    prepare: Callable[[], Mapping[str, Any]]
    execute: Callable[[], Mapping[str, Any]]
    provider_call_count: Callable[[], int]
    start_call_count: Callable[[], int]

    def __post_init__(self) -> None:
        _clean_id(self.arm_id, name="arm_id")
        _clean_id(self.profile_id, name="profile_id")
        if not isinstance(self.lineage, GateArmLineage):
            raise ValueError("lineage must be a GateArmLineage")
        for name in ("prepare", "execute", "provider_call_count", "start_call_count"):
            if not callable(getattr(self, name)):
                raise ValueError(f"{name} must be callable")


@dataclass(frozen=True)
class GateComparisonBounds:
    """Exact fields that make two prepared executions comparable."""

    objective_digest: str
    repository_digest: str
    plan_phase_hash: str
    required_gates: tuple[str, ...]
    budgets: tuple[tuple[str, int], ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> GateComparisonBounds:
        if not isinstance(value, Mapping):
            raise ValueError("prepared bounds must be an object")
        gates_value = value.get("required_gates")
        if not isinstance(gates_value, (list, tuple)) or not gates_value:
            raise ValueError("required_gates must be a non-empty array")
        gates = tuple(_clean_id(item, name="required_gate") for item in gates_value)
        if len(gates) != len(set(gates)):
            raise ValueError("required_gates cannot contain duplicates")

        budgets_value = value.get("budgets")
        if not isinstance(budgets_value, Mapping) or not budgets_value:
            raise ValueError("budgets must be a non-empty object")
        budgets: list[tuple[str, int]] = []
        for raw_name, raw_value in budgets_value.items():
            name = _clean_id(raw_name, name="budget name")
            if type(raw_value) is not int or raw_value < 0:
                raise ValueError(f"budget {name} must be a non-negative integer")
            budgets.append((name, raw_value))
        budgets.sort()
        return cls(
            objective_digest=_clean_id(value.get("objective_digest"), name="objective_digest"),
            repository_digest=_clean_id(value.get("repository_digest"), name="repository_digest"),
            plan_phase_hash=_clean_id(value.get("plan_phase_hash"), name="plan_phase_hash"),
            required_gates=gates,
            budgets=tuple(budgets),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_digest": self.objective_digest,
            "repository_digest": self.repository_digest,
            "plan_phase_hash": self.plan_phase_hash,
            "required_gates": list(self.required_gates),
            "budgets": dict(self.budgets),
        }


class GateComparisonAuthorizationStore:
    """Durable, transactional, content-bound authorization consumption."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS gate_comparison_authorization_consumptions (
                    authorization_id TEXT PRIMARY KEY,
                    authorization_digest TEXT NOT NULL,
                    claim_digest TEXT NOT NULL,
                    consumer_id TEXT NOT NULL,
                    consumed_at REAL NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path), timeout=10.0, isolation_level=None)
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def consume(
        self,
        authorization: ExecutionAuthorization,
        *,
        claim: Mapping[str, Any],
        consumer_id: str,
        consumed_at: float,
    ) -> bool:
        """Atomically consume an authorization once, bound to its exact claim."""
        if not isinstance(authorization, ExecutionAuthorization):
            raise ValueError("authorization must be an ExecutionAuthorization")
        if not isinstance(claim, Mapping):
            raise ValueError("claim must be an object")
        consumer = _clean_id(consumer_id, name="consumer_id")
        timestamp = float(consumed_at)
        if not math.isfinite(timestamp) or timestamp < 0:
            raise ValueError("consumed_at must be a non-negative finite number")
        authorization_digest = _digest(authorization.identity_basis())
        claim_digest = _digest(dict(claim))

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    """
                    INSERT INTO gate_comparison_authorization_consumptions (
                        authorization_id, authorization_digest, claim_digest,
                        consumer_id, consumed_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        authorization.authorization_id,
                        authorization_digest,
                        claim_digest,
                        consumer,
                        timestamp,
                    ),
                )
            except sqlite3.IntegrityError:
                connection.rollback()
                return False
            connection.commit()
            return True
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def consumption(self, authorization_id: str) -> dict[str, Any] | None:
        """Return digest-only evidence for audit and tests; never the raw claim."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT authorization_id, authorization_digest, claim_digest,
                       consumer_id, consumed_at
                FROM gate_comparison_authorization_consumptions
                WHERE authorization_id = ?
                """,
                (_clean_id(authorization_id, name="authorization_id"),),
            ).fetchone()
        if row is None:
            return None
        return {
            "authorization_id": row[0],
            "authorization_digest": row[1],
            "claim_digest": row[2],
            "consumer_id": row[3],
            "consumed_at": row[4],
        }


@dataclass(frozen=True)
class _PreparedArm:
    arm: GateComparisonArm
    bounds: GateComparisonBounds
    estimated: Mapping[str, int | float]


class AuraGateComparisonRunner:
    """Execute non-authoritative, bounded comparison evidence workflows."""

    def __init__(self, authorization_store: GateComparisonAuthorizationStore) -> None:
        if not isinstance(authorization_store, GateComparisonAuthorizationStore):
            raise ValueError("authorization_store must be a GateComparisonAuthorizationStore")
        self.authorization_store = authorization_store

    @staticmethod
    def _error(code: str, errors: Sequence[str] = ()) -> dict[str, Any]:
        return {
            "ok": False,
            "version": GATE_COMPARISON_VERSION,
            "error": code,
            "errors": list(errors),
            "human_review_evidence": {
                "preferred_arm_id": None,
                "authority": HUMAN_REVIEW_ONLY,
            },
            "comparison_complete": False,
            "promotion_performed": False,
            "production_mutation": False,
            "human_review_required": True,
        }

    @staticmethod
    def _validate_pair(left: GateComparisonArm, right: GateComparisonArm) -> list[str]:
        errors: list[str] = []
        if left.arm_id == right.arm_id:
            errors.append("paired arms must have distinct arm IDs")
        if left.profile_id == right.profile_id:
            errors.append("paired arms must have distinct profile IDs")
        shared_lineage = sorted(left.lineage.ids() & right.lineage.ids())
        if shared_lineage:
            errors.append("paired arms share mutable lineage IDs")
        return errors

    @staticmethod
    def _snapshot(arm: GateComparisonArm) -> tuple[int, int]:
        return (
            _counter_value(arm.provider_call_count, name=f"{arm.arm_id}.provider_call_count"),
            _counter_value(arm.start_call_count, name=f"{arm.arm_id}.start_call_count"),
        )

    @staticmethod
    def _prepare_arm(arm: GateComparisonArm) -> _PreparedArm:
        packet = arm.prepare()
        if not isinstance(packet, Mapping):
            raise ValueError("prepare result must be an object")
        bounds_value = packet.get("bounds")
        if not isinstance(bounds_value, Mapping):
            raise ValueError("prepare result must contain bounds")
        if packet.get("promotion_performed") is True or packet.get("production_mutation") is True:
            raise ValueError("prepare result reports forbidden mutation")
        bounds = GateComparisonBounds.from_mapping(bounds_value)
        estimated = _numeric_fields(packet.get("estimated", {}), name="estimated")
        return _PreparedArm(arm=arm, bounds=bounds, estimated=estimated)

    def run_shadow(self, left: GateComparisonArm, right: GateComparisonArm) -> dict[str, Any]:
        """Prepare two DERIVED estimates while proving live counters stay unchanged."""
        pair_errors = self._validate_pair(left, right)
        if pair_errors:
            return self._error("shadow_pair_invalid", pair_errors)
        try:
            before = {arm.arm_id: self._snapshot(arm) for arm in (left, right)}
        except (TypeError, ValueError, RuntimeError):
            return self._error("shadow_counter_invalid")

        prepared: list[_PreparedArm] = []
        prepare_errors: list[str] = []
        for arm in (left, right):
            try:
                prepared.append(self._prepare_arm(arm))
            except Exception as exc:
                prepare_errors.append(f"prepare_failed:{arm.arm_id}:{type(exc).__name__}")
        try:
            after = {arm.arm_id: self._snapshot(arm) for arm in (left, right)}
        except (TypeError, ValueError, RuntimeError):
            return self._error("shadow_counter_invalid")
        counter_errors = [
            f"shadow_live_counter_changed:{arm_id}" for arm_id in before if before[arm_id] != after[arm_id]
        ]
        if prepare_errors or counter_errors:
            return self._error("shadow_evidence_invalid", [*prepare_errors, *counter_errors])

        claim = {
            "mode": SHADOW,
            "arms": [
                {
                    "arm_id": item.arm.arm_id,
                    "profile_id": item.arm.profile_id,
                    "bounds": item.bounds.to_dict(),
                    "estimated": dict(item.estimated),
                }
                for item in prepared
            ],
        }
        return {
            "ok": True,
            "version": GATE_COMPARISON_VERSION,
            "comparison_id": f"GATE-SHADOW-{_digest(claim)[:24]}",
            "measurement_mode": SHADOW,
            "measurement_class": DERIVED,
            "arms": [
                {
                    "arm_id": item.arm.arm_id,
                    "profile_id": item.arm.profile_id,
                    "bounds": item.bounds.to_dict(),
                    "measured": {},
                    "estimated": dict(item.estimated),
                    "provider_call_delta": 0,
                    "start_call_delta": 0,
                }
                for item in prepared
            ],
            "human_review_evidence": {
                "preferred_arm_id": None,
                "reason": "shadow_evidence_is_derived_only",
                "authority": HUMAN_REVIEW_ONLY,
            },
            "comparison_complete": False,
            "promotion_performed": False,
            "production_mutation": False,
            "human_review_required": True,
        }

    def run_paired(
        self,
        left: GateComparisonArm,
        right: GateComparisonArm,
        *,
        authorization: ExecutionAuthorization,
        purpose_digest: str,
        graph_digest: str,
        policy_mode: str,
        verifier_id: str,
        consumer_id: str,
        now: float | None = None,
        preference_metric: str | None = None,
        lower_is_better: bool = True,
    ) -> dict[str, Any]:
        """Run exactly two isolated live arms after consuming exact authorization."""
        pair_errors = self._validate_pair(left, right)
        if pair_errors:
            return self._error("paired_isolation_invalid", pair_errors)
        if type(lower_is_better) is not bool:
            return self._error("paired_preference_direction_invalid")
        if policy_mode == "ZERO_MODEL":
            return self._error("paired_policy_invalid", ["PAIRED_LIVE requires a model policy"])
        if preference_metric is not None and not isinstance(preference_metric, str):
            return self._error("paired_preference_metric_invalid")
        if type(authorization) is not ExecutionAuthorization:
            return self._error("paired_authorization_invalid")
        auth = authorization

        try:
            before = {arm.arm_id: self._snapshot(arm) for arm in (left, right)}
        except (TypeError, ValueError, RuntimeError):
            return self._error("paired_counter_invalid")
        prepared: list[_PreparedArm] = []
        prepare_errors: list[str] = []
        for arm in (left, right):
            try:
                prepared.append(self._prepare_arm(arm))
            except Exception as exc:
                prepare_errors.append(f"prepare_failed:{arm.arm_id}:{type(exc).__name__}")
        try:
            after_prepare = {arm.arm_id: self._snapshot(arm) for arm in (left, right)}
        except (TypeError, ValueError, RuntimeError):
            return self._error("paired_counter_invalid")
        for arm_id, before_counts in before.items():
            if before_counts != after_prepare[arm_id]:
                prepare_errors.append(f"prepare_live_counter_changed:{arm_id}")
        if prepare_errors:
            return self._error("paired_preparation_invalid", prepare_errors)
        if len(prepared) != 2 or prepared[0].bounds != prepared[1].bounds:
            return self._error(
                "paired_comparability_mismatch",
                ["objective, repository, plan, gates, or budgets differ"],
            )

        try:
            if now is None:
                evaluation_time = time.time()
            elif type(now) in {int, float} and math.isfinite(float(now)):
                evaluation_time = float(now)
            else:
                raise ValueError("now must be finite")
            clean_purpose = _clean_id(purpose_digest, name="purpose_digest")
            clean_graph = _clean_id(graph_digest, name="graph_digest")
            clean_policy = _clean_id(policy_mode, name="policy_mode")
            clean_verifier = _clean_id(verifier_id, name="verifier_id")
        except (TypeError, ValueError, OverflowError):
            return self._error("paired_request_invalid")
        auth_errors = auth.validate_for(
            purpose_digest=clean_purpose,
            graph_digest=clean_graph,
            policy_mode=clean_policy,
            profile_ids=(left.profile_id, right.profile_id),
            call_count=2,
            forced_override=False,
            verifier_id=clean_verifier,
            now=evaluation_time,
        )
        if auth_errors:
            return self._error("paired_authorization_denied", auth_errors)

        claim = {
            "version": GATE_COMPARISON_VERSION,
            "measurement_mode": PAIRED_LIVE,
            "authorization_id": auth.authorization_id,
            "purpose_digest": clean_purpose,
            "graph_digest": clean_graph,
            "policy_mode": clean_policy,
            "verifier_id": clean_verifier,
            "call_count": 2,
            "bounds": prepared[0].bounds.to_dict(),
            "arms": [
                {
                    "arm_id": item.arm.arm_id,
                    "profile_id": item.arm.profile_id,
                    "lineage": item.arm.lineage.to_dict(),
                }
                for item in prepared
            ],
        }
        try:
            consumed = self.authorization_store.consume(
                auth,
                claim=claim,
                consumer_id=consumer_id,
                consumed_at=evaluation_time,
            )
        except (OSError, sqlite3.Error, TypeError, ValueError, RuntimeError):
            return self._error("paired_authorization_store_error")
        if not consumed:
            return self._error("paired_authorization_already_consumed")

        arm_evidence: list[dict[str, Any]] = []
        evidence_errors: list[str] = []
        for item in prepared:
            arm = item.arm
            execution_failed = False
            try:
                raw_result = arm.execute()
            except Exception as exc:
                raw_result = None
                execution_failed = True
                evidence_errors.append(f"execute_failed:{arm.arm_id}:{type(exc).__name__}")
            evidence: dict[str, Any] = {
                "arm_id": arm.arm_id,
                "profile_id": arm.profile_id,
                "measurement_class": None,
                "verifier_id": None,
                "verification_complete": False,
                "measured": {},
                "estimated": {},
            }
            if isinstance(raw_result, Mapping):
                raw_result = dict(raw_result)
                evidence["measurement_class"] = raw_result.get("measurement_class")
                evidence["verifier_id"] = raw_result.get("verifier_id")
                evidence["verification_complete"] = raw_result.get("verification_complete") is True
                try:
                    measured = _numeric_fields(raw_result.get("measured"), name="measured")
                    estimated = _numeric_fields(raw_result.get("estimated", {}), name="estimated")
                    if set(measured) & set(estimated):
                        raise ValueError("measured and estimated metrics must not overlap")
                    evidence["measured"] = measured
                    evidence["estimated"] = estimated
                except (TypeError, ValueError, OverflowError, RuntimeError):
                    evidence_errors.append(f"measurement_fields_invalid:{arm.arm_id}")
                if raw_result.get("ok") is not True:
                    evidence_errors.append(f"arm_not_ok:{arm.arm_id}")
                if raw_result.get("measurement_class") != VERIFIER_BACKED:
                    evidence_errors.append(f"verifier_evidence_missing:{arm.arm_id}")
                if raw_result.get("verifier_id") != clean_verifier:
                    evidence_errors.append(f"verifier_id_mismatch:{arm.arm_id}")
                if raw_result.get("verification_complete") is not True:
                    evidence_errors.append(f"verification_incomplete:{arm.arm_id}")
                if not evidence["measured"]:
                    evidence_errors.append(f"measured_metrics_missing:{arm.arm_id}")
                if raw_result.get("promotion_performed") is True:
                    evidence_errors.append(f"arm_reported_promotion:{arm.arm_id}")
                if raw_result.get("production_mutation") is True:
                    evidence_errors.append(f"arm_reported_production_mutation:{arm.arm_id}")
            elif not execution_failed:
                evidence_errors.append(f"execute_result_invalid:{arm.arm_id}")
            arm_evidence.append(evidence)

        try:
            after_execute = {arm.arm_id: self._snapshot(arm) for arm in (left, right)}
        except (TypeError, ValueError, RuntimeError):
            return self._error("paired_counter_invalid_after_consumption")
        for arm in (left, right):
            provider_delta = after_execute[arm.arm_id][0] - after_prepare[arm.arm_id][0]
            start_delta = after_execute[arm.arm_id][1] - after_prepare[arm.arm_id][1]
            evidence = next(item for item in arm_evidence if item["arm_id"] == arm.arm_id)
            evidence["provider_call_delta"] = provider_delta
            evidence["start_call_delta"] = start_delta
            if provider_delta != 1:
                evidence_errors.append(f"provider_call_count_mismatch:{arm.arm_id}")
            if start_delta != 1:
                evidence_errors.append(f"start_call_count_mismatch:{arm.arm_id}")

        comparison_complete = not evidence_errors
        metric = str(preference_metric or "").strip()
        preferred_arm_id: str | None = None
        preference_reason = "preference_metric_not_requested"
        if comparison_complete and metric:
            left_metric = arm_evidence[0]["measured"].get(metric)
            right_metric = arm_evidence[1]["measured"].get(metric)
            if type(left_metric) in {int, float} and type(right_metric) in {int, float}:
                if left_metric == right_metric:
                    preference_reason = "named_metric_tie"
                elif (left_metric < right_metric) == lower_is_better:
                    preferred_arm_id = left.arm_id
                    preference_reason = "named_measured_metric"
                else:
                    preferred_arm_id = right.arm_id
                    preference_reason = "named_measured_metric"
            else:
                preference_reason = "named_metric_incomplete"
        elif not comparison_complete:
            preference_reason = "comparison_or_verifier_evidence_incomplete"

        return {
            "ok": True,
            "version": GATE_COMPARISON_VERSION,
            "comparison_id": f"GATE-PAIRED-{_digest(claim)[:24]}",
            "authorization_id": auth.authorization_id,
            "measurement_mode": PAIRED_LIVE,
            "bounds": prepared[0].bounds.to_dict(),
            "comparability": {
                "complete": True,
                "equal_fields": [
                    "objective_digest",
                    "repository_digest",
                    "plan_phase_hash",
                    "required_gates",
                    "budgets",
                ],
            },
            "arms": arm_evidence,
            "errors": evidence_errors,
            "comparison_complete": comparison_complete,
            "human_review_evidence": {
                "preference_metric": metric or None,
                "preference_direction": "LOWER_IS_BETTER" if lower_is_better else "HIGHER_IS_BETTER",
                "preferred_arm_id": preferred_arm_id,
                "reason": preference_reason,
                "authority": HUMAN_REVIEW_ONLY,
            },
            "promotion_performed": False,
            "production_mutation": False,
            "human_review_required": True,
        }


__all__ = [
    "DERIVED",
    "GATE_COMPARISON_VERSION",
    "HUMAN_REVIEW_ONLY",
    "SHADOW",
    "VERIFIER_BACKED",
    "AuraGateComparisonRunner",
    "GateArmLineage",
    "GateComparisonArm",
    "GateComparisonAuthorizationStore",
    "GateComparisonBounds",
]
