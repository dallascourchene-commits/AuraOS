"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f9-[Q-SYS:MODEL_PROBE_LEDGER]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Honest Black-Box Profiling)
DEPENDENCIES: argparse, dataclasses, json, os, time
FUNCTIONS: ModelProbeProfile, AuraModelProbeLedger, score_model, deterministic_probe_packets, main
SYNOPSIS: Black-box behavioral model profiling for AuraFusion routing. This stores observed API behavior only; it does not claim hidden-state or activation access for closed models.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
import time
from typing import Any

from aura_substrate import REPO_ROOT


MODEL_PROBE_LEDGER_PATH = os.path.join(REPO_ROOT, "Aura_Memory", "aura_model_probe_ledger.jsonl")


@dataclass
class ModelProbeProfile:
    provider: str
    model: str
    role: str = "WORKER"
    historical_quality: float = 0.5
    capsule_comprehension: float = 0.5
    json_success: float = 0.5
    role_affinity: float = 0.5
    latency_score: float = 0.5
    cost_score: float = 0.5
    failure_penalty: float = 0.0
    format_following: float = 0.5
    json_schema_success: float = 0.5
    json_edit_plan_success: float = 0.5
    hallucinated_path_rate: float = 0.0
    target_symbol_preservation: float = 0.5
    latency: float = 0.0
    cost: float = 0.0
    output_verbosity: float = 0.5
    truncation_probability: float = 0.0
    self_correction_success: float = 0.5
    refusal_rate: float = 0.0
    long_context_decay: float = 0.0
    capsule_comprehension_score: float = 0.5
    fusion_panel_value: float = 0.5
    verifier_accuracy: float = 0.5
    samples: int = 0
    updated_at: str = ""

    @property
    def key(self) -> str:
        return f"{self.provider}:{self.model}:{self.role}".lower()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["routing_score"] = score_model(data)
        return data


def _clamp(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def score_model(profile: dict[str, Any] | ModelProbeProfile, task: str | None = None) -> float:
    """Routing equation from the handoff, bounded to 0..1."""
    data = profile.to_dict() if isinstance(profile, ModelProbeProfile) else dict(profile)
    score = (
        0.30 * _clamp(data.get("historical_quality"), 0.5)
        + 0.20 * _clamp(data.get("capsule_comprehension", data.get("capsule_comprehension_score")), 0.5)
        + 0.15 * _clamp(data.get("json_success", data.get("json_schema_success")), 0.5)
        + 0.15 * _clamp(data.get("role_affinity"), 0.5)
        + 0.10 * _clamp(data.get("latency_score"), 0.5)
        + 0.10 * _clamp(data.get("cost_score"), 0.5)
        - 0.20 * _clamp(data.get("failure_penalty"), 0.0)
    )
    return round(max(0.0, min(1.0, score)), 4)


def deterministic_probe_packets() -> list[dict[str, Any]]:
    """Small offline probe set; real API probing can replay these later."""
    return [
        {
            "name": "json_schema",
            "task": "Return strict JSON with answer, risks, confidence.",
            "expected_fields": ["answer", "risks", "confidence"],
        },
        {
            "name": "fake_path_guard",
            "task": "Produce a JSON edit plan only for an existing CODEMAP target.",
            "expected_fields": ["edits"],
        },
        {
            "name": "phase_capsule",
            "task": "Continue incomplete JSON from a phase capsule boundary.",
            "expected_fields": ["continuation"],
        },
    ]


class AuraModelProbeLedger:
    def __init__(self, path: str = MODEL_PROBE_LEDGER_PATH):
        self.path = path

    def append(self, profile: ModelProbeProfile | dict[str, Any]) -> dict[str, Any]:
        data = profile.to_dict() if isinstance(profile, ModelProbeProfile) else dict(profile)
        data.setdefault("updated_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        data["routing_score"] = score_model(data)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(data, sort_keys=True) + "\n")
        return data

    def read_all(self) -> list[dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        rows: list[dict[str, Any]] = []
        with open(self.path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows

    def latest_profiles(self) -> dict[str, dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        for row in self.read_all():
            key = f"{row.get('provider')}:{row.get('model')}:{row.get('role', 'WORKER')}".lower()
            latest[key] = row
        return latest

    def score_agent(self, provider: str, model: str, role: str, task: str | None = None) -> float:
        key = f"{provider}:{model}:{role}".lower()
        profile = self.latest_profiles().get(key)
        if not profile:
            return 0.5
        return score_model(profile, task=task)


def _mock_profile(provider: str, model: str, role: str) -> ModelProbeProfile:
    base = (sum(ord(c) for c in f"{provider}:{model}:{role}") % 23) / 100
    return ModelProbeProfile(
        provider=provider,
        model=model,
        role=role,
        historical_quality=0.60 + base,
        capsule_comprehension=0.70,
        json_success=0.80,
        role_affinity=0.65,
        latency_score=0.55,
        cost_score=0.60,
        failure_penalty=0.05,
        samples=len(deterministic_probe_packets()),
        updated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aura model probe ledger")
    sub = parser.add_subparsers(dest="cmd", required=True)
    probe = sub.add_parser("probe", help="record deterministic/mock probe profile")
    probe.add_argument("--provider", required=True)
    probe.add_argument("--model", required=True)
    probe.add_argument("--role", default="WORKER")
    probe.add_argument("--mock", action="store_true")
    sub.add_parser("list", help="list latest profile scores")
    args = parser.parse_args(argv)

    ledger = AuraModelProbeLedger()
    if args.cmd == "probe":
        if not args.mock:
            raise SystemExit("Live probing is intentionally explicit; run with --mock for offline profile capture.")
        row = ledger.append(_mock_profile(args.provider, args.model, args.role))
        print(json.dumps(row, indent=2, sort_keys=True))
        return 0
    if args.cmd == "list":
        for key, row in sorted(ledger.latest_profiles().items()):
            print(f"{key} score={row.get('routing_score', score_model(row))}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
