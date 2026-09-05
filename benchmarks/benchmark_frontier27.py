from __future__ import annotations

import json
import os
import random
import re
import subprocess
import sys
import time
from typing import Any

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "tools", "arena"))
from frontier27_runtime import *

SEED = 2701000
BENCHMARK_SCHEMA = "AURA-FRONTIER27-BENCH-v2"
PROOF_RECEIPT_SCHEMA = "AURA-FRONTIER27-PROOF-RECEIPT-v1"

ROUTE_STEPS = 3000
ROUTE_EXPERTS = 96
ROUTE_K = 4
ROUTE_HOT_EXPERTS = 16
RETRIEVAL_RECORDS = 10000
RETRIEVAL_QUERIES = 500
RETRIEVAL_PREFIX_BITS = 10
RETRIEVAL_MAX_HAMMING = 24
EXPERT_SIZE_BYTES = 8 * 1024 * 1024
TIER_BANDWIDTH_BYTES_S = 1_200_000_000
TIER_JOULES_PER_GB = 2.4
TIER_CAPACITY_EXPERTS = 10_000
FRONTIER_CAPACITY = 24
PREFETCH_WINDOW_S = 0.010
PREFETCH_ENERGY_BUDGET_J = 0.1
CURRENTNESS_NODES = 20_000
CURRENTNESS_DEPENDENCY_CARDINALITY = 200
CURRENTNESS_INVALIDATED = "D17"
SNAPSHOT_INPUTS = 10_000
SNAPSHOT_CAPACITY = 128
SECURITY_CASES = 1000

BENCHMARK_INPUTS = {
    "schema": BENCHMARK_SCHEMA,
    "seed": SEED,
    "routes": {
        "steps": ROUTE_STEPS,
        "experts": ROUTE_EXPERTS,
        "k": ROUTE_K,
        "hot_experts": ROUTE_HOT_EXPERTS,
    },
    "retrieval": {
        "records": RETRIEVAL_RECORDS,
        "queries": RETRIEVAL_QUERIES,
        "prefix_bits": RETRIEVAL_PREFIX_BITS,
        "max_hamming": RETRIEVAL_MAX_HAMMING,
    },
    "offload": {
        "expert_size_bytes": EXPERT_SIZE_BYTES,
        "tier_capacity_experts": TIER_CAPACITY_EXPERTS,
        "tier_bandwidth_bytes_s": TIER_BANDWIDTH_BYTES_S,
        "tier_joules_per_gb": "2.4",
        "frontier_capacity": FRONTIER_CAPACITY,
        "prefetch_window_us": 10_000,
        "prefetch_energy_budget_millijoules": 100,
        "after_time_model": "serialized_all_transfers",
    },
    "currentness": {
        "nodes": CURRENTNESS_NODES,
        "dependency_cardinality": CURRENTNESS_DEPENDENCY_CARDINALITY,
        "invalidated_dependency": CURRENTNESS_INVALIDATED,
    },
    "snapshots": {"inputs": SNAPSHOT_INPUTS, "capacity": SNAPSHOT_CAPACITY},
    "security_cases": SECURITY_CASES,
}

DETERMINISTIC_GAIN_KEYS = (
    "offload_transfer_bytes_reduction",
    "offload_estimated_transfer_time_reduction",
    "offload_estimated_energy_reduction",
    "retrieval_candidate_reduction",
    "selective_reproof_reduction",
    "snapshot_retention_reduction",
    "security_false_admission_reduction",
)


