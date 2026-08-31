#!/usr/bin/env python3
"""Bind the K27 SIMD microbenchmark to the exact PR654 HyperScale owner.

This adapter intentionally creates no competing HyperScale implementation. It
loads the exact PR654 module supplied by the caller, then asks whether the
smallest read-only evidence observation is worth executing as VERIFICATION.
The result is admission only; the C++ benchmark is the separate observation.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
from dataclasses import asdict

PR654_EXACT_HEAD = "26e377fe543b8c1906832b8c1e968dfe63480005"
PR654_SOURCE_BLOB = "0b6a53612d4d2d9993da49180cfc74d5f4996548"
PR654_RUN = 33375530171


def load_owner(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location("aura_pr654_hyperscale_owner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("PR654_OWNER_LOAD_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: thinkpad_simd_benchmark_admission.py <exact-pr654-tool.py>")
    owner = load_owner(pathlib.Path(sys.argv[1]))

    unresolved = (
        "EXACT_PR608_BACKEND_IDENTITY",
        "HOSTED_RUNNER_HOST_IDENTITY",
        "HOSTED_RUNNER_REPEATED_COMPUTE_TIMING",
        "MATCHED_1024BIT_WORKLOAD_IDENTITY",
    )
    observations = (
        owner.EvidenceObservation(
            observation_id="matched-hosted-simd-compute-benchmark",
            covers=unresolved,
            cost_score=1,
            byte_cost=0,
        ),
        owner.EvidenceObservation(
            observation_id="combined-storage-plus-compute-sweep",
            covers=unresolved,
            cost_score=8,
            byte_cost=0,
        ),
        owner.EvidenceObservation(
            observation_id="broad-host-profiler",
            covers=unresolved,
            cost_score=5,
            byte_cost=0,
        ),
    )
    receipt = owner.admit_work(
        semantic_disposition=owner.SUPPORT_MERGE,
        hard_gates_pass=True,
        unresolved_leaves=unresolved,
        observations=observations,
        verification_benefit_score=2,
    )

    assert receipt.admitted is True
    assert receipt.mode == owner.MODE_VERIFICATION
    assert receipt.selected_observation_ids == ("matched-hosted-simd-compute-benchmark",)
    assert receipt.selected_cost_score == 1
    assert receipt.eligible_to_add_new_egk is True
    assert receipt.eligible_to_seek_new_sck is False
    assert receipt.verification_inflates_semantic_mass is False
    assert receipt.automatic_effect_execution is False
    assert receipt.native_private_transformer_kv_accessed is False
    assert receipt.gate10_promoted is False

    body = asdict(receipt)
    body.update(
        {
            "receipt_digest": receipt.receipt_digest,
            "pr654_exact_head": PR654_EXACT_HEAD,
            "pr654_source_blob": PR654_SOURCE_BLOB,
            "pr654_run": PR654_RUN,
            "benchmark_result_not_yet_implied_by_admission": True,
            "owner_thinkpad_host_required_for_thinkpad_claim": True,
            "laws": [
                "VerificationAdmission!=VerificationResult",
                "MinimumEvidenceConeBeforeHyperScaleFanout",
                "HostedRunnerTiming!=OwnerThinkPadTiming",
                "ComputeBenchmark!=StorageMmapBenchmark",
                "FreshEGK!=FreshSemanticSibling",
                "K27Coordinate!=SemanticAuthority",
            ],
        }
    )
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
