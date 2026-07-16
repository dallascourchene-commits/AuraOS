"""Append-only registry for Aura benchmark runs.

Benchmark reports remain immutable evidence objects.  This registry stores one
small index record per run so future operators and learning systems can discover,
compare, and replay prior benchmarks without scanning ad-hoc artifact folders.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

from aura_arena_experience import sanitize_experience_payload

BENCHMARK_REGISTRY_VERSION = "AURA_BENCHMARK_REGISTRY_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _digest(value: Any, *, size: int = 16) -> str:
    return hashlib.blake2b(_canonical(value).encode("utf-8"), digest_size=size).hexdigest()


class BenchmarkRegistry:
    def __init__(self, repo_root: str | Path = ".", *, path: str | Path | None = None) -> None:
        root = Path(repo_root).resolve()
        self.path = (
            Path(path).resolve()
            if path is not None
            else root / "Aura_Memory" / "benchmarks" / "benchmark_registry.jsonl"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, run: dict[str, Any]) -> dict[str, Any]:
        safe, redactions = sanitize_experience_payload(dict(run or {}))
        benchmark_id = str(safe.get("benchmark_id") or safe.get("benchmark_version") or "").strip()
        if not benchmark_id:
            return self._deny("benchmark_id_required")
        repository_commit_sha = str(safe.get("repository_commit_sha") or "")[:128]
        identity = {
            "benchmark_id": benchmark_id,
            "repository_commit_sha": repository_commit_sha,
            "generated_at": safe.get("generated_at"),
            "report_digest": safe.get("report_digest"),
            "nonce": time.time_ns(),
        }
        record = {
            "registry_version": BENCHMARK_REGISTRY_VERSION,
            "run_id": str(safe.get("run_id") or f"BENCH-{_digest(identity, size=12)}"),
            "benchmark_id": benchmark_id,
            "benchmark_version": str(safe.get("benchmark_version") or benchmark_id),
            "generated_at": str(safe.get("generated_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
            "repository_commit_sha": repository_commit_sha,
            "objective_hash": str(safe.get("objective_hash") or ""),
            "measurement_class": dict(safe.get("measurement_class") or {}),
            "length_profile": dict(safe.get("length_profile") or {}),
            "arms": dict(safe.get("arms") or {}),
            "role_token_totals": dict(safe.get("role_token_totals") or {}),
            "prompt_manifest": dict(safe.get("prompt_manifest") or {}),
            "comparison": dict(safe.get("comparison") or {}),
            "report_digest": str(safe.get("report_digest") or ""),
            "evidence_refs": list(safe.get("evidence_refs") or []),
            "limitations": list(safe.get("limitations") or []),
            "redactions": sorted(set(str(item) for item in redactions)),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
            "production_mutation": False,
        }
        line = _canonical(record) + "\n"
        try:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            return self._deny(f"benchmark_registry_write_failed:{type(exc).__name__}")
        return {
            "ok": True,
            "run_id": record["run_id"],
            "record_digest": _digest(record),
            "registry_path": str(self.path),
            "redactions": record["redactions"],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
            "production_mutation": False,
        }

    def history(self, *, benchmark_id: str = "", limit: int = 1000) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if not self.path.exists():
            return rows
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        row = json.loads(stripped)
                    except json.JSONDecodeError:
                        continue
                    if benchmark_id and row.get("benchmark_id") != benchmark_id:
                        continue
                    rows.append(row)
        except OSError:
            return []
        return rows[-max(1, min(int(limit), 10000)) :]

    @staticmethod
    def _deny(error: str) -> dict[str, Any]:
        return {
            "ok": False,
            "error": error,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
            "production_mutation": False,
        }


def compact_arm_tokens(report: dict[str, Any]) -> dict[str, Any]:
    """Return token/cost fields suitable for registry indexing."""
    output: dict[str, Any] = {}
    for name, arm in dict(report.get("arms") or {}).items():
        if not isinstance(arm, dict):
            continue
        output[str(name)] = {
            "model_calls": arm.get("model_calls"),
            "input_tokens_estimated": arm.get("input_tokens"),
            "output_tokens_estimated": arm.get("output_tokens"),
            "total_tokens_estimated": arm.get("total_tokens"),
            "input_tokens_reported": arm.get("input_tokens_reported"),
            "output_tokens_reported": arm.get("output_tokens_reported"),
            "reported_cost_usd": arm.get("reported_cost_usd"),
            "normalized_cost_usd": arm.get("normalized_cost_usd"),
            "quality_score": dict(arm.get("quality") or {}).get("quality_score"),
        }
    return output
