"""Deterministic local benchmark substrate for AuraOS BugHound.

D0 / local only. This module does not scan networks, invoke bounty targets,
submit reports, call providers, or widen authority. It provides seeded
ground-truth bug cases, the canonical W0-W8 topology registry, matched-run
planning, leakage-aware scoring, and an oracle-only harness self-test.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from types import MappingProxyType
from typing import Iterable, Mapping, Sequence

SCHEMA = "BugHoundSeedLabV1"


class BenchmarkError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


class Visibility(str, Enum):
    TRAIN_REFERENCE = "TRAIN_REFERENCE"
    DEV = "DEV"
    HOLDOUT = "HOLDOUT"
    REGRESSION = "REGRESSION"


_CANONICAL_TOPOLOGIES = {
    "W0": "SIMPLE_DAG",
    "W1": "RECIPROCAL_TRIADIC_HELIX",
    "W2": "ANTIPRISM_PERMUTATION_AUDIT",
    "W3": "TOROID_TRIGGERED_CYCLE",
    "W4": "BUTTERFLY_REDUCTION_TREE",
    "W5": "DIAMOND_AUTHOR_CHALLENGE_VERIFY_REDUCE",
    "W6": "OCTET_WORK_STEAL_GRID",
    "W7": "KAGOME_GYROID_SPARSE_CHALLENGE_MESH",
    "W8": "PYROCHLORE_RECOVERY_GOSSIP_RECONSTITUTION",
}
TOPOLOGY_REGISTRY: Mapping[str, str] = MappingProxyType(_CANONICAL_TOPOLOGIES)


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise BenchmarkError("NONCANONICAL_STATE") from exc


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


@dataclass(frozen=True)
class SeedBugCaseV1:
    case_id: str
    bug_family: str
    language: str
    is_bug: bool
    buggy_source: str
    fixed_source: str
    trigger_id: str
    oracle_id: str
    expected_symbol: str
    causal_cone: tuple[str, ...]
    visibility: Visibility = Visibility.HOLDOUT
    source_ref: str = "AURA_INTERNAL_SEEDLAB"
    source_generation: str = "BUGHOUND-SEEDLAB-V1"

    def __post_init__(self) -> None:
        if not self.case_id or not self.case_id.replace("-", "").replace("_", "").isalnum():
            raise BenchmarkError("CASE_ID_INVALID", self.case_id)
        if self.language != "python":
            raise BenchmarkError("SEEDLAB_LANGUAGE_UNSUPPORTED", self.language)
        if not isinstance(self.visibility, Visibility):
            raise BenchmarkError("VISIBILITY_INVALID")
        if not self.expected_symbol:
            raise BenchmarkError("EXPECTED_SYMBOL_REQUIRED")
        if not self.causal_cone:
            raise BenchmarkError("CAUSAL_CONE_REQUIRED")

    @property
    def case_digest(self) -> str:
        body = asdict(self)
        body["visibility"] = self.visibility.value
        return _digest("AURA_BUGHOUND_SEED_CASE_V1", body)


def seeded_cases() -> tuple[SeedBugCaseV1, ...]:
    return (
        SeedBugCaseV1(
            case_id="STALE_GENERATION_ACCEPTANCE",
            bug_family="stale_generation_currentness_acceptance",
            language="python",
            is_bug=True,
            buggy_source="def admit(observed, current):\n    return observed <= current\n",
            fixed_source="def admit(observed, current):\n    return observed == current\n",
            trigger_id="stale_generation_4_vs_5",
            oracle_id="reject_stale_generation",
            expected_symbol="admit",
            causal_cone=("admit", "generation_comparison"),
        ),
        SeedBugCaseV1(
            case_id="REPLAY_DUPLICATE_EFFECT",
            bug_family="replay_idempotency_duplicate_effect",
            language="python",
            is_bug=True,
            buggy_source=(
                "def apply(seen, key, count):\n"
                "    count += 1\n"
                "    seen.add(key)\n"
                "    return count\n"
            ),
            fixed_source=(
                "def apply(seen, key, count):\n"
                "    if key in seen:\n"
                "        return count\n"
                "    seen.add(key)\n"
                "    return count + 1\n"
            ),
            trigger_id="same_idempotency_key_twice",
            oracle_id="single_effect_credit",
            expected_symbol="apply",
            causal_cone=("apply", "idempotency_guard"),
        ),
        SeedBugCaseV1(
            case_id="BOUNDARY_OFF_BY_ONE",
            bug_family="parser_boundary_off_by_one",
            language="python",
            is_bug=True,
            buggy_source="def take(items, n):\n    return items[:n + 1]\n",
            fixed_source="def take(items, n):\n    return items[:n]\n",
            trigger_id="take_two_from_three",
            oracle_id="exact_requested_count",
            expected_symbol="take",
            causal_cone=("take", "slice_upper_bound"),
        ),
        SeedBugCaseV1(
            case_id="CLEAN_EXACT_CURRENTNESS",
            bug_family="negative_control_clean_currentness",
            language="python",
            is_bug=False,
            buggy_source="def admit(observed, current):\n    return observed == current\n",
            fixed_source="def admit(observed, current):\n    return observed == current\n",
            trigger_id="stale_generation_4_vs_5",
            oracle_id="reject_stale_generation",
            expected_symbol="admit",
            causal_cone=("admit", "generation_comparison"),
        ),
    )


def _load_function(source: str, symbol: str):
    namespace: dict[str, object] = {"__builtins__": {}}
    try:
        exec(compile(source, "<bughound-seed>", "exec"), namespace, namespace)
    except Exception as exc:
        raise BenchmarkError("SEED_SOURCE_EXECUTION_FAILED", type(exc).__name__) from exc
    fn = namespace.get(symbol)
    if not callable(fn):
        raise BenchmarkError("EXPECTED_SYMBOL_NOT_CALLABLE", symbol)
    return fn


def _oracle_outcome(case: SeedBugCaseV1, source: str) -> bool:
    fn = _load_function(source, case.expected_symbol)
    if case.trigger_id == "stale_generation_4_vs_5":
        return fn(4, 5) is False
    if case.trigger_id == "same_idempotency_key_twice":
        seen: set[str] = set()
        count = fn(seen, "k1", 0)
        count = fn(seen, "k1", count)
        return count == 1
    if case.trigger_id == "take_two_from_three":
        return fn([10, 20, 30], 2) == [10, 20]
    raise BenchmarkError("TRIGGER_UNSUPPORTED", case.trigger_id)


@dataclass(frozen=True)
class HarnessOracleResultV1:
    case_id: str
    buggy_passes_oracle: bool
    fixed_passes_oracle: bool
    ground_truth_consistent: bool
    evidence_class: str = "HARNESS_ORACLE_SELF_TEST"
    benchmark_candidate_credit: bool = False
    authority: bool = False

    @property
    def digest(self) -> str:
        return _digest("AURA_BUGHOUND_HARNESS_ORACLE_V1", asdict(self))


def run_harness_oracle(case: SeedBugCaseV1) -> HarnessOracleResultV1:
    buggy_ok = _oracle_outcome(case, case.buggy_source)
    fixed_ok = _oracle_outcome(case, case.fixed_source)
    expected = ((not buggy_ok) and fixed_ok) if case.is_bug else (buggy_ok and fixed_ok)
    return HarnessOracleResultV1(
        case_id=case.case_id,
        buggy_passes_oracle=buggy_ok,
        fixed_passes_oracle=fixed_ok,
        ground_truth_consistent=expected,
    )


@dataclass(frozen=True)
class FindingV1:
    case_id: str
    detected: bool
    localized_symbols: tuple[str, ...] = ()
    finding_ref: str = "LOCAL_CANDIDATE"
    evidence_class: str = "CANDIDATE"

    @property
    def digest(self) -> str:
        return _digest("AURA_BUGHOUND_FINDING_V1", asdict(self))


@dataclass(frozen=True)
class MatchedRunPlanV1:
    topology_id: str
    case_digests: tuple[str, ...]
    worker_budget: int
    tool_budget: int
    source_generation: str
    fixed_patch_visible: bool = False
    schema: str = SCHEMA

    def __post_init__(self) -> None:
        if self.topology_id not in TOPOLOGY_REGISTRY:
            raise BenchmarkError("TOPOLOGY_UNKNOWN", self.topology_id)
        if self.worker_budget <= 0 or self.tool_budget < 0:
            raise BenchmarkError("BUDGET_INVALID")
        if not self.case_digests:
            raise BenchmarkError("CASE_DIGESTS_REQUIRED")

    @property
    def match_basis_digest(self) -> str:
        return _digest(
            "AURA_BUGHOUND_MATCH_BASIS_V1",
            {
                "case_digests": self.case_digests,
                "worker_budget": self.worker_budget,
                "tool_budget": self.tool_budget,
                "source_generation": self.source_generation,
                "fixed_patch_visible": self.fixed_patch_visible,
            },
        )

    @property
    def run_plan_digest(self) -> str:
        return _digest(
            "AURA_BUGHOUND_RUN_PLAN_V1",
            {
                "topology_id": self.topology_id,
                "topology_name": TOPOLOGY_REGISTRY[self.topology_id],
                "match_basis_digest": self.match_basis_digest,
                "schema": self.schema,
            },
        )


def build_matched_plan(
    topology_id: str,
    cases: Sequence[SeedBugCaseV1],
    *,
    worker_budget: int = 1,
    tool_budget: int = 1,
    source_generation: str = "BUGHOUND-SEEDLAB-V1",
    fixed_patch_visible: bool = False,
) -> MatchedRunPlanV1:
    return MatchedRunPlanV1(
        topology_id=topology_id,
        case_digests=tuple(case.case_digest for case in cases),
        worker_budget=worker_budget,
        tool_budget=tool_budget,
        source_generation=source_generation,
        fixed_patch_visible=fixed_patch_visible,
    )


@dataclass(frozen=True)
class BenchmarkScoreV1:
    topology_id: str
    match_basis_digest: str
    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int
    recall: float | None
    precision: float | None
    false_positive_rate: float | None
    localization_accuracy: float | None
    leakage_state: str
    valid_for_comparison: bool
    observed_metrics_only: bool = True
    authority: bool = False
    external_effect: bool = False
    promotion_authorized: bool = False

    @property
    def digest(self) -> str:
        return _digest("AURA_BUGHOUND_BENCHMARK_SCORE_V1", asdict(self))


def score_findings(
    plan: MatchedRunPlanV1,
    cases: Sequence[SeedBugCaseV1],
    findings: Iterable[FindingV1],
    *,
    fixed_patch_visible_case_ids: Iterable[str] = (),
) -> BenchmarkScoreV1:
    expected_digests = tuple(case.case_digest for case in cases)
    if expected_digests != plan.case_digests:
        raise BenchmarkError("PLAN_CASE_SET_MISMATCH")

    by_case: dict[str, FindingV1] = {}
    for finding in findings:
        if finding.case_id in by_case:
            raise BenchmarkError("DUPLICATE_FINDING", finding.case_id)
        by_case[finding.case_id] = finding
    unknown = sorted(set(by_case) - {case.case_id for case in cases})
    if unknown:
        raise BenchmarkError("FINDING_CASE_UNKNOWN", ",".join(unknown))

    exposed = set(fixed_patch_visible_case_ids)
    holdout_exposed = sorted(
        case.case_id
        for case in cases
        if case.visibility is Visibility.HOLDOUT and case.case_id in exposed
    )
    leakage_state = "LEAKAGE_INVALIDATED" if (plan.fixed_patch_visible or holdout_exposed) else "CLEAN_HOLDOUT"
    valid = leakage_state == "CLEAN_HOLDOUT"

    tp = fp = fn = tn = 0
    localized_hits = localized_total = 0
    for case in cases:
        finding = by_case.get(case.case_id)
        predicted = bool(finding and finding.detected)
        if case.is_bug and predicted:
            tp += 1
            localized_total += 1
            if case.expected_symbol in finding.localized_symbols:
                localized_hits += 1
        elif case.is_bug and not predicted:
            fn += 1
        elif not case.is_bug and predicted:
            fp += 1
        else:
            tn += 1

    recall = tp / (tp + fn) if (tp + fn) else None
    precision = tp / (tp + fp) if (tp + fp) else None
    fpr = fp / (fp + tn) if (fp + tn) else None
    localization = localized_hits / localized_total if localized_total else None
    return BenchmarkScoreV1(
        topology_id=plan.topology_id,
        match_basis_digest=plan.match_basis_digest,
        true_positive=tp,
        false_positive=fp,
        false_negative=fn,
        true_negative=tn,
        recall=recall,
        precision=precision,
        false_positive_rate=fpr,
        localization_accuracy=localization,
        leakage_state=leakage_state,
        valid_for_comparison=valid,
    )


def oracle_self_test_findings(cases: Sequence[SeedBugCaseV1]) -> tuple[FindingV1, ...]:
    """Ground-truth harness self-test only; never counts as BugHound candidate performance."""
    findings: list[FindingV1] = []
    for case in cases:
        outcome = run_harness_oracle(case)
        if not outcome.ground_truth_consistent:
            raise BenchmarkError("GROUND_TRUTH_INCONSISTENT", case.case_id)
        findings.append(
            FindingV1(
                case_id=case.case_id,
                detected=case.is_bug,
                localized_symbols=(case.expected_symbol,) if case.is_bug else (),
                finding_ref="HARNESS_ORACLE_ONLY",
                evidence_class="HARNESS_ORACLE_SELF_TEST",
            )
        )
    return tuple(findings)
