"""Bounded ThinkPad owner-host benchmark evidence contract for K27 ASTGE.

This module validates the *shape and internal consistency* of a three-phase benchmark
receipt.  It does not execute a benchmark and deliberately does not infer physical
NVMe I/O, OS-page-cache coldness, device-cache coldness, W4 admission, or performance
policy from process-local counters.

The three phases are intentionally weaker than conventional "cold/warm/restart" names
can suggest:

* PROCESS_COLD: fresh benchmark process/local ASTGE state only.
* PROCESS_WARM: same process, same exact query sequence, after one completed phase.
* RESTART: a distinct process running the same exact query sequence.

None of those facts prove the Linux page cache or an NVMe device cache was cold.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Iterable

SCHEMA = "AuraK27ASTGEThinkPadOwnerHostBenchmarkV1"
PR459_REFERENCE_SHA = "a71d1c55af84973a29b28fdfa3db157056780e92"
PR459_REFERENCE_RUN = 33343082922
PR477_SAFE_SHA = "3d8f1e83fff13e622042543ca23c486008e19944"
PR477_SAFE_RUN = 33344540826
PHASES = ("PROCESS_COLD", "PROCESS_WARM", "RESTART")
MAX_ROOTS = 4096
MAX_DEPTH = 64
MAX_ITERATIONS = 1_000_000
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ThinkPadBenchmarkContractError(ValueError):
    """Typed fail-closed validation error."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ThinkPadBenchmarkContractError("NONCANONICAL_BENCHMARK_VALUE") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _require_sha256(name: str, value: str) -> None:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise ThinkPadBenchmarkContractError("INVALID_SHA256", name)


def _require_text(name: str, value: str) -> None:
    if type(value) is not str or not value.strip():
        raise ThinkPadBenchmarkContractError("INVALID_TEXT", name)


def _require_nonnegative_int(name: str, value: int) -> None:
    if type(value) is not int or value < 0:
        raise ThinkPadBenchmarkContractError("INVALID_NONNEGATIVE_INTEGER", name)


@dataclass(frozen=True)
class ThinkPadASTGEBenchmarkRequest:
    graph_sha256: str
    source_fixture_sha256: str
    root_node_ids: tuple[int, ...]
    max_depth: int
    iterations: int
    implementation_generation: str
    runner_generation: str
    host_snapshot_digest: str
    storage_plan_digest: str
    workload_label: str = "k27-astge-same-graph-cone-query"
    schema: str = SCHEMA
    process_cold_means_local_state_only: bool = True
    os_page_cache_cold_required: bool = False
    device_cache_cold_required: bool = False
    physical_io_claim_requested: bool = False
    performance_winner_claim_requested: bool = False
    effect_authority_requested: bool = False

    def __post_init__(self) -> None:
        _require_sha256("graph_sha256", self.graph_sha256)
        _require_sha256("source_fixture_sha256", self.source_fixture_sha256)
        _require_sha256("host_snapshot_digest", self.host_snapshot_digest)
        _require_sha256("storage_plan_digest", self.storage_plan_digest)
        _require_text("implementation_generation", self.implementation_generation)
        _require_text("runner_generation", self.runner_generation)
        _require_text("workload_label", self.workload_label)
        if self.schema != SCHEMA:
            raise ThinkPadBenchmarkContractError("REQUEST_SCHEMA_MISMATCH")
        if type(self.root_node_ids) is not tuple or not self.root_node_ids:
            raise ThinkPadBenchmarkContractError("ROOT_SEQUENCE_REQUIRED")
        if len(self.root_node_ids) > MAX_ROOTS:
            raise ThinkPadBenchmarkContractError("ROOT_SEQUENCE_TOO_LARGE")
        for root in self.root_node_ids:
            _require_nonnegative_int("root_node_id", root)
        if type(self.max_depth) is not int or not (0 <= self.max_depth <= MAX_DEPTH):
            raise ThinkPadBenchmarkContractError("MAX_DEPTH_OUT_OF_BOUNDS")
        if type(self.iterations) is not int or not (1 <= self.iterations <= MAX_ITERATIONS):
            raise ThinkPadBenchmarkContractError("ITERATIONS_OUT_OF_BOUNDS")
        for name in (
            "process_cold_means_local_state_only",
            "os_page_cache_cold_required",
            "device_cache_cold_required",
            "physical_io_claim_requested",
            "performance_winner_claim_requested",
            "effect_authority_requested",
        ):
            if type(getattr(self, name)) is not bool:
                raise ThinkPadBenchmarkContractError("STRICT_BOOLEAN_REQUIRED", name)
        if not self.process_cold_means_local_state_only:
            raise ThinkPadBenchmarkContractError("PROCESS_COLD_SCOPE_MUST_BE_LOCAL_ONLY")
        if self.os_page_cache_cold_required or self.device_cache_cold_required:
            raise ThinkPadBenchmarkContractError("UNPROVEN_COLDNESS_REQUIREMENT_FORBIDDEN")
        if (
            self.physical_io_claim_requested
            or self.performance_winner_claim_requested
            or self.effect_authority_requested
        ):
            raise ThinkPadBenchmarkContractError("REQUEST_AUTHORITY_WIDENING_FORBIDDEN")

    @property
    def query_count_per_phase(self) -> int:
        return len(self.root_node_ids) * self.iterations

    @property
    def query_sequence_sha256(self) -> str:
        return _digest(
            {
                "domain": "AURA-K27-ASTGE-QUERY-SEQUENCE-V1",
                "roots": self.root_node_ids,
                "max_depth": self.max_depth,
                "iterations": self.iterations,
            }
        )

    @property
    def request_digest(self) -> str:
        return _digest(asdict(self))


