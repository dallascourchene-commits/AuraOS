from __future__ import annotations

import aura_architect_consolidation_benchmark as benchmark
import aura_architect_consolidation_benchmark_refined as refined


def test_refined_facade_propagates_council_runner_to_legacy_scorer() -> None:
    legacy = benchmark._legacy
    original_public = getattr(benchmark, "_run_council", None)
    original_legacy = getattr(legacy, "_run_council", None)

    async def sentinel_runner(*args: object, **kwargs: object) -> dict[str, object]:
        return {"args": args, "kwargs": kwargs}

    try:
        benchmark._run_council = sentinel_runner
        refined._sync_runtime_overrides()
        assert legacy._run_council is sentinel_runner
    finally:
        if original_public is not None:
            benchmark._run_council = original_public
        if original_legacy is not None:
            legacy._run_council = original_legacy
        refined._sync_runtime_overrides()
