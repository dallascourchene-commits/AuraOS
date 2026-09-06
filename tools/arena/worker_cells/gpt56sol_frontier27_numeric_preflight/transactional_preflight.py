"""D0 donor membrane for Frontier-27 numeric and invocation preflight totality.

The donor does not replace the canonical owner. It bounds and validates one
invocation, proves owner-style derived accumulations are representable before
owner mutation, and restores exact residency/counters on downstream failure.
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


def _governed_float(v: object, *, minimum: float, label: str) -> float:
    if type(v) is int:
        if not minimum <= v <= MAX_GOVERNED_INT:
            raise ValueError(f"{label} is outside the governed numeric domain")
        return float(v)
    if type(v) is float and math.isfinite(v) and v >= minimum:
        return v
    raise ValueError(f"{label} is outside the governed numeric domain")


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


def _freeze_records(routes: Iterable[Sequence[int]], preds: Iterable[Sequence[int]], *, max_records: int = MAX_GOVERNED_RECORDS, max_items_per_record: int = MAX_GOVERNED_EXPERT_IDS_PER_RECORD):
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


def _checked_add(acc: float, term: float, *, label: str) -> float:
    if not _finite_derived(term):
        raise ValueError(f"{label} term is outside the governed finite domain")
    out = acc + term
    if not _finite_derived(out):
        raise ValueError(f"{label} owner-style accumulation is outside the governed finite domain")
    return out


def _checked_repeat_add(acc: float, term: float, count: int, *, label: str) -> float:
    if type(count) is not int or count < 0:
        raise ValueError(f"{label} count is outside the governed integer domain")
    for _ in range(count):
        acc = _checked_add(acc, term, label=label)
    return acc


def _prove_metric_domain(total_bytes: int, bandwidth: object, joules_per_gb: object) -> None:
    bw = _governed_float(bandwidth, minimum=0.0, label="bandwidth")
    if bw == 0.0:
        raise ValueError("bandwidth is outside the governed finite-positive domain")
    jpgb = _governed_float(joules_per_gb, minimum=0.0, label="joules_per_gb")
    seconds = float(total_bytes) / bw
    energy = (float(total_bytes) / 1_000_000_000.0) * jpgb
    if not _finite_derived(seconds) or not _finite_derived(energy):
        raise ValueError("aggregate derived metric is outside the governed finite domain")


def _prove_legacy_owner_accumulation(size: int, routes: tuple[tuple[int, ...], ...], preds: tuple[tuple[int, ...], ...], bandwidth: object, joules_per_gb: object) -> None:
    """Replay LegacyOffload's exact positive addition order without owner mutation."""
    bw = _governed_float(bandwidth, minimum=0.0, label="bandwidth")
    if bw == 0.0:
        raise ValueError("bandwidth is outside the governed finite-positive domain")
    jpgb = _governed_float(joules_per_gb, minimum=0.0, label="joules_per_gb")
    secs = energy = 0.0
    pred_seconds = size / bw
    pred_energy = size / 1_000_000_000.0 * jpgb
    for route, pred in zip(routes, preds):
        n = len(route) * size
        secs = _checked_add(secs, n / bw, label="seconds")
        energy = _checked_add(energy, n / 1_000_000_000.0 * jpgb, label="energy")
        secs = _checked_repeat_add(secs, pred_seconds, len(pred), label="seconds")
        energy = _checked_repeat_add(energy, pred_energy, len(pred), label="energy")


def _prove_frontier_owner_accumulation(size: int, routes: tuple[tuple[int, ...], ...], preds: tuple[tuple[int, ...], ...], bandwidth: object, joules_per_gb: object) -> None:
    """Conservatively replay the maximum possible Frontier transfer additions.

    Every actual prefetch or miss adds the same size-derived seconds/energy term.
    Actual transfers are a subset of route IDs plus prediction IDs, so proving
    the full bounded count finite is sufficient before the real residency state moves.
    """
    bw = _governed_float(bandwidth, minimum=0.0, label="bandwidth")
    if bw == 0.0:
        raise ValueError("bandwidth is outside the governed finite-positive domain")
    jpgb = _governed_float(joules_per_gb, minimum=0.0, label="joules_per_gb")
    max_transfers = sum(len(route) + len(pred) for route, pred in zip(routes, preds))
    seconds_term = size / bw
    energy_term = size / 1_000_000_000.0 * jpgb
    _checked_repeat_add(0.0, seconds_term, max_transfers, label="seconds")
    _checked_repeat_add(0.0, energy_term, max_transfers, label="energy")


def _prove_frontier_window(offload: FrontierOffload, preds: tuple[tuple[int, ...], ...]) -> None:
    w = _governed_float(offload.w, minimum=0.0, label="window_s")
    _governed_float(offload.e, minimum=0.0, label="budget_j")
    if not _bounded_int(offload.r.capacity, minimum=0):
        raise ValueError("residency capacity is outside the governed integer domain")
    if not _bounded_int(offload.t.capacity_bytes, minimum=0):
        raise ValueError("tier capacity is outside the governed integer domain")
    bandwidth = _governed_float(offload.t.bandwidth, minimum=0.0, label="bandwidth")
    window_bytes = bandwidth * w
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
    _prove_legacy_owner_accumulation(offload.size, frozen_routes, frozen_preds, offload.bw, offload.jpgb)
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
    _prove_frontier_owner_accumulation(offload.size, frozen_routes, frozen_preds, offload.t.bandwidth, offload.t.joules_per_gb)
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
