"""Hardened public facade for Architect consolidation benchmark V2.

The exact earlier V2 implementation is preserved in
``_aura_architect_consolidation_benchmark_v2_legacy``. This facade keeps its API
and applies the benchmark-wide deterministic char/4 token proxy while routing the
RAW and Aura-slice paths through the hardened active entrypoints.
"""
from __future__ import annotations

import _aura_architect_consolidation_benchmark_v2_legacy as _legacy

for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)


def _token_proxy(text: str) -> int:
    """Match the benchmark's deterministic char/4 proxy."""
    return (len(str(text)) + 3) // 4


_legacy._token_proxy = _token_proxy


def main(argv: list[str] | None = None) -> int:
    _legacy._token_proxy = _token_proxy
    return _legacy.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