@dataclass(frozen=True)
class ThinkPadASTGEBenchmarkPhaseSample:
    phase: str
    request_digest: str
    query_sequence_sha256: str
    process_identity: str
    elapsed_ns: int
    query_count: int
    process_read_bytes_before: int
    process_read_bytes_after: int
    minor_faults_before: int
    minor_faults_after: int
    major_faults_before: int
    major_faults_after: int
    astge_page_requests: int
    astge_cache_hits: int
    astge_cache_misses: int
    device_read_bytes_before: int | None = None
    device_read_bytes_after: int | None = None

    def __post_init__(self) -> None:
        if self.phase not in PHASES:
            raise ThinkPadBenchmarkContractError("UNKNOWN_PHASE", self.phase)
        _require_sha256("request_digest", self.request_digest)
        _require_sha256("query_sequence_sha256", self.query_sequence_sha256)
        _require_text("process_identity", self.process_identity)
        for name in (
            "elapsed_ns",
            "query_count",
            "process_read_bytes_before",
            "process_read_bytes_after",
            "minor_faults_before",
            "minor_faults_after",
            "major_faults_before",
            "major_faults_after",
            "astge_page_requests",
            "astge_cache_hits",
            "astge_cache_misses",
        ):
            _require_nonnegative_int(name, getattr(self, name))
        if self.elapsed_ns == 0:
            raise ThinkPadBenchmarkContractError("ZERO_ELAPSED_TIME")
        if (self.device_read_bytes_before is None) != (self.device_read_bytes_after is None):
            raise ThinkPadBenchmarkContractError("PARTIAL_DEVICE_COUNTER_PAIR")
        if self.device_read_bytes_before is not None:
            _require_nonnegative_int("device_read_bytes_before", self.device_read_bytes_before)
            _require_nonnegative_int("device_read_bytes_after", self.device_read_bytes_after)

    @property
    def process_read_bytes_delta(self) -> int:
        return self.process_read_bytes_after - self.process_read_bytes_before

    @property
    def minor_faults_delta(self) -> int:
        return self.minor_faults_after - self.minor_faults_before

    @property
    def major_faults_delta(self) -> int:
        return self.major_faults_after - self.major_faults_before

    @property
    def device_read_bytes_delta(self) -> int | None:
        if self.device_read_bytes_before is None:
            return None
        assert self.device_read_bytes_after is not None
        return self.device_read_bytes_after - self.device_read_bytes_before


@dataclass(frozen=True)
class ThinkPadASTGEBenchmarkReceipt:
    request_digest: str
    query_sequence_sha256: str
    host_observation_id: str
    runner_identity: str
    runner_generation: str
    phase_summaries: tuple[dict[str, Any], ...]
    same_graph_workload_proven: bool = True
    process_cold_scope_proven: bool = True
    process_warm_same_process_proven: bool = True
    restart_new_process_proven: bool = True
    logical_page_accounting_proven: bool = True
    process_storage_counter_monotonicity_proven: bool = True
    page_fault_counter_monotonicity_proven: bool = True
    device_counter_monotonicity_proven_when_present: bool = True
    os_page_cache_cold_proven: bool = False
    device_cache_cold_proven: bool = False
    process_read_bytes_are_physical_nvme_bytes: bool = False
    astge_page_requests_are_physical_nvme_reads: bool = False
    device_counter_is_exclusive_to_benchmark: bool = False
    physical_io_attested: bool = False
    producer_authenticated: bool = False
    w4_admitted: bool = False
    real_performance_winner_proven: bool = False
    effect_authority_proven: bool = False
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def receipt_digest(self) -> str:
        return _digest(self.to_dict())


