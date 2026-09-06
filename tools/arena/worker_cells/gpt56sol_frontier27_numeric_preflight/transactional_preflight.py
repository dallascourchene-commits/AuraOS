"""D0 donor membrane for Frontier-27 numeric and invocation preflight totality.

This module deliberately does not replace the canonical FrontierOffload owner. It
bounds and validates one caller invocation, proves consequential float metrics are
representable before owner mutation, and restores the exact residency/counter
snapshot if the owner raises or emits a non-finite governed metric.
"""
from __future__ import annotations

from collections import OrderedDict
import math
from typing import Iterable, Iterator, Sequence

from tools.arena.frontier27_runtime import FrontierOffload, LegacyOffload

MAX_GOVERNED_INT = (1 << 63) - 1
MAX_GOVERNED_RECORDS = 4096
MAX_GOVERNED_EXPERT_IDS_PER_RECORD = 4096


def _bounded_int(v: object, *, minimum: int = 0) -> bool:
    return type(v) is int and minimum <= v <= MAX_GOVERNED_INT


def _finite_scalar(v: object, *, minimum: float = 0.0) -> bool:
    if type(v) is int:
        return minimum <= v <= MAX_GOVERNED_INT
    return type(v) is float and math.isfinite(v) and v >= minimum


def _finite_derived(v: float) -> bool:
    return type(v) is float and math.isfinite(v) and v >= 0.0


def _iter_or_valueerror(source: object, *, label: str) -> Iterator:
    try:
        return iter(source)  # type: ignore[arg-type]
    except Exception as exc:
        raise ValueError(f"{label} must be iterable") from exc


def _next_or_valueerror(iterator: Iterator, *, label: str):
    try:
        return next(iterator)
    except StopIteration:
        raise
    except Exception as exc:
        raise ValueError(f"{label} iteration failed") from exc


def _freeze_record(record: object, *, label: str, max_items: int) -> tuple[int, ...]:
    iterator = _iter_or_valueerror(record, label=label)
    out: list[int] = []
    for index in range(max_items + 1):
        try:
            expert_id = _next_or_valueerror(iterator, label=label)
        except StopIteration:
            return tuple(out)
        if index == max_items:
            raise ValueError(f"{label} exceeds governed cardinality")
        if type(expert_id) is not int:
            raise ValueError(f"{label} expert ids must be integers")
        out.append(expert_id)
    raise AssertionError("unreachable")


def _freeze_family(source: object, *, family: str, max_records: int, max_items: int) -> tuple[tuple[int, ...], ...]:
    iterator = _iter_or_valueerror(source, label=family)
    out: list[tuple[int, ...]] = []
    for index in range(max_records + 1):
        try:
            record = _next_or_valueerror(iterator, label=family)
        except StopIteration:
            return tuple(out)
        if index == max_records:
            raise ValueError(f"{family} exceeds governed cardinality")
        out.append(_freeze_record(record, label=f"{family}[{index}]", max_items=max_items))
    raise AssertionError("unreachable")


def _freeze_records(
    routes: Iterable[Sequence[int]],
    preds: Iterable[Sequence[int]],
    *,
    max_records: int = MAX_GOVERNED_RECORDS,
    max_items_per_record: int = MAX_GOVERNED_EXPERT_IDS_PER_RECORD,
) -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]]:
    """Materialize caller records with bounded cardinality and governed errors.

    Ordinary exceptions from ``iter``/``next`` are translated to ``ValueError``.
    Process-control ``BaseException`` subclasses are intentionally not swallowed.
    The cardinality ceilings are conservative donor policy, not canonical Aura law.
    """
    if type(max_records) is not int or not 0 <= max_records <= MAX_GOVERNED_INT:
        raise ValueError("max_records is outside the governed integer domain")
    if type(max_items_per_record) is not int or not 0 <= max_items_per_record <= MAX_GOVERNED_INT:
        raise ValueError("max_items_per_record is outside the governed integer domain")
    frozen_routes = _freeze_family(routes, family="routes", max_records=max_records, max_items=max_items_per_record)
    frozen_preds = _freeze_family(preds, family="preds", max_records=max_records, max_items=max_items_per_record)
    if len(frozen_routes) != len(frozen_preds):
        raise ValueError("routes and preds must have equal length")
    return frozen_routes, frozen_preds


