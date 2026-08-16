"""WO-STAGE-002 / W2 — D0 falsifier-first mutation harness.

Standalone, dependency-free staged reference harness for:
- tri-valued PASS / FAIL / UNKNOWN semantics;
- reusable negative refutation cache keyed by
  (obligation_id, defeat_condition, validity_domain, generation);
- immediate short-circuit after the first definite FAIL;
- five canonical D0 mutant lanes;
- generation-coherence rejection for incompatible PASS receipts;
- formal STOP_SCALING assertion after synthetic evidence exhaustion.

Claim ceiling: synthetic staged reference only.  Not a production verifier,
cryptographic implementation, authority source, deployment, or canonical policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Mapping, MutableMapping, Optional, Sequence, Tuple


class Disposition(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class RefutationKey:
    obligation_id: str
    defeat_condition: str
    validity_domain: str
    generation: str

    def __post_init__(self) -> None:
        for name in ("obligation_id", "defeat_condition", "validity_domain", "generation"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class NegativeRefutation:
    key: RefutationKey
    reason: str
    evidence: Tuple[Tuple[str, str], ...] = ()


class NegativeRefutationCache:
    """FAIL-only cache. UNKNOWN/PASS are deliberately unrepresentable entries."""

    def __init__(self) -> None:
        self._entries: Dict[Tuple[str, str, str, str], NegativeRefutation] = {}
        self.hits = 0
        self.misses = 0

    @staticmethod
    def _key(key: RefutationKey) -> Tuple[str, str, str, str]:
        return (key.obligation_id, key.defeat_condition, key.validity_domain, key.generation)

    def lookup(self, key: RefutationKey) -> Optional[NegativeRefutation]:
        item = self._entries.get(self._key(key))
        if item is None:
            self.misses += 1
        else:
            self.hits += 1
        return item

    def record(self, refutation: NegativeRefutation) -> None:
        self._entries[self._key(refutation.key)] = refutation

    def invalidate_generation(self, generation: str) -> int:
        doomed = [k for k in self._entries if k[3] == generation]
        for key in doomed:
            del self._entries[key]
        return len(doomed)

    def __len__(self) -> int:
        return len(self._entries)


@dataclass(frozen=True, slots=True)
class ObligationResult:
    disposition: Disposition
    reason: str = ""
    evidence: Tuple[Tuple[str, str], ...] = ()
    reusable_refutation: bool = True


@dataclass(slots=True)
class CandidateClosure:
    closure_id: str
    facts: MutableMapping[str, Any] = field(default_factory=dict)
    refutation_cache: NegativeRefutationCache = field(default_factory=NegativeRefutationCache)


Evaluator = Callable[[CandidateClosure], ObligationResult]


@dataclass(frozen=True, slots=True)
class RequiredObligation:
    obligation_id: str
    defeat_condition: str
    validity_domain: str
    generation: str
    evaluator: Evaluator = field(compare=False, repr=False)
    cost_tier: int = 2
    estimated_cost: float = 1.0
    estimated_fail_probability: float = 0.0

    @property
    def key(self) -> RefutationKey:
        return RefutationKey(
            self.obligation_id,
            self.defeat_condition,
            self.validity_domain,
            self.generation,
        )


@dataclass(frozen=True, slots=True)
class ContainmentEvaluation:
    disposition: Disposition
    evaluated_obligations: Tuple[str, ...]
    first_failing_obligation: Optional[str] = None
    first_unknown_obligation: Optional[str] = None
    cache_hit: bool = False
    reason: str = ""


def order_for_falsification(obligations: Sequence[RequiredObligation]) -> Tuple[RequiredObligation, ...]:
    """Stable hard tiers, then trusted fail-probability-per-cost heuristic."""

    def score(o: RequiredObligation) -> tuple[int, float, str]:
        cost = max(o.estimated_cost, 1e-12)
        return (o.cost_tier, -(o.estimated_fail_probability / cost), o.obligation_id)

    return tuple(sorted(obligations, key=score))


def evaluate_containment_fast(
    candidate_closure: CandidateClosure,
    required_obligations: Sequence[RequiredObligation],
) -> ContainmentEvaluation:
    """FAIL short-circuits immediately; UNKNOWN remains first-class."""

    evaluated: list[str] = []
    first_unknown: Optional[ObligationResult] = None
    first_unknown_id: Optional[str] = None

    for obligation in order_for_falsification(required_obligations):
        cached = candidate_closure.refutation_cache.lookup(obligation.key)
        if cached is not None:
            return ContainmentEvaluation(
                Disposition.FAIL,
                tuple(evaluated),
                first_failing_obligation=obligation.obligation_id,
                first_unknown_obligation=first_unknown_id,
                cache_hit=True,
                reason=cached.reason,
            )

        result = obligation.evaluator(candidate_closure)
        evaluated.append(obligation.obligation_id)

        if result.disposition is Disposition.FAIL:
            if result.reusable_refutation:
                candidate_closure.refutation_cache.record(
                    NegativeRefutation(obligation.key, result.reason, result.evidence)
                )
            return ContainmentEvaluation(
                Disposition.FAIL,
                tuple(evaluated),
                first_failing_obligation=obligation.obligation_id,
                first_unknown_obligation=first_unknown_id,
                cache_hit=False,
                reason=result.reason,
            )

        if result.disposition is Disposition.UNKNOWN and first_unknown is None:
            first_unknown = result
            first_unknown_id = obligation.obligation_id

    if first_unknown is not None:
        return ContainmentEvaluation(
            Disposition.UNKNOWN,
            tuple(evaluated),
            first_unknown_obligation=first_unknown_id,
            reason=first_unknown.reason,
        )

    return ContainmentEvaluation(Disposition.PASS, tuple(evaluated))


def indexed_fact_obligation(
    *,
    obligation_id: str,
    defeat_condition: str,
    validity_domain: str,
    generation: str,
    fact_name: str,
    bad_value: object,
    reason: str,
    cost_tier: int = 1,
) -> RequiredObligation:
    def evaluator(candidate: CandidateClosure) -> ObligationResult:
        if fact_name not in candidate.facts or candidate.facts[fact_name] is None:
            return ObligationResult(
                Disposition.UNKNOWN,
                f"{obligation_id}: missing evidence for {fact_name}",
                reusable_refutation=False,
            )
        value = candidate.facts[fact_name]
        if value == bad_value:
            return ObligationResult(
                Disposition.FAIL,
                reason,
                evidence=(("fact", fact_name), ("value", repr(value))),
            )
        return ObligationResult(Disposition.PASS)

    return RequiredObligation(
        obligation_id=obligation_id,
        defeat_condition=defeat_condition,
        validity_domain=validity_domain,
        generation=generation,
        evaluator=evaluator,
        cost_tier=cost_tier,
        estimated_cost=1.0,
        estimated_fail_probability=0.9,
    )


@dataclass(frozen=True, slots=True)
class PassReceipt:
    receipt_id: str
    disposition: Disposition
    world_generation: Optional[str]
    world_timestamp: Optional[int]


def verify_generation_coherence(
    receipts: Sequence[PassReceipt],
    *,
    required_generation: str,
    reference_world_timestamp: Optional[int] = None,
    allowed_skew: Optional[int] = None,
) -> Disposition:
    """Reject known cross-generation PASS bundles; preserve missing data as UNKNOWN."""

    saw_unknown = False
    for receipt in receipts:
        if receipt.disposition is Disposition.FAIL:
            return Disposition.FAIL
        if receipt.disposition is Disposition.UNKNOWN:
            saw_unknown = True
            continue
        if receipt.world_generation is None:
            saw_unknown = True
            continue
        if receipt.world_generation != required_generation:
            return Disposition.FAIL
        if allowed_skew is not None and reference_world_timestamp is not None:
            if receipt.world_timestamp is None:
                saw_unknown = True
                continue
            if abs(receipt.world_timestamp - reference_world_timestamp) > allowed_skew:
                return Disposition.FAIL
    return Disposition.UNKNOWN if saw_unknown else Disposition.PASS


GEN = "D0-G1"

CANONICAL_MUTANTS: Mapping[str, tuple[str, object, str, str]] = {
    "JOINT_MARGINAL_MUTANT": (
        "joint_dependency_complete",
        False,
        "JOINT_DEPENDENCY_NOT_REDUCIBLE_TO_MARGINALS",
        "decision-changing joint interaction was certified from marginals only",
    ),
    "OMISSION_MUTANT": (
        "required_evidence_present",
        False,
        "REQUIRED_EVIDENCE_OMITTED",
        "known required evidence was omitted",
    ),
    "RECURSIVE_SAME_BLINDSPOT": (
        "independent_defeat_path",
        False,
        "AUDITOR_SHARES_SAME_BLINDSPOT",
        "recursive checker is correlated with the same blind spot",
    ),
    "SELF_CERTIFIED_KNOWN_ONLY": (
        "external_wake_path",
        False,
        "KNOWN_ONLY_VIEW_SELF_CERTIFIES_COMPLETENESS",
        "known-only view self-certified completeness without an external wake path",
    ),
    "STALE_GENERATION_MUTANT": (
        "generation_current",
        False,
        "STALE_GENERATION",
        "closure evidence is stale relative to required generation",
    ),
}


def _must_not_run(_: CandidateClosure) -> ObligationResult:
    raise AssertionError("short-circuit violated: evaluator after definite FAIL was executed")


def run_harness(verbose: bool = True) -> dict[str, object]:
    cache = NegativeRefutationCache()
    mutant_dispositions: dict[str, str] = {}
    unsafe_passes = 0

    # Five canonical mutant lanes.
    for name, (fact_name, bad_value, defeat, reason) in CANONICAL_MUTANTS.items():
        domain = f"D0::{name}::fixture-v1"
        failing = indexed_fact_obligation(
            obligation_id=f"D0::{name}",
            defeat_condition=defeat,
            validity_domain=domain,
            generation=GEN,
            fact_name=fact_name,
            bad_value=bad_value,
            reason=reason,
            cost_tier=1,
        )
        sentinel = RequiredObligation(
            obligation_id=f"D0::{name}::EXPENSIVE_SENTINEL",
            defeat_condition="MUST_NOT_EXECUTE_AFTER_FAIL",
            validity_domain=domain,
            generation=GEN,
            evaluator=_must_not_run,
            cost_tier=4,
            estimated_cost=1000.0,
            estimated_fail_probability=0.01,
        )
        outcome = evaluate_containment_fast(
            CandidateClosure(name, {fact_name: bad_value}, cache),
            (sentinel, failing),  # input deliberately reversed; router must move cheap defeat first
        )
        mutant_dispositions[name] = outcome.disposition.value
        unsafe_passes += int(outcome.disposition is Disposition.PASS)
        assert outcome.disposition is Disposition.FAIL
        assert outcome.first_failing_obligation == f"D0::{name}"
        assert outcome.evaluated_obligations == (f"D0::{name}",)

    # Exact negative-cache reuse: second evaluator must not run.
    key = RefutationKey(
        "D0::CACHE_REUSE",
        "KNOWN_DEFEAT",
        "D0::CACHE_REUSE::fixture-v1",
        GEN,
    )
    calls = {"count": 0}

    def first_eval(_: CandidateClosure) -> ObligationResult:
        calls["count"] += 1
        return ObligationResult(Disposition.FAIL, "reusable exact defeat")

    first_ob = RequiredObligation(
        key.obligation_id,
        key.defeat_condition,
        key.validity_domain,
        key.generation,
        first_eval,
        cost_tier=1,
    )
    first = evaluate_containment_fast(CandidateClosure("cache-1", {}, cache), (first_ob,))
    assert first.disposition is Disposition.FAIL and calls["count"] == 1

    second_ob = RequiredObligation(
        key.obligation_id,
        key.defeat_condition,
        key.validity_domain,
        key.generation,
        _must_not_run,
        cost_tier=1,
    )
    second = evaluate_containment_fast(CandidateClosure("cache-2", {}, cache), (second_ob,))
    assert second.disposition is Disposition.FAIL and second.cache_hit
    assert second.evaluated_obligations == ()

    # UNKNOWN remains UNKNOWN; later FAIL still dominates.
    unknown_ob = RequiredObligation(
        "D0::UNKNOWN_CONTROL",
        "EXTERNAL_EVIDENCE_UNAVAILABLE",
        "D0::UNKNOWN_CONTROL",
        GEN,
        lambda _: ObligationResult(
            Disposition.UNKNOWN,
            "external evidence unavailable",
            reusable_refutation=False,
        ),
        cost_tier=1,
    )
    unknown_only = evaluate_containment_fast(CandidateClosure("unknown", {}, cache), (unknown_ob,))
    assert unknown_only.disposition is Disposition.UNKNOWN

    later_fail_ob = RequiredObligation(
        "D0::LATER_FAIL",
        "KNOWN_DEFEAT",
        "D0::UNKNOWN_THEN_FAIL",
        GEN,
        lambda _: ObligationResult(Disposition.FAIL, "later known defeat"),
        cost_tier=2,
    )
    unknown_then_fail = evaluate_containment_fast(
        CandidateClosure("unknown-then-fail", {}, cache),
        (unknown_ob, later_fail_ob),
    )
    assert unknown_then_fail.disposition is Disposition.FAIL

    # Generation isolation: cached G0 defeat must not poison G1.
    cache.record(NegativeRefutation(
        RefutationKey("D0::GEN_ISOLATION", "STALE_GENERATION", "D0::GEN_ISOLATION", "D0-G0"),
        "old generation defeat",
    ))
    g1 = RequiredObligation(
        "D0::GEN_ISOLATION",
        "STALE_GENERATION",
        "D0::GEN_ISOLATION",
        "D0-G1",
        lambda _: ObligationResult(Disposition.PASS),
        cost_tier=1,
    )
    generation_isolation = evaluate_containment_fast(CandidateClosure("g1", {}, cache), (g1,))
    assert generation_isolation.disposition is Disposition.PASS

    # Generation coherence matrix.
    coherent = verify_generation_coherence(
        (
            PassReceipt("r1", Disposition.PASS, "G7", 1000),
            PassReceipt("r2", Disposition.PASS, "G7", 1002),
        ),
        required_generation="G7",
        reference_world_timestamp=1000,
        allowed_skew=5,
    )
    incompatible = verify_generation_coherence(
        (
            PassReceipt("r1", Disposition.PASS, "G7", 1000),
            PassReceipt("r2", Disposition.PASS, "G8", 1000),
        ),
        required_generation="G7",
    )
    missing_generation = verify_generation_coherence(
        (PassReceipt("r1", Disposition.PASS, None, 1000),),
        required_generation="G7",
    )
    stale_timestamp = verify_generation_coherence(
        (PassReceipt("r1", Disposition.PASS, "G7", 1200),),
        required_generation="G7",
        reference_world_timestamp=1000,
        allowed_skew=5,
    )
    assert coherent is Disposition.PASS
    assert incompatible is Disposition.FAIL
    assert missing_generation is Disposition.UNKNOWN
    assert stale_timestamp is Disposition.FAIL

    rejected = sum(v != Disposition.PASS.value for v in mutant_dispositions.values())
    total = len(CANONICAL_MUTANTS)

    # D0 lineage halting assertion: synthetic evidence is exhausted at this boundary.
    STOP_SCALING = True
    STOP_SCALING_REASON = (
        "synthetic evidence exhausted; remaining residual requires production/source instrumentation"
    )
    assert STOP_SCALING is True

    summary = {
        "work_order": "WO-STAGE-002",
        "canonical_mutants": total,
        "rejected": rejected,
        "rejection_rate_percent": 100.0 * rejected / total,
        "unsafe_passes": unsafe_passes,
        "mutant_dispositions": mutant_dispositions,
        "unknown_control": unknown_only.disposition.value,
        "unknown_then_fail": unknown_then_fail.disposition.value,
        "cache_reuse_hit": second.cache_hit,
        "cache_reuse_evaluator_calls_after_first": calls["count"] - 1,
        "generation_isolation": generation_isolation.disposition.value,
        "generation_coherence": {
            "coherent_same_generation": coherent.value,
            "incompatible_generations": incompatible.value,
            "missing_generation": missing_generation.value,
            "stale_timestamp": stale_timestamp.value,
        },
        "stop_scaling": STOP_SCALING,
        "stop_scaling_reason": STOP_SCALING_REASON,
        "cache_entries": len(cache),
    }

    assert rejected == total
    assert unsafe_passes == 0

    if verbose:
        for name in CANONICAL_MUTANTS:
            print(f"{name}: {mutant_dispositions[name]}")
        print(f"UNKNOWN_CONTROL: {unknown_only.disposition.value}")
        print(f"UNKNOWN_THEN_FAIL: {unknown_then_fail.disposition.value}")
        print(f"GENERATION_COHERENCE_SAME: {coherent.value}")
        print(f"GENERATION_COHERENCE_MISMATCH: {incompatible.value}")
        print(f"STOP_SCALING: {STOP_SCALING}")
        print(f"D0 RESULT: {rejected}/{total} rejected; unsafe_passes={unsafe_passes}")

    return summary


if __name__ == "__main__":
    run_harness(verbose=True)