def _monotonic(after: int, before: int, code: str) -> None:
    if after < before:
        raise ThinkPadBenchmarkContractError(code)


def _validate_sample(
    request: ThinkPadASTGEBenchmarkRequest,
    sample: ThinkPadASTGEBenchmarkPhaseSample,
) -> None:
    if sample.request_digest != request.request_digest:
        raise ThinkPadBenchmarkContractError("PHASE_REQUEST_DIGEST_MISMATCH", sample.phase)
    if sample.query_sequence_sha256 != request.query_sequence_sha256:
        raise ThinkPadBenchmarkContractError("QUERY_SEQUENCE_MISMATCH", sample.phase)
    if sample.query_count != request.query_count_per_phase:
        raise ThinkPadBenchmarkContractError("QUERY_COUNT_MISMATCH", sample.phase)
    _monotonic(
        sample.process_read_bytes_after,
        sample.process_read_bytes_before,
        "PROCESS_READ_COUNTER_ROLLBACK",
    )
    _monotonic(sample.minor_faults_after, sample.minor_faults_before, "MINOR_FAULT_COUNTER_ROLLBACK")
    _monotonic(sample.major_faults_after, sample.major_faults_before, "MAJOR_FAULT_COUNTER_ROLLBACK")
    if sample.astge_cache_hits + sample.astge_cache_misses != sample.astge_page_requests:
        raise ThinkPadBenchmarkContractError("ASTGE_CACHE_ACCOUNTING_MISMATCH", sample.phase)
    if sample.device_read_bytes_before is not None:
        assert sample.device_read_bytes_after is not None
        _monotonic(
            sample.device_read_bytes_after,
            sample.device_read_bytes_before,
            "DEVICE_READ_COUNTER_ROLLBACK",
        )


def admit_thinkpad_owner_host_benchmark(
    *,
    request: ThinkPadASTGEBenchmarkRequest,
    samples: Iterable[ThinkPadASTGEBenchmarkPhaseSample],
    host_observation_id: str,
    runner_identity: str,
) -> ThinkPadASTGEBenchmarkReceipt:
    """Validate a completed three-phase receipt without promoting its evidence class."""
    if type(request) is not ThinkPadASTGEBenchmarkRequest:
        raise ThinkPadBenchmarkContractError("EXACT_REQUEST_TYPE_REQUIRED")
    _require_text("host_observation_id", host_observation_id)
    _require_text("runner_identity", runner_identity)
    if type(samples) not in (tuple, list):
        raise ThinkPadBenchmarkContractError("EXACT_PHASE_COLLECTION_REQUIRED")
    phase_samples = tuple(samples)
    if len(phase_samples) != len(PHASES):
        raise ThinkPadBenchmarkContractError("EXACT_THREE_PHASES_REQUIRED")
    if any(type(s) is not ThinkPadASTGEBenchmarkPhaseSample for s in phase_samples):
        raise ThinkPadBenchmarkContractError("EXACT_PHASE_SAMPLE_TYPE_REQUIRED")
    if tuple(sample.phase for sample in phase_samples) != PHASES:
        raise ThinkPadBenchmarkContractError("PHASE_ORDER_MISMATCH")

    for sample in phase_samples:
        _validate_sample(request, sample)

    cold, warm, restart = phase_samples
    if cold.process_identity != warm.process_identity:
        raise ThinkPadBenchmarkContractError("PROCESS_WARM_MUST_REUSE_COLD_PROCESS")
    if restart.process_identity == cold.process_identity:
        raise ThinkPadBenchmarkContractError("RESTART_MUST_USE_NEW_PROCESS")

    summaries: list[dict[str, Any]] = []
    for sample in phase_samples:
        summaries.append(
            {
                "phase": sample.phase,
                "elapsed_ns": sample.elapsed_ns,
                "query_count": sample.query_count,
                "process_read_bytes_delta": sample.process_read_bytes_delta,
                "minor_faults_delta": sample.minor_faults_delta,
                "major_faults_delta": sample.major_faults_delta,
                "astge_page_requests": sample.astge_page_requests,
                "astge_cache_hits": sample.astge_cache_hits,
                "astge_cache_misses": sample.astge_cache_misses,
                "device_read_bytes_delta": sample.device_read_bytes_delta,
            }
        )

    return ThinkPadASTGEBenchmarkReceipt(
        request_digest=request.request_digest,
        query_sequence_sha256=request.query_sequence_sha256,
        host_observation_id=host_observation_id,
        runner_identity=runner_identity,
        runner_generation=request.runner_generation,
        phase_summaries=tuple(summaries),
    )