def _valid_source_head(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", value) is not None


def _observed_git_head() -> str | None:
    """Return the checked-out Git HEAD, or None when Git metadata is unavailable."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    observed = completed.stdout.strip()
    if not _valid_source_head(observed):
        raise RuntimeError("git rev-parse HEAD did not return a canonical Git object identity")
    return observed


def _tracked_worktree_dirty() -> bool | None:
    """Return tracked-worktree dirtiness, or None when Git metadata is unavailable."""
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return bool(completed.stdout.strip())


def resolve_source_head(configured: str | None = None) -> str:
    """Resolve source identity and reject Git disagreement or tracked dirty state."""
    configured = os.environ.get("FRONTIER27_SOURCE_HEAD") if configured is None else configured
    if configured is not None and not _valid_source_head(configured):
        raise ValueError("FRONTIER27_SOURCE_HEAD must be a 40- or 64-hex Git object identity")

    observed = _observed_git_head()
    if observed is not None:
        dirty = _tracked_worktree_dirty()
        if dirty is None:
            raise RuntimeError("tracked worktree state unavailable for Git-backed source identity")
        if dirty:
            raise RuntimeError("tracked worktree is dirty; exact Git source identity is unavailable")
    if configured is not None:
        if observed is not None and configured != observed:
            raise RuntimeError("configured source identity does not match checked-out Git HEAD")
        return configured
    if observed is None:
        raise RuntimeError("source identity unavailable; set FRONTIER27_SOURCE_HEAD")
    return observed


def routes(steps=ROUTE_STEPS, experts=ROUTE_EXPERTS, k=ROUTE_K):
    r = random.Random(SEED); out = []; pred = []; hot = list(range(ROUTE_HOT_EXPERTS))
    for _ in range(steps):
        x = r.sample(hot, k) if r.random() < 0.82 else r.sample(range(experts), k)
        out.append(x); pred.append([e if r.random() < 0.70 else r.randrange(experts) for e in x])
    return out, pred


def retrieval(n=RETRIEVAL_RECORDS, q=RETRIEVAL_QUERIES):
    records = {f"R{i:05d}": f"family_{i%100} mechanism_{i%27} currentness cache expert route evidence record_{i}" for i in range(n)}
    record_terms = {identity: set(tokens(text)) for identity, text in records.items()}
    rng = random.Random(SEED + 1); qs = [f"family_{rng.randrange(100)} mechanism_{rng.randrange(27)}" for _ in range(q)]

    t = time.perf_counter(); before_exam = 0; expected_by_query = []
    for term in qs:
        wanted_terms = set(tokens(term)); expected = {identity for identity, ts in record_terms.items() if wanted_terms <= ts}
        expected_by_query.append(expected); before_exam += len(records)
    before_s = time.perf_counter() - t

    t = time.perf_counter(); idx = HybridIndexBridge(RETRIEVAL_PREFIX_BITS); cache = HotColdCache(records)
    for identity, text in records.items():
        h = sha256(identity.encode()).digest(); idx.add(identity, text, (h[0] % 27, h[1] % 27, h[2] % 27))
    build = time.perf_counter() - t

    t = time.perf_counter(); after_exam = 0; expected_total = covered_total = 0
    for term, expected in zip(qs, expected_by_query):
        c = idx.candidates(term, RETRIEVAL_MAX_HAMMING); after_exam += len(c); ids = [x[0] for x in c]; got = set(ids)
        expected_total += len(expected); covered_total += len(expected & got)
        for identity in ids: cache.get(identity)
        receipt = RetrievalReceipt.build(term, ids, "g1")
        if not receipt.valid_for(term, ids, "g1"): raise AssertionError("retrieval receipt failed self/context verification")
    after_s = time.perf_counter() - t
    recall = 1.0 if expected_total == 0 else covered_total / expected_total
    return {
        "before": {"wall_s": before_s, "examined": before_exam},
        "after": {"query_wall_s": after_s, "index_build_s": build, "amortized_wall_s": after_s + build, "examined": after_exam, "hot_hits": cache.hits, "hot_misses": cache.misses},
        "quality": {"expected_relevant": expected_total, "covered_relevant": covered_total, "false_negatives": expected_total - covered_total, "recall": recall},
    }


def semantic_projection(result: dict[str, Any]) -> dict[str, Any]:
    """Return only deterministic benchmark consequences; wall-clock observations stay outside the root."""
    return {
        "schema": result["schema"],
        "seed": result["seed"],
        "manifest": result["manifest"],
        "offload": {
            "before": {
                "bytes": result["offload"]["before"]["bytes"],
                "seconds": result["offload"]["before"]["seconds"],
                "energy_j": result["offload"]["before"]["energy_j"],
                "hit_rate": result["offload"]["before"]["hit_rate"],
            },
            "after": {
                "bytes": result["offload"]["after"]["bytes"],
                "seconds": result["offload"]["after"]["seconds"],
                "energy_j": result["offload"]["after"]["energy_j"],
                "hit_rate": result["offload"]["after"]["hit_rate"],
                "prefetch_transfers": result["offload"]["after"]["prefetch_transfers"],
            },
            "after_time_model": result["offload"]["after_time_model"],
        },
        "retrieval": {
            "before_examined": result["retrieval"]["before"]["examined"],
            "after_examined": result["retrieval"]["after"]["examined"],
            "hot_hits": result["retrieval"]["after"]["hot_hits"],
            "hot_misses": result["retrieval"]["after"]["hot_misses"],
            "quality": result["retrieval"]["quality"],
        },
        "currentness": result["currentness"],
        "snapshots": result["snapshots"],
        "audit": result["audit"],
        "gains": {key: result["gains"][key] for key in DETERMINISTIC_GAIN_KEYS},
    }


def build_proof_receipt(result: dict[str, Any], source_head: str) -> dict[str, str]:
    """Bind deterministic result semantics to the benchmark inputs and exact source identity."""
    if not _valid_source_head(source_head):
        raise ValueError("source_head must be a 40- or 64-hex Git object identity")
    input_root = digest(BENCHMARK_INPUTS)
    result_root = digest(semantic_projection(result))
    receipt_digest = digest([PROOF_RECEIPT_SCHEMA, source_head, input_root, result_root])
    return {
        "schema": PROOF_RECEIPT_SCHEMA,
        "source_head": source_head,
        "input_root": input_root,
        "result_root": result_root,
        "receipt_digest": receipt_digest,
        "authority": "D0_NONPROMOTING",
    }


def verify_proof_receipt(result: dict[str, Any], expected_source_head: str | None = None) -> tuple[bool, tuple[str, ...]]:
    """Recompute all proof roots and optionally require an externally observed source head."""
    errors: list[str] = []
    receipt = result.get("proof_receipt")
    if not isinstance(receipt, dict):
        return False, ("missing proof_receipt",)
    if receipt.get("schema") != PROOF_RECEIPT_SCHEMA:
        errors.append("proof schema mismatch")
    if result.get("schema") != BENCHMARK_SCHEMA:
        errors.append("benchmark schema mismatch")
    manifest = result.get("manifest")
    if not isinstance(manifest, (list, tuple)) or tuple(manifest) != FRONTIER_27:
        errors.append("benchmark manifest mismatch")
    source_head = receipt.get("source_head")
    if not _valid_source_head(source_head):
        errors.append("invalid proof source_head")
    if expected_source_head is not None:
        if not _valid_source_head(expected_source_head):
            errors.append("invalid expected source head")
        elif source_head != expected_source_head:
            errors.append("proof source_head does not match expected source head")
    expected_input_root = digest(BENCHMARK_INPUTS)
    if receipt.get("input_root") != expected_input_root:
        errors.append("proof input_root mismatch")
    try:
        expected_result_root = digest(semantic_projection(result))
    except (KeyError, TypeError, ValueError):
        errors.append("proof semantic projection is malformed")
        expected_result_root = None
    if expected_result_root is not None and receipt.get("result_root") != expected_result_root:
        errors.append("proof result_root mismatch")
    if _valid_source_head(source_head) and expected_result_root is not None:
        expected_receipt_digest = digest([
            PROOF_RECEIPT_SCHEMA,
            source_head,
            expected_input_root,
            expected_result_root,
        ])
        if receipt.get("receipt_digest") != expected_receipt_digest:
            errors.append("proof receipt_digest mismatch")
    if receipt.get("authority") != "D0_NONPROMOTING":
        errors.append("proof authority ceiling mismatch")
    return not errors, tuple(errors)


def run_campaign(source_head: str | None = None) -> dict[str, Any]:
    rs, ps = routes(); size = EXPERT_SIZE_BYTES; tier = StorageTier(
        "ssd",
        TIER_CAPACITY_EXPERTS * size,
        TIER_BANDWIDTH_BYTES_S,
        TIER_JOULES_PER_GB,
    )
    # A 10 ms synthetic window admits at least one 8 MiB expert at 1.2 GB/s,
    # so the proof actually exercises prefetch while still charging serialized transfer time.
    b = LegacyOffload(size, TIER_BANDWIDTH_BYTES_S, TIER_JOULES_PER_GB).run(rs, ps)
    a = FrontierOffload(size, FRONTIER_CAPACITY, tier, PREFETCH_WINDOW_S, PREFETCH_ENERGY_BUDGET_J).run(rs, ps)
    inv = CurrentnessInvalidator(); nodes = CURRENTNESS_NODES
    for i in range(nodes):
        inv.bind(f"N{i}", [f"D{i%CURRENTNESS_DEPENDENCY_CARDINALITY}", f"D{(i*7)%CURRENTNESS_DEPENDENCY_CARDINALITY}"])
    affected = inv.invalidate([CURRENTNESS_INVALIDATED]); ring = SnapshotRing(SNAPSHOT_CAPACITY)
    for i in range(SNAPSHOT_INPUTS): ring.append(i, {"i": i})
    ret = retrieval(); audit = security_campaign(SECURITY_CASES); red = lambda x, y: (x - y) / x
    out: dict[str, Any] = {
        "schema": BENCHMARK_SCHEMA,
        "seed": SEED,
        "manifest": FRONTIER_27,
        "offload": {"before": b, "after": a, "after_time_model": "serialized_all_transfers"},
        "retrieval": ret,
        "currentness": {"before": nodes, "after": len(affected)},
        "snapshots": {"before": SNAPSHOT_INPUTS, "after": len(ring)},
        "audit": audit,
    }
    out["gains"] = {
        "offload_transfer_bytes_reduction": red(b["bytes"], a["bytes"]),
        "offload_estimated_transfer_time_reduction": red(b["seconds"], a["seconds"]),
        "offload_estimated_energy_reduction": red(b["energy_j"], a["energy_j"]),
        "retrieval_candidate_reduction": red(ret["before"]["examined"], ret["after"]["examined"]),
        "retrieval_query_wall_time_reduction": red(ret["before"]["wall_s"], ret["after"]["query_wall_s"]),
        "retrieval_amortized_wall_time_reduction": red(ret["before"]["wall_s"], ret["after"]["amortized_wall_s"]),
        "selective_reproof_reduction": red(nodes, len(affected)),
        "snapshot_retention_reduction": red(SNAPSHOT_INPUTS, len(ring)),
        "security_false_admission_reduction": audit["false_admission_reduction"],
    }
    out["proof_receipt"] = build_proof_receipt(out, resolve_source_head(source_head))
    return out


def main() -> None:
    print(json.dumps(run_campaign(), indent=2, sort_keys=True))


if __name__ == "__main__": main()
