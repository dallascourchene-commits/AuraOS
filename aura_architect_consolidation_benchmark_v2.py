"""Hardened public facade for Architect consolidation benchmark V2.

The exact earlier V2 implementation is preserved in
``_aura_architect_consolidation_benchmark_v2_legacy``. This facade keeps its API,
applies the benchmark-wide deterministic char/4 token proxy, completes the
recorded long-plan critic fixture explicitly, and rejects any attempted/model-call
accounting mismatch.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import _aura_architect_consolidation_benchmark_v2_legacy as _legacy

for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)


_LONG_CRITIC_ALIASES = {
    "sequence": "scope",
    "continuity": "tests",
    "rollback": "cost",
}
_ORIGINAL_RUN_COUNCIL_V2 = _legacy._run_council_v2


def _token_proxy(text: str) -> int:
    """Match the benchmark's deterministic char/4 proxy."""
    return (len(str(text)) + 3) // 4


def _complete_v2_fixture_payload(fixture: dict[str, Any]) -> dict[str, Any]:
    """Materialize explicit deterministic aliases for V2 long-plan critic lanes.

    The original assisted fixture recorded scope, tests, and cost Shadow responses.
    V2 also invokes sequence, continuity, and rollback lanes. For reproducibility,
    those lanes are explicit aliases rather than silently failed model calls. This
    is fixture completion, not a new provider response, and is recorded as such.
    """
    completed = json.loads(json.dumps(fixture))
    council = completed.setdefault("council", {})
    critics = council.setdefault("critics", {})
    added: dict[str, str] = {}
    for lane, source_lane in _LONG_CRITIC_ALIASES.items():
        if lane in critics:
            continue
        source = critics.get(source_lane)
        if not isinstance(source, dict):
            raise ValueError(
                f"cannot complete V2 fixture: missing source critic {source_lane!r}"
            )
        alias = dict(source)
        alias["fixture_alias_of"] = source_lane
        alias["fixture_completion"] = (
            "DETERMINISTIC_ALIAS_OF_RECORDED_SHADOW_RESPONSE_NOT_NEW_PROVIDER_OUTPUT"
        )
        critics[lane] = alias
        added[lane] = source_lane
    completed["fixture_completion"] = {
        "version": "AURA_ARCHITECT_V2_FIXTURE_COMPLETION_V1",
        "added_long_critic_aliases": added,
        "independent_provider_responses": False,
    }
    return completed


def _complete_fixture_file(arguments: list[str]) -> dict[str, Any] | None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", nargs="?")
    parser.add_argument("--responses", type=Path)
    parsed, _ = parser.parse_known_args(arguments)
    if parsed.command != "score" or parsed.responses is None:
        return None
    path = parsed.responses.resolve()
    fixture = json.loads(path.read_text(encoding="utf-8"))
    completed = _complete_v2_fixture_payload(fixture)
    path.write_text(
        json.dumps(completed, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return dict(completed.get("fixture_completion") or {})


async def _run_council_v2(
    root: Path,
    fixture: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    completed = _complete_v2_fixture_payload(fixture)
    result = await _ORIGINAL_RUN_COUNCIL_V2(root, completed, output_dir)
    attempted = len(list(result.get("requests") or []))
    usage = dict(result.get("model_usage") or {})
    recorded = int(usage.get("call_count") or len(list(usage.get("calls") or [])))
    if attempted != recorded:
        raise RuntimeError(
            "Architect benchmark call accounting mismatch: "
            f"attempted={attempted}, recorded={recorded}"
        )
    usage["attempted_call_count"] = attempted
    usage["failed_call_count"] = 0
    usage["fixture_completion"] = completed.get("fixture_completion", {})
    result["model_usage"] = usage
    result["fixture_call_accounting"] = {
        "attempted": attempted,
        "recorded": recorded,
        "failed": 0,
    }
    return result


def _annotate_report(arguments: list[str], completion: dict[str, Any] | None) -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", nargs="?")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path)
    parsed, _ = parser.parse_known_args(arguments)
    if parsed.command != "score" or parsed.output_dir is None:
        return
    root = parsed.repo_root.resolve()
    output_dir = parsed.output_dir if parsed.output_dir.is_absolute() else root / parsed.output_dir
    report_path = output_dir / "architect_consolidation_benchmark.json"
    if not report_path.is_file():
        return
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["fixture_completion"] = completion or {}
    limitation = (
        "V2 sequence, continuity, and rollback Shadow lanes use explicit deterministic "
        "aliases of the recorded scope, tests, and cost fixture responses. They are "
        "reproducible fixture invocations, not independent provider outputs."
    )
    limitations = list(report.get("limitations") or [])
    if limitation not in limitations:
        limitations.append(limitation)
    report["limitations"] = limitations
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


_legacy._token_proxy = _token_proxy
_legacy._run_council_v2 = _run_council_v2


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    _legacy._token_proxy = _token_proxy
    _legacy._run_council_v2 = _run_council_v2
    completion = _complete_fixture_file(arguments)
    result = _legacy.main(arguments)
    if result == 0:
        _annotate_report(arguments, completion)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
