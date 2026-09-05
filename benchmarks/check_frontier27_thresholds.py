from __future__ import annotations

import json
import math
import os
import sys
from typing import Any

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "benchmarks"))
from benchmark_frontier27 import resolve_source_head, verify_proof_receipt

THRESHOLDS = {
    "offload_transfer_bytes_reduction": 0.85,
    "offload_estimated_transfer_time_reduction": 0.85,
    "offload_estimated_energy_reduction": 0.85,
    "retrieval_candidate_reduction": 0.99,
    "selective_reproof_reduction": 0.95,
    "snapshot_retention_reduction": 0.95,
    "security_false_admission_reduction": 1.0,
}


def _finite_number(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _int_count(value: object) -> bool:
    return type(value) is int


def validate_result(result: dict[str, Any], expected_source_head: str | None = None) -> list[tuple[str, Any, Any]]:
    """Validate deterministic floors plus the source-bound proof receipt."""
    fail: list[tuple[str, Any, Any]] = []
    gains = result.get("gains")
    if not isinstance(gains, dict):
        return [("gains", gains, "mapping")]

    for key, minimum in THRESHOLDS.items():
        got = gains.get(key)
        if not _finite_number(got) or got + 1e-12 < minimum:
            fail.append((key, got, minimum))

    try:
        quality = result["retrieval"]["quality"]
        recall = quality["recall"]
        false_negatives = quality["false_negatives"]
    except (KeyError, TypeError):
        recall = None
        false_negatives = None
    if not _finite_number(recall) or recall + 1e-12 < 1.0:
        fail.append(("retrieval_recall", recall, 1.0))
    if not _int_count(false_negatives) or false_negatives != 0:
        fail.append(("retrieval_false_negatives", false_negatives, 0))

    try:
        prefetch_transfers = result["offload"]["after"].get("prefetch_transfers", 0)
    except (KeyError, TypeError, AttributeError):
        prefetch_transfers = 0
    if not _int_count(prefetch_transfers) or prefetch_transfers <= 0:
        fail.append(("prefetch_transfers", prefetch_transfers, ">0"))

    audit = result.get("audit") if isinstance(result.get("audit"), dict) else {}
    after_false_admits = audit.get("after_false_admits")
    valid_rejected = audit.get("valid_rejected")
    if not _int_count(after_false_admits) or after_false_admits != 0:
        fail.append(("security_after_false_admits", after_false_admits, 0))
    if not _int_count(valid_rejected) or valid_rejected != 0:
        fail.append(("security_valid_rejected", valid_rejected, 0))

    receipt_ok, receipt_errors = verify_proof_receipt(result, expected_source_head)
    if not receipt_ok:
        for error in receipt_errors:
            fail.append(("proof_receipt", error, "valid exact-bound receipt"))
    return fail


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    path = args[0] if args else "benchmark_result.json"
    with open(path, encoding="utf-8") as handle:
        result = json.load(handle)
    configured_expected = os.environ.get("FRONTIER27_EXPECTED_SOURCE_HEAD")
    expected_source_head = resolve_source_head(configured_expected)
    fail = validate_result(result, expected_source_head)
    if fail:
        for key, got, want in fail:
            print(f"FAIL {key}: {got} does not satisfy {want}")
        raise SystemExit(1)

    print("Frontier-27 deterministic thresholds + proof receipt PASS")
    gains = result["gains"]
    for key, minimum in THRESHOLDS.items():
        print(f"{key}={gains[key]:.6f} threshold={minimum:.6f}")
    print(f"retrieval_recall={result['retrieval']['quality']['recall']:.6f} threshold=1.000000")
    print(f"prefetch_transfers={result['offload']['after']['prefetch_transfers']} threshold=>0")
    print(f"security_after_false_admits={result['audit']['after_false_admits']} threshold=0")
    print(f"security_valid_rejected={result['audit']['valid_rejected']} threshold=0")
    print(f"proof_receipt={result['proof_receipt']['receipt_digest']}")
    print(f"proof_source_head={result['proof_receipt']['source_head']}")


if __name__ == "__main__":
    main()
