"""Append-only index for standardized refactor code-output quality records."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from aura_arena_experience import sanitize_experience_payload
from aura_refactor_output_record import RECORD_VERSION, RefactorOutputRecord

REGISTRY_VERSION = "AURA_CODE_QUALITY_REGISTRY_V1"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _digest(value: Any) -> str:
    return hashlib.blake2b(_canonical(value).encode("utf-8"), digest_size=16).hexdigest()


class CodeQualityRegistry:
    def __init__(self, repo_root: str | Path = ".", *, path: str | Path | None = None) -> None:
        root = Path(repo_root).resolve()
        self.path = (
            Path(path).resolve()
            if path is not None
            else root / "Aura_Memory" / "benchmarks" / "refactor_output_records.jsonl"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, value: RefactorOutputRecord | dict[str, Any]) -> dict[str, Any]:
        payload = value.to_dict() if isinstance(value, RefactorOutputRecord) else dict(value)
        safe, redactions = sanitize_experience_payload(payload)
        required = ("benchmark_id", "run_id", "case_id", "arm_id", "disposition")
        missing = [name for name in required if not str(safe.get(name) or "").strip()]
        if missing:
            return {"ok": False, "error": "missing:" + ",".join(missing)}
        record = {
            "registry_version": REGISTRY_VERSION,
            "record_version": str(safe.get("record_version") or RECORD_VERSION),
            "record_digest": _digest(safe),
            "benchmark_id": safe["benchmark_id"],
            "run_id": safe["run_id"],
            "case_id": safe["case_id"],
            "arm_id": safe["arm_id"],
            "method": safe.get("method"),
            "output_kind": safe.get("output_kind"),
            "working_status": safe.get("working_status"),
            "disposition": safe.get("disposition"),
            "mandatory_gate_passed": safe.get("mandatory_gate_passed"),
            "failed_required_gates": list(safe.get("failed_required_gates") or []),
            "observed_quality_score": safe.get("observed_quality_score"),
            "benchmark_quality_score": safe.get("benchmark_quality_score"),
            "measurement_completeness_pct": safe.get("measurement_completeness_pct"),
            "token_usage": dict(safe.get("token_usage") or {}),
            "patch_stats": dict(safe.get("patch_stats") or {}),
            "evidence_refs": list(safe.get("evidence_refs") or []),
            "generated_at": safe.get("generated_at"),
            "redactions": sorted(set(str(item) for item in redactions)),
            "production_mutation": False,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(_canonical(record) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return {
            "ok": True,
            "record_digest": record["record_digest"],
            "registry_path": str(self.path),
            "production_mutation": False,
        }

    def history(self, *, benchmark_id: str = "", limit: int = 1000) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if benchmark_id and row.get("benchmark_id") != benchmark_id:
                    continue
                rows.append(row)
        return rows[-max(1, min(int(limit), 10000)) :]
