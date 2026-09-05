from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Sequence

SCHEMA = "AURA-WORKLOAD-CONTAMINATION-GATE-v1"
RECEIPT_SCHEMA = "AURA-WORKLOAD-CONTAMINATION-RECEIPT-v1"


class WorkloadGateError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise WorkloadGateError("NON_CANONICAL_VALUE") from exc


def digest(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value:
        raise WorkloadGateError(f"INVALID_{name.upper()}")


class Decision(str, Enum):
    READY_NONAUTHORIZING = "READY_NONAUTHORIZING"
    HOLD_TRACE_INVALID = "HOLD_TRACE_INVALID"
    HOLD_ENVELOPE_MISMATCH = "HOLD_ENVELOPE_MISMATCH"
    HOLD_SOURCE_GENERATION_MISMATCH = "HOLD_SOURCE_GENERATION_MISMATCH"
    HOLD_STALE_SOURCE = "HOLD_STALE_SOURCE"
    HOLD_PREFIX_CONTAMINATION = "HOLD_PREFIX_CONTAMINATION"
    HOLD_INSUFFICIENT_RANKING_CLASSES = "HOLD_INSUFFICIENT_RANKING_CLASSES"
    HOLD_AUTHORITY_CEILING = "HOLD_AUTHORITY_CEILING"


@dataclass(frozen=True)
class TraceWitness:
    trace_root: str
    replay_receipt_root: str
    envelope_root: str
    atomic_semantics_preserved: bool

    def validate(self) -> None:
        _nonempty("trace_root", self.trace_root)
        _nonempty("replay_receipt_root", self.replay_receipt_root)
        _nonempty("envelope_root", self.envelope_root)
        if type(self.atomic_semantics_preserved) is not bool:
            raise WorkloadGateError("INVALID_ATOMIC_SEMANTICS_FLAG")


@dataclass(frozen=True)
class WorkloadSample:
    sample_id: str
    category: str
    template_id: str
    rendered_generation_prefix: str
    source_generation: str
    trace: TraceWitness
    ranking_eligible: bool = True
    control_group: str | None = None

    def validate(self) -> None:
        for name, value in (
            ("sample_id", self.sample_id),
            ("category", self.category),
            ("template_id", self.template_id),
            ("rendered_generation_prefix", self.rendered_generation_prefix),
            ("source_generation", self.source_generation),
        ):
            _nonempty(name, value)
        self.trace.validate()
        if type(self.ranking_eligible) is not bool:
            raise WorkloadGateError("INVALID_RANKING_ELIGIBILITY")
        if self.control_group is not None:
            _nonempty("control_group", self.control_group)
        if not self.ranking_eligible and self.control_group is None:
            raise WorkloadGateError("NONRANKING_SAMPLE_REQUIRES_CONTROL_GROUP")

    @property
    def prefix_root(self) -> str:
        return digest({"rendered_generation_prefix": self.rendered_generation_prefix})

    def canonical(self) -> dict[str, Any]:
        self.validate()
        return {
            "sample_id": self.sample_id,
            "category": self.category,
            "template_id": self.template_id,
            "prefix_root": self.prefix_root,
            "source_generation": self.source_generation,
            "trace_root": self.trace.trace_root,
            "replay_receipt_root": self.trace.replay_receipt_root,
            "envelope_root": self.trace.envelope_root,
            "atomic_semantics_preserved": self.trace.atomic_semantics_preserved,
            "ranking_eligible": self.ranking_eligible,
            "control_group": self.control_group,
        }


@dataclass(frozen=True)
class WorkloadBatch:
    benchmark_id: str
    benchmark_generation: str
    source_generation: str
    envelope_root: str
    source_current: bool
    samples: tuple[WorkloadSample, ...]
    asks_effect_authority: bool = False

    def validate_structure(self) -> None:
        for name, value in (
            ("benchmark_id", self.benchmark_id),
            ("benchmark_generation", self.benchmark_generation),
            ("source_generation", self.source_generation),
            ("envelope_root", self.envelope_root),
        ):
            _nonempty(name, value)
        if type(self.source_current) is not bool:
            raise WorkloadGateError("INVALID_CURRENTNESS_FLAG")
        if type(self.asks_effect_authority) is not bool:
            raise WorkloadGateError("INVALID_AUTHORITY_FLAG")
        if not isinstance(self.samples, tuple) or not self.samples:
            raise WorkloadGateError("NONEMPTY_SAMPLE_TUPLE_REQUIRED")
        ids: set[str] = set()
        for sample in self.samples:
            if type(sample) is not WorkloadSample:
                raise WorkloadGateError("INVALID_SAMPLE_TYPE")
            sample.validate()
            if sample.sample_id in ids:
                raise WorkloadGateError("DUPLICATE_SAMPLE_ID")
            ids.add(sample.sample_id)


@dataclass(frozen=True)
class PrefixCollision:
    prefix_root: str
    categories: tuple[str, ...]
    sample_ids: tuple[str, ...]


@dataclass(frozen=True)
class WorkloadContaminationReceipt:
    schema: str
    benchmark_id: str
    benchmark_generation: str
    decision: Decision
    batch_root: str
    ranking_sample_count: int
    ranking_category_count: int
    trace_invalid_sample_ids: tuple[str, ...]
    envelope_mismatch_sample_ids: tuple[str, ...]
    source_generation_mismatch_sample_ids: tuple[str, ...]
    prefix_collisions: tuple[PrefixCollision, ...]
    control_sample_count: int
    policy_ranking_eligible: bool
    truth_authority: bool = False
    effect_authority: bool = False
    gate10: bool = False

    @property
    def receipt_root(self) -> str:
        payload = asdict(self)
        payload["decision"] = self.decision.value
        return digest(payload)


class WorkloadContaminationGate:
    """Proof-only benchmark-workload identity gate.

    Router semantics, cache-policy ranking, physical performance, energy admission,
    and effect authority remain owned elsewhere. Intentional prefix-sharing controls
    are admitted only as non-ranking samples.
    """

    def assess(self, batch: WorkloadBatch) -> WorkloadContaminationReceipt:
        batch.validate_structure()
        trace_invalid = tuple(sorted(
            s.sample_id for s in batch.samples if not s.trace.atomic_semantics_preserved
        ))
        envelope_mismatch = tuple(sorted(
            s.sample_id for s in batch.samples if s.trace.envelope_root != batch.envelope_root
        ))
        source_mismatch = tuple(sorted(
            s.sample_id for s in batch.samples if s.source_generation != batch.source_generation
        ))
        ranking = tuple(s for s in batch.samples if s.ranking_eligible)
        categories = tuple(sorted({s.category for s in ranking}))

        by_prefix: dict[str, list[WorkloadSample]] = {}
        for sample in ranking:
            by_prefix.setdefault(sample.prefix_root, []).append(sample)
        collisions: list[PrefixCollision] = []
        for prefix_root, members in sorted(by_prefix.items()):
            member_categories = tuple(sorted({s.category for s in members}))
            if len(member_categories) > 1:
                collisions.append(PrefixCollision(
                    prefix_root=prefix_root,
                    categories=member_categories,
                    sample_ids=tuple(sorted(s.sample_id for s in members)),
                ))

        batch_root = digest({
            "schema": SCHEMA,
            "benchmark_id": batch.benchmark_id,
            "benchmark_generation": batch.benchmark_generation,
            "source_generation": batch.source_generation,
            "envelope_root": batch.envelope_root,
            "source_current": batch.source_current,
            "samples": [s.canonical() for s in batch.samples],
            "asks_effect_authority": batch.asks_effect_authority,
        })

        if trace_invalid:
            decision = Decision.HOLD_TRACE_INVALID
        elif envelope_mismatch:
            decision = Decision.HOLD_ENVELOPE_MISMATCH
        elif source_mismatch:
            decision = Decision.HOLD_SOURCE_GENERATION_MISMATCH
        elif not batch.source_current:
            decision = Decision.HOLD_STALE_SOURCE
        elif collisions:
            decision = Decision.HOLD_PREFIX_CONTAMINATION
        elif len(categories) < 2:
            decision = Decision.HOLD_INSUFFICIENT_RANKING_CLASSES
        elif batch.asks_effect_authority:
            decision = Decision.HOLD_AUTHORITY_CEILING
        else:
            decision = Decision.READY_NONAUTHORIZING

        return WorkloadContaminationReceipt(
            schema=RECEIPT_SCHEMA,
            benchmark_id=batch.benchmark_id,
            benchmark_generation=batch.benchmark_generation,
            decision=decision,
            batch_root=batch_root,
            ranking_sample_count=len(ranking),
            ranking_category_count=len(categories),
            trace_invalid_sample_ids=trace_invalid,
            envelope_mismatch_sample_ids=envelope_mismatch,
            source_generation_mismatch_sample_ids=source_mismatch,
            prefix_collisions=tuple(collisions),
            control_sample_count=len(batch.samples) - len(ranking),
            policy_ranking_eligible=decision == Decision.READY_NONAUTHORIZING,
        )


def crystalline_admission(omega8: Sequence[int]) -> bool:
    if len(omega8) != 8 or any(type(v) is not int or v not in (0, 1, 2) for v in omega8):
        raise WorkloadGateError("INVALID_OMEGA8")
    return tuple(omega8) == (2, 2, 2, 2, 2, 2, 2, 1)


def sample(
    i: int,
    category: str,
    prefix: str,
    *,
    source_generation: str = "src-g1",
    envelope_root: str = "env-root",
    atomic: bool = True,
    ranking_eligible: bool = True,
    control_group: str | None = None,
) -> WorkloadSample:
    return WorkloadSample(
        sample_id=f"s{i}",
        category=category,
        template_id=f"template-{category}",
        rendered_generation_prefix=prefix,
        source_generation=source_generation,
        trace=TraceWitness(
            trace_root=digest({"trace": i, "category": category}),
            replay_receipt_root=digest({"replay": i, "atomic": atomic}),
            envelope_root=envelope_root,
            atomic_semantics_preserved=atomic,
        ),
        ranking_eligible=ranking_eligible,
        control_group=control_group,
    )


def valid_batch() -> WorkloadBatch:
    return WorkloadBatch(
        benchmark_id="moe-cache-policy-bench",
        benchmark_generation="bench-g1",
        source_generation="src-g1",
        envelope_root="env-root",
        source_current=True,
        samples=(
            sample(1, "reasoning", "prefix::reasoning::1"),
            sample(2, "reasoning", "prefix::reasoning::2"),
            sample(3, "code", "prefix::code::1"),
            sample(4, "code", "prefix::code::2"),
        ),
    )
