#!/usr/bin/env python3
"""Deterministic BugHound intake primitives.

This module is intentionally D0/local: it performs no network access and never
interprets a bounty listing, safe-harbor statement, heuristic score, or K27
placement as authorization.  It compiles source-bound program/currentness and
BugCase records that later BugHound stages can consume.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable

SCHEMA_VERSION = "BugHoundFoundryIntakeV1"
DEFAULT_MAX_AGE_SECONDS = 24 * 60 * 60


class IntakeError(ValueError):
    """Typed fail-closed intake error."""


class Authorization(str, Enum):
    LOCAL_SANDBOX_ONLY = "LOCAL_SANDBOX_ONLY"
    PUBLIC_PROGRAM = "PUBLIC_PROGRAM"


class DuplicateClass(str, Enum):
    ROOT_CAUSE_DUPLICATE = "ROOT_CAUSE_DUPLICATE"
    PATCH_COLLISION_ONLY = "PATCH_COLLISION_ONLY"
    DISTINCT = "DISTINCT"


class Visibility(str, Enum):
    TRAIN_REFERENCE = "TRAIN_REFERENCE"
    DEV = "DEV"
    HOLDOUT_TEST = "HOLDOUT_TEST"
    REGRESSION = "REGRESSION"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(value: Any) -> str:
    body = value if isinstance(value, str) else canonical_json(value)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def k27_hint(locator: str) -> int:
    """Advisory physical shard only; never identity, truth, or authority."""
    if not isinstance(locator, str) or not locator.strip():
        raise IntakeError("K27_LOCATOR_REQUIRED")
    return int(hashlib.sha256(locator.strip().encode("utf-8")).hexdigest(), 16) % 27


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise IntakeError("INVALID_CHECKED_AT") from exc
    if parsed.tzinfo is None:
        raise IntakeError("CHECKED_AT_MUST_BE_OFFSET_AWARE")
    return parsed.astimezone(timezone.utc)


def _require_digest(name: str, value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise IntakeError(f"{name}_MUST_BE_SHA256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise IntakeError(f"{name}_MUST_BE_SHA256") from exc


@dataclass(frozen=True)
class ProgramCurrentnessReceiptV1:
    program_id: str
    program_source: str
    program_generation: str
    checked_at: str
    scope_source: str
    rules_source: str
    scope_digest: str
    rules_digest: str
    authorization: str
    testing_mode: str
    submission_gate: str
    safe_harbor_source: str | None = None
    exact_scope_bound: bool = False
    rules_current: bool = False

    def validate(
        self,
        *,
        now: datetime | None = None,
        max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    ) -> dict[str, Any]:
        required_text = {
            "program_id": self.program_id,
            "program_source": self.program_source,
            "program_generation": self.program_generation,
            "scope_source": self.scope_source,
            "rules_source": self.rules_source,
            "testing_mode": self.testing_mode,
            "submission_gate": self.submission_gate,
        }
        for key, value in required_text.items():
            if not isinstance(value, str) or not value.strip():
                raise IntakeError(f"{key.upper()}_REQUIRED")

        _require_digest("SCOPE_DIGEST", self.scope_digest)
        _require_digest("RULES_DIGEST", self.rules_digest)
        try:
            authorization = Authorization(self.authorization)
        except ValueError as exc:
            raise IntakeError("UNKNOWN_AUTHORIZATION") from exc

        checked = _parse_time(self.checked_at)
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        age_seconds = (current - checked).total_seconds()
        if age_seconds < -300:
            raise IntakeError("CHECKED_AT_IN_FUTURE")
        if age_seconds > max_age_seconds:
            raise IntakeError("PROGRAM_CURRENTNESS_STALE")

        local_testing_admitted = authorization in {
            Authorization.LOCAL_SANDBOX_ONLY,
            Authorization.PUBLIC_PROGRAM,
        }
        live_testing_admitted = bool(
            authorization is Authorization.PUBLIC_PROGRAM
            and self.exact_scope_bound
            and self.rules_current
            and self.testing_mode == "EXACT_CURRENT_SCOPE"
        )
        if self.submission_gate != "HUMAN_GATE10":
            raise IntakeError("SUBMISSION_GATE_MUST_REMAIN_HUMAN_GATE10")

        return {
            "schema": SCHEMA_VERSION,
            "program_id": self.program_id,
            "receipt_digest": self.digest(),
            "age_seconds": int(max(0, age_seconds)),
            "local_testing_admitted": local_testing_admitted,
            "live_testing_admitted": live_testing_admitted,
            "safe_harbor_is_scope": False,
            "claim_ceiling": "CURRENTNESS_AND_ADMISSION_INPUT_ONLY",
        }

    def digest(self) -> str:
        return sha256_hex(asdict(self))


@dataclass(frozen=True)
class BugCaseV1:
    case_id: str
    source_ref: str
    source_generation: str
    language: str
    component: str
    defect_operator: str
    invariant: str
    consequence_class: str
    trigger: str
    oracle: str
    causal_cone: tuple[str, ...]
    fix_ref: str | None
    visibility: str
    patch_digest: str | None = None

    def validate(self) -> None:
        for key in (
            "case_id",
            "source_ref",
            "source_generation",
            "language",
            "component",
            "defect_operator",
            "invariant",
            "consequence_class",
            "trigger",
            "oracle",
        ):
            value = getattr(self, key)
            if not isinstance(value, str) or not value.strip():
                raise IntakeError(f"{key.upper()}_REQUIRED")
        try:
            Visibility(self.visibility)
        except ValueError as exc:
            raise IntakeError("UNKNOWN_VISIBILITY") from exc
        if not self.causal_cone or any(not isinstance(x, str) or not x.strip() for x in self.causal_cone):
            raise IntakeError("CAUSAL_CONE_REQUIRED")
        if self.patch_digest is not None:
            _require_digest("PATCH_DIGEST", self.patch_digest)

    def root_cause_descriptor(self) -> dict[str, Any]:
        self.validate()
        return {
            "language": self.language,
            "component": self.component,
            "defect_operator": self.defect_operator,
            "invariant": self.invariant,
            "consequence_class": self.consequence_class,
            "causal_cone": sorted(set(self.causal_cone)),
        }

    def root_cause_digest(self) -> str:
        return sha256_hex(self.root_cause_descriptor())

    def case_identity(self) -> str:
        self.validate()
        return sha256_hex(
            {
                "source_ref": self.source_ref,
                "source_generation": self.source_generation,
                "root_cause_digest": self.root_cause_digest(),
                "trigger": self.trigger,
                "oracle": self.oracle,
            }
        )

    def public_packet(self) -> dict[str, Any]:
        """Hide fixed-answer material for holdout/test cases."""
        self.validate()
        packet = {
            "schema": "BugCaseV1",
            "case_id": self.case_id,
            "case_identity": self.case_identity(),
            "source_ref": self.source_ref,
            "source_generation": self.source_generation,
            "language": self.language,
            "component": self.component,
            "defect_operator": self.defect_operator,
            "invariant": self.invariant,
            "consequence_class": self.consequence_class,
            "trigger": self.trigger,
            "oracle": self.oracle,
            "causal_cone": list(self.causal_cone),
            "visibility": self.visibility,
        }
        if self.visibility != Visibility.HOLDOUT_TEST.value:
            packet["fix_ref"] = self.fix_ref
            packet["patch_digest"] = self.patch_digest
        return packet


def classify_duplicate(left: BugCaseV1, right: BugCaseV1) -> DuplicateClass:
    left.validate()
    right.validate()
    if left.root_cause_digest() == right.root_cause_digest():
        return DuplicateClass.ROOT_CAUSE_DUPLICATE
    if left.patch_digest and right.patch_digest and left.patch_digest == right.patch_digest:
        return DuplicateClass.PATCH_COLLISION_ONLY
    return DuplicateClass.DISTINCT


def currentness_binding_digest(receipt: ProgramCurrentnessReceiptV1) -> str:
    """Identity for scope/rules/program-generation consumption."""
    return sha256_hex(
        {
            "program_id": receipt.program_id,
            "program_generation": receipt.program_generation,
            "scope_digest": receipt.scope_digest,
            "rules_digest": receipt.rules_digest,
        }
    )


def compile_case_index(cases: Iterable[BugCaseV1]) -> list[dict[str, Any]]:
    rows = []
    seen_ids: set[str] = set()
    seen_identity: set[str] = set()
    for case in cases:
        case.validate()
        if case.case_id in seen_ids:
            raise IntakeError("DUPLICATE_CASE_ID")
        identity = case.case_identity()
        if identity in seen_identity:
            raise IntakeError("DUPLICATE_CASE_IDENTITY")
        seen_ids.add(case.case_id)
        seen_identity.add(identity)
        rows.append(
            {
                "case_id": case.case_id,
                "case_identity": identity,
                "root_cause_digest": case.root_cause_digest(),
                "k27_hint": k27_hint(case.source_ref),
                "visibility": case.visibility,
            }
        )
    return sorted(rows, key=lambda row: row["case_id"])


def lattice_registry_state(resolved_registry: dict[str, Any] | None) -> dict[str, Any]:
    """Fail closed instead of fabricating the canonical eight structures."""
    if not resolved_registry:
        return {
            "status": "LATTICE_REGISTRY_GAP",
            "semantic_lattice_use": False,
            "claim_ceiling": "CONTROL_TOPOLOGIES_ONLY",
        }
    structures = resolved_registry.get("structures")
    if not isinstance(structures, list) or len(structures) != 8:
        return {
            "status": "LATTICE_REGISTRY_GAP",
            "semantic_lattice_use": False,
            "claim_ceiling": "CONTROL_TOPOLOGIES_ONLY",
        }
    if any(not isinstance(row, dict) or not row.get("name") or not row.get("source_ref") for row in structures):
        raise IntakeError("INVALID_LATTICE_REGISTRY")
    return {
        "status": "LATTICE_REGISTRY_RESOLVED",
        "semantic_lattice_use": True,
        "count": 8,
        "registry_digest": sha256_hex(structures),
        "claim_ceiling": "TOPOLOGY_EXPERIMENT_INPUT_ONLY",
    }
