"""Additive D0 exact-projection membrane for Frontier-27 donor evaluation.

This module composes the current R10.2 bounded-materialization/numeric helpers
without changing them. It adds a shared aggregate expert-ID budget, projects the
canonical Frontier owner on an exact clone of the caller's pre-state, and only
then permits the same canonical owner method to mutate the real state.
"""
from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from typing import Iterable
from tools.arena.frontier27_runtime import FrontierOffload, ExpertResidencyLRU
from tools.arena.worker_cells.gpt56sol_frontier27_numeric_preflight.transactional_preflight import (
    MAX_GOVERNED_EXPERT_IDS_PER_RECORD,
    MAX_GOVERNED_INT,
    MAX_GOVERNED_RECORDS,
    _assert_result_finite,
    _freeze_records,
    _preflight_common,
    _prove_frontier_window,
)

MAX_GOVERNED_EXPERT_IDS_PER_INVOCATION = 100_000

@dataclass
class _AggregateBudget:
    limit: int
    used: int = 0
    def consume(self) -> None:
        self.used += 1
        if self.used > self.limit:
            raise ValueError("aggregate expert-id budget exceeded")

def _budgeted_record(record: Iterable[int], budget: _AggregateBudget):
    for value in record:
        budget.consume()
        yield value

def _budgeted_family(source, budget: _AggregateBudget):
    for record in source:
        yield _budgeted_record(record, budget)

def freeze_records_with_aggregate_budget(
    routes,
    preds,
    *,
    max_records: int = MAX_GOVERNED_RECORDS,
    max_items_per_record: int = MAX_GOVERNED_EXPERT_IDS_PER_RECORD,
    max_aggregate_items: int = MAX_GOVERNED_EXPERT_IDS_PER_INVOCATION,
):
    """Freeze both families under one shared aggregate expert-ID budget."""
    if type(max_aggregate_items) is not int or not 0 <= max_aggregate_items <= MAX_GOVERNED_INT:
        raise ValueError("max_aggregate_items is outside the governed integer domain")
    budget = _AggregateBudget(max_aggregate_items)
    return _freeze_records(
        _budgeted_family(routes, budget),
        _budgeted_family(preds, budget),
        max_records=max_records,
        max_items_per_record=max_items_per_record,
    )

def _state(offload: FrontierOffload):
    return (tuple(offload.r.r.items()), offload.r.hits, offload.r.misses)

def _clone_frontier(offload: FrontierOffload) -> FrontierOffload:
    if type(offload) is not FrontierOffload or type(offload.r) is not ExpertResidencyLRU:
        raise ValueError("exact FrontierOffload owner generation required")
    clone = FrontierOffload(offload.size, offload.r.capacity, offload.t, offload.w, offload.e)
    clone.r.r = OrderedDict(offload.r.r)
    clone.r.hits = offload.r.hits
    clone.r.misses = offload.r.misses
    return clone

def project_frontier_exact(offload: FrontierOffload, frozen_routes, frozen_preds):
    """Execute canonical owner semantics against an exact pre-state clone."""
    shadow = _clone_frontier(offload)
    projected = FrontierOffload.run(shadow, frozen_routes, frozen_preds)
    _assert_result_finite(projected)
    return projected, _state(shadow)

def run_frontier_exact_projected(offload: FrontierOffload, routes, preds):
    """Admit only when exact dry-run and real canonical execution agree."""
    frozen_routes, frozen_preds = freeze_records_with_aggregate_budget(routes, preds)
    total_bytes = _preflight_common(offload.size, frozen_routes, frozen_preds)
    # Keep the governed aggregate-byte ceiling, but do not infer actual-transfer
    # seconds/energy from potential route+prediction bytes. Exact transfer metrics
    # are decided by the canonical shadow execution below.
    del total_bytes
    _prove_frontier_window(offload, frozen_preds)
    before = _state(offload)
    try:
        projected_result, projected_state = project_frontier_exact(offload, frozen_routes, frozen_preds)
    except Exception as exc:
        if _state(offload) != before:
            raise AssertionError("projection mutated real owner state") from exc
        raise ValueError("frontier exact-owner projection rejected invocation") from exc
    if _state(offload) != before:
        raise AssertionError("projection mutated real owner state")
    try:
        result = FrontierOffload.run(offload, frozen_routes, frozen_preds)
        _assert_result_finite(result)
        actual_state = _state(offload)
        if result != projected_result or actual_state != projected_state:
            raise ValueError("real owner diverged from exact projection")
        return result
    except Exception:
        offload.r.r = OrderedDict(before[0])
        offload.r.hits = before[1]
        offload.r.misses = before[2]
        raise
