from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Sequence

from tools.benchmarks.long_horizon_state_benchmark import build_workload


SCHEMA_ID = "AURA_LONG_HORIZON_PREREGISTRATION_V1"
BENCHMARK_SCHEMA_ID = "AURA_LONG_HORIZON_STATE_BENCHMARK_V1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def canonical_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def command_digest(command: Sequence[str]) -> str:
    if not command or any(not isinstance(part, str) or not part for part in command):
        raise ValueError("ADAPTER_COMMAND_REQUIRED")
    return canonical_digest(list(command))


def _normalize_arms(arms: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not arms:
        raise ValueError("AT_LEAST_ONE_BLINDED_ARM_REQUIRED")
    normalized_arms: list[dict[str, str]] = []
    seen_labels: set[str] = set()
    for raw in arms:
        if not isinstance(raw, dict):
            raise ValueError("ARM_MUST_BE_OBJECT")
        if "condition_name" in raw or "treatment" in raw:
            raise ValueError("UNBLINDED_CONDITION_FIELD_FORBIDDEN")
        blinded_label = str(raw.get("blinded_label", "")).strip()
        adapter_generation = str(raw.get("adapter_generation", "")).strip()
        adapter_command_digest = str(raw.get("adapter_command_digest", "")).strip().lower()
        condition_commitment = str(raw.get("condition_commitment", "")).strip().lower()
        if not blinded_label:
            raise ValueError("BLINDED_LABEL_REQUIRED")
        if blinded_label in seen_labels:
            raise ValueError("DUPLICATE_BLINDED_LABEL")
        if not adapter_generation:
            raise ValueError("ADAPTER_GENERATION_REQUIRED")
        if not _SHA256_RE.fullmatch(adapter_command_digest):
            raise ValueError("ADAPTER_COMMAND_DIGEST_MUST_BE_SHA256")
        if not _SHA256_RE.fullmatch(condition_commitment):
            raise ValueError("CONDITION_COMMITMENT_MUST_BE_SHA256")
        seen_labels.add(blinded_label)
        normalized_arms.append(
            {
                "blinded_label": blinded_label,
                "adapter_generation": adapter_generation,
                "adapter_command_digest": adapter_command_digest,
                "condition_commitment": condition_commitment,
            }
        )
    normalized_arms.sort(key=lambda arm: arm["blinded_label"])
    return normalized_arms


def build_preregistration(
    *,
    campaign_id: str,
    rounds: int,
    seed: int,
    timeout_seconds: float,
    arms: list[dict[str, Any]],
    startup_timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    if not isinstance(campaign_id, str) or not campaign_id.strip():
        raise ValueError("CAMPAIGN_ID_REQUIRED")
    if rounds < 4:
        raise ValueError("ROUNDS_MUST_BE_AT_LEAST_4")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("SEED_MUST_BE_INTEGER")
    if timeout_seconds <= 0:
        raise ValueError("TIMEOUT_SECONDS_MUST_BE_POSITIVE")
    if startup_timeout_seconds <= 0:
        raise ValueError("STARTUP_TIMEOUT_SECONDS_MUST_BE_POSITIVE")

    normalized_arms = _normalize_arms(arms)
    workload = build_workload(rounds, seed=seed)
    manifest = {
        "schema_id": SCHEMA_ID,
        "benchmark_schema_id": BENCHMARK_SCHEMA_ID,
        "campaign_id": campaign_id.strip(),
        "claim_ceiling": "PREREGISTRATION_ONLY_NO_COMPARATIVE_RESULT",
        "semantic_k27_coordinate": "UNRESOLVED_CANONICAL_RESOLVER_REQUIRED",
        "cache_or_index_hit_is_evidence": False,
        "rounds": rounds,
        "seed": seed,
        "startup_timeout_seconds": float(startup_timeout_seconds),
        "timeout_seconds": float(timeout_seconds),
        "workload_digest": canonical_digest(workload),
        "arms": normalized_arms,
    }
    manifest["preregistration_digest"] = canonical_digest(manifest)
    return manifest


def validate_preregistration(manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, dict) or manifest.get("schema_id") != SCHEMA_ID:
        raise ValueError("INVALID_PREREGISTRATION_SCHEMA")
    observed_digest = manifest.get("preregistration_digest")
    if not isinstance(observed_digest, str) or not _SHA256_RE.fullmatch(observed_digest):
        raise ValueError("INVALID_PREREGISTRATION_DIGEST")
    unsigned = dict(manifest)
    del unsigned["preregistration_digest"]
    if canonical_digest(unsigned) != observed_digest:
        raise ValueError("PREREGISTRATION_DIGEST_MISMATCH")
    if manifest.get("benchmark_schema_id") != BENCHMARK_SCHEMA_ID:
        raise ValueError("INVALID_BENCHMARK_SCHEMA")
    if manifest.get("claim_ceiling") != "PREREGISTRATION_ONLY_NO_COMPARATIVE_RESULT":
        raise ValueError("INVALID_PREREGISTRATION_CLAIM_CEILING")
    if manifest.get("semantic_k27_coordinate") != "UNRESOLVED_CANONICAL_RESOLVER_REQUIRED":
        raise ValueError("SEMANTIC_K27_MUST_REMAIN_UNRESOLVED")
    if manifest.get("cache_or_index_hit_is_evidence") is not False:
        raise ValueError("CACHE_INDEX_CANNOT_BE_EVIDENCE")

    rounds = manifest.get("rounds")
    seed = manifest.get("seed")
    startup_timeout = manifest.get("startup_timeout_seconds")
    turn_timeout = manifest.get("timeout_seconds")
    if not isinstance(rounds, int) or isinstance(rounds, bool) or rounds < 4:
        raise ValueError("INVALID_ROUNDS")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("INVALID_SEED")
    if not isinstance(startup_timeout, (int, float)) or isinstance(startup_timeout, bool) or startup_timeout <= 0:
        raise ValueError("INVALID_STARTUP_TIMEOUT")
    if not isinstance(turn_timeout, (int, float)) or isinstance(turn_timeout, bool) or turn_timeout <= 0:
        raise ValueError("INVALID_TURN_TIMEOUT")

    normalized_arms = _normalize_arms(manifest.get("arms"))
    if normalized_arms != manifest.get("arms"):
        raise ValueError("NONCANONICAL_ARM_ORDER_OR_VALUES")
    expected_workload_digest = canonical_digest(build_workload(rounds, seed=seed))
    if manifest.get("workload_digest") != expected_workload_digest:
        raise ValueError("WORKLOAD_DIGEST_MISMATCH")
    return manifest


def get_preregistered_arm(manifest: dict[str, Any], blinded_label: str) -> dict[str, str]:
    validated = validate_preregistration(manifest)
    for arm in validated["arms"]:
        if arm["blinded_label"] == blinded_label:
            return arm
    raise ValueError("UNREGISTERED_BLINDED_LABEL")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a blinded, frozen long-horizon comparison preregistration.")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--rounds", type=int, default=25)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--startup-timeout-seconds", type=float, default=10.0)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--arms-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    arms = json.loads(args.arms_json.read_text(encoding="utf-8"))
    if not isinstance(arms, list):
        raise ValueError("ARMS_JSON_MUST_BE_ARRAY")
    manifest = build_preregistration(
        campaign_id=args.campaign_id,
        rounds=args.rounds,
        seed=args.seed,
        startup_timeout_seconds=args.startup_timeout_seconds,
        timeout_seconds=args.timeout_seconds,
        arms=arms,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