def _preflight_common(size: object, routes: tuple[tuple[int, ...], ...], preds: tuple[tuple[int, ...], ...]) -> int:
    if not _bounded_int(size, minimum=1):
        raise ValueError("size is outside the governed integer domain")
    total_transfers = 0
    for route, pred in zip(routes, preds):
        transfer_count = len(route) + len(pred)
        if not _bounded_int(transfer_count):
            raise ValueError("transfer count is outside the governed integer domain")
        total_transfers += transfer_count
        if total_transfers > MAX_GOVERNED_INT:
            raise ValueError("aggregate transfer count is outside the governed integer domain")
    total_bytes = total_transfers * size
    if total_bytes > MAX_GOVERNED_INT:
        raise ValueError("aggregate bytes are outside the governed integer domain")
    return total_bytes


def _prove_metric_domain(total_bytes: int, bandwidth: object, joules_per_gb: object) -> None:
    if not _finite_scalar(bandwidth, minimum=0.0) or bandwidth == 0:
        raise ValueError("bandwidth is outside the governed finite-positive domain")
    if not _finite_scalar(joules_per_gb, minimum=0.0):
        raise ValueError("joules_per_gb is outside the governed finite domain")
    seconds = float(total_bytes) / float(bandwidth)
    energy = (float(total_bytes) / 1_000_000_000.0) * float(joules_per_gb)
    if not _finite_derived(seconds) or not _finite_derived(energy):
        raise ValueError("derived metric is outside the governed finite domain")


def _prove_frontier_window(offload: FrontierOffload, preds: tuple[tuple[int, ...], ...]) -> None:
    if not _finite_scalar(offload.w, minimum=0.0):
        raise ValueError("window_s is outside the governed finite domain")
    if not _finite_scalar(offload.e, minimum=0.0):
        raise ValueError("budget_j is outside the governed finite domain")
    if not _bounded_int(offload.r.capacity, minimum=0):
        raise ValueError("residency capacity is outside the governed integer domain")
    if not _bounded_int(offload.t.capacity_bytes, minimum=0):
        raise ValueError("tier capacity is outside the governed integer domain")
    window_bytes = float(offload.t.bandwidth) * float(offload.w)
    if not math.isfinite(window_bytes) or window_bytes < 0.0:
        raise ValueError("bandwidth*window_s is outside the governed finite domain")
    for pred in preds:
        cap = offload.size * len(pred)
        if cap > MAX_GOVERNED_INT:
            raise ValueError("prediction byte cap is outside the governed integer domain")


def _assert_result_finite(result: dict) -> None:
    for key in ("seconds", "energy_j", "hit_rate"):
        value = result.get(key)
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f"owner returned non-finite {key}")


def run_legacy_totalized(offload: LegacyOffload, routes, preds) -> dict:
    frozen_routes, frozen_preds = _freeze_records(routes, preds)
    total_bytes = _preflight_common(offload.size, frozen_routes, frozen_preds)
    _prove_metric_domain(total_bytes, offload.bw, offload.jpgb)
    try:
        result = offload.run(frozen_routes, frozen_preds)
    except (OverflowError, TypeError) as exc:
        raise ValueError("governed legacy invocation rejected") from exc
    _assert_result_finite(result)
    return result


def run_frontier_totalized(offload: FrontierOffload, routes, preds) -> dict:
    frozen_routes, frozen_preds = _freeze_records(routes, preds)
    total_bytes = _preflight_common(offload.size, frozen_routes, frozen_preds)
    _prove_metric_domain(total_bytes, offload.t.bandwidth, offload.t.joules_per_gb)
    _prove_frontier_window(offload, frozen_preds)

    prior_residency = OrderedDict(offload.r.r)
    prior_hits = offload.r.hits
    prior_misses = offload.r.misses
    try:
        result = offload.run(frozen_routes, frozen_preds)
        _assert_result_finite(result)
        return result
    except Exception:
        offload.r.r = prior_residency
        offload.r.hits = prior_hits
        offload.r.misses = prior_misses
        raise
