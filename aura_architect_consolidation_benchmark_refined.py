"""Hardened context-ranking facade for the Architect consolidation benchmark.

The previous refined implementation is preserved verbatim in
``_aura_architect_consolidation_benchmark_refined_legacy``. This facade retains
its ranking behavior and post-processes the Aura packet so exact grounding spans
remain exact rather than being re-localized through a heuristic AST search.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aura_architect_consolidation_benchmark as benchmark
import _aura_architect_consolidation_benchmark_refined_legacy as _legacy

for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)

_ORIGINAL_BUILD_AURA_SLICE_PACKET = _legacy._build_aura_slice_packet


def _exact_span_slice(root: Path, span: dict[str, Any]) -> dict[str, Any] | None:
    rel = benchmark._normalize_candidate_path(span.get("file_path"))
    if not rel:
        return None
    path = root / rel
    if not path.is_file():
        return None
    try:
        start = int(span.get("start_line") or 0)
        end = int(span.get("end_line") or 0)
    except (TypeError, ValueError, OverflowError):
        return None
    if start <= 0 or end < start:
        return None
    item = benchmark._slice_text(path, start, end, max_lines=max(1, end - start + 1))
    item.update(
        {
            "file": rel,
            "symbol": str(span.get("symbol") or ""),
            "selection_score": 44.0,
            "selection_reasons": ["grounding_exact_source_span"],
            "exact_span": {
                "start_line": start,
                "end_line": end,
                "symbol": str(span.get("symbol") or ""),
                "source_hash": str(span.get("source_hash") or ""),
                "file_source_hash": str(span.get("file_source_hash") or ""),
            },
        }
    )
    return item


def _build_aura_slice_packet(
    root: Path,
    objective: str,
    *,
    token_budget: int = 6_200,
) -> dict[str, Any]:
    packet = _ORIGINAL_BUILD_AURA_SLICE_PACKET(
        root,
        objective,
        token_budget=token_budget,
    )
    grounding = dict(packet.get("grounding") or {})
    exact_items = [
        item
        for item in (
            _exact_span_slice(root, span)
            for span in list(grounding.get("source_spans") or [])
            if isinstance(span, dict)
        )
        if item is not None
    ]
    if not exact_items:
        return packet

    source_budget = int(token_budget * 0.70)
    existing = list(packet.get("source_slices") or [])
    exact_keys = {
        (
            str(item.get("file") or ""),
            int(dict(item.get("exact_span") or {}).get("start_line") or 0),
            int(dict(item.get("exact_span") or {}).get("end_line") or 0),
        )
        for item in exact_items
    }
    candidates = exact_items + [
        item
        for item in existing
        if (
            str(item.get("file") or ""),
            int(item.get("start_line") or 0),
            int(item.get("end_line") or 0),
        )
        not in exact_keys
    ]
    selected: list[dict[str, Any]] = []
    used = 0
    for item in candidates:
        cost = benchmark._token_proxy(item)
        if cost <= max(0, source_budget - used):
            selected.append(item)
            used += cost
    packet["source_slices"] = selected
    packet["measurement"] = {
        **dict(packet.get("measurement") or {}),
        "bytes": len(benchmark._canonical(packet).encode("utf-8")),
        "token_proxy": benchmark._token_proxy(packet),
        "source_slice_count": len(selected),
        "test_slice_count": len(list(packet.get("test_slices") or [])),
        "requested_token_budget": token_budget,
        "unused_source_budget": max(0, source_budget - used),
        "exact_grounding_span_count": len(exact_items),
    }
    return packet


def _sync_runtime_overrides() -> None:
    """Propagate public-facade overrides into preserved legacy globals.

    Functions defined in the preserved legacy module resolve globals from that
    module, not from this public facade. Without this synchronization, V2 can
    assign a Council runner on the facade while the legacy scorer silently calls
    its original runner.
    """
    benchmark._build_aura_slice_packet = _build_aura_slice_packet
    _legacy.benchmark._build_aura_slice_packet = _build_aura_slice_packet
    council_runner = getattr(benchmark, "_run_council", None)
    legacy_benchmark = getattr(benchmark, "_legacy", None)
    if council_runner is not None and legacy_benchmark is not None:
        legacy_benchmark._run_council = council_runner


_sync_runtime_overrides()


def main(argv: list[str] | None = None) -> int:
    _sync_runtime_overrides()
    return benchmark.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
