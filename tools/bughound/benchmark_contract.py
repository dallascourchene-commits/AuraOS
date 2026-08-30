"""Deterministic D0 benchmark contract for AWJ-BUGHOUND-002-R1.

This module does not run a model, inspect a third-party target, or claim broad
BugHound capability. It defines one source-bound seeded case and one matched
control-vs-invariant route so benchmark validity, leakage state, capability mode,
and observable metrics cannot be collapsed into a headline score.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Callable

SCHEMA_CASE = "BugCaseV1"
SCHEMA_RUN = "BugBenchmarkRunV1"
SCHEMA_MATCHED = "BugMatchedBenchmarkV1"

CAPABILITY_MODES = frozenset({"ISSUE_GUIDED_FIX", "PROACTIVE_DISCOVERY"})
CASE_VALIDITY_STATES = frozenset({"VALIDATED", "DISPUTED", "INVALIDATED", "UNKNOWN"})
LEAKAGE_STATES = frozenset({"TRAIN_REFERENCE", "DEV", "HOLDOUT", "REGRESSION"})
CANDIDATE_REVISIONS = frozenset({"BUGGY", "FIXED"})


class BugBenchmarkError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _nonempty(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BugBenchmarkError(code)
    return value.strip()


@dataclass(frozen=True)
class BugCase:
    case_id: str
    bug_family: str
    capability_mode: str
    case_validity_state: str
    leakage_state: str
    source_generation: str
    trigger_id: str
    oracle_id: str
    causal_cone: tuple[str, ...]
    buggy_source: str
    fixed_source: str
    fixed_patch_visible_to_candidate: bool
    schema: str = SCHEMA_CASE

    def normalized(self) -> dict[str, object]:
        case_id = _nonempty(self.case_id, "BUG_CASE_ID_REQUIRED")
        bug_family = _nonempty(self.bug_family, "BUG_FAMILY_REQUIRED")
        source_generation = _nonempty(self.source_generation, "SOURCE_GENERATION_REQUIRED")
        trigger_id = _nonempty(self.trigger_id, "TRIGGER_ID_REQUIRED")
        oracle_id = _nonempty(self.oracle_id, "ORACLE_ID_REQUIRED")
        buggy_source = _nonempty(self.buggy_source, "BUGGY_SOURCE_REQUIRED")
        fixed_source = _nonempty(self.fixed_source, "FIXED_SOURCE_REQUIRED")
        if self.schema != SCHEMA_CASE:
            raise BugBenchmarkError("BUG_CASE_SCHEMA_MISMATCH")
        if self.capability_mode not in CAPABILITY_MODES:
            raise BugBenchmarkError("CAPABILITY_MODE_INVALID", self.capability_mode)
        if self.case_validity_state not in CASE_VALIDITY_STATES:
            raise BugBenchmarkError("CASE_VALIDITY_STATE_INVALID", self.case_validity_state)
        if self.leakage_state not in LEAKAGE_STATES:
            raise BugBenchmarkError("LEAKAGE_STATE_INVALID", self.leakage_state)
        if type(self.fixed_patch_visible_to_candidate) is not bool:
            raise BugBenchmarkError("FIXED_PATCH_VISIBILITY_BOOL_REQUIRED")
        if self.leakage_state == "HOLDOUT" and self.fixed_patch_visible_to_candidate:
            raise BugBenchmarkError("HOLDOUT_PATCH_LEAKAGE_FORBIDDEN")
        if not isinstance(self.causal_cone, tuple) or not self.causal_cone:
            raise BugBenchmarkError("CAUSAL_CONE_REQUIRED")
        cone: list[str] = []
        for item in self.causal_cone:
            cone.append(_nonempty(item, "CAUSAL_CONE_ENTRY_INVALID"))
        return {
            "schema": self.schema,
            "case_id": case_id,
            "bug_family": bug_family,
            "capability_mode": self.capability_mode,
            "case_validity_state": self.case_validity_state,
            "leakage_state": self.leakage_state,
            "source_generation": source_generation,
            "trigger_id": trigger_id,
            "oracle_id": oracle_id,
            "causal_cone": cone,
            "buggy_source_sha256": hashlib.sha256(buggy_source.encode()).hexdigest(),
            "fixed_source_sha256": hashlib.sha256(fixed_source.encode()).hexdigest(),
            "fixed_patch_visible_to_candidate": self.fixed_patch_visible_to_candidate,
        }

    @property
    def case_digest(self) -> str:
        return _sha(self.normalized())


@dataclass(frozen=True)
class BugBenchmarkRun:
    case_digest: str
    route: str
    candidate_revision: str
    tests_run: int
    failed_checks: tuple[str, ...]
    detected: bool
    provider_calls: int = 0
    provider_cost: None = None
    wall_latency_ms: None = None
    schema: str = SCHEMA_RUN

    def normalized(self) -> dict[str, object]:
        if self.schema != SCHEMA_RUN:
            raise BugBenchmarkError("BENCHMARK_RUN_SCHEMA_MISMATCH")
        if len(self.case_digest) != 64:
            raise BugBenchmarkError("CASE_DIGEST_INVALID")
        route = _nonempty(self.route, "ROUTE_REQUIRED")
        if self.candidate_revision not in CANDIDATE_REVISIONS:
            raise BugBenchmarkError("CANDIDATE_REVISION_INVALID")
        if isinstance(self.tests_run, bool) or not isinstance(self.tests_run, int) or self.tests_run <= 0:
            raise BugBenchmarkError("TEST_COUNT_INVALID")
        if not isinstance(self.failed_checks, tuple):
            raise BugBenchmarkError("FAILED_CHECKS_TUPLE_REQUIRED")
        if type(self.detected) is not bool:
            raise BugBenchmarkError("DETECTED_BOOL_REQUIRED")
        if self.detected != bool(self.failed_checks):
            raise BugBenchmarkError("DETECTION_FAILURES_INCONSISTENT")
        if self.provider_calls != 0 or self.provider_cost is not None or self.wall_latency_ms is not None:
            raise BugBenchmarkError("D0_UNKNOWN_OR_ZERO_METRIC_CEILING")
        return {
            "schema": self.schema,
            "case_digest": self.case_digest,
            "route": route,
            "candidate_revision": self.candidate_revision,
            "tests_run": self.tests_run,
            "failed_checks": list(self.failed_checks),
            "detected": self.detected,
            "provider_calls": 0,
            "provider_cost": None,
            "wall_latency_ms": None,
        }


@dataclass(frozen=True)
class MatchedBenchmarkReceipt:
    case: BugCase
    control_buggy: BugBenchmarkRun
    control_fixed: BugBenchmarkRun
    bughound_buggy: BugBenchmarkRun
    bughound_fixed: BugBenchmarkRun
    proactive_discovery_credited: bool = False
    schema: str = SCHEMA_MATCHED

    def normalized(self) -> dict[str, object]:
        if self.schema != SCHEMA_MATCHED:
            raise BugBenchmarkError("MATCHED_SCHEMA_MISMATCH")
        case = self.case.normalized()
        if case["case_validity_state"] != "VALIDATED":
            raise BugBenchmarkError("VALIDATED_CASE_REQUIRED_FOR_ACCEPTED_RECEIPT")
        digest = self.case.case_digest
        runs = (
            self.control_buggy,
            self.control_fixed,
            self.bughound_buggy,
            self.bughound_fixed,
        )
        normalized_runs = [run.normalized() for run in runs]
        if any(run["case_digest"] != digest for run in normalized_runs):
            raise BugBenchmarkError("MATCHED_CASE_DIGEST_MISMATCH")
        if self.proactive_discovery_credited:
            raise BugBenchmarkError("PROACTIVE_DISCOVERY_CREDIT_FORBIDDEN_IN_SEEDED_ISSUE_GUIDED_CASE")
        if case["capability_mode"] != "ISSUE_GUIDED_FIX":
            raise BugBenchmarkError("SEEDED_CASE_CAPABILITY_MODE_MISMATCH")
        return {
            "schema": self.schema,
            "case": case,
            "case_digest": digest,
            "runs": normalized_runs,
            "proactive_discovery_credited": False,
            "observable_metrics_only": True,
            "unknown_metrics_preserved": ["provider_cost", "wall_latency_ms"],
            "claim_ceiling": "ONE_VALIDATED_SEEDED_ISSUE_GUIDED_CASE_NOT_PROACTIVE_DISCOVERY_CAPABILITY",
        }

    @property
    def receipt_digest(self) -> str:
        return _sha(self.normalized())


def generation_accept_buggy(current_generation: int, candidate_generation: int) -> bool:
    """Seeded bug: stale generations are incorrectly accepted."""
    return candidate_generation <= current_generation


def generation_accept_fixed(current_generation: int, candidate_generation: int) -> bool:
    """Ground-truth fix: only the current generation is accepted."""
    return candidate_generation == current_generation


BUGGY_SOURCE = "def accept(current, candidate): return candidate <= current"
FIXED_SOURCE = "def accept(current, candidate): return candidate == current"


def seeded_generation_case() -> BugCase:
    return BugCase(
        case_id="BUGBOT-STAGE-001-STALE-GENERATION",
        bug_family="STALE_GENERATION_CURRENTNESS_ACCEPTANCE",
        capability_mode="ISSUE_GUIDED_FIX",
        case_validity_state="VALIDATED",
        leakage_state="HOLDOUT",
        source_generation="bugbot-lab:r1:20260830",
        trigger_id="trigger:current=7,candidate=6",
        oracle_id="oracle:accept iff candidate_generation == current_generation",
        causal_cone=("generation-admission predicate",),
        buggy_source=BUGGY_SOURCE,
        fixed_source=FIXED_SOURCE,
        fixed_patch_visible_to_candidate=False,
    )


def _run_route(
    *,
    case: BugCase,
    route: str,
    revision: str,
    subject: Callable[[int, int], bool],
    checks: tuple[tuple[str, int, int, bool], ...],
) -> BugBenchmarkRun:
    failures: list[str] = []
    for check_id, current, candidate, expected in checks:
        observed = subject(current, candidate)
        if observed is not expected:
            failures.append(check_id)
    return BugBenchmarkRun(
        case_digest=case.case_digest,
        route=route,
        candidate_revision=revision,
        tests_run=len(checks),
        failed_checks=tuple(failures),
        detected=bool(failures),
    )


def happy_path_control(case: BugCase, revision: str, subject: Callable[[int, int], bool]) -> BugBenchmarkRun:
    """Simple control: only checks the current-generation happy path."""
    return _run_route(
        case=case,
        route="FLAT_HAPPY_PATH_CONTROL",
        revision=revision,
        subject=subject,
        checks=(("current-generation-accepted", 7, 7, True),),
    )


def generation_invariant_route(
    case: BugCase,
    revision: str,
    subject: Callable[[int, int], bool],
) -> BugBenchmarkRun:
    """BugHound candidate route: paired current/stale invariant probe."""
    return _run_route(
        case=case,
        route="BUGHOUND_GENERATION_INVARIANT_PAIR",
        revision=revision,
        subject=subject,
        checks=(
            ("current-generation-accepted", 7, 7, True),
            ("stale-generation-rejected", 7, 6, False),
        ),
    )


def run_seeded_generation_benchmark() -> MatchedBenchmarkReceipt:
    case = seeded_generation_case()
    receipt = MatchedBenchmarkReceipt(
        case=case,
        control_buggy=happy_path_control(case, "BUGGY", generation_accept_buggy),
        control_fixed=happy_path_control(case, "FIXED", generation_accept_fixed),
        bughound_buggy=generation_invariant_route(case, "BUGGY", generation_accept_buggy),
        bughound_fixed=generation_invariant_route(case, "FIXED", generation_accept_fixed),
    )
    receipt.normalized()
    return receipt


def main() -> int:
    receipt = run_seeded_generation_benchmark()
    print(json.dumps(receipt.normalized(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
