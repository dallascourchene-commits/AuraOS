"""BugHound O12: evaluator-sealed hardness frontier for historical-blind benchmarks.

D0 benchmark infrastructure only. This module does not scan targets, execute exploits,
or grant operational authority. Hardness is a declared benchmark policy over evaluator-only
facts, not an ontological truth about a vulnerability.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from itertools import product
import json
import math
from typing import Iterable, Mapping, Sequence

AXES = (
    "interprocedural_hops",
    "cross_file_span",
    "trace_depth",
    "statefulness",
    "control_flow_ambiguity",
    "historical_signal_scarcity",
    "oracle_cost",
    "patch_distance",
)

EFFECT_CEILING = "D0_BENCHMARK_ONLY"
HARDNESS_DOMAIN = "BUGHOUND-HARDNESS-FRONTIER-V1"


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: object) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _require_digest(name: str, value: str) -> None:
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")


@dataclass(frozen=True)
class RawHardnessFactsV1:
    """Evaluator-only measurable facts.

    The first three count axes are factual observations. The remaining five ordinal axes are explicit
    evaluator classifications in {0,1,2}; they must be independently reviewable and are
    bound into the evaluator seal. None are solver-visible.
    """

    interprocedural_hops: int
    cross_file_span: int
    trace_depth: int
    statefulness: int
    control_flow_ambiguity: int
    historical_signal_scarcity: int
    oracle_cost: int
    patch_distance: int

    def validate(self) -> None:
        if self.interprocedural_hops < 0:
            raise ValueError("interprocedural_hops must be >= 0")
        if self.cross_file_span < 1:
            raise ValueError("cross_file_span must be >= 1")
        if self.trace_depth < 1:
            raise ValueError("trace_depth must be >= 1")
        for name in (
            "statefulness",
            "control_flow_ambiguity",
            "historical_signal_scarcity",
            "oracle_cost",
            "patch_distance",
        ):
            if getattr(self, name) not in (0, 1, 2):
                raise ValueError(f"{name} must be 0, 1, or 2")


@dataclass(frozen=True)
class HardnessPolicyV1:
    """Explicit benchmark-local binning and noncompensatory claim policy."""

    interproc_medium: int = 2
    interproc_high: int = 5
    files_medium: int = 2
    files_high: int = 4
    trace_medium: int = 3
    trace_high: int = 6
    hard_tail_min_high_axes: int = 2
    extreme_min_high_axes: int = 4
    min_slice_cases: int = 8
    hard_tail_recall_floor: float = 0.50
    per_axis_high_recall_floor: float = 0.40
    confidence_z: float = 1.959963984540054

    def validate(self) -> None:
        if not (0 < self.interproc_medium < self.interproc_high):
            raise ValueError("bad interprocedural thresholds")
        if not (1 <= self.files_medium < self.files_high):
            raise ValueError("bad file thresholds")
        if not (1 <= self.trace_medium < self.trace_high):
            raise ValueError("bad trace thresholds")
        if not (1 <= self.hard_tail_min_high_axes <= len(AXES)):
            raise ValueError("bad hard tail threshold")
        if not (self.hard_tail_min_high_axes <= self.extreme_min_high_axes <= len(AXES)):
            raise ValueError("bad extreme threshold")
        if self.min_slice_cases < 1:
            raise ValueError("min_slice_cases must be >= 1")
        for name in ("hard_tail_recall_floor", "per_axis_high_recall_floor"):
            value = getattr(self, name)
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"{name} must be in [0,1]")
        if self.confidence_z <= 0:
            raise ValueError("confidence_z must be positive")

    @property
    def digest(self) -> str:
        self.validate()
        return _digest({"domain": HARDNESS_DOMAIN, "policy": asdict(self)})


@dataclass(frozen=True)
class HardnessVectorV1:
    levels: tuple[int, int, int, int, int, int, int, int]

    def validate(self) -> None:
        if len(self.levels) != len(AXES) or any(level not in (0, 1, 2) for level in self.levels):
            raise ValueError("hardness vector must contain exactly eight ternary levels")

    def as_map(self) -> dict[str, int]:
        self.validate()
        return dict(zip(AXES, self.levels, strict=True))

    @property
    def high_axis_count(self) -> int:
        self.validate()
        return sum(level == 2 for level in self.levels)


@dataclass(frozen=True)
class EvaluatorHardnessSealV1:
    opaque_target: str
    benchmark_semantic_root: str
    historical_cut_digest: str
    corpus_generation: str
    evaluator_generation: str
    policy_digest: str
    facts_digest: str
    vector: HardnessVectorV1
    stratum: str
    seal_digest: str
    evaluator_only: bool = True
    effect_ceiling: str = EFFECT_CEILING

    def solver_projection(self) -> dict[str, str]:
        """The only legal solver-facing projection: no hardness metadata."""
        return {
            "opaque_target": self.opaque_target,
            "instruction": "Inspect the provided historical source snapshot for security defects.",
        }


@dataclass(frozen=True)
class CaseOutcomeV1:
    opaque_target: str
    discovered: bool


@dataclass(frozen=True)
class BinomialIntervalV1:
    successes: int
    trials: int
    point: float | None
    low: float | None
    high: float | None


@dataclass(frozen=True)
class HardnessFrontierReportV1:
    benchmark_semantic_root: str
    historical_cut_digest: str
    policy_digest: str
    case_set_digest: str
    evaluator_generation: str
    overall: BinomialIntervalV1
    strata: Mapping[str, BinomialIntervalV1]
    axis_high: Mapping[str, BinomialIntervalV1]
    hard_tail: BinomialIntervalV1
    extreme_frontier: BinomialIntervalV1
    claim_status: str
    unmet_debts: tuple[str, ...]
    report_digest: str
    generalized_real_world_superiority: bool = False
    effect_ceiling: str = EFFECT_CEILING


def _bin_level(value: int, medium: int, high: int) -> int:
    if value >= high:
        return 2
    if value >= medium:
        return 1
    return 0


def vectorize(facts: RawHardnessFactsV1, policy: HardnessPolicyV1) -> HardnessVectorV1:
    facts.validate()
    policy.validate()
    vector = HardnessVectorV1(
        (
            _bin_level(facts.interprocedural_hops, policy.interproc_medium, policy.interproc_high),
            _bin_level(facts.cross_file_span, policy.files_medium, policy.files_high),
            _bin_level(facts.trace_depth, policy.trace_medium, policy.trace_high),
            facts.statefulness,
            facts.control_flow_ambiguity,
            facts.historical_signal_scarcity,
            facts.oracle_cost,
            facts.patch_distance,
        )
    )
    vector.validate()
    return vector


def stratum_for(vector: HardnessVectorV1, policy: HardnessPolicyV1) -> str:
    vector.validate()
    policy.validate()
    high = vector.high_axis_count
    if high >= policy.extreme_min_high_axes:
        return "EXTREME_FRONTIER"
    if high >= policy.hard_tail_min_high_axes:
        return "HARD_TAIL"
    if any(level == 2 for level in vector.levels) or sum(level == 1 for level in vector.levels) >= 3:
        return "MID_COMPLEX"
    return "EASY_CORE"


def _evaluator_seal_body(
    *,
    opaque_target: str,
    benchmark_semantic_root: str,
    historical_cut_digest: str,
    corpus_generation: str,
    evaluator_generation: str,
    policy_digest: str,
    facts_digest: str,
    vector: HardnessVectorV1,
    stratum: str,
    evaluator_only: bool,
    effect_ceiling: str,
) -> dict[str, object]:
    return {
        "domain": HARDNESS_DOMAIN,
        "opaque_target": opaque_target,
        "benchmark_semantic_root": benchmark_semantic_root,
        "historical_cut_digest": historical_cut_digest,
        "corpus_generation": corpus_generation,
        "evaluator_generation": evaluator_generation,
        "policy_digest": policy_digest,
        "facts_digest": facts_digest,
        "vector": vector.levels,
        "stratum": stratum,
        "evaluator_only": evaluator_only,
        "effect_ceiling": effect_ceiling,
    }


def validate_evaluator_seal(seal: EvaluatorHardnessSealV1, policy: HardnessPolicyV1) -> None:
    seal.vector.validate()
    _require_digest("benchmark_semantic_root", seal.benchmark_semantic_root)
    _require_digest("historical_cut_digest", seal.historical_cut_digest)
    _require_digest("policy_digest", seal.policy_digest)
    _require_digest("facts_digest", seal.facts_digest)
    _require_digest("seal_digest", seal.seal_digest)
    if not seal.evaluator_only:
        raise ValueError("hardness seal must remain evaluator-only")
    if seal.effect_ceiling != EFFECT_CEILING:
        raise ValueError("hardness seal exceeds D0 benchmark effect ceiling")
    if seal.policy_digest != policy.digest:
        raise ValueError("hardness policy drift")
    if stratum_for(seal.vector, policy) != seal.stratum:
        raise ValueError("hardness stratum is inconsistent with sealed vector")
    expected = _digest(_evaluator_seal_body(
        opaque_target=seal.opaque_target,
        benchmark_semantic_root=seal.benchmark_semantic_root,
        historical_cut_digest=seal.historical_cut_digest,
        corpus_generation=seal.corpus_generation,
        evaluator_generation=seal.evaluator_generation,
        policy_digest=seal.policy_digest,
        facts_digest=seal.facts_digest,
        vector=seal.vector,
        stratum=seal.stratum,
        evaluator_only=seal.evaluator_only,
        effect_ceiling=seal.effect_ceiling,
    ))
    if expected != seal.seal_digest:
        raise ValueError("hardness evaluator seal digest mismatch")


def compile_evaluator_seal(
    *,
    opaque_target: str,
    benchmark_semantic_root: str,
    historical_cut_digest: str,
    corpus_generation: str,
    evaluator_generation: str,
    facts: RawHardnessFactsV1,
    policy: HardnessPolicyV1,
) -> EvaluatorHardnessSealV1:
    if not opaque_target or not evaluator_generation or not corpus_generation:
        raise ValueError("identity fields must be nonempty")
    _require_digest("benchmark_semantic_root", benchmark_semantic_root)
    _require_digest("historical_cut_digest", historical_cut_digest)
    vector = vectorize(facts, policy)
    facts_digest = _digest({"domain": HARDNESS_DOMAIN, "facts": asdict(facts)})
    stratum = stratum_for(vector, policy)
    body = _evaluator_seal_body(
        opaque_target=opaque_target,
        benchmark_semantic_root=benchmark_semantic_root,
        historical_cut_digest=historical_cut_digest,
        corpus_generation=corpus_generation,
        evaluator_generation=evaluator_generation,
        policy_digest=policy.digest,
        facts_digest=facts_digest,
        vector=vector,
        stratum=stratum,
        evaluator_only=True,
        effect_ceiling=EFFECT_CEILING,
    )
    return EvaluatorHardnessSealV1(
        opaque_target=opaque_target,
        benchmark_semantic_root=benchmark_semantic_root,
        historical_cut_digest=historical_cut_digest,
        corpus_generation=corpus_generation,
        evaluator_generation=evaluator_generation,
        policy_digest=policy.digest,
        facts_digest=facts_digest,
        vector=vector,
        stratum=stratum,
        seal_digest=_digest(body),
    )


def validate_solver_projection(projection: Mapping[str, object]) -> None:
    allowed = {"opaque_target", "instruction"}
    if set(projection) != allowed:
        raise ValueError("solver projection contains evaluator-only or unknown fields")
    if not isinstance(projection.get("opaque_target"), str) or not projection["opaque_target"]:
        raise ValueError("opaque target required")
    forbidden_tokens = tuple(axis.lower() for axis in AXES) + (
        "hard_tail",
        "extreme_frontier",
        "facts_digest",
        "policy_digest",
        "seal_digest",
        "vulnerability",
        "cve-",
        "ghsa-",
    )
    text = _canonical(projection).lower()
    if any(token in text for token in forbidden_tokens):
        raise ValueError("solver projection leaks evaluator or vulnerability metadata")


def wilson_interval(successes: int, trials: int, z: float) -> BinomialIntervalV1:
    if successes < 0 or trials < 0 or successes > trials:
        raise ValueError("invalid binomial counts")
    if z <= 0:
        raise ValueError("z must be positive")
    if trials == 0:
        return BinomialIntervalV1(successes=0, trials=0, point=None, low=None, high=None)
    p = successes / trials
    z2 = z * z
    denom = 1.0 + z2 / trials
    center = (p + z2 / (2.0 * trials)) / denom
    radius = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * trials)) / trials) / denom
    return BinomialIntervalV1(
        successes=successes,
        trials=trials,
        point=p,
        low=max(0.0, center - radius),
        high=min(1.0, center + radius),
    )


def _slice_interval(items: Iterable[tuple[EvaluatorHardnessSealV1, bool]], z: float) -> BinomialIntervalV1:
    rows = list(items)
    return wilson_interval(sum(discovered for _, discovered in rows), len(rows), z)


def _case_set_digest(seals: Sequence[EvaluatorHardnessSealV1]) -> str:
    return _digest(
        {
            "domain": HARDNESS_DOMAIN,
            "cases": sorted((seal.opaque_target, seal.seal_digest) for seal in seals),
        }
    )


def build_frontier_report(
    seals: Sequence[EvaluatorHardnessSealV1],
    outcomes: Sequence[CaseOutcomeV1],
    *,
    expected_benchmark_semantic_root: str,
    expected_historical_cut_digest: str,
    expected_evaluator_generation: str,
    policy: HardnessPolicyV1,
) -> HardnessFrontierReportV1:
    policy.validate()
    _require_digest("expected_benchmark_semantic_root", expected_benchmark_semantic_root)
    _require_digest("expected_historical_cut_digest", expected_historical_cut_digest)
    if not seals:
        raise ValueError("at least one evaluator seal is required")
    if len({s.opaque_target for s in seals}) != len(seals):
        raise ValueError("duplicate evaluator target")
    if len({o.opaque_target for o in outcomes}) != len(outcomes):
        raise ValueError("duplicate outcome target")
    outcome_map = {o.opaque_target: o.discovered for o in outcomes}
    if set(outcome_map) != {s.opaque_target for s in seals}:
        raise ValueError("outcome case set must exactly match evaluator seals")

    for seal in seals:
        validate_evaluator_seal(seal, policy)
        if seal.benchmark_semantic_root != expected_benchmark_semantic_root:
            raise ValueError("benchmark semantic root drift")
        if seal.historical_cut_digest != expected_historical_cut_digest:
            raise ValueError("historical cut drift")
        if seal.evaluator_generation != expected_evaluator_generation:
            raise ValueError("evaluator generation drift")
        validate_solver_projection(seal.solver_projection())

    joined = [(seal, outcome_map[seal.opaque_target]) for seal in seals]
    overall = _slice_interval(joined, policy.confidence_z)
    strata: dict[str, BinomialIntervalV1] = {}
    for name in ("EASY_CORE", "MID_COMPLEX", "HARD_TAIL", "EXTREME_FRONTIER"):
        strata[name] = _slice_interval((row for row in joined if row[0].stratum == name), policy.confidence_z)
    axis_high: dict[str, BinomialIntervalV1] = {}
    for index, axis in enumerate(AXES):
        axis_high[axis] = _slice_interval((row for row in joined if row[0].vector.levels[index] == 2), policy.confidence_z)
    hard_tail = _slice_interval(
        (row for row in joined if row[0].vector.high_axis_count >= policy.hard_tail_min_high_axes),
        policy.confidence_z,
    )
    extreme = _slice_interval(
        (row for row in joined if row[0].vector.high_axis_count >= policy.extreme_min_high_axes),
        policy.confidence_z,
    )

    debts: list[str] = []
    if hard_tail.trials < policy.min_slice_cases:
        debts.append("INSUFFICIENT_HARD_TAIL_CASES")
    elif hard_tail.low is None or hard_tail.low < policy.hard_tail_recall_floor:
        debts.append("HARD_TAIL_RECALL_FLOOR_NOT_MET")
    for axis in AXES:
        interval = axis_high[axis]
        if interval.trials < policy.min_slice_cases:
            debts.append(f"INSUFFICIENT_HIGH_AXIS_CASES:{axis}")
        elif interval.low is None or interval.low < policy.per_axis_high_recall_floor:
            debts.append(f"HIGH_AXIS_RECALL_FLOOR_NOT_MET:{axis}")

    status = "HARDNESS_FRONTIER_COVERAGE_SUPPORTED" if not debts else "HOLD_HARDNESS_FRONTIER_DEBT"
    report_body = {
        "domain": HARDNESS_DOMAIN,
        "benchmark_semantic_root": expected_benchmark_semantic_root,
        "historical_cut_digest": expected_historical_cut_digest,
        "policy_digest": policy.digest,
        "case_set_digest": _case_set_digest(seals),
        "evaluator_generation": expected_evaluator_generation,
        "overall": asdict(overall),
        "strata": {k: asdict(v) for k, v in sorted(strata.items())},
        "axis_high": {k: asdict(v) for k, v in sorted(axis_high.items())},
        "hard_tail": asdict(hard_tail),
        "extreme_frontier": asdict(extreme),
        "claim_status": status,
        "unmet_debts": debts,
        "generalized_real_world_superiority": False,
        "effect_ceiling": EFFECT_CEILING,
    }
    return HardnessFrontierReportV1(
        benchmark_semantic_root=expected_benchmark_semantic_root,
        historical_cut_digest=expected_historical_cut_digest,
        policy_digest=policy.digest,
        case_set_digest=report_body["case_set_digest"],
        evaluator_generation=expected_evaluator_generation,
        overall=overall,
        strata=strata,
        axis_high=axis_high,
        hard_tail=hard_tail,
        extreme_frontier=extreme,
        claim_status=status,
        unmet_debts=tuple(debts),
        report_digest=_digest(report_body),
    )


def omega8_lattice() -> tuple[HardnessVectorV1, ...]:
    """Exact 3^8 challenge lattice over the eight ternary hardness axes."""
    return tuple(HardnessVectorV1(tuple(cell)) for cell in product((0, 1, 2), repeat=len(AXES)))


def k27_coordinate(url: str) -> tuple[int, int, int, str]:
    """Retrieval coordinate only: first three SHA-256 bytes mod 27 + full digest."""
    if not url.startswith(("https://", "http://")):
        raise ValueError("absolute http(s) URL required")
    digest = sha256(url.encode("utf-8")).digest()
    full = sha256(url.encode("utf-8")).hexdigest()
    return digest[0] % 27, digest[1] % 27, digest[2] % 27, full
